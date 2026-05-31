from datetime import datetime
from typing import Any
from uuid import uuid4

from calliope.config import EMBEDDING_DIMENSIONS
from calliope.db.base import Base
from calliope.db.types import EmbeddingVector
from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column, relationship


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex}"


class Workspace(Base):
    __tablename__ = "workspaces"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: new_id("workspace"))
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    root_path: Mapped[str] = mapped_column(Text, nullable=False)
    include_globs: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    exclude_globs: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    # Nullable tri-state: NULL inherits the global CALLIOPE_VERSIONING_ENABLED flag;
    # True/False is an explicit per-workspace override.
    versioning_enabled: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    documents: Mapped[list["Document"]] = relationship(
        back_populates="workspace",
        cascade="all, delete-orphan",
    )


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: new_id("document"))
    workspace_id: Mapped[str] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    path: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    frontmatter_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    content_hash: Mapped[str] = mapped_column(String, nullable=False)
    modified_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    indexed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    workspace: Mapped[Workspace] = relationship(back_populates="documents")
    chunks: Mapped[list["Chunk"]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
    )

    __table_args__ = (Index("ix_documents_workspace_path", "workspace_id", "path", unique=True),)


class Chunk(Base):
    __tablename__ = "chunks"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: new_id("chunk"))
    document_id: Mapped[str] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    heading_path: Mapped[str] = mapped_column(Text, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    token_count: Mapped[int] = mapped_column(Integer, nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    embedding: Mapped[list[float] | None] = mapped_column(EmbeddingVector(EMBEDDING_DIMENSIONS))
    search_vector: Mapped[str | None] = mapped_column(TSVECTOR)

    document: Mapped[Document] = relationship(back_populates="chunks")

    __table_args__ = (
        Index("ix_chunks_document_index", "document_id", "chunk_index", unique=True),
        Index("ix_chunks_search_vector", "search_vector", postgresql_using="gin"),
        Index(
            "ix_chunks_embedding",
            "embedding",
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_l2_ops"},
        ),
    )


class ConversationFolder(Base):
    __tablename__ = "conversation_folders"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: new_id("folder"))
    name: Mapped[str] = mapped_column(Text, nullable=False)
    parent_id: Mapped[str | None] = mapped_column(
        ForeignKey("conversation_folders.id", ondelete="CASCADE"),
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    parent: Mapped["ConversationFolder | None"] = relationship(
        remote_side="ConversationFolder.id",
        back_populates="children",
    )
    children: Mapped[list["ConversationFolder"]] = relationship(
        back_populates="parent",
        cascade="all, delete-orphan",
    )
    sessions: Mapped[list["ChatSession"]] = relationship(back_populates="folder")


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: new_id("session"))
    title: Mapped[str | None] = mapped_column(Text)
    folder_id: Mapped[str | None] = mapped_column(
        ForeignKey("conversation_folders.id", ondelete="SET NULL"),
    )
    # Nullable: the workspace a conversation belongs to is captured on the first
    # turn. Sessions predating this column stay NULL and are filtered out of every
    # workspace-scoped listing rather than being shown or reassigned.
    workspace_id: Mapped[str | None] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Nullable: only write-mode sessions hold a canvas; chat-only sessions leave this NULL.
    canvas: Mapped[str | None] = mapped_column(Text)

    folder: Mapped[ConversationFolder | None] = relationship(back_populates="sessions")
    messages: Mapped[list["ChatMessage"]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
    )
    retrieval_traces: Mapped[list["RetrievalTrace"]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
    )


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: new_id("message"))
    session_id: Mapped[str] = mapped_column(
        ForeignKey("chat_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    role: Mapped[str] = mapped_column(String, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)

    session: Mapped[ChatSession] = relationship(back_populates="messages")
    retrieval_traces: Mapped[list["RetrievalTrace"]] = relationship(
        back_populates="message",
        passive_deletes=True,
    )


class RetrievalTrace(Base):
    __tablename__ = "retrieval_traces"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: new_id("trace"))
    session_id: Mapped[str] = mapped_column(
        ForeignKey("chat_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    message_id: Mapped[str | None] = mapped_column(
        ForeignKey("chat_messages.id", ondelete="SET NULL"),
    )
    query: Mapped[str] = mapped_column(Text, nullable=False)
    policy: Mapped[str] = mapped_column(String, nullable=False)
    selected_sources_json: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False)
    scores_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    session: Mapped[ChatSession] = relationship(back_populates="retrieval_traces")
    message: Mapped[ChatMessage | None] = relationship(back_populates="retrieval_traces")


class ConnectionProfile(Base):
    __tablename__ = "connection_profiles"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: new_id("profile"))
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    kind: Mapped[str] = mapped_column(String, nullable=False)
    base_url: Mapped[str] = mapped_column(Text, nullable=False)
    model: Mapped[str] = mapped_column(Text, nullable=False)
    api_key_ref: Mapped[str | None] = mapped_column(Text)
    capabilities_json: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    # server_default=true preserves local-backend behaviour for all existing rows
    # without a data migration step.
    prefer_min_p: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    # Nullable: operators who are happy with policy defaults leave this unset.
    sampling_override_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    # Per-profile completion ceiling. NULL inherits Settings.default_max_tokens; an
    # explicit value lets a small-context local model and a large commercial model
    # carry different limits without changing the global default.
    max_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
