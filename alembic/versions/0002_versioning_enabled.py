from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0002_versioning_enabled"
down_revision: str | None = "0001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "workspaces",
        sa.Column("versioning_enabled", sa.Boolean(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("workspaces", "versioning_enabled")
