"""web session token for browser access

Revision ID: 0003
Revises: 0002
Create Date: 2026-04-04

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("web_session_token", sa.String(length=128), nullable=True))
    op.add_column(
        "users",
        sa.Column("web_session_expires_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_users_web_session_token", "users", ["web_session_token"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_users_web_session_token", table_name="users")
    op.drop_column("users", "web_session_expires_at")
    op.drop_column("users", "web_session_token")
