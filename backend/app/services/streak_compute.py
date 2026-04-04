from datetime import date, datetime, timedelta, timezone
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.entities import StudyLog, StudyPlan, StudyTask, TaskStatus, User
from app.services.streak import apply_streak_update, effective_quota, is_streak_eligible, local_today


def _local_day_utc_bounds(today_local: date, tz_name: str) -> tuple[datetime, datetime]:
    tz = ZoneInfo(tz_name)
    start_local = datetime.combine(today_local, datetime.min.time(), tzinfo=tz)
    end_local = start_local + timedelta(days=1)
    return start_local.astimezone(timezone.utc), end_local.astimezone(timezone.utc)


async def daily_quota_minutes(db: AsyncSession, user_id: UUID, today: date) -> int:
    r2 = await db.execute(
        select(func.coalesce(func.sum(StudyTask.estimated_minutes), 0))
        .select_from(StudyTask)
        .join(StudyPlan, StudyTask.plan_id == StudyPlan.id)
        .where(
            and_(
                StudyPlan.user_id == user_id,
                StudyTask.due_date == today,
            )
        )
    )
    total = int(r2.scalar_one() or 0)
    return effective_quota(total)


async def completed_minutes_today(
    db: AsyncSession, user_id: UUID, today: date, tz_name: str
) -> int:
    start_utc, end_utc = _local_day_utc_bounds(today, tz_name)

    r_tasks = await db.execute(
        select(func.coalesce(func.sum(StudyTask.estimated_minutes), 0))
        .select_from(StudyTask)
        .join(StudyPlan, StudyTask.plan_id == StudyPlan.id)
        .where(
            and_(
                StudyPlan.user_id == user_id,
                StudyTask.status == TaskStatus.done,
                StudyTask.completed_at >= start_utc,
                StudyTask.completed_at < end_utc,
            )
        )
    )
    tasks_done = int(r_tasks.scalar_one() or 0)

    r_logs = await db.execute(
        select(func.coalesce(func.sum(StudyLog.time_spent), 0)).where(
            and_(
                StudyLog.user_id == user_id,
                StudyLog.log_date == today,
            )
        )
    )
    logs = int(r_logs.scalar_one() or 0)

    return tasks_done + logs


async def recompute_user_streak(db: AsyncSession, user: User) -> User:
    tz_name = user.timezone or "UTC"
    today = local_today(tz_name)

    if user.last_streak_eligible_date and user.last_streak_eligible_date < today - timedelta(days=1):
        user.streak_current = 0

    quota = await daily_quota_minutes(db, user.id, today)
    completed = await completed_minutes_today(db, user.id, today, tz_name)
    eligible = is_streak_eligible(completed, quota)

    new_streak, new_best, new_last = apply_streak_update(
        last_eligible=user.last_streak_eligible_date,
        today=today,
        eligible_today=eligible,
        streak_current=user.streak_current,
        streak_best=user.streak_best,
    )

    user.streak_current = new_streak
    user.streak_best = new_best
    if eligible:
        user.last_streak_eligible_date = new_last
    await db.commit()
    await db.refresh(user)
    return user


async def streak_snapshot(db: AsyncSession, user: User) -> dict:
    tz_name = user.timezone or "UTC"
    today = local_today(tz_name)
    quota = await daily_quota_minutes(db, user.id, today)
    completed = await completed_minutes_today(db, user.id, today, tz_name)
    ratio = completed / quota if quota > 0 else (1.0 if completed > 0 else 0.0)
    ratio = min(1.0, ratio)
    need = max(0, int((0.2 * quota) - completed + 0.999))  # rough minutes to 20%
    eligible = is_streak_eligible(completed, quota)
    return {
        "streak_current": user.streak_current,
        "streak_best": user.streak_best,
        "today_completed_minutes": completed,
        "today_quota_minutes": quota,
        "progress_ratio": round(ratio, 3),
        "streak_eligible_today": eligible,
        "approx_minutes_to_threshold": need if not eligible else 0,
        "timezone": tz_name,
        "local_date": str(today),
    }
