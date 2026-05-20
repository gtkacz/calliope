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
    limit: int = Field(default=8, ge=1, le=50)


class SearchResponse(BaseModel):
    sources: list[SourceReference]


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
    limit: int = Field(default=8, ge=1, le=50)


class ChatResponse(BaseModel):
    answer: str
    sources: list[SourceReference]
    trace_id: str


class DocumentRead(BaseModel):
    id: str
    workspace_id: str
    path: str
    title: str
    frontmatter: dict[str, Any]
    modified_at: datetime
    indexed_at: datetime | None


class SessionRead(BaseModel):
    id: str
    title: str | None
    created_at: datetime
    updated_at: datetime
