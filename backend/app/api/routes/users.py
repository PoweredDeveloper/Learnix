from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, verify_api_key
from app.models.entities import User
from app.schemas.dto import UserEnsureIn, UserOut

router = APIRouter(prefix="/users", tags=["users"])


async def _telegram_id(x_telegram_user_id: int = Header(..., alias="X-Telegram-User-Id")) -> int:
    return x_telegram_user_id


@router.post("/ensure", dependencies=[Depends(verify_api_key)])
async def ensure_user(body: UserEnsureIn, db: AsyncSession = Depends(get_db)) -> UserOut:
    r = await db.execute(select(User).where(User.telegram_id == body.telegram_id))
    user = r.scalar_one_or_none()
    if user:
        if body.name:
            user.name = body.name
        user.timezone = body.timezone
        await db.commit()
        await db.refresh(user)
        return UserOut.model_validate(user)
    user = User(
        telegram_id=body.telegram_id,
        name=body.name,
        timezone=body.timezone,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return UserOut.model_validate(user)


@router.get("/me", dependencies=[Depends(verify_api_key)])
async def me(
    telegram_user_id: int = Depends(_telegram_id),
    db: AsyncSession = Depends(get_db),
) -> UserOut:
    r = await db.execute(select(User).where(User.telegram_id == telegram_user_id))
    user = r.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return UserOut.model_validate(user)
