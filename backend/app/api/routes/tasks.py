from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, verify_api_key
from app.models.entities import StudyPlan, StudyTask, TaskStatus, User
from app.services.streak_compute import recompute_user_streak
from app.schemas.dto import TaskOut, TaskUpdate
from app.services.streak import local_today

router = APIRouter(prefix="/tasks", tags=["tasks"])


async def _tid(x_telegram_user_id: int = Header(..., alias="X-Telegram-User-Id")) -> int:
    return x_telegram_user_id


async def _user(db: AsyncSession, telegram_id: int) -> User:
    r = await db.execute(select(User).where(User.telegram_id == telegram_id))
    u = r.scalar_one_or_none()
    if not u:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return u


@router.get("/today", dependencies=[Depends(verify_api_key)])
async def tasks_today(
    telegram_user_id: int = Depends(_tid),
    db: AsyncSession = Depends(get_db),
) -> list[TaskOut]:
    user = await _user(db, telegram_user_id)
    today = local_today(user.timezone or "UTC")
    r = await db.execute(
        select(StudyTask)
        .join(StudyPlan, StudyTask.plan_id == StudyPlan.id)
        .where(
            and_(
                StudyPlan.user_id == user.id,
                StudyTask.due_date == today,
            )
        )
        .order_by(StudyTask.sort_order)
    )
    return [TaskOut.model_validate(t) for t in r.scalars().all()]


@router.patch("/{task_id}", dependencies=[Depends(verify_api_key)])
async def update_task(
    task_id: UUID,
    body: TaskUpdate,
    telegram_user_id: int = Depends(_tid),
    db: AsyncSession = Depends(get_db),
) -> TaskOut:
    from datetime import datetime, timezone

    user = await _user(db, telegram_user_id)
    task = await db.get(StudyTask, task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    plan = await db.get(StudyPlan, task.plan_id)
    if not plan or plan.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    task.status = body.status
    if body.status == TaskStatus.done:
        task.completed_at = datetime.now(timezone.utc)
    elif body.status == TaskStatus.pending:
        task.completed_at = None
    await db.commit()
    await db.refresh(task)
    await recompute_user_streak(db, user)
    await db.refresh(user)
    return TaskOut.model_validate(task)
