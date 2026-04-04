from datetime import date, timedelta

from app.services.streak import (
    apply_streak_update,
    effective_quota,
    is_streak_eligible,
    streak_ratio,
)


def test_streak_ratio_cap():
    assert streak_ratio(100, 50) == 1.0


def test_is_streak_eligible_twenty_percent():
    assert is_streak_eligible(6, 30) is True
    assert is_streak_eligible(5, 30) is False


def test_effective_quota_uses_default_when_zero():
    assert effective_quota(0, default_quota=40) == 40
    assert effective_quota(15, default_quota=40) == 15


def test_apply_streak_consecutive():
    today = date(2026, 4, 4)
    s, b, last = apply_streak_update(
        last_eligible=today - timedelta(days=1),
        today=today,
        eligible_today=True,
        streak_current=2,
        streak_best=2,
    )
    assert s == 3
    assert b == 3
    assert last == today


def test_apply_streak_same_day_no_double():
    today = date(2026, 4, 4)
    s, b, last = apply_streak_update(
        last_eligible=today,
        today=today,
        eligible_today=True,
        streak_current=5,
        streak_best=5,
    )
    assert s == 5
