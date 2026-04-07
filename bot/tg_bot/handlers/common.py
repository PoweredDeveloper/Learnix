import asyncio
import html
import re
from io import BytesIO
from urllib.parse import quote
from uuid import UUID

import httpx
from aiogram import Bot, F, Router, types
from aiogram.enums import ChatAction, ParseMode
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import BufferedInputFile, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto

from tg_bot.api_client import BackendClient
from tg_bot.bot_common import backend_client
from tg_bot.config import get_settings
from tg_bot.handlers.onboarding_course import begin_onboarding, start_course_flow
from tg_bot.keyboards.learn import study_keyboard_for_segment
from tg_bot.web_menu import refresh_web_menu

router = Router()

# Telegram legacy Markdown breaks on URLs with "_" and does not support **bold**; use HTML for formatted text.
TG_CAP = 4096
TG_PHOTO_CAPTION = 1024
# White margin around CodeCogs PNGs (TeX struts are often cropped; PIL padding is reliable).
LATEX_IMAGE_PADDING_PX = 36
LATEX_EXPR_RE = re.compile(r"\\\((.+?)\\\)|\\\[(.+?)\\\]|\$\$(.+?)\$\$", flags=re.DOTALL)
MATHY_LINE_RE = re.compile(r"[=∫√^]|[a-zA-Z]\([a-zA-Z](?:,[a-zA-Z])?\)")
TASK_BLOCK_RE = re.compile(
    r"(?:^|\n)📝\s*(?:\*\*)?(?:Task|Next task|𝗧𝗮𝘀𝗸|𝗡𝗲𝘅𝘁 𝘁𝗮𝘀𝗸):(?:\*\*)?\s*\n(?P<body>.*?)(?=\n\n|$)",
    flags=re.IGNORECASE | re.DOTALL,
)
EXAMPLE_BLOCK_RE = re.compile(
    r"(?:^|\n)📝\s*\*\*Example:\*\*\s*\n(?P<body>.*?)(?=\n\n📝\s*\*\*|\n\n📋|\Z)",
    flags=re.IGNORECASE | re.DOTALL,
)
EXAM_BLOCK_RE = re.compile(
    r"(?:^|\n)📋\s*(?:\*\*)?Exam:(?:\*\*)?\s*\n(?P<body>.*?)(?=\Z)",
    flags=re.IGNORECASE | re.DOTALL,
)


class LearnStates(StatesGroup):
    choosing_course = State()
    in_session = State()


def _subject_label(name: str, max_len: int = 58) -> str:
    n = (name or "Course").strip()
    return n if len(n) <= max_len else n[: max_len - 1] + "…"


async def _start_learn_session(
    message: types.Message,
    state: FSMContext,
    api: BackendClient,
    *,
    topic_hint: str | None = None,
    subject_id: UUID | None = None,
) -> None:
    try:
        data = await api.session_start(topic_hint=topic_hint, subject_id=subject_id)
        sid = UUID(data["session_id"])
    except Exception as e:
        await message.answer(f"Could not start session: {e}")
        return
    await state.set_state(LearnStates.in_session)
    await state.update_data(session_id=str(sid))
    await _deliver_study_turn(message, data["message"], meta=data.get("meta"))


def _https_dashboard_url(open_url: str | None) -> str | None:
    """Telegram rejects http:// for inline keyboard URL buttons; only https:// is allowed."""
    if open_url and open_url.startswith("https://"):
        return open_url
    return None


def _http_dashboard_copy_lines(open_url: str | None) -> list[str]:
    """When dashboard URL is not button-safe, send a plain clickable link line."""
    if not open_url or open_url.startswith("https://"):
        return []
    return [
        "Open your dashboard here:",
        open_url,
    ]


def main_menu_keyboard(open_url: str | None) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = [
        [
            InlineKeyboardButton(text="Study", callback_data="menu:learn"),
            InlineKeyboardButton(text="New course", callback_data="menu:course"),
        ],
        [
            InlineKeyboardButton(text="Today's plan", callback_data="menu:plan"),
            InlineKeyboardButton(text="Streak", callback_data="menu:streak"),
        ],
        [
            InlineKeyboardButton(text="End session", callback_data="menu:done"),
            InlineKeyboardButton(text="Refresh web link", callback_data="menu:web"),
        ],
    ]
    dash = _https_dashboard_url(open_url)
    if dash:
        rows.append([InlineKeyboardButton(text="Open web dashboard", url=dash)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _chunks(text: str, limit: int = TG_CAP) -> list[str]:
    if not text:
        return [""]
    return [text[i : i + limit] for i in range(0, len(text), limit)]


def _ordered_latex_bodies(raw: str) -> tuple[str, list[str]]:
    """Strip example/task/exam LaTeX blocks (in document order) for image rendering."""
    patterns = (EXAMPLE_BLOCK_RE, TASK_BLOCK_RE, EXAM_BLOCK_RE)
    found: list[tuple[int, str]] = []
    for rx in patterns:
        for m in rx.finditer(raw):
            found.append((m.start(), (m.group("body") or "").strip()))
    found.sort(key=lambda x: x[0])
    bodies = [b for _, b in found if b]
    visible = raw
    for rx in patterns:
        visible = rx.sub("", visible)
    visible = re.sub(r"\n{3,}", "\n\n", visible).strip()
    if not visible:
        visible = " "
    return visible, bodies


def _strip_theory_header(text: str) -> str:
    return re.sub(r"^📚\s*\*\*Theory\*\*\s*\n?", "", text, count=1, flags=re.MULTILINE).strip()


def _pill_font(size: int):
    from PIL import ImageFont

    for path in (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/TTF/DejaVuSans.ttf",
        "/usr/share/fonts/dejavu/DejaVuSans.ttf",
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
    ):
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            continue
    return ImageFont.load_default()


def _render_progress_png(meta: dict) -> bytes:
    from PIL import Image, ImageDraw

    W, H = 720, 112
    img = Image.new("RGB", (W, H), (255, 255, 255))
    draw = ImageDraw.Draw(img)
    title = str(meta.get("topic_name") or "Study")[:80]
    sub = str(meta.get("progress_label") or "")
    try:
        frac = float(meta.get("progress_fraction", 0))
    except (TypeError, ValueError):
        frac = 0.0
    frac = max(0.0, min(1.0, frac))
    font = _pill_font(20)
    font_sm = _pill_font(16)
    draw.text((24, 10), title, fill=(25, 25, 25), font=font)
    draw.text((24, 40), sub, fill=(90, 90, 90), font=font_sm)
    bx0, bx1, by0, by1 = 22, W - 22, 74, 98
    draw.rounded_rectangle([bx0, by0, bx1, by1], radius=8, outline=(210, 210, 210), width=2)
    inner = (bx1 - bx0 - 8) * frac
    if inner > 1:
        draw.rounded_rectangle(
            [bx0 + 4, by0 + 4, bx0 + 4 + inner, by1 - 4], radius=6, fill=(70, 130, 220)
        )
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _stack_progress_on_latex(progress_png: bytes, latex_png: bytes | None) -> bytes:
    from PIL import Image

    top = Image.open(BytesIO(progress_png)).convert("RGBA")
    if not latex_png:
        out = BytesIO()
        top.convert("RGB").save(out, format="PNG")
        return out.getvalue()
    bot = Image.open(BytesIO(latex_png)).convert("RGBA")
    gap = 10
    w = max(top.width, bot.width)
    h = top.height + gap + bot.height
    canvas = Image.new("RGBA", (w, h), (255, 255, 255, 255))
    canvas.paste(top, ((w - top.width) // 2, 0), top)
    canvas.paste(bot, ((w - bot.width) // 2, top.height + gap), bot)
    out = BytesIO()
    canvas.convert("RGB").save(out, format="PNG")
    return out.getvalue()


def _stack_latex_pngs_vertical(png_parts: list[bytes], gap: int = 14) -> bytes | None:
    """Concatenate multiple LaTeX renders into a single tall image (centered)."""
    from PIL import Image

    if not png_parts:
        return None
    images = [Image.open(BytesIO(p)).convert("RGBA") for p in png_parts]
    w = max(im.width for im in images)
    h = sum(im.height for im in images) + gap * (len(images) - 1)
    canvas = Image.new("RGBA", (w, h), (255, 255, 255, 255))
    y = 0
    for im in images:
        canvas.paste(im, ((w - im.width) // 2, y), im)
        y += im.height + gap
    out = BytesIO()
    canvas.convert("RGB").save(out, format="PNG")
    return out.getvalue()


def _prepare_study_content(api_message: str) -> tuple[str, list[str]]:
    visible, bodies = _ordered_latex_bodies(api_message)
    rendered = _prettify_study_text(visible)
    return rendered, bodies


_STUDY_CAPTION_OVERFLOW_HINT = "📚 <b>Study text</b> — full text in the next message ⬇️"


def _normalize_study_escapes(text: str) -> str:
    """Models sometimes emit literal backslash-n instead of newlines; fix before parsing."""
    if not text:
        return text
    s = text.replace("\r\n", "\n").replace("\r", "\n")
    s = s.replace("\\n", "\n").replace("\\t", "\t")
    return s


def _plain_text_without_latex_math(text: str) -> str:
    """Remove LaTeX / math markup from prose so formulas only appear in rendered task images."""
    if not text:
        return text
    s = _normalize_study_escapes(text)
    s = re.sub(r"\$\$(?:.|\n)*?\$\$", "", s)
    s = re.sub(r"\\\[(?:.|\n)*?\\\]", "", s)
    s = re.sub(r"\\\((?:.|\n)*?\\\)", "", s)
    s = re.sub(r"\$[^$\n]+\$", "", s)
    s = re.sub(r"\\begin\{[a-zA-Z*]+\}(?:.|\n)*?\\end\{[a-zA-Z*]+\}", "", s)
    # Preserve paragraph breaks; only collapse spaces within a line (old `\s{2,}` nuked newlines).
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in s.split("\n")]
    s = "\n".join(lines)
    s = re.sub(r"\n{3,}", "\n\n", s)
    s = re.sub(r"[ \t]+,", ",", s)
    s = re.sub(r",\s*\.", ".", s)
    s = re.sub(r"\s+\.", ".", s)
    s = re.sub(r"\bsuch as and\b", "and", s, flags=re.IGNORECASE)
    s = re.sub(r"\bidentities such as and\b", "identities and", s, flags=re.IGNORECASE)
    return s.strip()


def _split_plain_for_messages(plain: str, max_len: int = TG_CAP) -> list[str]:
    """Merge paragraphs into Telegram-sized chunks without cutting mid-paragraph when possible."""
    plain = plain.strip()
    if not plain:
        return []
    paras = [p.strip() for p in plain.split("\n\n") if p.strip()]
    if not paras:
        return [plain] if len(plain) <= max_len else _chunks(plain, max_len)
    out: list[str] = []
    buf: list[str] = []
    buf_len = 0
    for p in paras:
        sep = 2 if buf else 0
        if buf_len + sep + len(p) > max_len and buf:
            out.append("\n\n".join(buf))
            buf = [p]
            buf_len = len(p)
        else:
            buf.append(p)
            buf_len += sep + len(p)
    if buf:
        out.append("\n\n".join(buf))
    final: list[str] = []
    for ch in out:
        if len(ch) <= max_len:
            final.append(ch)
        else:
            final.extend(_chunks(ch, max_len))
    return final


def _line_inline_markdown_to_html(line: str) -> str:
    """Telegram HTML: **bold**, *italic*, rest escaped."""
    bold_inner: list[str] = []
    ital_inner: list[str] = []

    def bold_repl(m: re.Match[str]) -> str:
        bold_inner.append(m.group(1))
        return f"\x00B{len(bold_inner) - 1}\x00"

    s = re.sub(r"\*\*(.+?)\*\*", bold_repl, line)

    def ital_repl(m: re.Match[str]) -> str:
        ital_inner.append(m.group(1))
        return f"\x00I{len(ital_inner) - 1}\x00"

    s = re.sub(r"(?<!\*)\*([^*]+?)\*(?!\*)", ital_repl, s)
    s = html.escape(s, quote=False)
    for i, t in enumerate(bold_inner):
        s = s.replace(f"\x00B{i}\x00", "<b>" + html.escape(t, quote=False) + "</b>")
    for i, t in enumerate(ital_inner):
        s = s.replace(f"\x00I{i}\x00", "<i>" + html.escape(t, quote=False) + "</i>")
    return s


def _study_prose_to_html(text: str) -> str:
    """Turn tutor prose into Telegram HTML (** / * only). Telegram HTML has no <br>; use real newlines."""
    text = _normalize_study_escapes(text)
    if not text.strip():
        return ""
    paras = [p.strip() for p in text.split("\n\n")]
    blocks: list[str] = []
    for p in paras:
        if not p:
            continue
        lines = p.split("\n")
        html_lines = [_line_inline_markdown_to_html(L) for L in lines]
        blocks.append("\n".join(html_lines))
    return "\n\n".join(blocks)


def _study_photo_caption_and_followups(caption_plain: str) -> tuple[str, list[str]]:
    """
    Photo caption is limited to TG_PHOTO_CAPTION; overflow is sent as separate HTML messages
    so nothing is truncated with an ellipsis.
    """
    html_full = _study_prose_to_html(caption_plain)
    if not html_full.strip():
        return " ", []
    if len(html_full) <= TG_PHOTO_CAPTION:
        return html_full, []
    parts = _split_plain_for_messages(caption_plain, TG_CAP)
    html_parts = [_study_prose_to_html(p) for p in parts]
    return _STUDY_CAPTION_OVERFLOW_HINT, html_parts


async def _send_study_messages_after_photo(
    message: types.Message,
    follow_html_chunks: list[str],
) -> None:
    for ch in follow_html_chunks:
        await message.answer(ch, parse_mode=ParseMode.HTML)


async def _send_study_text_or_photo(
    message: types.Message,
    *,
    photo_bytes: bytes | None,
    caption_plain: str,
    reply_markup: InlineKeyboardMarkup,
) -> None:
    """Photo + HTML caption (overflow in follow-up messages) or HTML text if photo fails / missing."""
    if caption_plain.strip():
        cap, follow = _study_photo_caption_and_followups(caption_plain)
        if not cap.strip():
            cap = " "
    else:
        cap, follow = " ", []
    if photo_bytes:
        try:
            await message.answer_photo(
                photo=BufferedInputFile(photo_bytes, filename="study.png"),
                caption=cap,
                parse_mode=ParseMode.HTML,
                reply_markup=reply_markup,
            )
            await _send_study_messages_after_photo(message, follow)
            return
        except Exception:
            pass
    if not caption_plain.strip():
        await message.answer(" ", reply_markup=reply_markup)
        return
    parts = _split_plain_for_messages(caption_plain, TG_CAP)
    for i, p in enumerate(parts):
        await message.answer(
            _study_prose_to_html(p),
            parse_mode=ParseMode.HTML,
            reply_markup=reply_markup if i == len(parts) - 1 else None,
        )


def _latex_source_for_codecogs(expr: str) -> str:
    """Normalize task LaTeX for CodeCogs (padding is done in post-process, not in TeX)."""
    s = expr.strip()
    if s.startswith("$$") and s.endswith("$$") and len(s) > 4:
        s = s[2:-2].strip()
    return r"\large\displaystyle " + s


def _latex_image_url(expr: str) -> str:
    body = _latex_source_for_codecogs(expr)
    return f"https://latex.codecogs.com/png.image?\\dpi{{180}}\\bg_white%20{quote(body, safe='')}"


def _pad_png_white_margin(png_bytes: bytes, padding: int = LATEX_IMAGE_PADDING_PX) -> bytes:
    from PIL import Image, ImageOps

    im = Image.open(BytesIO(png_bytes))
    im = im.convert("RGBA")
    out = ImageOps.expand(im, border=padding, fill=(255, 255, 255, 255))
    buf = BytesIO()
    out.save(buf, format="PNG")
    return buf.getvalue()


async def _fetch_latex_png_bytes(expr: str) -> bytes | None:
    url = _latex_image_url(expr)
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.get(url)
            r.raise_for_status()
            raw = r.content
        return await asyncio.to_thread(_pad_png_white_margin, raw)
    except Exception:
        return None


async def _latex_to_png_bytes(expr: str) -> bytes | None:
    """Best-effort PNG bytes for one expression (padded); used to build a single composite image."""
    b = await _fetch_latex_png_bytes(expr)
    if b:
        return b
    url = _latex_image_url(expr)
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.get(url)
            r.raise_for_status()
        return await asyncio.to_thread(_pad_png_white_margin, r.content)
    except Exception:
        return None


async def _compose_study_photo_bytes(meta: dict, exprs_use: list[str]) -> bytes:
    """
    One PNG: progress header + all LaTeX blocks stacked (or progress only if no expressions).
    Note: empty ``meta`` still yields a default progress strip — never use ``if meta:`` on dicts (``{}`` is falsy).
    """
    progress_bytes = await asyncio.to_thread(_render_progress_png, meta)
    if not exprs_use:
        return progress_bytes
    pngs: list[bytes] = []
    for body in exprs_use:
        b = await _latex_to_png_bytes(body)
        if b:
            pngs.append(b)
    if not pngs:
        return progress_bytes
    combined_latex = await asyncio.to_thread(_stack_latex_pngs_vertical, pngs)
    if not combined_latex:
        return progress_bytes
    return await asyncio.to_thread(_stack_progress_on_latex, progress_bytes, combined_latex)


async def _deliver_study_turn(
    message: types.Message,
    api_message: str,
    meta: dict | None = None,
) -> None:
    """Send theory / task / exam: one photo (progress + all LaTeX) + caption; segment-specific keyboard."""
    meta = dict(meta or {})
    seg = meta.get("segment") or "practice"
    kb = study_keyboard_for_segment(seg)
    rendered, bodies = _prepare_study_content(api_message)
    visible = _strip_theory_header(rendered)
    caption_plain = _plain_text_without_latex_math(visible)
    exprs_use = bodies if bodies else _extract_latex_expressions(rendered)

    if not exprs_use:
        try:
            photo_bytes = await _compose_study_photo_bytes(meta, [])
        except Exception:
            photo_bytes = None
        await _send_study_text_or_photo(message, photo_bytes=photo_bytes, caption_plain=caption_plain, reply_markup=kb)
        return

    try:
        photo_bytes = await _compose_study_photo_bytes(meta, exprs_use)
    except Exception:
        photo_bytes = None
    await _send_study_text_or_photo(message, photo_bytes=photo_bytes, caption_plain=caption_plain, reply_markup=kb)


async def _edit_thinking_with_text(
    anchor: types.Message,
    text: str,
    *,
    reply_markup: InlineKeyboardMarkup | None = None,
    meta: dict | None = None,
) -> None:
    meta = dict(meta or {})
    seg = meta.get("segment") or "practice"
    kb = reply_markup or study_keyboard_for_segment(seg)
    rendered, bodies = _prepare_study_content(text)
    visible = _strip_theory_header(rendered)
    caption_plain = _plain_text_without_latex_math(visible)
    exprs_use = bodies if bodies else _extract_latex_expressions(rendered)
    chat_id = anchor.chat.id
    bot = anchor.bot

    try:
        photo_bytes = await _compose_study_photo_bytes(meta, exprs_use)
    except Exception:
        photo_bytes = None

    if caption_plain.strip():
        cap, follow = _study_photo_caption_and_followups(caption_plain)
        if not cap.strip():
            cap = " "
    else:
        cap, follow = " ", []

    if photo_bytes:
        file = BufferedInputFile(photo_bytes, filename="study.png")
        try:
            await anchor.edit_media(
                InputMediaPhoto(
                    media=file,
                    caption=cap,
                    parse_mode=ParseMode.HTML,
                ),
                reply_markup=kb,
            )
        except Exception:
            try:
                await anchor.delete()
            except Exception:
                pass
            await bot.send_photo(
                chat_id=chat_id,
                photo=BufferedInputFile(photo_bytes, filename="study.png"),
                caption=cap,
                parse_mode=ParseMode.HTML,
                reply_markup=kb,
            )
        for ch in follow:
            await bot.send_message(chat_id, ch, parse_mode=ParseMode.HTML)
        return

    if not caption_plain.strip():
        await anchor.edit_text(" ", reply_markup=kb)
        return
    html_full = _study_prose_to_html(caption_plain)
    if len(html_full) <= TG_CAP:
        await anchor.edit_text(html_full, parse_mode=ParseMode.HTML, reply_markup=kb)
        return
    parts = _split_plain_for_messages(caption_plain, TG_CAP)
    first_html = _study_prose_to_html(parts[0])
    await anchor.edit_text(
        first_html,
        parse_mode=ParseMode.HTML,
        reply_markup=kb if len(parts) == 1 else None,
    )
    for j, p in enumerate(parts[1:]):
        await bot.send_message(
            chat_id,
            _study_prose_to_html(p),
            parse_mode=ParseMode.HTML,
            reply_markup=kb if j == len(parts) - 2 else None,
        )


def _prettify_study_text(text: str) -> str:
    """Make task labels visually bold without relying on Markdown parsing."""
    return (
        text.replace("📝 **Task:**", "📝 𝗧𝗮𝘀𝗸:")
        .replace("📝 **Next task:**", "📝 𝗡𝗲𝘅𝘁 𝘁𝗮𝘀𝗸:")
        .replace("**Task:**", "𝗧𝗮𝘀𝗸:")
        .replace("**Next task:**", "𝗡𝗲𝘅𝘁 𝘁𝗮𝘀𝗸:")
        .replace("📋 **Exam:**", "📋 𝗘𝘅𝗮𝗺:")
    )



def _extract_latex_expressions(text: str, limit: int = 24) -> list[str]:
    exprs: list[str] = []
    for m in LATEX_EXPR_RE.finditer(text):
        expr = (m.group(1) or m.group(2) or m.group(3) or "").strip()
        if not expr:
            continue
        exprs.append(expr)
        if len(exprs) >= limit:
            break
    if exprs:
        return exprs
    return _extract_plain_math_expressions(text, limit=limit)


def _extract_plain_math_expressions(text: str, limit: int = 24) -> list[str]:
    exprs: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or len(line) > 220:
            continue
        if not MATHY_LINE_RE.search(line):
            continue
        if line.lower().startswith(("task:", "next task:", "compute ", "find ", "show ")):
            # keep only the mathematical part after '=' if present
            if "=" in line:
                line = line.split("=", 1)[1].strip()
        tex = _to_latexish(line)
        if not tex:
            continue
        exprs.append(tex)
        if len(exprs) >= limit:
            break
    return exprs


def _to_latexish(expr: str) -> str:
    """Convert common unicode/plain math into TeX-like form for preview rendering."""
    s = " ".join(expr.split())
    if not s:
        return ""
    s = s.replace("∫", r"\int ")
    s = s.replace("√", r"\sqrt")
    s = s.replace("≤", r"\le ")
    s = s.replace("≥", r"\ge ")
    s = s.replace("∞", r"\infty ")
    s = s.replace("dx", r"\,dx")
    return s


@router.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext, bot: Bot) -> None:
    await state.clear()
    uid = message.from_user.id
    api = backend_client(uid)
    await api.ensure_user(message.from_user.full_name)
    open_url, menu_ok = await refresh_web_menu(bot, uid)
    lines = [
        "👋 <b>Welcome!</b>",
        "",
        "I can help you study step by step. Tap a button below to start.",
        "If you like typing commands, <code>/learn algebra</code> works too.",
    ]
    base_set = bool((get_settings().web_public_base_url or "").strip())
    if not base_set:
        lines.extend(
            [
                "",
                "Dashboard setup is not ready yet.",
            ]
        )
    elif open_url and not menu_ok:
        if open_url.startswith("http://") and not open_url.startswith("https://"):
            lines.extend(
                [
                    "",
                    "Your dashboard link is ready below.",
                ]
            )
        else:
            lines.extend(["", "I couldn't add the menu web button right now, but your dashboard link is ready below."])
    copy_lines = _http_dashboard_copy_lines(open_url)
    if copy_lines:
        lines.extend(["", *[html.escape(line, quote=False) for line in copy_lines]])
    await message.answer(
        "\n".join(lines),
        parse_mode=ParseMode.HTML,
        reply_markup=main_menu_keyboard(open_url),
    )


@router.message(Command("web"))
async def cmd_web(message: types.Message, bot: Bot) -> None:
    uid = message.from_user.id
    api = backend_client(uid)
    await api.ensure_user(message.from_user.full_name)
    if not (get_settings().web_public_base_url or "").strip():
        await message.answer(
            "Web dashboard is not available right now.",
        )
        return
    open_url, menu_ok = await refresh_web_menu(bot, uid)
    if not open_url:
        await message.answer(
            "I couldn't open the web dashboard right now. Please try again in a moment.",
        )
        return
    parts = [
        "Web session refreshed (valid up to <b>3 days</b>).",
    ]
    if not menu_ok:
        if open_url.startswith("http://") and not open_url.startswith("https://"):
            parts.append("Your dashboard link is ready below.")
        else:
            parts.append("I couldn't set the menu web button this time, but your dashboard link is available below.")
    copy_lines = _http_dashboard_copy_lines(open_url)
    if copy_lines:
        parts.append("\n".join(html.escape(line, quote=False) for line in copy_lines))
    await message.answer(
        "\n\n".join(parts),
        parse_mode=ParseMode.HTML,
        reply_markup=main_menu_keyboard(open_url),
    )


async def run_learn_flow(
    message: types.Message,
    state: FSMContext,
    topic_hint: str | None,
    *,
    acting_user_id: int | None = None,
    acting_display_name: str | None = None,
) -> None:
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
        await begin_onboarding(message, state)
        return

    if topic_hint:
        await _start_learn_session(message, state, api, topic_hint=topic_hint, subject_id=None)
        return

    try:
        subs = await api.list_subjects()
    except Exception as e:
        await message.answer(f"Could not load courses: {e}")
        return

    if not subs:
        await _start_learn_session(message, state, api, topic_hint=None, subject_id=None)
        return

    await state.set_state(LearnStates.choosing_course)
    rows: list[list[InlineKeyboardButton]] = []
    for s in subs:
        sid = s.get("id")
        if not sid:
            continue
        name = _subject_label(str(s.get("name", "Course")))
        rows.append([InlineKeyboardButton(text=name, callback_data=f"learn:pick:{sid}")])
    rows.append([InlineKeyboardButton(text="General (no course)", callback_data="learn:pick:none")])
    await message.answer(
        "Pick a <b>course</b> to study (uses your uploaded material when available), or general practice.\n"
        "Tip: <code>/learn algebra</code> starts a one-off topic without picking a course.",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
    )


@router.message(Command("learn"))
async def cmd_learn(message: types.Message, state: FSMContext, command: Command) -> None:
    hint = (command.args or "").strip() or None
    await run_learn_flow(message, state, hint)


async def run_plan_flow(
    message: types.Message,
    *,
    acting_user_id: int | None = None,
    acting_display_name: str | None = None,
) -> None:
    uid = acting_user_id if acting_user_id is not None else message.from_user.id
    display = acting_display_name if acting_display_name is not None else message.from_user.full_name
    api = backend_client(uid)
    await api.ensure_user(display)
    try:
        tasks = await api.tasks_today()
    except Exception as e:
        await message.answer(f"Error: {e}")
        return
    if not tasks:
        await message.answer("No tasks due today.")
        return
    lines = ["📅 <b>Today:</b>\n"]
    rows: list[list[InlineKeyboardButton]] = []
    for t in tasks:
        title = html.escape(str(t["title"]), quote=False)
        st = html.escape(str(t["status"]), quote=False)
        lines.append(f"• [{st}] {title} (~{t['estimated_minutes']}m)")
        tid = t["id"]
        rows.append(
            [
                InlineKeyboardButton(text="✅ Done", callback_data=f"p:done:{tid}"),
                InlineKeyboardButton(text="⏭ Skip", callback_data=f"p:skip:{tid}"),
            ]
        )
    await message.answer(
        "\n".join(lines),
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
    )


async def run_streak_flow(
    message: types.Message,
    *,
    acting_user_id: int | None = None,
    acting_display_name: str | None = None,
) -> None:
    uid = acting_user_id if acting_user_id is not None else message.from_user.id
    display = acting_display_name if acting_display_name is not None else message.from_user.full_name
    api = backend_client(uid)
    await api.ensure_user(display)
    try:
        s = await api.streak()
    except Exception as e:
        await message.answer(f"Error: {e}")
        return
    await message.answer(
        f"🔥 Streak: <b>{s['streak_current']}</b> (best {s['streak_best']})\n"
        f"Today: {s['today_completed_minutes']} / {s['today_quota_minutes']} min "
        f"({int(s['progress_ratio'] * 100)}%)\n\n"
        f"20% goal: {'✅ met' if s['streak_eligible_today'] else '⏳ not yet'}",
        parse_mode=ParseMode.HTML,
    )


async def run_done_flow(
    message: types.Message,
    state: FSMContext,
    *,
    acting_user_id: int | None = None,
) -> None:
    data = await state.get_data()
    sid = data.get("session_id")
    if not sid:
        await message.answer("No active session.")
        return
    uid = acting_user_id if acting_user_id is not None else message.from_user.id
    api = backend_client(uid)
    try:
        await api.session_action(UUID(sid), "end")
    except Exception:
        pass
    await state.clear()
    await message.answer("Session closed. Nice work! 🎓")


@router.callback_query(F.data == "menu:learn")
async def menu_learn(query: types.CallbackQuery, state: FSMContext) -> None:
    await query.answer()
    if query.message and query.from_user:
        await run_learn_flow(
            query.message,
            state,
            None,
            acting_user_id=query.from_user.id,
            acting_display_name=query.from_user.full_name,
        )


@router.callback_query(F.data == "menu:course")
async def menu_course(query: types.CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    if data.get("session_id"):
        await query.answer("End your study session first (End session).", show_alert=True)
        return
    await query.answer()
    if query.message and query.from_user:
        await start_course_flow(
            query.message,
            state,
            acting_user_id=query.from_user.id,
            acting_display_name=query.from_user.full_name,
        )


@router.callback_query(F.data == "menu:plan")
async def menu_plan(query: types.CallbackQuery) -> None:
    await query.answer()
    if query.message and query.from_user:
        await run_plan_flow(
            query.message,
            acting_user_id=query.from_user.id,
            acting_display_name=query.from_user.full_name,
        )


@router.callback_query(F.data == "menu:streak")
async def menu_streak(query: types.CallbackQuery) -> None:
    await query.answer()
    if query.message and query.from_user:
        await run_streak_flow(
            query.message,
            acting_user_id=query.from_user.id,
            acting_display_name=query.from_user.full_name,
        )


@router.callback_query(F.data == "menu:done")
async def menu_done(query: types.CallbackQuery, state: FSMContext) -> None:
    await query.answer()
    if query.message and query.from_user:
        await run_done_flow(query.message, state, acting_user_id=query.from_user.id)


@router.callback_query(F.data == "menu:web")
async def menu_web(query: types.CallbackQuery, bot: Bot) -> None:
    await query.answer()
    if not query.from_user or not query.message:
        return
    uid = query.from_user.id
    api = backend_client(uid)
    await api.ensure_user(query.from_user.full_name)
    if not (get_settings().web_public_base_url or "").strip():
        await query.message.answer(
            "Web dashboard is not available right now.",
        )
        return
    open_url, menu_ok = await refresh_web_menu(bot, uid)
    if not open_url:
        await query.message.answer(
            "I couldn't open the web dashboard right now. Please try again in a moment.",
        )
        return
    parts = ["Web session refreshed."]
    if not menu_ok:
        if open_url.startswith("http://") and not open_url.startswith("https://"):
            parts.append("Your dashboard link is ready below.")
        else:
            parts.append("I couldn't set the menu web button this time, but your dashboard link is available below.")
    copy_lines = _http_dashboard_copy_lines(open_url)
    if copy_lines:
        parts.append("\n".join(html.escape(line, quote=False) for line in copy_lines))
    await query.message.answer(
        "\n\n".join(parts),
        parse_mode=ParseMode.HTML,
        reply_markup=main_menu_keyboard(open_url),
    )


@router.callback_query(StateFilter(LearnStates.choosing_course), F.data.startswith("learn:pick:"))
async def learn_pick_course(query: types.CallbackQuery, state: FSMContext) -> None:
    if not query.data or not query.from_user:
        await query.answer()
        return
    parts = query.data.split(":", 2)
    if len(parts) < 3:
        await query.answer()
        return
    raw = parts[2]
    subject_id: UUID | None
    if raw == "none":
        subject_id = None
    else:
        try:
            subject_id = UUID(raw)
        except ValueError:
            await query.answer("Invalid course", show_alert=True)
            return
    await query.answer()
    api = backend_client(query.from_user.id)
    if query.message:
        try:
            await query.message.edit_reply_markup(reply_markup=None)
        except Exception:
            pass
        await _start_learn_session(query.message, state, api, subject_id=subject_id)


@router.message(Command("cancel"), StateFilter(LearnStates.choosing_course))
async def cmd_cancel_learn_pick(message: types.Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Cancelled. Use /learn when you want to study.")


@router.message(StateFilter(LearnStates.choosing_course), F.text)
async def learn_choose_reminder(message: types.Message) -> None:
    if message.text and message.text.startswith("/"):
        return
    await message.answer("Tap a course button above, or send /cancel.")


@router.message(Command("done"))
async def cmd_done(message: types.Message, state: FSMContext) -> None:
    await run_done_flow(message, state)


@router.message(Command("plan"))
async def cmd_plan(message: types.Message) -> None:
    await run_plan_flow(message)


@router.message(Command("streak"))
async def cmd_streak(message: types.Message) -> None:
    await run_streak_flow(message)


@router.callback_query(F.data.in_(("learn:skip", "learn:end", "learn:continue")))
async def learn_callbacks(query: types.CallbackQuery, state: FSMContext) -> None:
    action = query.data.split(":", 1)[1]
    data = await state.get_data()
    sid = data.get("session_id")
    if not sid:
        await query.answer("No session", show_alert=True)
        return
    api = backend_client(query.from_user.id)
    try:
        if action == "continue":
            await query.answer()
            if query.message:
                try:
                    await query.message.edit_reply_markup(reply_markup=None)
                except Exception:
                    pass
                await query.bot.send_chat_action(query.message.chat.id, ChatAction.TYPING)
            res = await api.session_action(UUID(sid), "begin_practice")
            if query.message:
                await _deliver_study_turn(query.message, res["message"], meta=res.get("meta"))
            return
        if action == "skip":
            await query.answer()
            if query.message:
                try:
                    await query.message.edit_text("🤔 Thinking…", reply_markup=None)
                except Exception:
                    try:
                        await query.message.edit_caption(caption="🤔 Thinking…", reply_markup=None)
                    except Exception:
                        pass
                await query.bot.send_chat_action(query.message.chat.id, ChatAction.TYPING)
                res = await api.session_action(UUID(sid), "skip")
                await _edit_thinking_with_text(
                    query.message,
                    res["message"],
                    meta=res.get("meta"),
                )
        elif action == "end":
            await api.session_action(UUID(sid), "end")
            await state.clear()
            if query.message:
                try:
                    await query.message.edit_text("🛑 Session ended.")
                except Exception:
                    try:
                        await query.message.edit_caption(caption="🛑 Session ended.", reply_markup=None)
                    except Exception:
                        await query.message.answer("🛑 Session ended.")
            await query.answer()
    except Exception as e:
        await query.answer(str(e)[:200], show_alert=True)
        return


@router.callback_query(F.data.startswith("p:"))
async def plan_callbacks(query: types.CallbackQuery) -> None:
    parts = query.data.split(":")
    if len(parts) < 3:
        await query.answer()
        return
    _, action, task_id = parts[0], parts[1], parts[2]
    api = backend_client(query.from_user.id)
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
    api = backend_client(message.from_user.id)
    thinking = await message.answer("🤔 Thinking…")
    await message.bot.send_chat_action(message.chat.id, ChatAction.TYPING)
    try:
        res = await api.session_answer(UUID(sid), message.text)
    except Exception as e:
        try:
            await thinking.edit_text(f"Error: {e}")
        except Exception:
            try:
                await thinking.edit_caption(caption=f"Error: {e}")
            except Exception:
                await thinking.answer(f"Error: {e}")
        return
    try:
        await _edit_thinking_with_text(
            thinking,
            res["message"],
            meta=res.get("meta"),
        )
    except Exception:
        try:
            plain = _plain_text_without_latex_math(res["message"])
            seg = (res.get("meta") or {}).get("segment")
            await thinking.edit_text(
                plain[:TG_CAP],
                reply_markup=study_keyboard_for_segment(seg),
            )
        except Exception:
            await _deliver_study_turn(thinking, res["message"], meta=res.get("meta"))
