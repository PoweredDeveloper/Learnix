from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _discover_env_files() -> tuple[str, ...]:
    """Prefer repo-root `.env`, then `bot/.env` (for this package layout: tg_bot/config.py)."""
    here = Path(__file__).resolve()
    repo_root = here.parents[2]
    bot_dir = here.parents[1]
    paths = [p for p in (repo_root / ".env", bot_dir / ".env") if p.is_file()]
    return tuple(str(p) for p in paths)


_env_kwargs: dict = {"env_file_encoding": "utf-8", "extra": "ignore"}
_env_files = _discover_env_files()
if _env_files:
    _env_kwargs["env_file"] = _env_files


class Settings(BaseSettings):
    model_config = SettingsConfigDict(**_env_kwargs)

    telegram_bot_token: str = ""
    api_base_url: str = "http://127.0.0.1:8000"
    api_secret: str = "dev-secret-change-me"
    # Public HTTPS URL of the web UI (e.g. https://yourhost or ngrok). Used for the Telegram menu Web App link.
    web_public_base_url: str = ""
    # aiogram default Telegram HTTP timeout is 60s; slow or flaky egress may need more.
    telegram_http_timeout: float = 120.0
    # Optional HTTP(S) proxy for Bot API (e.g. socks5://user:pass@host:port) if api.telegram.org is unreachable.
    telegram_http_proxy: str = ""

    @field_validator("telegram_bot_token", mode="after")
    @classmethod
    def telegram_token_required(cls, v: str) -> str:
        t = (v or "").strip()
        if not t:
            raise ValueError(
                "TELEGRAM_BOT_TOKEN is missing or empty. Add it to `.env` at the project root "
                "(same folder as docker-compose.yml) — copy `.env.example` and paste the token "
                "from @BotFather on Telegram."
            )
        return t


@lru_cache
def get_settings() -> Settings:
    return Settings()
