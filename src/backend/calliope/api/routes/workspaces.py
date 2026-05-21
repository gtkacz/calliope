from typing import Annotated

from calliope.api.dependencies import get_db_session, get_embedding_client
from calliope.domain.schemas import (
    ReindexRequest,
    ReindexResponse,
    WorkspaceCreate,
    WorkspacePatch,
    WorkspaceRead,
)
from calliope.ingest.indexer import EmbeddingClient, Reindexer
from calliope.services.workspaces import WorkspaceService
from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

router = APIRouter()


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
) -> ReindexResponse:
    embedding_client: EmbeddingClient = get_embedding_client(session)
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
