from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0006_profile_sampling"
down_revision: str | None = "0005_session_canvas"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # prefer_min_p default=true preserves local-backend behaviour for all
    # existing profiles without requiring a data migration step.
    op.add_column(
        "connection_profiles",
        sa.Column("prefer_min_p", sa.Boolean(), nullable=False, server_default="true"),
    )
    # Nullable: operators who are happy with policy defaults leave this unset.
    op.add_column(
        "connection_profiles",
        sa.Column(
            "sampling_override_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("connection_profiles", "sampling_override_json")
    op.drop_column("connection_profiles", "prefer_min_p")
