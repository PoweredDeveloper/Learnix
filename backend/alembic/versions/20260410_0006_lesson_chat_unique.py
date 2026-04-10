"""Deduplicate lesson_chats and enforce one row per (lesson_id, user_id)

Revision ID: 0006
Revises: 0005
Create Date: 2026-04-10

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        sa.text("""
        DELETE FROM lesson_chats a
        USING lesson_chats b
        WHERE a.lesson_id = b.lesson_id
          AND a.user_id = b.user_id
          AND (a.updated_at, a.id) < (b.updated_at, b.id)
        """)
    )
    op.create_unique_constraint(
        "uq_lesson_chats_lesson_user",
        "lesson_chats",
        ["lesson_id", "user_id"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_lesson_chats_lesson_user", "lesson_chats", type_="unique")
