from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_ollama, verify_api_key
from app.models.entities import User
from app.schemas.dto import AnswerIn, SessionActionIn, SessionOut, SessionStartIn
from app.services.ollama import OllamaClient
from app.services.streak_compute import recompute_user_streak
from app.services.study_session import StudySessionService, get_active_session_for_user

router = APIRouter(prefix="/sessions", tags=["sessions"])


async def _tid(x_telegram_user_id: int = Header(..., alias="X-Telegram-User-Id")) -> int:
    return x_telegram_user_id


async def _user(db: AsyncSession, telegram_id: int) -> User:
    r = await db.execute(select(User).where(User.telegram_id == telegram_id))
    u = r.scalar_one_or_none()
    if not u:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return u


@router.post("/start", dependencies=[Depends(verify_api_key)])
async def start_session(
    body: SessionStartIn,
    telegram_user_id: int = Depends(_tid),
    db: AsyncSession = Depends(get_db),
    ollama: OllamaClient = Depends(get_ollama),
) -> SessionOut:
    user = await _user(db, telegram_user_id)
    existing = await get_active_session_for_user(db, user.id)
    if existing:
        msg = existing.state.get("last_assistant", "Session already active. Send your answer or /done.")
        return SessionOut(session_id=existing.id, message=str(msg))

    svc = StudySessionService(db, ollama)
    session, message = await svc.start_session(
        user_id=user.id,
        topic_id=body.topic_id,
        subject_id=body.subject_id,
        topic_hint=body.topic_hint,
    )
    return SessionOut(session_id=session.id, message=message)


@router.post("/{session_id}/answer", dependencies=[Depends(verify_api_key)])
async def answer(
    session_id: UUID,
    body: AnswerIn,
    telegram_user_id: int = Depends(_tid),
    db: AsyncSession = Depends(get_db),
    ollama: OllamaClient = Depends(get_ollama),
) -> dict:
    user = await _user(db, telegram_user_id)
    svc = StudySessionService(db, ollama)
    try:
        message, correct = await svc.submit_answer(
            session_id=session_id,
            user_id=user.id,
            answer_text=body.text,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    await recompute_user_streak(db, user)
    return {"message": message, "correct": correct}


@router.post("/{session_id}/action", dependencies=[Depends(verify_api_key)])
async def session_action(
    session_id: UUID,
    body: SessionActionIn,
    telegram_user_id: int = Depends(_tid),
    db: AsyncSession = Depends(get_db),
    ollama: OllamaClient = Depends(get_ollama),
) -> dict:
    user = await _user(db, telegram_user_id)
    svc = StudySessionService(db, ollama)
    if body.action == "skip":
        try:
            msg = await svc.skip_task(session_id=session_id, user_id=user.id)
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
        await recompute_user_streak(db, user)
        return {"message": msg}
    if body.action == "end":
        try:
            summary = await svc.end_session(session_id=session_id, user_id=user.id)
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
        await recompute_user_streak(db, user)
        return {"summary": summary, "message": "Session ended."}
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown action")


@router.get("/active", dependencies=[Depends(verify_api_key)])
async def active_session(
    telegram_user_id: int = Depends(_tid),
    db: AsyncSession = Depends(get_db),
) -> SessionOut | dict:
    user = await _user(db, telegram_user_id)
    s = await get_active_session_for_user(db, user.id)
    if not s:
        return {"active": False}
    return SessionOut(session_id=s.id, message=str(s.state.get("last_assistant", "")))
