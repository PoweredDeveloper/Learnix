import json
from datetime import date, timedelta
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entities import StudyPlan, StudyTask, Subject, User
from app.schemas.dto import TaskOut
from app.services.ollama import OllamaClient

PLAN_SYSTEM = """You help build a study schedule. Return JSON only: {"tasks": [{"title": string, "day_offset": int, "estimated_minutes": int}]}
day_offset is 0 for first day, 1 for next, etc. relative to start_date. 3-12 tasks."""


def _learning_blurb(user: User) -> str:
    lp = user.learning_profile
    if not lp:
        return ""
    try:
        s = json.dumps(lp, ensure_ascii=False)
    except (TypeError, ValueError):
        return ""
    return f"\nLearner profile (respect this when sizing tasks and ordering): {s[:2000]}"


async def build_study_plan(
    *,
    db: AsyncSession,
    user: User,
    subject: Subject,
    start_date: date,
    end_date: date,
    topic_names: list[str],
    ollama: OllamaClient,
    prep_excerpt: str | None = None,
) -> list[TaskOut]:
    topics = topic_names[:] if topic_names else [subject.name]
    user_prompt = (
        f"Subject/course: {subject.name}. Topics focus: {', '.join(topics)}. "
        f"From {start_date} to {end_date}. Spread tasks across days."
        f"{_learning_blurb(user)}"
    )
    if prep_excerpt:
        user_prompt += f"\n\nSource material excerpt (use to ground task titles):\n{prep_excerpt[:12000]}"

    data = await ollama.chat_json(PLAN_SYSTEM, user_prompt)
    raw_tasks = data.get("tasks") or []

    plan = StudyPlan(
        user_id=user.id,
        subject_id=subject.id,
        start_date=start_date,
        end_date=end_date,
    )
    db.add(plan)
    await db.flush()

    out: list[StudyTask] = []
    for i, item in enumerate(raw_tasks):
        title = str(item.get("title", f"Study: {topics[0]}"))
        try:
            offset = int(item.get("day_offset", 0))
        except (TypeError, ValueError):
            offset = 0
        try:
            minutes = int(item.get("estimated_minutes", 30))
        except (TypeError, ValueError):
            minutes = 30
        due = start_date + timedelta(days=offset)
        if due > end_date:
            due = end_date
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
            title=f"Review {subject.name}",
            due_date=start_date,
            sort_order=0,
            estimated_minutes=45,
        )
        db.add(t)
        out.append(t)

    await db.commit()
    for t in out:
        await db.refresh(t)
    return [TaskOut.model_validate(x) for x in out]
