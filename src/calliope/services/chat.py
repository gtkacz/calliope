from __future__ import annotations

from typing import Protocol

from sqlalchemy.orm import Session

from calliope.domain.schemas import ChatRequest, ChatResponse, SearchRequest
from calliope.prompts.builder import build_chat_messages
from calliope.repositories.chats import ChatRepository
from calliope.retrieval.hybrid import EmbeddingClient, _AsyncRunner
from calliope.services.search import SearchService


class ChatClient(Protocol):
    async def chat(self, messages: list[dict[str, str]]) -> str: ...


class ChatService:
    def __init__(
        self,
        session: Session,
        *,
        embedding_client: EmbeddingClient,
        chat_client: ChatClient,
    ) -> None:
        self.session = session
        self.embedding_client = embedding_client
        self.chat_client = chat_client
        self._async_runner = _AsyncRunner()

    def chat(self, request: ChatRequest) -> ChatResponse:
        repository = ChatRepository(self.session)
        if request.session_id is not None:
            repository.get_session_row(request.session_id)

        search_service = SearchService(
            self.session,
            self.embedding_client,
            async_runner=self._async_runner,
        )
        try:
            search_response = search_service.search(
                SearchRequest(
                    query=request.message,
                    workspace_id=request.workspace_id,
                    limit=request.limit,
                )
            )
        finally:
            search_service.close()

        messages = build_chat_messages(
            message=request.message,
            policy=request.policy,
            sources=search_response.sources,
        )
        answer = self._async_runner.run(self.chat_client.chat(messages))

        try:
            session_id = request.session_id
            if session_id is None:
                chat_session = repository.create_session(title=request.message[:80])
                session_id = chat_session.id

            user_message = repository.add_message(
                session_id=session_id,
                role="user",
                content=request.message,
                metadata={},
            )
            repository.add_message(
                session_id=session_id,
                role="assistant",
                content=answer,
                metadata={
                    "policy": request.policy.value,
                    "source_count": len(search_response.sources),
                },
            )
            trace = repository.add_trace(
                session_id=session_id,
                message_id=user_message.id,
                query=request.message,
                policy=request.policy,
                sources=search_response.sources,
                scores={source.chunk_id: source.score for source in search_response.sources},
            )
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise

        return ChatResponse(
            answer=answer,
            sources=search_response.sources,
            trace_id=trace.id,
        )

    def close(self) -> None:
        self._async_runner.close()
