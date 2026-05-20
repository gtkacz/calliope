from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from calliope.api.dependencies import (
    get_chat_client,
    get_db_session,
    get_embedding_client,
)
from calliope.domain.schemas import ChatRequest, ChatResponse
from calliope.ingest.indexer import EmbeddingClient
from calliope.services.chat import ChatClient, ChatService

router = APIRouter()


@router.post("/v1/chat", response_model=ChatResponse)
def chat(
    request: ChatRequest,
    session: Annotated[Session, Depends(get_db_session)],
) -> ChatResponse:
    embedding_client: EmbeddingClient = get_embedding_client(session)
    chat_client: ChatClient = get_chat_client(session)
    service = ChatService(
        session,
        embedding_client=embedding_client,
        chat_client=chat_client,
        close_embedding_client=True,
        close_chat_client=True,
    )
    try:
        return service.chat(request)
    finally:
        service.close()
