from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from calliope.api.dependencies import (
    close_model_client,
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
    embedding_client: Annotated[EmbeddingClient, Depends(get_embedding_client)],
    chat_client: Annotated[ChatClient, Depends(get_chat_client)],
) -> ChatResponse:
    service = ChatService(
        session,
        embedding_client=embedding_client,
        chat_client=chat_client,
    )
    try:
        return service.chat(request)
    finally:
        service.close()
        close_model_client(embedding_client)
        if chat_client is not embedding_client:
            close_model_client(chat_client)
