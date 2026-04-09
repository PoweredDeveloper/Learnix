"""courses, lessons, and lesson chats

Revision ID: 0004
Revises: 0003
Create Date: 2026-04-07

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "courses",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("subject_id", UUID(as_uuid=True), sa.ForeignKey("subjects.id"), nullable=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), server_default="", nullable=False),
        sa.Column("duration_label", sa.String(32), server_default="1w", nullable=False),
        sa.Column(
            "status",
            sa.Enum("generating", "ready", "archived", name="coursestatus"),
            server_default="generating",
            nullable=False,
        ),
        sa.Column("syllabus_json", JSONB, nullable=True),
        sa.Column("total_lessons", sa.Integer(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_courses_user_id", "courses", ["user_id"])

    op.create_table(
        "lessons",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("course_id", UUID(as_uuid=True), sa.ForeignKey("courses.id"), nullable=False),
        sa.Column("section_index", sa.Integer(), server_default="0", nullable=False),
        sa.Column("lesson_index", sa.Integer(), server_default="0", nullable=False),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column(
            "lesson_type",
            sa.Enum("theory", "practice", "exam", name="lessontype"),
            server_default="theory",
            nullable=False,
        ),
        sa.Column("content_json", JSONB, nullable=True),
        sa.Column(
            "status",
            sa.Enum("locked", "active", "completed", name="lessonstatus"),
            server_default="locked",
            nullable=False,
        ),
        sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_lessons_course_id", "lessons", ["course_id"])

    op.create_table(
        "lesson_chats",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("lesson_id", UUID(as_uuid=True), sa.ForeignKey("lessons.id"), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("messages", JSONB, server_default="[]", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_lesson_chats_lesson_id", "lesson_chats", ["lesson_id"])
    op.create_index("ix_lesson_chats_user_id", "lesson_chats", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_lesson_chats_user_id", table_name="lesson_chats")
    op.drop_index("ix_lesson_chats_lesson_id", table_name="lesson_chats")
    op.drop_table("lesson_chats")

    op.drop_index("ix_lessons_course_id", table_name="lessons")
    op.drop_table("lessons")

    op.drop_index("ix_courses_user_id", table_name="courses")
    op.drop_table("courses")

    op.execute("DROP TYPE lessonstatus")
    op.execute("DROP TYPE lessontype")
    op.execute("DROP TYPE coursestatus")
