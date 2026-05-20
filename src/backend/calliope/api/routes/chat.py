from typing import Annotated

from calliope.api.dependencies import (
    get_chat_client,
    get_db_session,
    get_embedding_client,
)
from calliope.domain.schemas import ChatRequest, ChatResponse
from calliope.ingest.indexer import EmbeddingClient
from calliope.retrieval.hybrid import _AsyncRunner, aclose_client
from calliope.services.chat import ChatClient, ChatService
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

router = APIRouter()


@router.post("/v1/chat", response_model=ChatResponse)
def chat(
    request: ChatRequest,
    session: Annotated[Session, Depends(get_db_session)],
) -> ChatResponse:
    embedding_client: EmbeddingClient = get_embedding_client(session)
    try:
        chat_client: ChatClient = get_chat_client(session)
    except Exception:
        runner = _AsyncRunner()
        try:
            runner.run(aclose_client(embedding_client))
        except Exception:
            pass
        finally:
            runner.close()
        raise

    service = ChatService(
        session,
        embedding_client=embedding_client,
        chat_client=chat_client,
        close_embedding_client=True,
        close_chat_client=True,
    )
    operation_error: Exception | None = None
    try:
        return service.chat(request)
    except Exception as exc:
        operation_error = exc
        raise
    finally:
        try:
            service.close()
        except Exception:
            if operation_error is None:
                raise
