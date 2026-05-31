from typing import Annotated

from calliope.api.dependencies import (
    get_chat_client_for_profile,
    get_db_session,
    get_embedding_client,
    get_settings,
)
from calliope.config import Settings
from calliope.domain.schemas import WriteRequest, WriteResponse
from calliope.ingest.indexer import EmbeddingClient
from calliope.retrieval.hybrid import _AsyncRunner, aclose_client
from calliope.services.write import ChatClient, WriteService
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

router = APIRouter()


@router.post("/v1/write", response_model=WriteResponse)
def write(
    request: WriteRequest,
    session: Annotated[Session, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> WriteResponse:
    embedding_client: EmbeddingClient = get_embedding_client(session, settings)
    try:
        chat_client: ChatClient = get_chat_client_for_profile(
            session,
            request.chat_profile_id,
            settings,
        )
    except Exception:
        runner = _AsyncRunner()
        try:
            runner.run(aclose_client(embedding_client))
        except Exception:
            pass
        finally:
            runner.close()
        raise

    service = WriteService(
        session,
        embedding_client=embedding_client,
        chat_client=chat_client,
        close_embedding_client=True,
        close_chat_client=True,
    )
    operation_error: Exception | None = None
    try:
        return service.write(request)
    except Exception as exc:
        operation_error = exc
        raise
    finally:
        try:
            service.close()
        except Exception:
            if operation_error is None:
                raise
