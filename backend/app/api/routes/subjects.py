from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import authenticate_user, get_db
from app.models.entities import Subject, User
from app.schemas.dto import SubjectCreate, SubjectOut

router = APIRouter(prefix="/subjects", tags=["subjects"])


@router.post("")
async def create_subject(
    body: SubjectCreate,
    user: User = Depends(authenticate_user),
    db: AsyncSession = Depends(get_db),
) -> SubjectOut:
    s = Subject(user_id=user.id, name=body.name, exam_date=body.exam_date)
    db.add(s)
    await db.commit()
    await db.refresh(s)
    return SubjectOut.model_validate(s)


@router.get("")
async def list_subjects(
    user: User = Depends(authenticate_user),
    db: AsyncSession = Depends(get_db),
) -> list[SubjectOut]:
    r = await db.execute(select(Subject).where(Subject.user_id == user.id))
    return [SubjectOut.model_validate(x) for x in r.scalars().all()]


@router.get("/{subject_id}")
async def get_subject(
    subject_id: UUID,
    user: User = Depends(authenticate_user),
    db: AsyncSession = Depends(get_db),
) -> SubjectOut:
    s = await db.get(Subject, subject_id)
    if not s or s.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return SubjectOut.model_validate(s)
