from typing import Annotated

from calliope.api.dependencies import get_db_session, get_embedding_client
from calliope.domain.schemas import (
    ReindexRequest,
    ReindexResponse,
    WorkspaceCreate,
    WorkspaceRead,
)
from calliope.ingest.indexer import EmbeddingClient, Reindexer
from calliope.services.workspaces import WorkspaceService
from fastapi import APIRouter, Depends
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
