"""Telegram notification scheduling: daily + custom reminders (user local timezone)."""

from __future__ import annotations

import copy
import re
import uuid
from datetime import datetime, timezone
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entities import User

_TIME_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


def default_notification_prefs() -> dict[str, Any]:
    return {
        "daily_enabled": False,
        "daily_time": "09:00",
        "last_daily_sent_local_date": None,
        "custom_reminders": [],
    }


def merge_notification_prefs(raw: dict[str, Any] | None) -> dict[str, Any]:
    base = default_notification_prefs()
    if not raw:
        return copy.deepcopy(base)
    out = copy.deepcopy(base)
    for k in ("daily_enabled", "daily_time", "last_daily_sent_local_date", "custom_reminders"):
        if k in raw:
            out[k] = raw[k]
    return out


def safe_zoneinfo(name: str) -> ZoneInfo:
    try:
        return ZoneInfo((name or "UTC").strip() or "UTC")
    except Exception:
        return ZoneInfo("UTC")


def normalize_time(s: str) -> str:
    t = (s or "09:00").strip()[:5]
    return t if _TIME_RE.match(t) else "09:00"


def normalize_custom_reminders(raw: Any) -> list[dict[str, Any]]:
    if not isinstance(raw, list):
        return []
    out: list[dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        rid = str(item.get("id") or uuid.uuid4())
        d = str(item.get("date", ""))[:10]
        if len(d) != 10:
            continue
        out.append(
            {
                "id": rid,
                "date": d,
                "time": normalize_time(str(item.get("time", "09:00"))),
                "message": str(item.get("message", "Study reminder"))[:500],
                "enabled": bool(item.get("enabled", True)),
                "last_fired_local_date": item.get("last_fired_local_date"),
            }
        )
    return out


def sanitize_prefs_for_client(prefs: dict[str, Any]) -> dict[str, Any]:
    """Strip internal keys the UI does not edit."""
    p = copy.deepcopy(prefs)
    p.pop("last_daily_sent_local_date", None)
    for c in p.get("custom_reminders", []):
        if isinstance(c, dict):
            c.pop("last_fired_local_date", None)
    return p


async def claim_due_notifications(db: AsyncSession, *, now_utc: datetime | None = None) -> list[dict[str, Any]]:
    """Find users due for a notification this minute; update prefs so duplicates are not sent."""
    now = now_utc or datetime.now(timezone.utc)
    r = await db.execute(select(User))
    users = list(r.scalars().all())
    items: list[dict[str, Any]] = []

    for user in users:
        prefs = merge_notification_prefs(user.notification_preferences)
        zi = safe_zoneinfo(user.timezone)
        local = now.astimezone(zi)
        hhmm = local.strftime("%H:%M")
        today = local.date().isoformat()
        changed = False

        custom_list: list[dict[str, Any]] = []
        for c in prefs.get("custom_reminders", []):
            if isinstance(c, dict):
                custom_list.append(copy.deepcopy(c))

        daily_t = normalize_time(str(prefs.get("daily_time", "09:00")))
        prefs["daily_time"] = daily_t

        if prefs.get("daily_enabled") and hhmm == daily_t:
            if prefs.get("last_daily_sent_local_date") != today:
                nm = user.name or "there"
                items.append(
                    {
                        "telegram_id": user.telegram_id,
                        "text": (
                            f"📚 Hi {nm}! Your daily Learnix reminder — "
                            "open the bot or web app and keep learning."
                        ),
                        "kind": "daily",
                    }
                )
                prefs["last_daily_sent_local_date"] = today
                changed = True

        for cr in custom_list:
            if not cr.get("enabled", True):
                continue
            if cr.get("date") != today:
                continue
            if normalize_time(str(cr.get("time", "09:00"))) != hhmm:
                continue
            if cr.get("last_fired_local_date") == today:
                continue
            msg = (cr.get("message") or "Study reminder").strip()
            items.append(
                {
                    "telegram_id": user.telegram_id,
                    "text": f"🔔 {msg}",
                    "kind": "custom",
                    "reminder_id": cr.get("id"),
                }
            )
            cr["last_fired_local_date"] = today
            changed = True

        prefs["custom_reminders"] = custom_list
        if changed:
            user.notification_preferences = prefs

    return items
