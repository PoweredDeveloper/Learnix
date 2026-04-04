from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, verify_api_key
from app.models.entities import Subject, User
from app.schemas.dto import SubjectCreate, SubjectOut

router = APIRouter(prefix="/subjects", tags=["subjects"])


async def _tid(x_telegram_user_id: int = Header(..., alias="X-Telegram-User-Id")) -> int:
    return x_telegram_user_id


async def _user(db: AsyncSession, telegram_id: int) -> User:
    r = await db.execute(select(User).where(User.telegram_id == telegram_id))
    u = r.scalar_one_or_none()
    if not u:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return u


@router.post("", dependencies=[Depends(verify_api_key)])
async def create_subject(
    body: SubjectCreate,
    telegram_user_id: int = Depends(_tid),
    db: AsyncSession = Depends(get_db),
) -> SubjectOut:
    user = await _user(db, telegram_user_id)
    s = Subject(user_id=user.id, name=body.name, exam_date=body.exam_date)
    db.add(s)
    await db.commit()
    await db.refresh(s)
    return SubjectOut.model_validate(s)


@router.get("", dependencies=[Depends(verify_api_key)])
async def list_subjects(
    telegram_user_id: int = Depends(_tid),
    db: AsyncSession = Depends(get_db),
) -> list[SubjectOut]:
    user = await _user(db, telegram_user_id)
    r = await db.execute(select(Subject).where(Subject.user_id == user.id))
    return [SubjectOut.model_validate(x) for x in r.scalars().all()]


@router.get("/{subject_id}", dependencies=[Depends(verify_api_key)])
async def get_subject(
    subject_id: UUID,
    telegram_user_id: int = Depends(_tid),
    db: AsyncSession = Depends(get_db),
) -> SubjectOut:
    user = await _user(db, telegram_user_id)
    s = await db.get(Subject, subject_id)
    if not s or s.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return SubjectOut.model_validate(s)
