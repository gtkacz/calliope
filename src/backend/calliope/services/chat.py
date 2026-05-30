from __future__ import annotations

from typing import Protocol

from calliope.domain.schemas import ChatRequest, ChatResponse, CitedDocument, SearchRequest
from calliope.prompts.builder import build_chat_messages
from calliope.repositories.chats import ChatRepository
from calliope.repositories.chunks import ChunkRepository
from calliope.repositories.documents import DocumentRepository
from calliope.retrieval.hybrid import EmbeddingClient, _AsyncRunner, aclose_client
from calliope.services.search import SearchService
from sqlalchemy.orm import Session


class ChatClient(Protocol):
    async def chat(self, messages: list[dict[str, str]]) -> str: ...


class ChatService:
    def __init__(
        self,
        session: Session,
        *,
        embedding_client: EmbeddingClient,
        chat_client: ChatClient,
        close_embedding_client: bool = False,
        close_chat_client: bool = False,
    ) -> None:
        self.session = session
        self.embedding_client = embedding_client
        self.chat_client = chat_client
        self._async_runner = _AsyncRunner()
        self._close_embedding_client = close_embedding_client
        self._close_chat_client = close_chat_client

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
        except Exception:
            try:
                search_service.close()
            except Exception:
                pass
            raise
        finally:
            if "search_response" in locals():
                search_service.close()

        chunk_repo = ChunkRepository(self.session)
        doc_repo = DocumentRepository(self.session)
        cited_documents: list[CitedDocument] = []
        for doc_id in request.cited_document_ids:
            try:
                doc = doc_repo.get(doc_id)
            except Exception:
                continue
            # Silently skip documents from other workspaces to prevent data leakage.
            if request.workspace_id is not None and doc.workspace_id != request.workspace_id:
                continue
            cited_documents.append(
                CitedDocument(
                    document_id=doc.id,
                    path=doc.path,
                    title=doc.title,
                    content=chunk_repo.text_for_document(doc.id),
                )
            )

        messages = build_chat_messages(
            message=request.message,
            policy=request.policy,
            sources=search_response.sources,
            cited_documents=cited_documents or None,
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
                metadata={"turn_kind": "chat_user"},
            )
            assistant_message = repository.add_message(
                session_id=session_id,
                role="assistant",
                content=answer,
                metadata={
                    "turn_kind": "assistant",
                    "policy": request.policy.value,
                    "chat_profile_id": request.chat_profile_id,
                    "source_count": len(search_response.sources),
                    "sources": [
                        source.model_dump(mode="json") for source in search_response.sources
                    ],
                    "cited_document_ids": [doc.document_id for doc in cited_documents],
                    "cited_paths": [doc.path for doc in cited_documents],
                },
            )
            trace = repository.add_trace(
                session_id=session_id,
                message_id=assistant_message.id,
                query=request.message,
                policy=request.policy,
                sources=search_response.sources,
                scores={source.chunk_id: source.score for source in search_response.sources},
            )
            repository.touch_session(session_id)
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise

        return ChatResponse(
            session=repository.get_session_summary(session_id),
            user_message=repository.message_to_read(user_message),
            assistant_message=repository.message_to_read(assistant_message),
            answer=answer,
            sources=search_response.sources,
            trace_id=trace.id,
        )

    def close(self) -> None:
        cleanup_error: Exception | None = None
        try:
            closed_client_ids: set[int] = set()
            if self._close_embedding_client:
                closed_client_ids.add(id(self.embedding_client))
                try:
                    self._async_runner.run(aclose_client(self.embedding_client))
                except Exception as exc:
                    cleanup_error = exc
            if self._close_chat_client and id(self.chat_client) not in closed_client_ids:
                try:
                    self._async_runner.run(aclose_client(self.chat_client))
                except Exception as exc:
                    if cleanup_error is None:
                        cleanup_error = exc
        finally:
            try:
                self._async_runner.close()
            except Exception as exc:
                if cleanup_error is None:
                    cleanup_error = exc

        if cleanup_error is not None:
            raise cleanup_error
