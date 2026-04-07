import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import authenticate_user, get_db, get_ollama
from app.api.ollama_http import raise_for_ollama_http
from app.models.entities import Subject, Topic, User
from app.schemas.dto import PlanGenerateIn, TaskOut
from app.services.ollama import OllamaClient
from app.services.plan_build import build_study_plan

router = APIRouter(prefix="/plan", tags=["plan"])


@router.post("/generate")
async def generate_plan(
    body: PlanGenerateIn,
    user: User = Depends(authenticate_user),
    db: AsyncSession = Depends(get_db),
    ollama: OllamaClient = Depends(get_ollama),
) -> list[TaskOut]:
    subj = await db.get(Subject, body.subject_id)
    if not subj or subj.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subject not found")

    topics = body.topic_names
    if not topics:
        r = await db.execute(select(Topic).where(Topic.subject_id == subj.id))
        topics = [t.name for t in r.scalars().all()]
    if not topics:
        topics = [subj.name]

    try:
        return await build_study_plan(
            db=db,
            user=user,
            subject=subj,
            start_date=body.start_date,
            end_date=body.end_date,
            topic_names=topics,
            ollama=ollama,
            prep_excerpt=None,
        )
    except httpx.HTTPError as e:
        raise_for_ollama_http(e)
