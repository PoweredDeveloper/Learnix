from datetime import datetime, timezone

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.session import get_db
from app.models.entities import User
from app.services.ollama import OllamaClient


def get_ollama() -> OllamaClient:
    return OllamaClient()


async def verify_api_key(x_api_key: str | None = Header(None, alias="X-API-Key")) -> None:
    settings = get_settings()
    if not x_api_key or x_api_key != settings.api_secret:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")


async def authenticate_user(
    db: AsyncSession = Depends(get_db),
    x_api_key: str | None = Header(None, alias="X-API-Key"),
    x_telegram_user_id: str | None = Header(None, alias="X-Telegram-User-Id"),
    x_web_session_key: str | None = Header(None, alias="X-Web-Session-Key"),
) -> User:
    """Accepts bot credentials (API key + Telegram id) or browser web session key."""
    settings = get_settings()
    raw_key = (x_web_session_key or "").strip()
    if raw_key:
        r = await db.execute(select(User).where(User.web_session_token == raw_key))
        user = r.scalar_one_or_none()
        now = datetime.now(timezone.utc)
        if not user or not user.web_session_expires_at or user.web_session_expires_at <= now:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired web session",
            )
        return user

    if x_api_key and x_api_key == settings.api_secret and x_telegram_user_id is not None:
        try:
            tid = int(x_telegram_user_id)
        except ValueError:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
        ur = await db.execute(select(User).where(User.telegram_id == tid))
        u = ur.scalar_one_or_none()
        if u:
            return u

    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
