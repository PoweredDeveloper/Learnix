import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import authenticate_user, get_db, verify_api_key
from app.core.config import get_settings
from app.models.entities import User
from app.schemas.dto import (
    NotificationPreferencesIn,
    OnboardingCompleteIn,
    UserEnsureIn,
    UserOut,
    WebSessionOut,
)
from app.services.notification_dispatch import (
    merge_notification_prefs,
    normalize_custom_reminders,
    normalize_time,
    sanitize_prefs_for_client,
)

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


@router.get("/me")
async def me(user: User = Depends(authenticate_user)) -> UserOut:
    return UserOut.model_validate(user)


@router.get("/me/notifications")
async def get_notification_settings(user: User = Depends(authenticate_user)) -> dict:
    prefs = merge_notification_prefs(user.notification_preferences)
    return {"timezone": user.timezone, **sanitize_prefs_for_client(prefs)}


@router.put("/me/notifications")
async def put_notification_settings(
    body: NotificationPreferencesIn,
    user: User = Depends(authenticate_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    cur = merge_notification_prefs(user.notification_preferences)
    cur["daily_enabled"] = body.daily_enabled
    cur["daily_time"] = normalize_time(body.daily_time)
    if body.timezone is not None:
        tz = body.timezone.strip()[:64] or "UTC"
        user.timezone = tz
    old_by_id = {
        str(c.get("id")): c
        for c in cur.get("custom_reminders", [])
        if isinstance(c, dict) and c.get("id")
    }
    merged_custom: list = []
    for item in normalize_custom_reminders(body.custom_reminders):
        oid = str(item["id"])
        if oid in old_by_id:
            item["last_fired_local_date"] = old_by_id[oid].get("last_fired_local_date")
        merged_custom.append(item)
    cur["custom_reminders"] = merged_custom
    user.notification_preferences = cur
    await db.commit()
    await db.refresh(user)
    prefs = merge_notification_prefs(user.notification_preferences)
    return {"timezone": user.timezone, **sanitize_prefs_for_client(prefs)}


@router.post("/me/web-session", dependencies=[Depends(verify_api_key)])
async def issue_web_session(
    telegram_user_id: int = Depends(_telegram_id),
    db: AsyncSession = Depends(get_db),
) -> WebSessionOut:
    r = await db.execute(select(User).where(User.telegram_id == telegram_user_id))
    user = r.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    settings = get_settings()
    now = datetime.now(timezone.utc)
    ttl = timedelta(days=max(1, min(settings.web_session_ttl_days, 30)))
    if (
        user.web_session_token
        and user.web_session_expires_at
        and user.web_session_expires_at > now
    ):
        return WebSessionOut(web_key=user.web_session_token, expires_at=user.web_session_expires_at)
    user.web_session_token = secrets.token_urlsafe(32)
    user.web_session_expires_at = now + ttl
    await db.commit()
    await db.refresh(user)
    return WebSessionOut(web_key=user.web_session_token, expires_at=user.web_session_expires_at)


@router.post("/me/onboarding", dependencies=[Depends(verify_api_key)])
async def complete_onboarding(
    body: OnboardingCompleteIn,
    telegram_user_id: int = Depends(_telegram_id),
    db: AsyncSession = Depends(get_db),
) -> UserOut:
    r = await db.execute(select(User).where(User.telegram_id == telegram_user_id))
    user = r.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    user.learning_profile = body.answers
    user.onboarding_completed = True
    await db.commit()
    await db.refresh(user)
    return UserOut.model_validate(user)
