import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from tg_bot.config import get_settings
from tg_bot.handlers.common import router


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    s = get_settings()
    bot = Bot(s.telegram_bot_token)
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
