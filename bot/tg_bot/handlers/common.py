from uuid import UUID

from aiogram import F, Router, types
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from tg_bot.api_client import BackendClient
from tg_bot.config import get_settings
from tg_bot.keyboards.learn import learn_controls

router = Router()


class LearnStates(StatesGroup):
    in_session = State()


def _client(user_id: int) -> BackendClient:
    s = get_settings()
    return BackendClient(s.api_base_url, s.api_secret, user_id)


@router.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext) -> None:
    await state.clear()
    uid = message.from_user.id
    api = _client(uid)
    await api.ensure_user(message.from_user.full_name)
    await message.answer(
        "👋 **Smart Study Assistant**\n\n"
        "Commands:\n"
        "• /learn — guided session (explain → tasks → you answer)\n"
        "• /plan — today's tasks\n"
        "• /streak — streak & daily progress\n"
        "• /done — end learn session",
        parse_mode="Markdown",
    )


@router.message(Command("learn"))
async def cmd_learn(message: types.Message, state: FSMContext, command: Command) -> None:
    uid = message.from_user.id
    api = _client(uid)
    await api.ensure_user(message.from_user.full_name)
    hint = (command.args or "").strip() or None
    try:
        data = await api.session_start(topic_hint=hint)
    except Exception as e:
        await message.answer(f"Could not start session: {e}")
        return
    sid = UUID(data["session_id"])
    await state.set_state(LearnStates.in_session)
    await state.update_data(session_id=str(sid))
    await message.answer(data["message"], reply_markup=learn_controls())


@router.message(Command("done"))
async def cmd_done(message: types.Message, state: FSMContext) -> None:
    data = await state.get_data()
    sid = data.get("session_id")
    await state.clear()
    if not sid:
        await message.answer("No active session.")
        return
    api = _client(message.from_user.id)
    try:
        await api.session_action(UUID(sid), "end")
    except Exception:
        pass
    await message.answer("Session closed. Nice work! 🎓")


@router.message(Command("plan"))
async def cmd_plan(message: types.Message) -> None:
    api = _client(message.from_user.id)
    await api.ensure_user(message.from_user.full_name)
    try:
        tasks = await api.tasks_today()
    except Exception as e:
        await message.answer(f"Error: {e}")
        return
    if not tasks:
        await message.answer("No tasks due today.")
        return
    lines = ["📅 **Today:**\n"]
    rows: list[list[InlineKeyboardButton]] = []
    for t in tasks:
        lines.append(f"• [{t['status']}] {t['title']} (~{t['estimated_minutes']}m)")
        tid = t["id"]
        rows.append(
            [
                InlineKeyboardButton(text="✅ Done", callback_data=f"p:done:{tid}"),
                InlineKeyboardButton(text="⏭ Skip", callback_data=f"p:skip:{tid}"),
            ]
        )
    await message.answer(
        "\n".join(lines),
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
    )


@router.message(Command("streak"))
async def cmd_streak(message: types.Message) -> None:
    api = _client(message.from_user.id)
    await api.ensure_user(message.from_user.full_name)
    try:
        s = await api.streak()
    except Exception as e:
        await message.answer(f"Error: {e}")
        return
    await message.answer(
        f"🔥 Streak: **{s['streak_current']}** (best {s['streak_best']})\n"
        f"Today: {s['today_completed_minutes']} / {s['today_quota_minutes']} min "
        f"({int(s['progress_ratio'] * 100)}%)\n"
        f"20% goal: {'✅ met' if s['streak_eligible_today'] else '⏳ not yet'}",
        parse_mode="Markdown",
    )


@router.callback_query(F.data.startswith("learn:"))
async def learn_callbacks(query: types.CallbackQuery, state: FSMContext) -> None:
    action = query.data.split(":", 1)[1]
    data = await state.get_data()
    sid = data.get("session_id")
    if not sid:
        await query.answer("No session", show_alert=True)
        return
    api = _client(query.from_user.id)
    try:
        if action == "skip":
            res = await api.session_action(UUID(sid), "skip")
            if query.message:
                await query.message.edit_text(res["message"], reply_markup=learn_controls())
        elif action == "end":
            await api.session_action(UUID(sid), "end")
            await state.clear()
            if query.message:
                await query.message.edit_text("🛑 Session ended.")
    except Exception as e:
        await query.answer(str(e)[:200], show_alert=True)
        return
    await query.answer()


@router.callback_query(F.data.startswith("p:"))
async def plan_callbacks(query: types.CallbackQuery) -> None:
    parts = query.data.split(":")
    if len(parts) < 3:
        await query.answer()
        return
    _, action, task_id = parts[0], parts[1], parts[2]
    api = _client(query.from_user.id)
    try:
        status = "done" if action == "done" else "skipped"
        await api.update_task(UUID(task_id), status)
    except Exception as e:
        await query.answer(str(e)[:120], show_alert=True)
        return
    await query.answer("Updated ✅")
    if query.message:
        cur = query.message.text or ""
        await query.message.edit_text(f"{cur}\n\n→ marked {status}")


@router.message(StateFilter(LearnStates.in_session), F.text)
async def learn_answer(message: types.Message, state: FSMContext) -> None:
    if message.text and message.text.startswith("/"):
        return
    data = await state.get_data()
    sid = data.get("session_id")
    if not sid:
        return
    api = _client(message.from_user.id)
    try:
        res = await api.session_answer(UUID(sid), message.text)
    except Exception as e:
        await message.answer(f"Error: {e}")
        return
    await message.answer(res["message"], reply_markup=learn_controls())
