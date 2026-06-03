from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0008_workspace_guidelines"
down_revision: str | None = "0007_profile_max_tokens"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Nullable with no server_default: existing workspaces read NULL and behave
    # exactly as before (no standing guidelines), so no data backfill is needed.
    op.add_column(
        "workspaces",
        sa.Column("guidelines", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("workspaces", "guidelines")
