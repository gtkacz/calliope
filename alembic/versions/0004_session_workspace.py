from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0004_session_workspace"
down_revision: str | None = "0003_embedding_dims_1024"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Nullable: existing conversations have no workspace and must not be force-fit
    # into one. They stay NULL and are hidden from every workspace-scoped listing.
    op.add_column(
        "chat_sessions",
        sa.Column("workspace_id", sa.String(), nullable=True),
    )
    op.create_foreign_key(
        "fk_chat_sessions_workspace_id",
        "chat_sessions",
        "workspaces",
        ["workspace_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index(
        "ix_chat_sessions_workspace_id",
        "chat_sessions",
        ["workspace_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_chat_sessions_workspace_id", table_name="chat_sessions")
    op.drop_constraint("fk_chat_sessions_workspace_id", "chat_sessions", type_="foreignkey")
    op.drop_column("chat_sessions", "workspace_id")
