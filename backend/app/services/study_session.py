from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entities import SessionEvent, SessionStatus, StudySession, StudyLog, Topic
from app.services.ollama import OllamaClient


START_SYSTEM = """You are a concise tutor. Reply with a single JSON object only, no markdown.
Keys: "explanation" (short intro to the sub-topic), "task" (one easy question), "rubric" (how to judge a correct answer)."""

GRADE_SYSTEM = """You are a tutor grading a short answer. Reply with JSON only.
Keys:
- "correct" (boolean)
- "feedback" (string, for the student — if wrong, explain what was wrong and give a hint; if right, brief praise)
- "next_task" (string or null) — if correct, a slightly harder follow-up question; if wrong, null
- "next_rubric" (string or null) — rubric for next_task if next_task is set; else null
- "session_complete" (boolean) — true if the student should wrap up (e.g. after several correct answers)"""


class StudySessionService:
    def __init__(self, db: AsyncSession, ollama: OllamaClient | Any) -> None:
        self.db = db
        self.ollama = ollama

    async def start_session(
        self,
        *,
        user_id: UUID,
        topic_id: UUID | None,
        subject_id: UUID | None,
        topic_hint: str | None = None,
    ) -> tuple[StudySession, str]:
        topic_name = topic_hint or "General study"
        if topic_id:
            t = await self.db.get(Topic, topic_id)
            if t:
                topic_name = t.name

        user_msg = f'Topic to teach: "{topic_name}". Start with something easy.'
        data = await self.ollama.chat_json(START_SYSTEM, user_msg)

        explanation = str(data.get("explanation", ""))
        task = str(data.get("task", ""))
        rubric = str(data.get("rubric", ""))

        state: dict[str, Any] = {
            "phase": "await_answer",
            "topic_name": topic_name,
            "current_task": task,
            "rubric": rubric,
            "attempts_on_task": 0,
            "correct_count": 0,
            "session_study_minutes": 0,
            "last_assistant": f"{explanation}\n\n📝 **Task:**\n{task}",
        }

        session = StudySession(
            user_id=user_id,
            topic_id=topic_id,
            subject_id=subject_id,
            status=SessionStatus.active,
            state=state,
        )
        self.db.add(session)
        await self.db.flush()

        await self._log_event(session.id, "assistant", state["last_assistant"])
        await self.db.commit()
        await self.db.refresh(session)

        return session, state["last_assistant"]

    async def submit_answer(
        self,
        *,
        session_id: UUID,
        user_id: UUID,
        answer_text: str,
        session_minutes_contribution: int = 5,
    ) -> tuple[str, bool]:
        session = await self._get_active(session_id, user_id)
        st = dict(session.state)
        task = st.get("current_task", "")
        rubric = st.get("rubric", "")

        await self._log_event(session.id, "user", answer_text)

        user_prompt = (
            f"Task: {task}\nRubric: {rubric}\nStudent answer: {answer_text}\n"
            f"Correct answers so far in session: {st.get('correct_count', 0)}"
        )
        data = await self.ollama.chat_json(GRADE_SYSTEM, user_prompt)

        correct = bool(data.get("correct"))
        feedback = str(data.get("feedback", ""))
        next_task = data.get("next_task")
        next_rubric = data.get("next_rubric")
        session_complete = bool(data.get("session_complete"))

        st["attempts_on_task"] = int(st.get("attempts_on_task", 0)) + 1
        st["session_study_minutes"] = int(st.get("session_study_minutes", 0)) + session_minutes_contribution

        lines = [feedback]

        if correct:
            st["correct_count"] = int(st.get("correct_count", 0)) + 1
            st["attempts_on_task"] = 0
            if next_task:
                st["current_task"] = str(next_task)
                st["rubric"] = str(next_rubric or "")
                lines.append(f"\n\n📝 **Next task:**\n{next_task}")
            elif session_complete or st["correct_count"] >= 3:
                lines.append(
                    "\n\n✅ Nice progress. Use `/done` to close the session or type another question topic."
                )
            else:
                fallback = "In one sentence, state the main takeaway from this topic."
                st["current_task"] = fallback
                st["rubric"] = "One clear sentence about the main idea."
                lines.append(f"\n\n📝 **Next task:**\n{fallback}")
        else:
            lines.append("\n\n🔄 Try again, or tap **Skip** to get a different question.")

        st["last_assistant"] = "\n".join(lines)
        session.state = st

        await self._log_event(session.id, "assistant", st["last_assistant"])
        await self.db.commit()

        return st["last_assistant"], correct

    async def skip_task(self, *, session_id: UUID, user_id: UUID) -> str:
        session = await self._get_active(session_id, user_id)
        st = dict(session.state)
        topic_name = st.get("topic_name", "the topic")
        user_prompt = (
            f'Student skipped this task: "{st.get("current_task")}". '
            f"Give ONE easier replacement task on {topic_name}. JSON only with keys: "
            '"task", "rubric"'
        )
        data = await self.ollama.chat_json(
            "Reply with JSON only: task (string), rubric (string).", user_prompt
        )
        task = str(data.get("task", "Name one key idea from the topic."))
        rubric = str(data.get("rubric", "Any reasonable answer."))
        st["current_task"] = task
        st["rubric"] = rubric
        st["attempts_on_task"] = 0
        st["session_study_minutes"] = int(st.get("session_study_minutes", 0)) + 2
        msg = f"⏭ Skipped.\n\n📝 **Next task:**\n{task}"
        st["last_assistant"] = msg
        session.state = st
        await self._log_event(session.id, "assistant", msg)
        await self.db.commit()
        return msg

    async def end_session(self, *, session_id: UUID, user_id: UUID) -> dict[str, Any]:
        session = await self._get_active(session_id, user_id)
        st = dict(session.state)
        session.status = SessionStatus.ended
        session.ended_at = datetime.now(timezone.utc)

        minutes = int(st.get("session_study_minutes", 0))
        if minutes > 0:
            from app.models.entities import User

            u = await self.db.get(User, user_id)
            if u:
                from app.services.streak import local_today

                log_date = local_today(u.timezone or "UTC")
                self.db.add(
                    StudyLog(
                        user_id=user_id,
                        topic_id=session.topic_id,
                        status="session",
                        time_spent=minutes,
                        log_date=log_date,
                    )
                )

        summary = {
            "correct_count": st.get("correct_count", 0),
            "session_study_minutes": minutes,
        }
        await self.db.commit()
        return summary

    async def _get_active(self, session_id: UUID, user_id: UUID) -> StudySession:
        r = await self.db.execute(
            select(StudySession).where(
                StudySession.id == session_id,
                StudySession.user_id == user_id,
                StudySession.status == SessionStatus.active,
            )
        )
        session = r.scalar_one_or_none()
        if not session:
            raise ValueError("Session not found or already ended")
        return session

    async def _log_event(self, session_id: UUID, role: str, payload: str) -> None:
        self.db.add(SessionEvent(session_id=session_id, role=role, payload=payload[:8000]))


async def get_active_session_for_user(db: AsyncSession, user_id: UUID) -> StudySession | None:
    r = await db.execute(
        select(StudySession)
        .where(StudySession.user_id == user_id, StudySession.status == SessionStatus.active)
        .order_by(StudySession.started_at.desc())
        .limit(1)
    )
    return r.scalar_one_or_none()
