import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from app.services.course_gen import generate_course, complete_lesson, get_course_with_progress
from app.models.entities import Course, CourseStatus, Lesson, LessonChat, LessonStatus, LessonType


class FakeOllama:
    def __init__(self):
        self.call_count = 0
        self.responses = [
            {
                "sections": [
                    {
                        "title": "Basics",
                        "lessons": [
                            {"title": "Intro", "type": "theory"},
                            {"title": "Practice 1", "type": "practice"},
                            {"title": "Final Exam", "type": "exam"},
                        ],
                    }
                ]
            },
            {"body": "# Introduction\nThis is theory."},
            {"body": "Solve this:", "task": "$$x^2$$", "rubric": "Factor it."},
            {
                "body": "Answer these:",
                "questions": [{"question": "What is 2+2?", "rubric": "Should be 4"}],
            },
        ]

    async def chat_json(self, system: str, user: str) -> dict:
        resp = self.responses[self.call_count % len(self.responses)]
        self.call_count += 1
        return resp


class FakeDB:
    """Minimal fake async session for unit testing."""

    def __init__(self):
        self.added = []
        self.flushed = False

    def add(self, obj):
        self.added.append(obj)

    async def flush(self):
        self.flushed = True
        for obj in self.added:
            if hasattr(obj, "id") and obj.id is None:
                obj.id = uuid4()

    async def execute(self, stmt):
        return FakeResult([])


class FakeResult:
    def __init__(self, items):
        self._items = items

    def scalars(self):
        return self

    def all(self):
        return self._items

    def scalar_one_or_none(self):
        return self._items[0] if self._items else None


@pytest.mark.asyncio
async def test_generate_course_creates_lessons():
    db = FakeDB()
    ollama = FakeOllama()

    course = await generate_course(
        db=db,
        ollama=ollama,
        user_id=uuid4(),
        name="Test Course",
        description="Learn testing",
        duration_label="3d",
    )

    assert course.status == CourseStatus.ready
    assert course.total_lessons == 3
    assert course.name == "Test Course"

    lessons = [o for o in db.added if isinstance(o, Lesson)]
    assert len(lessons) == 3

    assert lessons[0].status == LessonStatus.active
    assert lessons[0].lesson_type == LessonType.theory
    assert lessons[1].status == LessonStatus.locked
    assert lessons[1].lesson_type == LessonType.practice
    assert lessons[2].status == LessonStatus.locked
    assert lessons[2].lesson_type == LessonType.exam

    assert ollama.call_count == 4


@pytest.mark.asyncio
async def test_generate_course_handles_empty_syllabus():
    db = FakeDB()
    ollama = FakeOllama()
    ollama.responses = [{"sections": []}]

    course = await generate_course(
        db=db,
        ollama=ollama,
        user_id=uuid4(),
        name="Empty",
        description="",
        duration_label="2h",
    )

    assert course.status == CourseStatus.ready
    assert course.total_lessons == 0


@pytest.mark.asyncio
async def test_generate_course_handles_unknown_lesson_type():
    db = FakeDB()
    ollama = FakeOllama()
    ollama.responses = [
        {
            "sections": [
                {
                    "title": "S1",
                    "lessons": [{"title": "L1", "type": "unknown_type"}],
                }
            ]
        },
        {"body": "Content"},
    ]

    course = await generate_course(
        db=db,
        ollama=ollama,
        user_id=uuid4(),
        name="Fallback",
        description="test",
        duration_label="1d",
    )

    lessons = [o for o in db.added if isinstance(o, Lesson)]
    assert len(lessons) == 1
    assert lessons[0].lesson_type == LessonType.theory
