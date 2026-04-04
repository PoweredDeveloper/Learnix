from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, verify_api_key
from app.models.entities import User
from app.schemas.dto import StreakOut
from app.services.streak_compute import recompute_user_streak, streak_snapshot

router = APIRouter(prefix="/streak", tags=["streak"])


async def _tid(x_telegram_user_id: int = Header(..., alias="X-Telegram-User-Id")) -> int:
    return x_telegram_user_id


@router.get("", dependencies=[Depends(verify_api_key)])
async def get_streak(
    telegram_user_id: int = Depends(_tid),
    db: AsyncSession = Depends(get_db),
) -> StreakOut:
    r = await db.execute(select(User).where(User.telegram_id == telegram_user_id))
    user = r.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    await recompute_user_streak(db, user)
    await db.refresh(user)
    snap = await streak_snapshot(db, user)
    return StreakOut(**snap)


@router.post("/recompute", dependencies=[Depends(verify_api_key)])
async def post_recompute(
    telegram_user_id: int = Depends(_tid),
    db: AsyncSession = Depends(get_db),
) -> StreakOut:
    return await get_streak(telegram_user_id=telegram_user_id, db=db)
