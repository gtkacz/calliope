from typing import Annotated

from calliope.api.dependencies import get_db_session, get_embedding_client, get_settings
from calliope.config import Settings
from calliope.domain.schemas import (
    GlobPreviewBucket,
    GlobPreviewRequest,
    GlobPreviewResponse,
    ReindexRequest,
    ReindexResponse,
    WorkspaceCreate,
    WorkspacePatch,
    WorkspaceRead,
)
from calliope.ingest.scanner import preview_workspace_globs
from calliope.services.filesystem import FilesystemService
from calliope.ingest.indexer import EmbeddingClient, Reindexer
from calliope.services.workspaces import WorkspaceService
from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

router = APIRouter()


@router.post("/v1/workspaces/glob-preview", response_model=GlobPreviewResponse)
def preview_workspace_globs_route(
    payload: GlobPreviewRequest,
    settings: Annotated[Settings, Depends(get_settings)],
) -> GlobPreviewResponse:
    root = FilesystemService(browse_root=settings.browse_root).resolve_directory(payload.root_path)
    preview = preview_workspace_globs(root, payload.include_globs, payload.exclude_globs)
    return GlobPreviewResponse(
        visited_count=preview.visited_count,
        included=GlobPreviewBucket(count=preview.included_count, paths=preview.included_paths),
        ignored=GlobPreviewBucket(count=preview.ignored_count, paths=preview.ignored_paths),
        truncated=preview.truncated,
    )


@router.post("/v1/workspaces", response_model=WorkspaceRead)
def create_workspace(
    payload: WorkspaceCreate,
    session: Annotated[Session, Depends(get_db_session)],
) -> WorkspaceRead:
    return WorkspaceService(session).create(payload)


@router.get("/v1/workspaces", response_model=list[WorkspaceRead])
def list_workspaces(
    session: Annotated[Session, Depends(get_db_session)],
) -> list[WorkspaceRead]:
    return WorkspaceService(session).list()


@router.get("/v1/workspaces/{workspace_id}", response_model=WorkspaceRead)
def get_workspace(
    workspace_id: str,
    session: Annotated[Session, Depends(get_db_session)],
) -> WorkspaceRead:
    return WorkspaceService(session).get(workspace_id)


@router.patch("/v1/workspaces/{workspace_id}", response_model=WorkspaceRead)
def update_workspace(
    workspace_id: str,
    payload: WorkspacePatch,
    session: Annotated[Session, Depends(get_db_session)],
) -> WorkspaceRead:
    return WorkspaceService(session).update(workspace_id, payload)


@router.delete("/v1/workspaces/{workspace_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_workspace(
    workspace_id: str,
    session: Annotated[Session, Depends(get_db_session)],
) -> Response:
    WorkspaceService(session).delete(workspace_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/v1/reindex", response_model=ReindexResponse)
def reindex_workspace(
    payload: ReindexRequest,
    session: Annotated[Session, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> ReindexResponse:
    embedding_client: EmbeddingClient = get_embedding_client(session, settings)
    reindexer = Reindexer(
        session,
        embedding_client=embedding_client,
        close_embedding_client=True,
    )
    result = reindexer.reindex_workspace(payload.workspace_id)
    return ReindexResponse(
        documents_indexed=result.documents_indexed,
        chunks_indexed=result.chunks_indexed,
    )
