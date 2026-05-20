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
) -> SearchResponse:
    embedding_client: EmbeddingClient = get_embedding_client(session)
    service = SearchService(
        session,
        embedding_client,
        close_embedding_client=True,
    )
    operation_error: Exception | None = None
    try:
        return service.search(request)
    except Exception as exc:
        operation_error = exc
        raise
    finally:
        try:
            service.close()
        except Exception:
            if operation_error is None:
                raise
