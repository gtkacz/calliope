from __future__ import annotations

from typing import Protocol

from calliope.domain.errors import AppError
from calliope.domain.schemas import ChatRequest, ChatResponse, CitedDocument, SearchRequest
from calliope.llm.openai_compatible import ChatCompletion
from calliope.prompts.budget import (
    PromptTrim,
    estimate_messages_chars,
    prompt_budget_chars,
    trim_to_budget,
)
from calliope.prompts.builder import (
    HistoryTurn,
    build_chat_messages,
    build_conversation_title_messages,
)
from calliope.repositories.chats import ChatRepository
from calliope.repositories.chunks import ChunkRepository
from calliope.repositories.documents import DocumentRepository
from calliope.retrieval.hybrid import EmbeddingClient, RerankClient, _AsyncRunner, aclose_client
from calliope.services.guidelines import resolve_workspace_guidelines
from calliope.services.search import SearchService
from sqlalchemy.orm import Session


class ChatClient(Protocol):
    async def chat(self, messages: list[dict[str, str]]) -> ChatCompletion: ...


class ChatService:
    def __init__(
        self,
        session: Session,
        *,
        embedding_client: EmbeddingClient,
        chat_client: ChatClient,
        close_embedding_client: bool = False,
        close_chat_client: bool = False,
        close_rerank_client: bool = False,
        score_threshold: float = 0.0,
        rerank_client: RerankClient | None = None,
    ) -> None:
        self.session = session
        self.embedding_client = embedding_client
        self.chat_client = chat_client
        self._async_runner = _AsyncRunner()
        self._close_embedding_client = close_embedding_client
        self._close_chat_client = close_chat_client
        self._close_rerank_client = close_rerank_client
        self._score_threshold = score_threshold
        self._rerank_client = rerank_client

    def chat(self, request: ChatRequest) -> ChatResponse:
        repository = ChatRepository(self.session)
        if request.session_id is not None:
            existing = repository.get_session_row(request.session_id)
            # A session is pinned to the workspace captured on its first turn;
            # refuse to add a turn under a different workspace.
            if (
                existing.workspace_id is not None
                and request.workspace_id is not None
                and existing.workspace_id != request.workspace_id
            ):
                raise AppError(
                    code="session_workspace_mismatch",
                    message="Session does not belong to the specified workspace.",
                    status_code=403,
                )

        history: list[HistoryTurn] | None = None
        if request.session_id is not None:
            history = repository.get_recent_history(request.session_id)

        search_service = SearchService(
            self.session,
            self.embedding_client,
            async_runner=self._async_runner,
            score_threshold=self._score_threshold,
            rerank_client=self._rerank_client,
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

        guidelines = resolve_workspace_guidelines(
            self.session,
            workspace_id=request.workspace_id,
            apply_guidelines=request.apply_guidelines,
        )
        sources = search_response.sources
        messages = build_chat_messages(
            message=request.message,
            policy=request.policy,
            sources=sources,
            cited_documents=cited_documents or None,
            history=history,
            guidelines=guidelines,
        )
        trim = PromptTrim()
        budget = prompt_budget_chars(self.chat_client)
        if budget is not None:
            overage = estimate_messages_chars(messages) - budget
            if overage > 0:
                sources, kept_cited, history, trim = trim_to_budget(
                    overage_chars=overage,
                    sources=sources,
                    cited_documents=cited_documents or None,
                    history=history,
                )
                cited_documents = kept_cited or []
                messages = build_chat_messages(
                    message=request.message,
                    policy=request.policy,
                    sources=sources,
                    cited_documents=cited_documents or None,
                    history=history,
                    guidelines=guidelines,
                )
        completion = self._async_runner.run(self.chat_client.chat(messages))
        answer = completion.content
        trim_metadata = trim.as_metadata()

        new_session_title: str | None = None
        if request.session_id is None:
            fallback_title = _fallback_conversation_title(request.message)
            new_session_title = self._generate_conversation_title(
                user_message=request.message,
                assistant_answer=answer,
                fallback=fallback_title,
            )

        try:
            session_id = request.session_id
            if session_id is None:
                chat_session = repository.create_session(
                    title=new_session_title,
                    workspace_id=request.workspace_id,
                )
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
                    "source_count": len(sources),
                    "sources": [source.model_dump(mode="json") for source in sources],
                    "cited_document_ids": [doc.document_id for doc in cited_documents],
                    "cited_paths": [doc.path for doc in cited_documents],
                    "truncated": completion.truncated,
                    "context_overflow": completion.context_overflow,
                    **({"prompt_trim": trim_metadata} if trim_metadata else {}),
                },
            )
            trace = repository.add_trace(
                session_id=session_id,
                message_id=assistant_message.id,
                query=request.message,
                policy=request.policy,
                sources=sources,
                scores={source.chunk_id: source.score for source in sources},
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
            sources=sources,
            trace_id=trace.id,
        )

    def _generate_conversation_title(
        self,
        *,
        user_message: str,
        assistant_answer: str,
        fallback: str,
    ) -> str:
        try:
            title_completion = self._async_runner.run(
                self.chat_client.chat(
                    build_conversation_title_messages(
                        user_message=user_message,
                        assistant_answer=assistant_answer,
                    )
                )
            )
        except Exception:
            return fallback
        return _clean_generated_title(title_completion.content, fallback=fallback)

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
            if self._close_rerank_client and self._rerank_client is not None:
                try:
                    self._async_runner.run(aclose_client(self._rerank_client))
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


def _fallback_conversation_title(message: str) -> str:
    return message.strip()[:80]


def _clean_generated_title(raw_title: str, *, fallback: str) -> str:
    lines = raw_title.strip().splitlines()
    if not lines:
        return fallback
    title = lines[0].strip()
    if title.lower().startswith("title:"):
        title = title[6:].strip()
    title = " ".join(title.strip(" \"'`").split())
    title = title.rstrip(".!?").strip()
    if not title:
        return fallback
    if len(title) > 60:
        title = title[:60].rstrip()
    return title
