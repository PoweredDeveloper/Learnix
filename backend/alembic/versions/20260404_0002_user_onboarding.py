"""user onboarding + learning profile

Revision ID: 0002
Revises: 0001
Create Date: 2026-04-04

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("onboarding_completed", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.add_column("users", sa.Column("learning_profile", JSONB(), nullable=True))
    op.alter_column("users", "onboarding_completed", server_default=None)


def downgrade() -> None:
    op.drop_column("users", "learning_profile")
    op.drop_column("users", "onboarding_completed")
