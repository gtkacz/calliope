from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0005_session_canvas"
down_revision: str | None = "0004_session_workspace"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Nullable: only write-mode sessions carry a canvas value; existing and future
    # chat-only sessions leave this NULL.
    op.add_column(
        "chat_sessions",
        sa.Column("canvas", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("chat_sessions", "canvas")
