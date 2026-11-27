"""drop thread_id from sessions

Revision ID: a1c2e3f4b5d6
Revises: 31b770dbe6f5
Create Date: 2026-10-08 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "a1c2e3f4b5d6"
down_revision: Union[str, Sequence[str], None] = "31b770dbe6f5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_index(op.f("ix_sessions_thread_id"), table_name="sessions")
    op.drop_column("sessions", "thread_id")


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column(
        "sessions",
        sa.Column("thread_id", sa.String(length=255), nullable=False),
    )
    op.create_index(
        op.f("ix_sessions_thread_id"), "sessions", ["thread_id"], unique=True
    )
