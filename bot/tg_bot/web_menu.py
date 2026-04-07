import logging
from urllib.parse import quote

from aiogram import Bot
from aiogram.types import MenuButtonDefault, MenuButtonWebApp, WebAppInfo

from tg_bot.bot_common import backend_client
from tg_bot.config import get_settings

_log = logging.getLogger(__name__)


async def get_web_open_url(telegram_user_id: int) -> str | None:
    """Returns full dashboard URL with ?key= after minting a web session."""
    base = (get_settings().web_public_base_url or "").strip().rstrip("/")
    if not base:
        return None
    api = backend_client(telegram_user_id)
    try:
        ws = await api.ensure_web_session()
        key = quote(ws["web_key"], safe="")
        return f"{base}/?key={key}"
    except Exception as e:
        _log.warning("ensure_web_session failed: %s", e)
        return None


async def _set_menu_default(bot: Bot, telegram_user_id: int) -> None:
    try:
        await bot.set_chat_menu_button(chat_id=telegram_user_id, menu_button=MenuButtonDefault())
    except Exception as e:
        _log.debug("set_menu_default: %s", e)


async def set_telegram_menu_web_app(bot: Bot, telegram_user_id: int, url: str) -> bool:
    """Telegram only accepts HTTPS URLs for the menu Web App button."""
    if not url.startswith("https://"):
        await _set_menu_default(bot, telegram_user_id)
        return False
    try:
        await bot.set_chat_menu_button(
            chat_id=telegram_user_id,
            menu_button=MenuButtonWebApp(text="Web app", web_app=WebAppInfo(url=url)),
        )
        return True
    except Exception as e:
        _log.warning("set_chat_menu_button (Web App) failed: %s", e)
        await _set_menu_default(bot, telegram_user_id)
        return False


async def refresh_web_menu(bot: Bot, telegram_user_id: int) -> tuple[str | None, bool]:
    """
    Mint session URL and try to set the chat menu Web App (HTTPS only).
    Returns (open_url, menu_web_app_set).
    For http://localhost (Docker), open_url is still valid for inline URL buttons.
    """
    url = await get_web_open_url(telegram_user_id)
    if not url:
        return None, False
    menu_ok = await set_telegram_menu_web_app(bot, telegram_user_id, url)
    return url, menu_ok


async def refresh_web_menu_button(bot: Bot, telegram_user_id: int) -> bool:
    """Backward-compatible: True if user got a usable web URL (menu or inline)."""
    url, _ = await refresh_web_menu(bot, telegram_user_id)
    return url is not None
