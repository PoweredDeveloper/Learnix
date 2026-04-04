"""init

Revision ID: 0001
Revises:
Create Date: 2026-04-04

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("name", sa.String(255), nullable=True),
        sa.Column("timezone", sa.String(64), nullable=False),
        sa.Column("streak_current", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("streak_best", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_streak_eligible_date", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_users_telegram_id", "users", ["telegram_id"], unique=True)

    op.create_table(
        "subjects",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("exam_date", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_subjects_user_id", "subjects", ["user_id"])

    op.create_table(
        "topics",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("subject_id", UUID(as_uuid=True), sa.ForeignKey("subjects.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("difficulty_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("is_weak", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_topics_subject_id", "topics", ["subject_id"])

    op.create_table(
        "study_plans",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("subject_id", UUID(as_uuid=True), sa.ForeignKey("subjects.id"), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    op.create_table(
        "study_tasks",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("plan_id", UUID(as_uuid=True), sa.ForeignKey("study_plans.id"), nullable=False),
        sa.Column("topic_id", UUID(as_uuid=True), sa.ForeignKey("topics.id"), nullable=True),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "status",
            sa.Enum("pending", "done", "skipped", name="taskstatus"),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("estimated_minutes", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_study_tasks_plan_id", "study_tasks", ["plan_id"])

    op.create_table(
        "prep_sources",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("subject_id", UUID(as_uuid=True), sa.ForeignKey("subjects.id"), nullable=True),
        sa.Column("file_path", sa.String(1024), nullable=False),
        sa.Column("extracted_text", sa.Text(), nullable=False, server_default=""),
        sa.Column("outline_json", JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    op.create_table(
        "cheat_sheets",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("subject_id", UUID(as_uuid=True), sa.ForeignKey("subjects.id"), nullable=False),
        sa.Column("prep_source_id", UUID(as_uuid=True), sa.ForeignKey("prep_sources.id"), nullable=True),
        sa.Column("content_md", sa.Text(), nullable=False, server_default=""),
        sa.Column("density", sa.String(32), nullable=False, server_default="normal"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    op.create_table(
        "study_logs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("topic_id", UUID(as_uuid=True), sa.ForeignKey("topics.id"), nullable=True),
        sa.Column("status", sa.String(64), nullable=False),
        sa.Column("time_spent", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("log_date", sa.Date(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_study_logs_user_id", "study_logs", ["user_id"])

    op.create_table(
        "study_sessions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("topic_id", UUID(as_uuid=True), sa.ForeignKey("topics.id"), nullable=True),
        sa.Column("subject_id", UUID(as_uuid=True), sa.ForeignKey("subjects.id"), nullable=True),
        sa.Column(
            "status",
            sa.Enum("active", "ended", name="sessionstatus"),
            nullable=False,
            server_default="active",
        ),
        sa.Column("state", JSONB(), nullable=False, server_default="{}"),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_study_sessions_user_id", "study_sessions", ["user_id"])

    op.create_table(
        "session_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("session_id", UUID(as_uuid=True), sa.ForeignKey("study_sessions.id"), nullable=False),
        sa.Column("role", sa.String(32), nullable=False),
        sa.Column("payload", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_session_events_session_id", "session_events", ["session_id"])


def downgrade() -> None:
    op.drop_table("session_events")
    op.drop_table("study_sessions")
    op.drop_table("study_logs")
    op.drop_table("cheat_sheets")
    op.drop_table("prep_sources")
    op.drop_table("study_tasks")
    op.drop_table("study_plans")
    op.drop_table("topics")
    op.drop_table("subjects")
    op.drop_table("users")
    op.execute("DROP TYPE IF EXISTS sessionstatus")
    op.execute("DROP TYPE IF EXISTS taskstatus")
