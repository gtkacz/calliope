from collections.abc import Sequence

from pgvector.sqlalchemy import Vector

from alembic import op

revision: str = "0003_embedding_dims_1024"
down_revision: str | None = "0002_versioning_enabled"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Widths before/after this migration. The HNSW index is dimension-bound, so the
# column type cannot be altered while the index exists; it must be dropped and
# rebuilt around the ALTER.
_OLD_DIM = 384
_NEW_DIM = 1024


def upgrade() -> None:
    op.drop_index("ix_chunks_embedding", table_name="chunks", postgresql_using="hnsw")
    op.alter_column(
        "chunks",
        "embedding",
        existing_type=Vector(_OLD_DIM),
        type_=Vector(_NEW_DIM),
        existing_nullable=True,
    )
    op.create_index(
        "ix_chunks_embedding",
        "chunks",
        ["embedding"],
        unique=False,
        postgresql_using="hnsw",
        postgresql_ops={"embedding": "vector_l2_ops"},
    )


def downgrade() -> None:
    op.drop_index("ix_chunks_embedding", table_name="chunks", postgresql_using="hnsw")
    # pgvector cannot cast a stored vector to a different width, and shrinking the
    # column invalidates every embedding regardless, so clear them before the
    # type change; a re-index repopulates the column at the old width.
    op.execute("UPDATE chunks SET embedding = NULL")
    op.alter_column(
        "chunks",
        "embedding",
        existing_type=Vector(_NEW_DIM),
        type_=Vector(_OLD_DIM),
        existing_nullable=True,
    )
    op.create_index(
        "ix_chunks_embedding",
        "chunks",
        ["embedding"],
        unique=False,
        postgresql_using="hnsw",
        postgresql_ops={"embedding": "vector_l2_ops"},
    )
