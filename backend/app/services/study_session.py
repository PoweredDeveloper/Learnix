import math
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entities import PrepSource, SessionEvent, SessionStatus, StudySession, StudyLog, Subject, Topic
from app.services.ollama import OllamaClient

PRACTICE_TASKS_TOTAL = 5

THEORY_START_SYSTEM = """You are an expert tutor. Reply with a single JSON object only, no markdown outside JSON.
Keys:
- "theory" (string) — a clear, structured explanation: definitions, intuition, and when to use ideas. Use real line breaks between paragraphs (newline characters in the JSON string). Optional emphasis: **bold** and *italic* around key terms. Plain English only: no LaTeX, no $...$, no \\(...\\) in this field.
- "examples" (array of strings, may be empty) — optional LaTeX snippets illustrating the theory. Each string must be full LaTeX wrapped in $$...$$ and can include \\text{...} for readable text inside math. Up to 3 items.
- "topic_title" (string) — short title for the session (e.g. course/topic name for a progress header).

Do not include practice tasks or exam questions here — only teaching content."""

FIRST_TASK_SYSTEM = """You are a tutor. Reply JSON only, no markdown.
Keys: "task" (string) — one practice question, full LaTeX in $$...$$ including \\text{...} for wording;
"rubric" (string) — plain text, how to judge the answer.
The question should match the theory already taught and be doable in a few minutes."""

EXAM_GENERATION_SYSTEM = """You are a tutor. Reply JSON only.
Keys: "exam" (string) — a short exam (2–4 parts) in LaTeX, everything in $$...$$ / \\text{...} as needed;
"rubric" (string) — plain text criteria for grading the whole exam."""

GRADE_SYSTEM = """You are a supportive math/CS tutor during PRACTICE (one task at a time).

The student's latest message may be EITHER:
(A) A genuine attempt — final answer, partial work, steps, or typed math (even messy).
(B) Help / chat — asking for a hint, whether their idea is OK, what method to use, reassurance, confusion, or a follow-up after your previous feedback (e.g. "but is that fine?", "what next?").

Reply with JSON only. Keys:
- "correct" (boolean) — true ONLY for (A) when the work satisfies the rubric for THIS task. Always false for (B): do not advance them for questions or hints alone.
- "feedback" (string) — plain text, no LaTeX, no $...$.
  • For (B): answer what they asked directly (reassure, explain, or give ONE concrete next step or hint). Never say they "did not provide a solution" if they are clearly conversing.
  • For (A) wrong: say what is off; use "prior_attempts_on_this_task" — if ≥2, include a clearer hint or suggest a method; if ≥3, offer a stronger nudge or first step without giving the full final answer unless they are totally stuck.
  • For (A) right: short praise + what was good.
- "next_task" (string or null) — if correct and more practice remains, next question in LaTeX $$...$$; else null
- "next_rubric" (string or null)
- "session_complete" (boolean) — true only if practice should end without exam (rare)
- "counts_as_attempt" (boolean) — false for (B) help/chat only; true for (A) any solution attempt (even wrong).

Put formulas only in "next_task", never in "feedback". When "next_task" is not null, full LaTeX in $$...$$."""

EXAM_GRADE_SYSTEM = """You are grading an EXAM submission or helping during the exam.

The message may be:
(A) A real attempt to answer the exam (work or final answers).
(B) Not a submission — asking for a hint, clarification, or chatting (e.g. "can you give a hint?", "is part (a) enough?").

Reply JSON only. Keys:
- "is_exam_submission" (boolean) — true only for (A). false for (B).
- "correct" (boolean) — for (A): pass/fail vs rubric. For (B): always false.
- "feedback" (string) — plain text, no LaTeX. For (B): helpful hint or answer to their question; do not dismiss as "no answer". For (A): detailed comments.
- "session_complete" (boolean) — true ONLY when (A) was graded and the exam interaction should end. false for (B) so they can keep working."""


def study_meta_from_state(st: dict[str, Any]) -> dict[str, Any]:
    seg = str(st.get("segment", "practice"))
    topic = str(st.get("topic_name") or "Study")
    total = int(st.get("practice_tasks_total", PRACTICE_TASKS_TOTAL))
    completed = int(st.get("tasks_completed", 0))
    if seg == "theory":
        return {
            "segment": "theory",
            "topic_name": topic,
            "progress_label": "Theory",
            "progress_fraction": 0.0,
        }
    if seg == "exam":
        return {
            "segment": "exam",
            "topic_name": topic,
            "progress_label": "Exam",
            "progress_fraction": 1.0,
        }
    cur = min(completed + 1, total) if total > 0 else 1
    # Align bar fill with "Practice k/n" (k = current step), not only completed tasks.
    frac = min(1.0, cur / total) if total > 0 else 0.0
    return {
        "segment": "practice",
        "topic_name": topic,
        "progress_label": f"Practice {cur}/{total}",
        "progress_fraction": frac,
    }


class StudySessionService:
    def __init__(self, db: AsyncSession, ollama: OllamaClient | Any) -> None:
        self.db = db
        self.ollama = ollama

    async def _material_excerpt_for_subject(self, user_id: UUID, subject_id: UUID, limit: int = 12_000) -> str:
        r = await self.db.execute(
            select(PrepSource)
            .where(PrepSource.subject_id == subject_id, PrepSource.user_id == user_id)
            .order_by(PrepSource.created_at.desc())
            .limit(1)
        )
        ps = r.scalar_one_or_none()
        if not ps or not (ps.extracted_text or "").strip():
            return ""
        return (ps.extracted_text or "")[:limit]

    def _topic_title(self, topic_name: str, data_title: str | None) -> str:
        t = (data_title or "").strip()
        return t if t else topic_name

    def _format_theory_message(self, theory: str, examples: list[str]) -> str:
        parts = ["📚 **Theory**\n", theory.strip()]
        for ex in examples:
            e = (ex or "").strip()
            if not e:
                continue
            parts.append("\n\n📝 **Example:**\n")
            parts.append(e)
        return "".join(parts)

    async def start_session(
        self,
        *,
        user_id: UUID,
        topic_id: UUID | None,
        subject_id: UUID | None,
        topic_hint: str | None = None,
    ) -> tuple[StudySession, str, dict[str, Any]]:
        topic_name = topic_hint or "General study"
        material_excerpt = ""

        if topic_id:
            t = await self.db.get(Topic, topic_id)
            if t:
                owner = await self.db.get(Subject, t.subject_id)
                if owner and owner.user_id == user_id:
                    topic_name = t.name
                else:
                    topic_id = None
            else:
                topic_id = None

        if subject_id:
            s = await self.db.get(Subject, subject_id)
            if not s or s.user_id != user_id:
                subject_id = None
            else:
                if not topic_id:
                    topic_name = topic_hint or s.name
                material_excerpt = await self._material_excerpt_for_subject(user_id, subject_id)

        if material_excerpt:
            user_msg = (
                f'Course / subject: "{topic_name}". The learner attached material — teach from it.\n\n'
                f"--- Material (excerpt) ---\n{material_excerpt}\n--- End excerpt ---\n\n"
                "Give a solid theory section and optional LaTeX examples only (no practice tasks yet)."
            )
        else:
            user_msg = f'Topic: "{topic_name}". Give a solid theory section and optional LaTeX examples (no practice tasks yet).'

        data = await self.ollama.chat_json(THEORY_START_SYSTEM, user_msg)

        theory = str(data.get("theory", "")).strip()
        examples_raw = data.get("examples") or []
        examples: list[str] = [str(x).strip() for x in examples_raw if str(x).strip()]
        title = self._topic_title(topic_name, data.get("topic_title"))

        excerpt_for_state = (material_excerpt[:8000] if material_excerpt else "")
        display = self._format_theory_message(theory, examples)

        state: dict[str, Any] = {
            "segment": "theory",
            "phase": "await_continue",
            "topic_name": title,
            "practice_tasks_total": PRACTICE_TASKS_TOTAL,
            "tasks_completed": 0,
            "theory_body": theory,
            "examples": examples,
            "current_task": None,
            "rubric": None,
            "session_study_minutes": 0,
            "correct_count": 0,
            "attempts_on_task": 0,
            "last_assistant": display,
            "material_excerpt": excerpt_for_state,
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

        await self._log_event(session.id, "assistant", display)
        await self.db.commit()
        await self.db.refresh(session)

        meta = study_meta_from_state(state)
        return session, display, meta

    async def begin_practice(self, *, session_id: UUID, user_id: UUID) -> tuple[str, dict[str, Any]]:
        session = await self._get_active(session_id, user_id)
        st = dict(session.state)
        if st.get("segment") != "theory":
            raise ValueError("Theory was already started or session is not in theory phase")
        topic = st.get("topic_name", "the topic")
        mat = (st.get("material_excerpt") or "").strip()
        theory_body = st.get("theory_body", "")
        ex_blocks = st.get("examples") or []
        mat_block = f"\n\nMaterial:\n{mat[:4000]}" if mat else ""
        ex_text = "\n".join(f"- {e[:500]}" for e in ex_blocks[:3])
        user_prompt = (
            f"Topic / title: {topic}\n\nTheory taught:\n{theory_body}\n\n"
            f"Examples used (LaTeX):\n{ex_text}{mat_block}\n\nProduce the first practice task only."
        )
        data = await self.ollama.chat_json(FIRST_TASK_SYSTEM, user_prompt)
        task = str(data.get("task", "")).strip()
        rubric = str(data.get("rubric", "Reasonable attempt.")).strip()
        if not task:
            task = "$$\\text{State one key idea from the topic in one sentence.}$$"
        st["segment"] = "practice"
        st["phase"] = "await_answer"
        st["current_task"] = task
        st["rubric"] = rubric
        st["task_assigned_at"] = _utc_now_iso()
        msg = (
            f"📝 **Task:**\n{task}\n\n"
            "💬 You can ask for a **hint**, check whether an idea is on the right track, or chat briefly — "
            "that counts as help, not a wrong answer. Send your full work when you want it graded."
        )
        st["last_assistant"] = msg
        session.state = st
        await self._log_event(session.id, "assistant", msg)
        await self.db.commit()
        meta = study_meta_from_state(st)
        return msg, meta

    async def submit_answer(
        self,
        *,
        session_id: UUID,
        user_id: UUID,
        answer_text: str,
        session_minutes_contribution: int = 5,
    ) -> tuple[str, bool, dict[str, Any]]:
        session = await self._get_active(session_id, user_id)
        st = dict(session.state)
        seg = st.get("segment", "practice")

        if seg == "theory":
            raise ValueError("Continue the lesson: tap Continue to start practice tasks.")

        if seg == "exam":
            return await self._submit_exam_answer(session, st, answer_text)

        task = st.get("current_task", "")
        rubric = st.get("rubric", "")

        await self._log_event(session.id, "user", answer_text)

        mat = (st.get("material_excerpt") or "").strip()
        prefix = ""
        if mat:
            prefix = f"Course material (context):\n{mat[:6000]}\n\n---\n"
        total = int(st.get("practice_tasks_total", PRACTICE_TASKS_TOTAL))
        completed = int(st.get("tasks_completed", 0))
        prior_attempts = int(st.get("attempts_on_task", 0))
        last_assistant = str(st.get("last_assistant", ""))[:2000]
        user_prompt = prefix + (
            f"Task (LaTeX / context):\n{task}\n\nRubric:\n{rubric}\n\n"
            f"Your previous message to the student (context; may be empty):\n{last_assistant}\n\n"
            f"prior_attempts_on_this_task (before this message): {prior_attempts}\n\n"
            f"Student's latest message:\n{answer_text}\n\n"
            f"Practice tasks completed so far: {completed} / {total}\n"
            "If they solved the task correctly and counting this would finish all practice tasks, set next_task to null (the system adds the exam)."
        )
        data = await self.ollama.chat_json(GRADE_SYSTEM, user_prompt)

        correct = bool(data.get("correct"))
        feedback = str(data.get("feedback", ""))
        next_task = data.get("next_task")
        next_rubric = data.get("next_rubric")
        raw_counts = data.get("counts_as_attempt")
        counts_as_attempt = True if raw_counts is None else bool(raw_counts)

        if counts_as_attempt:
            st["attempts_on_task"] = int(st.get("attempts_on_task", 0)) + 1
            add_minutes = _session_minutes_for_answer(
                assigned_at=st.get("task_assigned_at"),
                now=datetime.now(timezone.utc),
                max_minutes=session_minutes_contribution,
            )
        else:
            add_minutes = min(2, max(1, session_minutes_contribution // 3 or 1))
        st["session_study_minutes"] = int(st.get("session_study_minutes", 0)) + add_minutes

        lines = [feedback]

        if correct:
            st["correct_count"] = int(st.get("correct_count", 0)) + 1
            st["tasks_completed"] = int(st.get("tasks_completed", 0)) + 1
            st["attempts_on_task"] = 0
            tc = int(st.get("tasks_completed", 0))

            if tc >= total:
                exam_msg = await self._generate_exam(session, st)
                st["segment"] = "exam"
                st["phase"] = "await_answer"
                st["current_task"] = exam_msg["exam_body"]
                st["rubric"] = exam_msg["exam_rubric"]
                st["task_assigned_at"] = _utc_now_iso()
                display = f"{feedback}\n\n📋 **Exam:**\n{st['current_task']}"
                st["last_assistant"] = display
                session.state = st
                await self._log_event(session.id, "assistant", display)
                await self.db.commit()
                meta = study_meta_from_state(st)
                return display, True, meta

            if next_task:
                st["current_task"] = str(next_task)
                st["rubric"] = str(next_rubric or "")
                lines.append(f"\n\n📝 **Next task:**\n{next_task}")
            else:
                fallback = "$$\\text{In one sentence, state the main takeaway from this topic.}$$"
                st["current_task"] = fallback
                st["rubric"] = "One clear sentence about the main idea."
                lines.append(f"\n\n📝 **Next task:**\n{fallback}")

        else:
            if counts_as_attempt:
                lines.append("\n\n🔄 Try again, or tap **Skip** to get a different question.")
            else:
                lines.append("\n\n🔄 Send your work when ready, or tap **Skip** for a different question.")

        st["last_assistant"] = "\n".join(lines)
        st["task_assigned_at"] = _utc_now_iso()
        session.state = st

        await self._log_event(session.id, "assistant", st["last_assistant"])
        await self.db.commit()
        meta = study_meta_from_state(st)
        return st["last_assistant"], correct, meta

    async def _submit_exam_answer(
        self, session: StudySession, st: dict[str, Any], answer_text: str
    ) -> tuple[str, bool, dict[str, Any]]:
        await self._log_event(session.id, "user", answer_text)
        exam = st.get("current_task", "")
        rubric = st.get("rubric", "")
        last_assistant = str(st.get("last_assistant", ""))[:2000]
        prompt = (
            f"Exam questions (LaTeX context):\n{exam}\n\nRubric:\n{rubric}\n\n"
            f"Your previous message to the student:\n{last_assistant}\n\n"
            f"Student message:\n{answer_text}"
        )
        data = await self.ollama.chat_json(EXAM_GRADE_SYSTEM, prompt)
        feedback = str(data.get("feedback", "Thanks for submitting."))
        is_submission = bool(data.get("is_exam_submission", True))

        if not is_submission:
            st["last_assistant"] = feedback
            session.state = st
            await self._log_event(session.id, "assistant", feedback)
            await self.db.commit()
            meta = study_meta_from_state(st)
            return feedback, False, meta

        ok = bool(data.get("correct", True))
        st["last_assistant"] = feedback
        st["phase"] = "exam_done"
        session.state = st
        await self._log_event(session.id, "assistant", feedback)
        await self.db.commit()
        meta = study_meta_from_state(st)
        return feedback, ok, meta

    async def _generate_exam(self, session: StudySession, st: dict[str, Any]) -> dict[str, str]:
        topic = st.get("topic_name", "the topic")
        theory = st.get("theory_body", "")
        mat = (st.get("material_excerpt") or "").strip()
        block = f"\n\nMaterial:\n{mat[:4000]}" if mat else ""
        user_prompt = f"Topic: {topic}\n\nTheory summary:\n{theory[:6000]}{block}\n\nWrite a concise final exam."
        data = await self.ollama.chat_json(EXAM_GENERATION_SYSTEM, user_prompt)
        exam = str(data.get("exam", "")).strip()
        rubric = str(data.get("rubric", "Overall correctness and reasoning.")).strip()
        if not exam:
            exam = "$$\\text{Answer briefly: what was the main idea of this session?}$$"
        return {"exam_body": exam, "exam_rubric": rubric}

    async def skip_task(self, *, session_id: UUID, user_id: UUID) -> tuple[str, dict[str, Any]]:
        session = await self._get_active(session_id, user_id)
        st = dict(session.state)
        if st.get("segment") == "theory":
            raise ValueError("Nothing to skip yet — tap Continue to start tasks.")
        if st.get("segment") == "exam":
            raise ValueError("Exam cannot be skipped — answer or use End session.")
        topic_name = st.get("topic_name", "the topic")
        mat = (st.get("material_excerpt") or "").strip()
        mat_block = f"\n\nAlign with this material:\n{mat[:4000]}" if mat else ""
        user_prompt = (
            f'Student skipped this task: "{st.get("current_task")}". '
            f"Give ONE easier replacement task on {topic_name}.{mat_block} JSON only with keys: "
            '"task", "rubric"'
        )
        data = await self.ollama.chat_json(
            "Reply with JSON only: task (string), rubric (string).", user_prompt
        )
        task = str(data.get("task", "$$\\text{Name one key idea from the topic.}$$"))
        rubric = str(data.get("rubric", "Any reasonable answer."))
        st["current_task"] = task
        st["rubric"] = rubric
        st["attempts_on_task"] = 0
        st["session_study_minutes"] = int(st.get("session_study_minutes", 0)) + 2
        st["task_assigned_at"] = _utc_now_iso()
        msg = f"⏭ Skipped.\n\n📝 **Next task:**\n{task}"
        st["last_assistant"] = msg
        session.state = st
        await self._log_event(session.id, "assistant", msg)
        await self.db.commit()
        meta = study_meta_from_state(st)
        return msg, meta

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


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _session_minutes_for_answer(
    *,
    assigned_at: str | None,
    now: datetime,
    max_minutes: int = 5,
) -> int:
    if max_minutes <= 0:
        return 0
    if not assigned_at:
        return max_minutes
    try:
        started = datetime.fromisoformat(assigned_at)
    except ValueError:
        return max_minutes
    if started.tzinfo is None:
        started = started.replace(tzinfo=timezone.utc)
    elapsed_seconds = (now - started).total_seconds()
    if elapsed_seconds <= 0:
        return 0
    return min(max_minutes, max(1, math.ceil(elapsed_seconds / 60)))


async def get_active_session_for_user(db: AsyncSession, user_id: UUID) -> StudySession | None:
    r = await db.execute(
        select(StudySession)
        .where(StudySession.user_id == user_id, StudySession.status == SessionStatus.active)
        .order_by(StudySession.started_at.desc())
        .limit(1)
    )
    return r.scalar_one_or_none()
