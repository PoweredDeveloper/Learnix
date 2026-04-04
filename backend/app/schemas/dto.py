from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.entities import TaskStatus


class UserEnsureIn(BaseModel):
    telegram_id: int
    name: str | None = None
    timezone: str = "UTC"


class UserOut(BaseModel):
    id: UUID
    telegram_id: int
    name: str | None
    timezone: str
    streak_current: int
    streak_best: int
    last_streak_eligible_date: date | None

    model_config = {"from_attributes": True}


class SubjectCreate(BaseModel):
    name: str
    exam_date: date | None = None


class SubjectOut(BaseModel):
    id: UUID
    name: str
    exam_date: date | None

    model_config = {"from_attributes": True}


class TaskOut(BaseModel):
    id: UUID
    title: str
    due_date: date
    status: TaskStatus
    estimated_minutes: int

    model_config = {"from_attributes": True}


class TaskUpdate(BaseModel):
    status: TaskStatus


class SessionStartIn(BaseModel):
    topic_id: UUID | None = None
    subject_id: UUID | None = None
    topic_hint: str | None = None


class SessionOut(BaseModel):
    session_id: UUID
    message: str


class AnswerIn(BaseModel):
    text: str = Field(..., min_length=1, max_length=8000)


class SessionActionIn(BaseModel):
    action: str  # skip | end


class StreakOut(BaseModel):
    streak_current: int
    streak_best: int
    today_completed_minutes: int
    today_quota_minutes: int
    progress_ratio: float
    streak_eligible_today: bool
    approx_minutes_to_threshold: int
    timezone: str
    local_date: str


class CheatSheetOut(BaseModel):
    id: UUID
    content_md: str
    created_at: datetime

    model_config = {"from_attributes": True}


class PlanGenerateIn(BaseModel):
    subject_id: UUID
    topic_names: list[str] = Field(default_factory=list)
    start_date: date
    end_date: date


class TodayPlanOut(BaseModel):
    tasks: list[TaskOut]
