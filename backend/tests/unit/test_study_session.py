from datetime import datetime, timedelta, timezone

from app.services.study_session import _session_minutes_for_answer


def test_session_minutes_caps_after_five_minutes() -> None:
    now = datetime(2026, 4, 6, 12, 10, tzinfo=timezone.utc)
    assigned = (now - timedelta(minutes=12)).isoformat()
    assert _session_minutes_for_answer(assigned_at=assigned, now=now, max_minutes=5) == 5


def test_session_minutes_counts_short_gap() -> None:
    now = datetime(2026, 4, 6, 12, 10, tzinfo=timezone.utc)
    assigned = (now - timedelta(seconds=70)).isoformat()
    assert _session_minutes_for_answer(assigned_at=assigned, now=now, max_minutes=5) == 2


def test_session_minutes_handles_missing_timestamp() -> None:
    now = datetime(2026, 4, 6, 12, 10, tzinfo=timezone.utc)
    assert _session_minutes_for_answer(assigned_at=None, now=now, max_minutes=5) == 5
