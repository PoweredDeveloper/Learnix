from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import authenticate_user, get_db, get_ollama
from app.api.ollama_http import raise_for_ollama_http
from app.models.entities import Course, CourseStatus, Lesson, User
from app.schemas.dto import CourseCreateIn, CourseOut, LessonChatIn, LessonOut
from app.services.course_gen import (
    chat_with_lesson,
    complete_lesson,
    generate_course,
    get_course_with_progress,
    get_lesson_chat,
)
from app.services.ollama import OllamaClient

router = APIRouter(prefix="/web-courses", tags=["web-courses"])


@router.get("", response_model=list[CourseOut])
async def list_courses(
    user: User = Depends(authenticate_user),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    result = await db.execute(
        select(Course)
        .where(Course.user_id == user.id, Course.status != CourseStatus.archived)
        .order_by(Course.created_at.desc())
    )
    courses = result.scalars().all()

    out = []
    for c in courses:
        lessons_result = await db.execute(
            select(Lesson).where(Lesson.course_id == c.id)
        )
        lessons = lessons_result.scalars().all()
        completed = sum(1 for l in lessons if l.status.value == "completed")
        out.append(
            {
                "id": c.id,
                "name": c.name,
                "description": c.description,
                "duration_label": c.duration_label,
                "status": c.status.value,
                "total_lessons": c.total_lessons,
                "completed_lessons": completed,
                "created_at": c.created_at,
            }
        )
    return out


@router.get("/{course_id}")
async def get_course(
    course_id: UUID,
    user: User = Depends(authenticate_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    data = await get_course_with_progress(db, course_id, user.id)
    if not data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")
    return data


@router.post("/create")
async def create_course(
    body: CourseCreateIn,
    user: User = Depends(authenticate_user),
    db: AsyncSession = Depends(get_db),
    ollama: OllamaClient = Depends(get_ollama),
) -> dict:
    try:
        course = await generate_course(
            db=db,
            ollama=ollama,
            user_id=user.id,
            name=body.name,
            description=body.description,
            duration_label=body.duration_label,
        )
    except httpx.HTTPError as e:
        raise_for_ollama_http(e)
    except (ValueError, KeyError) as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"AI generation failed: {e}",
        ) from e

    data = await get_course_with_progress(db, course.id, user.id)
    await db.commit()
    return data


@router.delete("/{course_id}")
async def archive_course(
    course_id: UUID,
    user: User = Depends(authenticate_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    result = await db.execute(
        select(Course).where(Course.id == course_id, Course.user_id == user.id)
    )
    course = result.scalar_one_or_none()
    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")
    course.status = CourseStatus.archived
    await db.commit()
    return {"status": "archived"}


@router.get("/{course_id}/lessons/{lesson_id}", response_model=LessonOut)
async def get_lesson(
    course_id: UUID,
    lesson_id: UUID,
    user: User = Depends(authenticate_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    result = await db.execute(
        select(Course).where(Course.id == course_id, Course.user_id == user.id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")

    les_result = await db.execute(
        select(Lesson).where(Lesson.id == lesson_id, Lesson.course_id == course_id)
    )
    lesson = les_result.scalar_one_or_none()
    if not lesson:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lesson not found")

    return {
        "id": lesson.id,
        "course_id": lesson.course_id,
        "section_index": lesson.section_index,
        "lesson_index": lesson.lesson_index,
        "title": lesson.title,
        "lesson_type": lesson.lesson_type.value,
        "status": lesson.status.value,
        "sort_order": lesson.sort_order,
        "content": lesson.content_json,
    }


@router.post("/{course_id}/lessons/{lesson_id}/complete", response_model=LessonOut)
async def mark_lesson_complete(
    course_id: UUID,
    lesson_id: UUID,
    user: User = Depends(authenticate_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    try:
        lesson = await complete_lesson(db, course_id, lesson_id, user.id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    await db.commit()
    return {
        "id": lesson.id,
        "course_id": lesson.course_id,
        "section_index": lesson.section_index,
        "lesson_index": lesson.lesson_index,
        "title": lesson.title,
        "lesson_type": lesson.lesson_type.value,
        "status": lesson.status.value,
        "sort_order": lesson.sort_order,
        "content": lesson.content_json,
    }


@router.post("/{course_id}/lessons/{lesson_id}/chat")
async def lesson_chat(
    course_id: UUID,
    lesson_id: UUID,
    body: LessonChatIn,
    user: User = Depends(authenticate_user),
    db: AsyncSession = Depends(get_db),
    ollama: OllamaClient = Depends(get_ollama),
) -> dict:
    try:
        reply = await chat_with_lesson(
            db=db,
            ollama=ollama,
            course_id=course_id,
            lesson_id=lesson_id,
            user_id=user.id,
            message=body.message,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except httpx.HTTPError as e:
        raise_for_ollama_http(e)
    await db.commit()
    return {"reply": reply}


@router.get("/{course_id}/lessons/{lesson_id}/chat")
async def get_chat_messages(
    course_id: UUID,
    lesson_id: UUID,
    user: User = Depends(authenticate_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    messages = await get_lesson_chat(db, lesson_id, user.id)
    return {"messages": messages}
