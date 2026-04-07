from functools import lru_cache
from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/sethack"
    api_secret: str = "dev-secret-change-me"
    lms_backend_api_key: str = ""
    # local: native daemon. cloud: https://ollama.com + /api/chat + Bearer key (see docs.ollama.com/cloud)
    ollama_mode: Literal["local", "cloud"] = "local"
    ollama_base_url: str = "http://localhost:11434"
    ollama_api_key: str = ""
    ollama_model: str = "llama3.2"
    ollama_timeout_s: float = 120.0
    upload_dir: str = "./uploads"
    default_daily_quota_minutes: int = 30
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    web_session_ttl_days: int = 3

    @model_validator(mode="after")
    def ollama_cloud_base_default(self) -> "Settings":
        if self.ollama_mode != "cloud":
            return self
        u = self.ollama_base_url.strip().rstrip("/")
        if u in ("", "http://localhost:11434", "http://127.0.0.1:11434"):
            self.ollama_base_url = "https://ollama.com"
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
