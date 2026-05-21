from __future__ import annotations

from datetime import datetime
from typing import Any

from calliope.domain.enums import CanonPolicy, ProfileCapability, ProfileKind
from pydantic import BaseModel, Field


class WorkspaceCreate(BaseModel):
    name: str
    root_path: str
    include_globs: list[str] = Field(default_factory=lambda: ["**/*.md", "**/*.markdown"])
    exclude_globs: list[str] = Field(
        default_factory=lambda: [".git/**", ".venv/**", "node_modules/**"]
    )


class WorkspacePatch(BaseModel):
    name: str | None = None
    root_path: str | None = None
    include_globs: list[str] | None = None
    exclude_globs: list[str] | None = None


class WorkspaceRead(WorkspaceCreate):
    id: str
    created_at: datetime


class ProfileCreate(BaseModel):
    name: str
    kind: ProfileKind = ProfileKind.OPENAI_COMPATIBLE
    base_url: str
    model: str
    api_key_ref: str | None = None
    capabilities: list[ProfileCapability]


class ProfilePatch(BaseModel):
    name: str | None = None
    kind: ProfileKind | None = None
    base_url: str | None = None
    model: str | None = None
    api_key_ref: str | None = None
    capabilities: list[ProfileCapability] | None = None


class ProfileRead(ProfileCreate):
    id: str
    created_at: datetime


class SourceReference(BaseModel):
    document_id: str
    chunk_id: str
    path: str
    heading: str
    excerpt: str
    score: float


class SearchRequest(BaseModel):
    query: str
    workspace_id: str | None = None
    session_id: str | None = None
    limit: int = Field(default=8, ge=1, le=50)
    persist: bool = False


class SearchResponse(BaseModel):
    sources: list[SourceReference]
    session: SessionSummary | None = None
    search_message: MessageRead | None = None


class ReindexRequest(BaseModel):
    workspace_id: str


class ReindexResponse(BaseModel):
    documents_indexed: int
    chunks_indexed: int


class ChatRequest(BaseModel):
    message: str
    policy: CanonPolicy = CanonPolicy.STRICT_CANON
    session_id: str | None = None
    workspace_id: str | None = None
    chat_profile_id: str | None = None
    limit: int = Field(default=8, ge=1, le=50)


class DocumentRead(BaseModel):
    id: str
    workspace_id: str
    path: str
    title: str
    frontmatter: dict[str, Any]
    modified_at: datetime
    indexed_at: datetime | None


class ConversationFolderCreate(BaseModel):
    name: str
    parent_id: str | None = None
    position: int = 0


class ConversationFolderPatch(BaseModel):
    name: str | None = None
    parent_id: str | None = None
    position: int | None = None


class ConversationFolderRead(BaseModel):
    id: str
    name: str
    parent_id: str | None
    position: int
    created_at: datetime
    updated_at: datetime


class SessionSummary(BaseModel):
    id: str
    title: str | None
    folder_id: str | None
    created_at: datetime
    updated_at: datetime


class MessageRead(BaseModel):
    id: str
    session_id: str
    role: str
    content: str
    metadata: dict[str, Any]
    created_at: datetime


class ChatResponse(BaseModel):
    session: SessionSummary
    user_message: MessageRead
    assistant_message: MessageRead
    answer: str
    sources: list[SourceReference]
    trace_id: str


class SessionDetail(SessionSummary):
    messages: list[MessageRead]


class SessionPatch(BaseModel):
    title: str | None = None
    folder_id: str | None = None


SessionRead = SessionSummary
