import asyncio
import logging

import httpx
from aiogram import Bot, Dispatcher
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.exceptions import TelegramConflictError, TelegramNetworkError, TelegramUnauthorizedError
from aiogram.fsm.storage.memory import MemoryStorage

from tg_bot.config import get_settings
from tg_bot.handlers.common import router as common_router
from tg_bot.handlers.onboarding_course import router as onboarding_router


def _telegram_session() -> AiohttpSession:
    s = get_settings()
    proxy = (s.telegram_http_proxy or "").strip() or None
    kwargs: dict = {"timeout": s.telegram_http_timeout}
    if proxy:
        kwargs["proxy"] = proxy
    return AiohttpSession(**kwargs)


async def _log_tcp_probe(host: str, port: int) -> None:
    """Outbound connectivity hint (TLS not exercised — only TCP handshake)."""
    try:
        _r, writer = await asyncio.wait_for(asyncio.open_connection(host, port), timeout=12.0)
        writer.close()
        try:
            await writer.wait_closed()
        except Exception:
            pass
        logging.info("Outbound TCP probe OK: %s:%s", host, port)
    except Exception as e:
        logging.warning(
            "Outbound TCP probe failed (%s:%s): %s — Telegram get_me will likely fail until "
            "this host can reach Telegram (firewall, provider block, or use TELEGRAM_HTTP_PROXY + Mihomo subscription).",
            host,
            port,
            e,
        )


async def run_notification_worker(bot: Bot) -> None:
    s = get_settings()
    url = f"{s.api_base_url.rstrip('/')}/internal/notifications/due"
    headers = {"X-API-Key": s.api_secret}
    while True:
        await asyncio.sleep(60)
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                r = await client.get(url, headers=headers)
                r.raise_for_status()
                data = r.json()
                for item in data.get("items", []):
                    tid = item.get("telegram_id")
                    text = item.get("text", "")
                    if not tid or not text:
                        continue
                    try:
                        await bot.send_message(chat_id=int(tid), text=text)
                    except Exception:
                        logging.exception("Failed to send notification to %s", tid)
        except Exception:
            logging.exception("Notification poll failed")


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    s = get_settings()
    proxy_raw = (s.telegram_http_proxy or "").strip() or None
    logging.info(
        "Learnix bot starting — backend %s | TELEGRAM_HTTP_PROXY=%r | next: Telegram get_me()",
        s.api_base_url,
        proxy_raw,
    )
    await _log_tcp_probe("api.telegram.org", 443)

    bot = Bot(s.telegram_bot_token, session=_telegram_session())
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(onboarding_router)
    dp.include_router(common_router)
    # Transient egress/DNS issues on deploy: retry get_me until Telegram is reachable.
    delay_s = 5.0
    max_delay_s = 120.0
    attempt = 0
    me = None
    while True:
        attempt += 1
        try:
            me = await bot.get_me()
            break
        except TelegramUnauthorizedError as e:
            logging.error("Invalid TELEGRAM_BOT_TOKEN — fix .env and restart: %s", e)
            raise SystemExit(1) from e
        except TelegramConflictError as e:
            logging.error(
                "Telegram returned conflict (another process is polling with this token). "
                "Stop duplicate bots / duplicate compose stacks: %s",
                e,
            )
            raise SystemExit(2) from e
        except TelegramNetworkError as e:
            proxy = (get_settings().telegram_http_proxy or "").strip()
            hint = (
                " If this host blocks api.telegram.org, set PROXY_SUBSCRIPTION_* on the mihomo service and "
                "TELEGRAM_HTTP_PROXY=http://mihomo:7890 on the bot. socks5:// needs aiohttp-socks."
                if not proxy
                else f" Current TELEGRAM_HTTP_PROXY={proxy!r} — verify Mihomo is up and the subscription works."
            )
            logging.warning(
                "Telegram Bot API unreachable (attempt %s): %s — retrying in %.0fs.%s",
                attempt,
                e,
                delay_s,
                hint,
            )
            await asyncio.sleep(delay_s)
            delay_s = min(delay_s * 1.5, max_delay_s)
    assert me is not None
    logging.info(
        "Telegram OK — polling as @%s (proxy=%r)",
        me.username or me.first_name,
        proxy_raw,
    )
    asyncio.create_task(run_notification_worker(bot))
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
