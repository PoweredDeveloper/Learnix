import json
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entities import Course, CourseStatus, Lesson, LessonChat, LessonStatus, LessonType, StudyLog, User
from app.services.ollama import OllamaClient
from app.services.streak import local_today


def _estimated_lesson_study_minutes(lesson: Lesson) -> int:
    raw = lesson.content_json or {}
    em = raw.get("estimated_minutes")
    if isinstance(em, (int, float)) and em > 0:
        return min(int(em), 120)
    if lesson.lesson_type == LessonType.theory:
        return 10
    if lesson.lesson_type == LessonType.practice:
        return 15
    if lesson.lesson_type == LessonType.exam:
        return 20
    return 12

SYLLABUS_SYSTEM = """You are an expert course-curriculum designer.
Given a topic, description, and desired duration, produce a structured course syllabus as JSON.
Adjust depth to the duration:
  - Short (2h, 12h): 1–2 sections, 5–10 lessons total.
  - Medium (1w): 3–5 sections, 10–20 lessons.
  - Long (1month+): 5–8 sections, 20–40 lessons.
Mix lesson types: mostly "theory", sprinkle in "practice" for hands-on tasks,
and end each section with an "exam" lesson.

Return ONLY valid JSON in this exact shape (no markdown fences):
{"sections": [{"title": "Section Name", "lessons": [{"title": "Lesson Title", "type": "theory|practice|exam"}]}]}"""

LESSON_CONTENT_SYSTEM = """You are an expert educational content writer.
Generate detailed lesson content as JSON. Use **bold**, *italic*, and LaTeX
($$...$$ for display math, $...$ for inline math) inside markdown strings.
Be thorough, educational, and include real-world examples.

Depending on the lesson type, return ONLY valid JSON (no markdown fences):

For type "theory":
{"body": "Detailed markdown lesson body with LaTeX where appropriate."}

For type "practice":
{"body": "Task description in markdown.", "task": "The problem statement, may include LaTeX.", "rubric": "Grading criteria."}

For type "exam":
{"body": "Exam instructions in markdown.", "questions": [{"question": "Question text with LaTeX if needed.", "rubric": "How this question is graded."}]}"""

LESSON_CHAT_SYSTEM = """You are a friendly, encouraging tutor helping a student with a lesson.
You have access to the lesson content below. When the student asks a question:
- Give helpful hints rather than full answers when they're working on practice problems.
- Explain concepts clearly with examples.
- Answer follow-up questions patiently.
- Use LaTeX ($...$ inline, $$...$$ display) when writing math.
- If the user asks for grading JSON (boolean "correct" and string "feedback"), make the outer response {{"reply": "<string>"}} where the inner string is valid JSON only: double quotes, lowercase true/false. Put math in "feedback" as readable LaTeX (e.g. $x=2\\\\sin\\\\theta$), never one character per line. Do not use Python dict syntax with single quotes.

Lesson content:
{lesson_content}

Conversation so far:
{history}

Respond with ONLY valid JSON: {{"reply": "Your helpful response here."}}"""


async def generate_course(
    db: AsyncSession,
    ollama: OllamaClient,
    user_id: UUID,
    name: str,
    description: str,
    duration_label: str,
    file_text: str | None = None,
    on_progress: Any = None,
) -> Course:
    course = Course(
        user_id=user_id,
        name=name,
        description=description,
        duration_label=duration_label,
        status=CourseStatus.generating,
    )
    db.add(course)
    await db.flush()

    async def _log(msg: str) -> None:
        if on_progress:
            await on_progress(msg)

    await _log("Generating course syllabus...")

    user_prompt = f"Topic: {name}\nDescription: {description}\nDuration: {duration_label}"
    if file_text:
        user_prompt += f"\n\nReference material (use this as the primary source):\n{file_text[:15_000]}"

    syllabus = await ollama.chat_json(
        system=SYLLABUS_SYSTEM,
        user=user_prompt,
    )

    sections = syllabus.get("sections", [])
    total_lessons = sum(len(s.get("lessons", [])) for s in sections)
    await _log(f"Syllabus ready — {len(sections)} sections, {total_lessons} lessons")

    sort_order = 0
    first_lesson = True
    for sec_i, section in enumerate(sections):
        sec_title = section.get("title", f"Section {sec_i + 1}")
        for les_i, les in enumerate(section.get("lessons", [])):
            les_title = les.get("title", f"Lesson {les_i + 1}")
            raw_type = les.get("type", "theory")
            try:
                lesson_type = LessonType(raw_type)
            except ValueError:
                lesson_type = LessonType.theory

            await _log(f"Generating {lesson_type.value}: {les_title}")

            content = await ollama.chat_json(
                system=LESSON_CONTENT_SYSTEM,
                user=(
                    f"Course: {name}\n"
                    f"Section: {sec_title}\n"
                    f"Lesson title: {les_title}\n"
                    f"Lesson type: {lesson_type.value}"
                ),
            )

            lesson = Lesson(
                course_id=course.id,
                section_index=sec_i,
                lesson_index=les_i,
                title=les_title,
                lesson_type=lesson_type,
                content_json=content,
                status=LessonStatus.active if first_lesson else LessonStatus.locked,
                sort_order=sort_order,
            )
            db.add(lesson)
            first_lesson = False
            sort_order += 1

            await _log(f"✓ {les_title} ({sort_order}/{total_lessons})")

    course.syllabus_json = syllabus
    course.total_lessons = sort_order
    course.status = CourseStatus.ready
    await db.flush()
    await _log("Course ready!")
    return course


async def get_course_with_progress(
    db: AsyncSession,
    course_id: UUID,
    user_id: UUID,
) -> dict[str, Any]:
    result = await db.execute(
        select(Course).where(Course.id == course_id, Course.user_id == user_id)
    )
    course = result.scalar_one_or_none()
    if not course:
        return {}

    lessons_result = await db.execute(
        select(Lesson).where(Lesson.course_id == course_id).order_by(Lesson.sort_order)
    )
    lessons = list(lessons_result.scalars().all())
    completed = sum(1 for l in lessons if l.status == LessonStatus.completed)

    return {
        "id": course.id,
        "name": course.name,
        "description": course.description,
        "duration_label": course.duration_label,
        "status": course.status.value,
        "total_lessons": course.total_lessons,
        "completed_lessons": completed,
        "created_at": course.created_at,
        "lessons": [
            {
                "id": l.id,
                "course_id": l.course_id,
                "section_index": l.section_index,
                "lesson_index": l.lesson_index,
                "title": l.title,
                "lesson_type": l.lesson_type.value,
                "status": l.status.value,
                "sort_order": l.sort_order,
                "content": l.content_json,
            }
            for l in lessons
        ],
    }


async def complete_lesson(
    db: AsyncSession,
    course_id: UUID,
    lesson_id: UUID,
    user_id: UUID,
) -> Lesson:
    result = await db.execute(
        select(Course).where(Course.id == course_id, Course.user_id == user_id)
    )
    course = result.scalar_one_or_none()
    if not course:
        raise ValueError("Course not found")

    les_result = await db.execute(
        select(Lesson).where(Lesson.id == lesson_id, Lesson.course_id == course_id)
    )
    lesson = les_result.scalar_one_or_none()
    if not lesson:
        raise ValueError("Lesson not found")

    prior_status = lesson.status
    lesson.status = LessonStatus.completed

    if prior_status != LessonStatus.completed:
        user = await db.get(User, user_id)
        tz = (user.timezone if user and user.timezone else None) or "UTC"
        log_date = local_today(tz)
        minutes = _estimated_lesson_study_minutes(lesson)
        db.add(
            StudyLog(
                user_id=user_id,
                topic_id=None,
                status="web_lesson",
                time_spent=minutes,
                log_date=log_date,
            )
        )

    next_result = await db.execute(
        select(Lesson)
        .where(Lesson.course_id == course_id, Lesson.sort_order > lesson.sort_order)
        .order_by(Lesson.sort_order)
        .limit(1)
    )
    next_lesson = next_result.scalar_one_or_none()
    if next_lesson and next_lesson.status == LessonStatus.locked:
        next_lesson.status = LessonStatus.active

    await db.flush()
    return lesson


async def _resolve_lesson_chat_row(
    db: AsyncSession,
    lesson_id: UUID,
    user_id: UUID,
) -> LessonChat | None:
    """
    One row per (lesson_id, user_id). Merges duplicate rows (no DB unique before migration),
    dedupes messages by (role, content, ts).
    """
    result = await db.execute(
        select(LessonChat)
        .where(LessonChat.lesson_id == lesson_id, LessonChat.user_id == user_id)
        .order_by(LessonChat.updated_at.desc(), LessonChat.id.desc())
    )
    rows = list(result.scalars().all())
    if not rows:
        return None
    if len(rows) == 1:
        return rows[0]
    primary = rows[0]
    merged: list[dict[str, Any]] = []
    for c in sorted(rows, key=lambda x: (x.created_at, x.id)):
        merged.extend(list(c.messages or []))
    seen: set[tuple[str, str, str]] = set()
    deduped: list[dict[str, Any]] = []
    for m in merged:
        key = (str(m.get("role", "")), str(m.get("content", "")), str(m.get("ts", "")))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(m)
    primary.messages = deduped
    for extra in rows[1:]:
        await db.delete(extra)
    await db.flush()
    return primary


async def chat_with_lesson(
    db: AsyncSession,
    ollama: OllamaClient,
    course_id: UUID,
    lesson_id: UUID,
    user_id: UUID,
    message: str,
) -> str:
    les_result = await db.execute(
        select(Lesson).where(Lesson.id == lesson_id, Lesson.course_id == course_id)
    )
    lesson = les_result.scalar_one_or_none()
    if not lesson:
        raise ValueError("Lesson not found")

    chat = await _resolve_lesson_chat_row(db, lesson_id, user_id)
    if not chat:
        chat = LessonChat(lesson_id=lesson_id, user_id=user_id, messages=[])
        db.add(chat)
        await db.flush()

    history_lines = []
    for msg in chat.messages:
        role = msg.get("role", "user")
        history_lines.append(f"{role}: {msg.get('content', '')}")
    history_text = "\n".join(history_lines) if history_lines else "(no prior messages)"

    lesson_content = json.dumps(lesson.content_json or {}, ensure_ascii=False)[:8000]
    system_prompt = LESSON_CHAT_SYSTEM.format(
        lesson_content=lesson_content,
        history=history_text,
    )

    response = await ollama.chat_json(system=system_prompt, user=message)
    reply = response.get("reply", str(response))

    updated_messages = list(chat.messages) + [
        {"role": "user", "content": message, "ts": datetime.now(timezone.utc).isoformat()},
        {"role": "assistant", "content": reply, "ts": datetime.now(timezone.utc).isoformat()},
    ]
    chat.messages = updated_messages
    await db.flush()
    return reply


async def get_lesson_chat(
    db: AsyncSession,
    lesson_id: UUID,
    user_id: UUID,
) -> list[dict[str, Any]]:
    chat = await _resolve_lesson_chat_row(db, lesson_id, user_id)
    if not chat:
        return []
    return list(chat.messages)
