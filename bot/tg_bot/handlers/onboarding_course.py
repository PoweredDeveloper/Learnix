"""Learning-style onboarding (/learn for new users) and personalized course creation (/course)."""

import html
from io import BytesIO

from aiogram import Bot, F, Router, types
from aiogram.enums import ChatAction, ParseMode
from aiogram.filters import BaseFilter, Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from tg_bot.bot_common import backend_client
from tg_bot.web_menu import refresh_web_menu

router = Router()


class _OnboardingOrCourseFilter(BaseFilter):
    async def __call__(self, _: types.Message, state: FSMContext) -> bool:
        cur = await state.get_state()
        return bool(cur and ("OnboardingStates" in cur or "CourseStates" in cur))


class OnboardingStates(StatesGroup):
    q1 = State()
    q2 = State()
    q3 = State()
    q4 = State()
    q5_notes = State()


class CourseStates(StatesGroup):
    awaiting_content = State()


def _kb_q1() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="15–25 min", callback_data="ob:1:short"),
                InlineKeyboardButton(text="45–60 min", callback_data="ob:1:medium"),
            ],
            [InlineKeyboardButton(text="90+ min", callback_data="ob:1:long")],
        ]
    )


def _kb_after_course() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Today's plan", callback_data="menu:plan"),
                InlineKeyboardButton(text="Start study", callback_data="menu:learn"),
            ]
        ]
    )


def _kb_q2() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🌅 Morning", callback_data="ob:2:morning"),
                InlineKeyboardButton(text="☀️ Afternoon", callback_data="ob:2:afternoon"),
            ],
            [
                InlineKeyboardButton(text="🌙 Evening", callback_data="ob:2:evening"),
                InlineKeyboardButton(text="🔄 Flexible", callback_data="ob:2:flexible"),
            ],
        ]
    )


def _kb_q3() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Practice & examples", callback_data="ob:3:practice")],
            [InlineKeyboardButton(text="Reading & notes", callback_data="ob:3:reading")],
            [InlineKeyboardButton(text="Visuals & diagrams", callback_data="ob:3:visual")],
            [InlineKeyboardButton(text="A mix", callback_data="ob:3:mixed")],
        ]
    )


def _kb_q4() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Quick overview first", callback_data="ob:4:overview")],
            [InlineKeyboardButton(text="Steady, balanced depth", callback_data="ob:4:steady")],
            [InlineKeyboardButton(text="Deep dives", callback_data="ob:4:deep")],
        ]
    )


def _kb_q5_skip() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="Skip", callback_data="ob:5:skip")]]
    )


def _kb_create_course() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📚 Create a course", callback_data="cr:open")],
        ]
    )


async def begin_onboarding(message: types.Message, state: FSMContext) -> None:
    await state.set_state(OnboardingStates.q1)
    await state.update_data(answers={})
    await message.answer(
        "Before we study together, a few quick questions about <b>how you learn</b> "
        "(about 1 minute).\n\n"
        "<b>1/5</b> — How long do you usually like to focus in one sitting?",
        parse_mode=ParseMode.HTML,
        reply_markup=_kb_q1(),
    )


async def _finish_onboarding(
    message: types.Message,
    state: FSMContext,
    answers: dict[str, str],
    *,
    acting_user_id: int | None = None,
    acting_display_name: str | None = None,
) -> None:
    # Callback flows pass query.message (owned by the bot) — message.from_user is the bot, not the learner.
    uid = acting_user_id if acting_user_id is not None else message.from_user.id
    display = (
        acting_display_name
        if acting_display_name is not None
        else (message.from_user.full_name if message.from_user else None)
    )
    api = backend_client(uid)
    try:
        await api.ensure_user(display)
        await api.complete_onboarding(answers)
    except Exception as e:
        await message.answer(f"Could not save your answers: {e}")
        return
    await state.clear()
    await message.answer(
        "Thanks — I’ll tailor explanations and pacing using that.\n\n"
        "Next, <b>create a course</b>: send a topic you want to learn, or upload slides/notes "
        "(PDF or .txt). Use /course when you’re ready.",
        parse_mode=ParseMode.HTML,
        reply_markup=_kb_create_course(),
    )
    await refresh_web_menu(message.bot, uid)


@router.callback_query(StateFilter(OnboardingStates.q1), F.data.startswith("ob:1:"))
async def onb_q1(query: types.CallbackQuery, state: FSMContext) -> None:
    val = query.data.split(":", 2)[2]
    data = await state.get_data()
    answers: dict[str, str] = dict(data.get("answers") or {})
    answers["session_length"] = val
    await state.update_data(answers=answers)
    await state.set_state(OnboardingStates.q2)
    await query.answer()
    if query.message:
        await query.message.edit_text(
            "<b>2/5</b> — When do you usually focus best?",
            parse_mode=ParseMode.HTML,
            reply_markup=_kb_q2(),
        )


@router.callback_query(StateFilter(OnboardingStates.q2), F.data.startswith("ob:2:"))
async def onb_q2(query: types.CallbackQuery, state: FSMContext) -> None:
    val = query.data.split(":", 2)[2]
    data = await state.get_data()
    answers: dict[str, str] = dict(data.get("answers") or {})
    answers["preferred_time"] = val
    await state.update_data(answers=answers)
    await state.set_state(OnboardingStates.q3)
    await query.answer()
    if query.message:
        await query.message.edit_text(
            "<b>3/5</b> — What tends to help you learn new material most?",
            parse_mode=ParseMode.HTML,
            reply_markup=_kb_q3(),
        )


@router.callback_query(StateFilter(OnboardingStates.q3), F.data.startswith("ob:3:"))
async def onb_q3(query: types.CallbackQuery, state: FSMContext) -> None:
    val = query.data.split(":", 2)[2]
    data = await state.get_data()
    answers: dict[str, str] = dict(data.get("answers") or {})
    answers["learning_style"] = val
    await state.update_data(answers=answers)
    await state.set_state(OnboardingStates.q4)
    await query.answer()
    if query.message:
        await query.message.edit_text(
            "<b>4/5</b> — What pace do you prefer when covering a new topic?",
            parse_mode=ParseMode.HTML,
            reply_markup=_kb_q4(),
        )


@router.callback_query(StateFilter(OnboardingStates.q4), F.data.startswith("ob:4:"))
async def onb_q4(query: types.CallbackQuery, state: FSMContext) -> None:
    val = query.data.split(":", 2)[2]
    data = await state.get_data()
    answers: dict[str, str] = dict(data.get("answers") or {})
    answers["pace"] = val
    await state.update_data(answers=answers)
    await state.set_state(OnboardingStates.q5_notes)
    await query.answer()
    if query.message:
        await query.message.edit_text(
            "<b>5/5</b> — Anything else I should know? (goals, constraints, exam date…)\n"
            "Send a message, or tap <b>Skip</b>.",
            parse_mode=ParseMode.HTML,
            reply_markup=_kb_q5_skip(),
        )


@router.callback_query(StateFilter(OnboardingStates.q5_notes), F.data == "ob:5:skip")
async def onb_q5_skip(query: types.CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    answers: dict[str, str] = dict(data.get("answers") or {})
    await query.answer()
    if query.message and query.from_user:
        await query.message.edit_reply_markup(reply_markup=None)
        await _finish_onboarding(
            query.message,
            state,
            answers,
            acting_user_id=query.from_user.id,
            acting_display_name=query.from_user.full_name,
        )


@router.message(StateFilter(OnboardingStates.q5_notes), F.text)
async def onb_q5_text(message: types.Message, state: FSMContext) -> None:
    if message.text and message.text.startswith("/"):
        return
    data = await state.get_data()
    answers: dict[str, str] = dict(data.get("answers") or {})
    answers["notes"] = (message.text or "").strip()[:2000]
    await _finish_onboarding(message, state, answers)


@router.message(Command("cancel"), _OnboardingOrCourseFilter())
async def cmd_cancel(message: types.Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Cancelled.")


async def start_course_flow(
    message: types.Message,
    state: FSMContext,
    *,
    acting_user_id: int | None = None,
    acting_display_name: str | None = None,
) -> None:
    """Open create-course flow (same as /course). Pass acting_* when message is from a callback (bot-owned)."""
    uid = acting_user_id if acting_user_id is not None else message.from_user.id
    display = acting_display_name if acting_display_name is not None else message.from_user.full_name
    api = backend_client(uid)
    await api.ensure_user(display)
    try:
        me = await api.get_me()
    except Exception as e:
        await message.answer(f"Could not load profile: {e}")
        return
    if not me.get("onboarding_completed"):
        await message.answer(
            "Finish onboarding first — tap <b>Study</b> in the menu.",
            parse_mode=ParseMode.HTML,
        )
        return
    await state.set_state(CourseStates.awaiting_content)
    await message.answer(
        "<b>Create a course</b>\n\n"
        "• Send a <b>topic</b> as text, or upload a <b>PDF / .txt</b>.\n"
        "• Tap <b>Cancel</b> below or use the menu when you want to stop.",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="Cancel", callback_data="course:cancel")]]
        ),
    )


@router.message(Command("course"))
async def cmd_course(message: types.Message, state: FSMContext) -> None:
    await start_course_flow(message, state)


@router.callback_query(F.data == "course:cancel")
async def course_cancel_cb(query: types.CallbackQuery, state: FSMContext) -> None:
    cur = await state.get_state()
    if not cur or "CourseStates" not in cur:
        await query.answer()
        return
    await state.clear()
    await query.answer("Cancelled.")
    if query.message:
        try:
            await query.message.edit_reply_markup(reply_markup=None)
        except Exception:
            pass
        await query.message.answer("Course creation cancelled.")


@router.callback_query(F.data == "cr:open")
async def course_open_cb(query: types.CallbackQuery, state: FSMContext) -> None:
    if not query.from_user or not query.message:
        await query.answer()
        return
    api = backend_client(query.from_user.id)
    try:
        me = await api.get_me()
    except Exception:
        await query.answer("Could not load profile", show_alert=True)
        return
    if not me.get("onboarding_completed"):
        await query.answer("Finish /learn first", show_alert=True)
        return
    await state.set_state(CourseStates.awaiting_content)
    await query.answer()
    await query.message.answer(
        "<b>Create a course</b>\n\n"
        "Send a <b>topic</b> as text, or upload a <b>PDF / .txt</b> with your material.\n"
        "/cancel to stop.",
        parse_mode=ParseMode.HTML,
    )


@router.message(StateFilter(CourseStates.awaiting_content), F.text)
async def course_theme(message: types.Message, state: FSMContext) -> None:
    if not message.text or message.text.startswith("/"):
        return
    theme = message.text.strip()
    if len(theme) < 2:
        await message.answer("Please send a bit more detail for the topic.")
        return
    api = backend_client(message.from_user.id)
    status_msg = await message.answer("🤔 Building your course and tasks…")
    await message.bot.send_chat_action(message.chat.id, ChatAction.TYPING)
    try:
        res = await api.create_course_theme(theme, days=14)
    except Exception as e:
        await status_msg.edit_text(f"Could not create course: {e}")
        return
    await state.clear()
    n = res.get("task_count", 0)
    name = res.get("subject_name", "Course")
    await status_msg.edit_text(
        f"✅ <b>{html.escape(str(name))}</b> is ready with <b>{n}</b> tasks.\n\n"
        "Great job. What would you like to do next?",
        parse_mode=ParseMode.HTML,
        reply_markup=_kb_after_course(),
    )


@router.message(StateFilter(CourseStates.awaiting_content), F.document)
async def course_document(message: types.Message, state: FSMContext, bot: Bot) -> None:
    doc = message.document
    if not doc or not doc.file_name:
        await message.answer("Please send a file with a name.")
        return
    ext = "." + doc.file_name.rsplit(".", 1)[-1].lower() if "." in doc.file_name else ""
    if ext not in (".pdf", ".txt", ".md"):
        await message.answer(
            "Please upload a <b>PDF</b>, <b>.txt</b>, or <b>.md</b> file.",
            parse_mode=ParseMode.HTML,
        )
        return
    max_bytes = 20 * 1024 * 1024
    if (doc.file_size or 0) > max_bytes:
        await message.answer("File is too large (max 20 MB).")
        return
    status_msg = await message.answer("🤔 Reading your file and building tasks…")
    await message.bot.send_chat_action(message.chat.id, ChatAction.TYPING)
    bio = BytesIO()
    await bot.download(doc, destination=bio)
    raw = bio.getvalue()
    api = backend_client(message.from_user.id)
    subj = doc.file_name.rsplit(".", 1)[0][:200] or "My course"
    try:
        res = await api.create_course_file(doc.file_name, raw, days=14, subject_name=subj)
    except Exception as e:
        await status_msg.edit_text(f"Could not create course: {e}")
        return
    await state.clear()
    n = res.get("task_count", 0)
    name = res.get("subject_name", "Course")
    chars = res.get("extracted_chars", 0)
    await status_msg.edit_text(
        f"✅ <b>{html.escape(str(name))}</b> from your file — <b>{n}</b> tasks "
        f"({chars} characters read).\n\nWhat would you like to do next?",
        parse_mode=ParseMode.HTML,
        reply_markup=_kb_after_course(),
    )
