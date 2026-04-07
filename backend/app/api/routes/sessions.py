from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import authenticate_user, get_db, get_ollama
from app.api.ollama_http import raise_for_ollama_http
from app.models.entities import User
from app.schemas.dto import AnswerIn, SessionActionIn, SessionOut, SessionStartIn
from app.services.ollama import OllamaClient
from app.services.streak_compute import recompute_user_streak
from app.services.study_session import StudySessionService, get_active_session_for_user, study_meta_from_state

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.post("/start")
async def start_session(
    body: SessionStartIn,
    user: User = Depends(authenticate_user),
    db: AsyncSession = Depends(get_db),
    ollama: OllamaClient = Depends(get_ollama),
) -> SessionOut:
    existing = await get_active_session_for_user(db, user.id)
    if existing:
        msg = existing.state.get("last_assistant", "Session already active. Send your answer or /done.")
        return SessionOut(
            session_id=existing.id,
            message=str(msg),
            meta=study_meta_from_state(dict(existing.state)),
        )

    svc = StudySessionService(db, ollama)
    try:
        session, message, meta = await svc.start_session(
            user_id=user.id,
            topic_id=body.topic_id,
            subject_id=body.subject_id,
            topic_hint=body.topic_hint,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    except httpx.HTTPError as e:
        raise_for_ollama_http(e)
    return SessionOut(session_id=session.id, message=message, meta=meta)


@router.post("/{session_id}/answer")
async def answer(
    session_id: UUID,
    body: AnswerIn,
    user: User = Depends(authenticate_user),
    db: AsyncSession = Depends(get_db),
    ollama: OllamaClient = Depends(get_ollama),
) -> dict:
    svc = StudySessionService(db, ollama)
    try:
        message, correct, meta = await svc.submit_answer(
            session_id=session_id,
            user_id=user.id,
            answer_text=body.text,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    except httpx.HTTPError as e:
        raise_for_ollama_http(e)
    await recompute_user_streak(db, user)
    return {"message": message, "correct": correct, "meta": meta}


@router.post("/{session_id}/action")
async def session_action(
    session_id: UUID,
    body: SessionActionIn,
    user: User = Depends(authenticate_user),
    db: AsyncSession = Depends(get_db),
    ollama: OllamaClient = Depends(get_ollama),
) -> dict:
    svc = StudySessionService(db, ollama)
    if body.action == "skip":
        try:
            msg, meta = await svc.skip_task(session_id=session_id, user_id=user.id)
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
        except httpx.HTTPError as e:
            raise_for_ollama_http(e)
        await recompute_user_streak(db, user)
        return {"message": msg, "meta": meta}
    if body.action == "begin_practice":
        try:
            msg, meta = await svc.begin_practice(session_id=session_id, user_id=user.id)
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
        except httpx.HTTPError as e:
            raise_for_ollama_http(e)
        await recompute_user_streak(db, user)
        return {"message": msg, "meta": meta}
    if body.action == "end":
        try:
            summary = await svc.end_session(session_id=session_id, user_id=user.id)
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
        await recompute_user_streak(db, user)
        return {"summary": summary, "message": "Session ended."}
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown action")


@router.get("/active")
async def active_session(
    user: User = Depends(authenticate_user),
    db: AsyncSession = Depends(get_db),
) -> SessionOut | dict:
    s = await get_active_session_for_user(db, user.id)
    if not s:
        return {"active": False}
    return SessionOut(
        session_id=s.id,
        message=str(s.state.get("last_assistant", "")),
        meta=study_meta_from_state(dict(s.state)),
    )
