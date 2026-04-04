from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    telegram_bot_token: str
    api_base_url: str = "http://127.0.0.1:8000"
    api_secret: str = "dev-secret-change-me"


@lru_cache
def get_settings() -> Settings:
    return Settings()
