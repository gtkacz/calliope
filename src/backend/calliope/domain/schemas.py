from __future__ import annotations

from datetime import datetime
from typing import Any

from calliope.domain.constants import VERSION_STORE_DIRNAME
from calliope.domain.enums import CanonPolicy, EditMode, ProfileCapability, ProfileKind
from pydantic import BaseModel, Field


class WorkspaceCreate(BaseModel):
    name: str
    root_path: str
    include_globs: list[str] = Field(default_factory=lambda: ["**/*.md", "**/*.markdown"])
    exclude_globs: list[str] = Field(
        default_factory=lambda: [
            ".git/**",
            ".venv/**",
            "node_modules/**",
            f"{VERSION_STORE_DIRNAME}/**",
        ]
    )
    # Tri-state: None inherits the global versioning flag; True/False overrides it.
    versioning_enabled: bool | None = None
    guidelines: str | None = None


class WorkspacePatch(BaseModel):
    name: str | None = None
    root_path: str | None = None
    include_globs: list[str] | None = None
    exclude_globs: list[str] | None = None
    versioning_enabled: bool | None = None
    guidelines: str | None = None


class WorkspaceRead(WorkspaceCreate):
    id: str
    created_at: datetime


class DirectoryEntry(BaseModel):
    name: str
    path: str
    is_dir: bool
    is_hidden: bool


class DirectoryListing(BaseModel):
    path: str
    parent: str | None
    entries: list[DirectoryEntry]
    # The configured browse root (read/write confinement boundary and the
    # picker's default open location), or None when unset. Lets the UI tell a
    # genuinely-empty subfolder apart from an empty configured root.
    browse_root: str | None = None


class FileContent(BaseModel):
    path: str
    content: str


class FileWriteRequest(BaseModel):
    path: str
    content: str
    # Optional label describing why the write happened (e.g. "manual save" or
    # "LLM edit: <instruction>"); recorded as the version-snapshot commit message.
    cause: str | None = None


class FileVersion(BaseModel):
    sha: str
    timestamp: datetime
    cause: str
    size_bytes: int
    is_binary: bool


class FileHistory(BaseModel):
    path: str
    versions: list[FileVersion]


class FileRestoreRequest(BaseModel):
    path: str
    sha: str


class ProfileCreate(BaseModel):
    name: str
    kind: ProfileKind = ProfileKind.OPENAI_COMPATIBLE
    base_url: str
    model: str
    api_key_ref: str | None = None
    capabilities: list[ProfileCapability]
    prefer_min_p: bool = True
    sampling_override: dict[str, Any] | None = None
    max_tokens: int | None = None


class ProfilePatch(BaseModel):
    name: str | None = None
    kind: ProfileKind | None = None
    base_url: str | None = None
    model: str | None = None
    api_key_ref: str | None = None
    capabilities: list[ProfileCapability] | None = None
    prefer_min_p: bool | None = None
    sampling_override: dict[str, Any] | None = None
    max_tokens: int | None = None


class ProfileRead(ProfileCreate):
    id: str
    created_at: datetime


class SourceReference(BaseModel):
    document_id: str
    chunk_id: str
    path: str
    heading: str
    context: str
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
    # 5 × ~1800 chars ≈ 9 000 chars of source text; fits comfortably within
    # typical context windows without the prompt budget concern of limit=8.
    limit: int = Field(default=5, ge=1, le=50)
    cited_document_ids: list[str] = Field(default_factory=list)
    # Whether to inject the workspace's standing guidelines (default on); the
    # web app toggles this per request.
    apply_guidelines: bool = True


class CitedDocument(BaseModel):
    document_id: str
    path: str
    title: str
    content: str


class EditProposalRequest(BaseModel):
    path: str
    instruction: str
    mode: EditMode = EditMode.APPEND
    chat_profile_id: str | None = None
    apply_guidelines: bool = True


class EditProposal(BaseModel):
    path: str
    mode: EditMode
    original_content: str
    proposed_content: str
    truncated: bool = False
    # The server reported a tokenized prompt far smaller than what was sent: part
    # of the prompt (document, instruction, or grounding) never reached the model.
    context_overflow: bool = False


class DocumentRead(BaseModel):
    id: str
    workspace_id: str
    path: str
    title: str
    frontmatter: dict[str, Any]
    modified_at: datetime
    indexed_at: datetime | None


class DocumentContent(BaseModel):
    id: str
    path: str
    title: str
    # The indexed body, reconstructed by joining the document's chunks in order.
    content: str
    # The full text of the cited chunk when a chunk_id is supplied, so the reader
    # can highlight the exact passage a citation came from. None when unrequested
    # or when the chunk does not belong to this document.
    passage: str | None = None


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
    workspace_id: str | None = None
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
    canvas: str | None = None


class SessionPatch(BaseModel):
    title: str | None = None
    folder_id: str | None = None
    # None means unchanged; an empty string clears the canvas.
    canvas: str | None = None


class WriteRequest(BaseModel):
    message: str
    canvas: str = ""
    policy: CanonPolicy = CanonPolicy.STRICT_CANON
    session_id: str | None = None
    workspace_id: str | None = None
    chat_profile_id: str | None = None
    # 5 × ~1800 chars ≈ 9 000 chars of source text; fits comfortably within
    # typical context windows without the prompt budget concern of limit=8.
    limit: int = Field(default=5, ge=1, le=50)
    cited_document_ids: list[str] = Field(default_factory=list)
    apply_guidelines: bool = True


class WriteResponse(BaseModel):
    session: SessionSummary
    user_message: MessageRead
    assistant_message: MessageRead
    canvas: str
    sources: list[SourceReference]
    trace_id: str


SessionRead = SessionSummary
