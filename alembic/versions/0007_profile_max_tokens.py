from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0007_profile_max_tokens"
down_revision: str | None = "0006_profile_sampling"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Nullable with no server_default: existing rows read NULL and inherit the
    # application-level Settings.default_max_tokens, so no data backfill is needed.
    op.add_column(
        "connection_profiles",
        sa.Column("max_tokens", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("connection_profiles", "max_tokens")
