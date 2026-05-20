from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from calliope.api.dependencies import get_db_session, get_embedding_client
from calliope.domain.schemas import SearchRequest, SearchResponse
from calliope.ingest.indexer import EmbeddingClient
from calliope.services.search import SearchService

router = APIRouter()


@router.post("/v1/search", response_model=SearchResponse)
def search(
    request: SearchRequest,
    session: Annotated[Session, Depends(get_db_session)],
    embedding_client: Annotated[EmbeddingClient, Depends(get_embedding_client)],
) -> SearchResponse:
    service = SearchService(session, embedding_client)
    try:
        return service.search(request)
    finally:
        service.close()
