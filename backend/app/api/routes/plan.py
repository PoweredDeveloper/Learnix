from datetime import timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_ollama, verify_api_key
from app.models.entities import StudyPlan, StudyTask, Subject, Topic, User
from app.schemas.dto import PlanGenerateIn, TaskOut
from app.services.ollama import OllamaClient

router = APIRouter(prefix="/plan", tags=["plan"])

PLAN_SYSTEM = """You help build a study schedule. Return JSON only: {"tasks": [{"title": string, "day_offset": int, "estimated_minutes": int}]}
day_offset is 0 for first day, 1 for next, etc. relative to start_date. 3-8 tasks total for MVP."""


async def _tid(x_telegram_user_id: int = Header(..., alias="X-Telegram-User-Id")) -> int:
    return x_telegram_user_id


async def _user(db: AsyncSession, telegram_id: int) -> User:
    r = await db.execute(select(User).where(User.telegram_id == telegram_id))
    u = r.scalar_one_or_none()
    if not u:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return u


@router.post("/generate", dependencies=[Depends(verify_api_key)])
async def generate_plan(
    body: PlanGenerateIn,
    telegram_user_id: int = Depends(_tid),
    db: AsyncSession = Depends(get_db),
    ollama: OllamaClient = Depends(get_ollama),
) -> list[TaskOut]:
    user = await _user(db, telegram_user_id)
    subj = await db.get(Subject, body.subject_id)
    if not subj or subj.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subject not found")

    topics = body.topic_names
    if not topics:
        r = await db.execute(select(Topic).where(Topic.subject_id == subj.id))
        topics = [t.name for t in r.scalars().all()]
    if not topics:
        topics = [subj.name]

    user_prompt = (
        f"Subject: {subj.name}. Topics: {', '.join(topics)}. "
        f"From {body.start_date} to {body.end_date}. Spread tasks across days."
    )
    data = await ollama.chat_json(PLAN_SYSTEM, user_prompt)
    raw_tasks = data.get("tasks") or []

    plan = StudyPlan(
        user_id=user.id,
        subject_id=subj.id,
        start_date=body.start_date,
        end_date=body.end_date,
    )
    db.add(plan)
    await db.flush()

    out: list[StudyTask] = []
    for i, item in enumerate(raw_tasks):
        title = str(item.get("title", f"Study: {topics[0]}"))
        offset = int(item.get("day_offset", 0))
        minutes = int(item.get("estimated_minutes", 30))
        due = body.start_date + timedelta(days=offset)
        if due > body.end_date:
            due = body.end_date
        t = StudyTask(
            plan_id=plan.id,
            title=title[:500],
            due_date=due,
            sort_order=i,
            estimated_minutes=minutes,
        )
        db.add(t)
        out.append(t)

    if not out:
        t = StudyTask(
            plan_id=plan.id,
            title=f"Review {subj.name}",
            due_date=body.start_date,
            sort_order=0,
            estimated_minutes=45,
        )
        db.add(t)
        out.append(t)

    await db.commit()
    for t in out:
        await db.refresh(t)
    return [TaskOut.model_validate(x) for x in out]
