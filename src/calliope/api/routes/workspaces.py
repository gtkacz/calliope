from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from calliope.api.dependencies import get_db_session, get_embedding_client
from calliope.domain.schemas import (
    ReindexRequest,
    ReindexResponse,
    WorkspaceCreate,
    WorkspaceRead,
)
from calliope.ingest.indexer import EmbeddingClient, Reindexer
from calliope.services.workspaces import WorkspaceService

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
    embedding_client: Annotated[EmbeddingClient, Depends(get_embedding_client)],
) -> ReindexResponse:
    result = Reindexer(session, embedding_client=embedding_client).reindex_workspace(
        payload.workspace_id
    )
    return ReindexResponse(
        documents_indexed=result.documents_indexed,
        chunks_indexed=result.chunks_indexed,
    )
