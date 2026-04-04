from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from app.core.config import get_settings


def local_today(timezone_name: str) -> date:
    tz = ZoneInfo(timezone_name)
    return datetime.now(tz).date()


def streak_ratio(completed_minutes: int, quota_minutes: int) -> float:
    if quota_minutes <= 0:
        return 1.0 if completed_minutes > 0 else 0.0
    return min(1.0, completed_minutes / quota_minutes)


def is_streak_eligible(completed_minutes: int, quota_minutes: int, threshold: float = 0.2) -> bool:
    if quota_minutes <= 0:
        return completed_minutes > 0
    return streak_ratio(completed_minutes, quota_minutes) >= threshold


def effective_quota(quota_from_tasks: int, default_quota: int | None = None) -> int:
    s = get_settings()
    d = default_quota if default_quota is not None else s.default_daily_quota_minutes
    return quota_from_tasks if quota_from_tasks > 0 else d


def apply_streak_update(
    *,
    last_eligible: date | None,
    today: date,
    eligible_today: bool,
    streak_current: int,
    streak_best: int,
) -> tuple[int, int, date | None]:
    """
    Returns (new_streak_current, new_streak_best, new_last_eligible_date).
    If eligible_today is False, streak does not increment today; last_eligible unchanged unless
    we need to clear — we only set last_streak_eligible_date when eligible_today.
    """
    if not eligible_today:
        return streak_current, streak_best, last_eligible

    new_last = today
    if last_eligible is None:
        new_streak = 1
    elif last_eligible == today:
        new_streak = streak_current
    elif last_eligible == today - timedelta(days=1):
        new_streak = streak_current + 1
    else:
        new_streak = 1

    new_best = max(streak_best, new_streak)
    return new_streak, new_best, new_last
