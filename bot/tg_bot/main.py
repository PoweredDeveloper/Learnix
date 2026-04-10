import asyncio
import logging

import httpx
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from tg_bot.config import get_settings
from tg_bot.handlers.common import router as common_router
from tg_bot.handlers.onboarding_course import router as onboarding_router


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
    bot = Bot(s.telegram_bot_token)
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(onboarding_router)
    dp.include_router(common_router)
    asyncio.create_task(run_notification_worker(bot))
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
