from tg_bot.api_client import BackendClient
from tg_bot.config import get_settings


def backend_client(telegram_user_id: int) -> BackendClient:
    s = get_settings()
    return BackendClient(s.api_base_url, s.api_secret, telegram_user_id)
