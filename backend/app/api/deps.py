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


async def get_telegram_user(
    telegram_user_id: int = Header(..., alias="X-Telegram-User-Id"),
    db: AsyncSession = Depends(get_db),
) -> User:
    r = await db.execute(select(User).where(User.telegram_id == telegram_user_id))
    user = r.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


async def get_optional_user_by_header(
    telegram_user_id: int | None = Header(None, alias="X-Telegram-User-Id"),
    db: AsyncSession = Depends(get_db),
) -> User | None:
    if telegram_user_id is None:
        return None
    r = await db.execute(select(User).where(User.telegram_id == telegram_user_id))
    return r.scalar_one_or_none()
