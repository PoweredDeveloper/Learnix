from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import authenticate_user, get_db
from app.models.entities import User
from app.schemas.dto import StreakOut
from app.services.streak_compute import recompute_user_streak, streak_snapshot

router = APIRouter(prefix="/streak", tags=["streak"])


@router.get("")
async def get_streak(
    user: User = Depends(authenticate_user),
    db: AsyncSession = Depends(get_db),
) -> StreakOut:
    await recompute_user_streak(db, user)
    await db.refresh(user)
    snap = await streak_snapshot(db, user)
    return StreakOut(**snap)


@router.post("/recompute")
async def post_recompute(
    user: User = Depends(authenticate_user),
    db: AsyncSession = Depends(get_db),
) -> StreakOut:
    return await get_streak(user=user, db=db)
