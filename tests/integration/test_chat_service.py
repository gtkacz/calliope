import asyncio
from datetime import UTC, datetime
from pathlib import Path

import pytest
from calliope.config import EMBEDDING_DIMENSIONS
from calliope.domain.enums import CanonPolicy
from calliope.domain.schemas import ChatRequest, SourceReference, WorkspaceCreate
from calliope.ingest.indexer import Reindexer
from calliope.llm.openai_compatible import ChatCompletion
from calliope.repositories.chats import ChatRepository
from calliope.repositories.chunks import ChunkRepository
from calliope.repositories.workspaces import WorkspaceRepository
from calliope.retrieval.hybrid import HybridRetriever
from calliope.services.chat import ChatService
from sqlalchemy.orm import Session


class FakeEmbeddingClient:
    async def embed(self, text: str) -> list[float]:
        value = 1.0 if "Kaelen" in text else 0.1
        return [value] * EMBEDDING_DIMENSIONS


class FakeChatClient:
    async def chat(self, messages: list[dict[str, str]]) -> ChatCompletion:
        return ChatCompletion(content="Kaelen was exiled from Velmora. [characters/kaelen.md]")


class RecordingTitleChatClient:
    def __init__(self) -> None:
        self.calls: list[list[dict[str, str]]] = []

    async def chat(self, messages: list[dict[str, str]]) -> ChatCompletion:
        self.calls.append(messages)
        if len(self.calls) == 1:
            return ChatCompletion(content="Kaelen was exiled from Velmora. [characters/kaelen.md]")
        return ChatCompletion(content='"Kaelen Exile"')


def test_chat_service_returns_grounded_answer_and_trace(db_session: Session) -> None:
    workspace = WorkspaceRepository(db_session).create(
        WorkspaceCreate(
            name="chat-world",
            root_path=str(Path("tests/fixtures/world").resolve()),
        )
    )
    embedding_client = FakeEmbeddingClient()
    Reindexer(db_session, embedding_client=embedding_client).reindex_workspace(workspace.id)

    service = ChatService(
        db_session,
        embedding_client=embedding_client,
        chat_client=FakeChatClient(),
    )
    try:
        response = service.chat(
            ChatRequest(
                message="Where was Kaelen exiled from?",
                policy=CanonPolicy.STRICT_CANON,
                workspace_id=workspace.id,
            )
        )
    finally:
        service.close()

    assert "Velmora" in response.answer
    assert response.sources
    assert response.trace_id.startswith("trace_")
    assert response.session.id.startswith("session_")
    assert response.answer
    assert response.user_message.role == "user"
    assert response.assistant_message.role == "assistant"


def test_chat_service_titles_new_session_with_separate_llm_call(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_vector_search(self, embedding, *, workspace_id, limit):
        return ["chunk_a"]

    def fake_lexical_search(self, query, *, workspace_id, limit):
        return ["chunk_a"]

    def fake_source_for_chunk(self, chunk_id, score=1.0):
        return SourceReference(
            document_id="document_a",
            chunk_id=chunk_id,
            path="characters/kaelen.md",
            heading="Kaelen",
            context="Kaelen exile",
            score=score,
        )

    monkeypatch.setattr(HybridRetriever, "_vector_search", fake_vector_search)
    monkeypatch.setattr(HybridRetriever, "_lexical_search", fake_lexical_search)
    monkeypatch.setattr(ChunkRepository, "source_for_chunk", fake_source_for_chunk)

    client = RecordingTitleChatClient()
    service = ChatService(
        db_session,
        embedding_client=FakeEmbeddingClient(),
        chat_client=client,
    )
    try:
        response = service.chat(
            ChatRequest(
                message="Where was Kaelen exiled from?",
                chat_profile_id="profile_chat",
                limit=1,
            )
        )
    finally:
        service.close()

    assert len(client.calls) == 2
    assert "Indexed canon sources" in client.calls[0][-1]["content"]
    assert "short title" in client.calls[1][0]["content"]
    assert response.session.title == "Kaelen Exile"
    assert ChatRepository(db_session).get_session_summary(response.session.id).title == (
        "Kaelen Exile"
    )


def test_chat_service_persists_frontend_messages_and_returns_session_payload(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_vector_search(self, embedding, *, workspace_id, limit):
        return ["chunk_a"]

    def fake_lexical_search(self, query, *, workspace_id, limit):
        return ["chunk_a"]

    def fake_source_for_chunk(self, chunk_id, score=1.0):
        return SourceReference(
            document_id="document_a",
            chunk_id=chunk_id,
            path="characters/kaelen.md",
            heading="Kaelen",
            context="Kaelen exile",
            score=score,
        )

    monkeypatch.setattr(HybridRetriever, "_vector_search", fake_vector_search)
    monkeypatch.setattr(HybridRetriever, "_lexical_search", fake_lexical_search)
    monkeypatch.setattr(ChunkRepository, "source_for_chunk", fake_source_for_chunk)

    service = ChatService(
        db_session,
        embedding_client=FakeEmbeddingClient(),
        chat_client=FakeChatClient(),
    )
    try:
        response = service.chat(
            ChatRequest(
                message="Where was Kaelen exiled from?",
                chat_profile_id="profile_chat",
                limit=1,
            )
        )
    finally:
        service.close()

    assert response.session.id.startswith("session_")
    assert response.user_message.metadata == {"turn_kind": "chat_user"}
    assert response.assistant_message.metadata["turn_kind"] == "assistant"
    assert response.assistant_message.metadata["chat_profile_id"] == "profile_chat"
    assert response.assistant_message.metadata["source_count"] == 1
    assert response.sources[0].path == "characters/kaelen.md"


def test_chat_service_updates_existing_session_summary_after_new_turn(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_vector_search(self, embedding, *, workspace_id, limit):
        return ["chunk_a"]

    def fake_lexical_search(self, query, *, workspace_id, limit):
        return ["chunk_a"]

    def fake_source_for_chunk(self, chunk_id, score=1.0):
        return SourceReference(
            document_id="document_a",
            chunk_id=chunk_id,
            path="characters/kaelen.md",
            heading="Kaelen",
            context="Kaelen exile",
            score=score,
        )

    monkeypatch.setattr(HybridRetriever, "_vector_search", fake_vector_search)
    monkeypatch.setattr(HybridRetriever, "_lexical_search", fake_lexical_search)
    monkeypatch.setattr(ChunkRepository, "source_for_chunk", fake_source_for_chunk)

    repository = ChatRepository(db_session)
    chat_session = repository.create_session(title="Existing")
    chat_session.updated_at = datetime(2025, 1, 1, tzinfo=UTC)
    db_session.commit()
    original_updated_at = chat_session.updated_at

    service = ChatService(
        db_session,
        embedding_client=FakeEmbeddingClient(),
        chat_client=FakeChatClient(),
    )
    try:
        response = service.chat(
            ChatRequest(
                message="Where was Kaelen exiled from?",
                session_id=chat_session.id,
                limit=1,
            )
        )
    finally:
        service.close()

    refreshed_summary = repository.get_session_summary(chat_session.id)
    assert response.session == refreshed_summary
    assert response.session.updated_at > original_updated_at


class LoopRecordingChatClient:
    def __init__(self) -> None:
        self.loops: list[asyncio.AbstractEventLoop] = []
        self.close_loops: list[asyncio.AbstractEventLoop] = []

    async def embed(self, text: str) -> list[float]:
        self._record_loop()
        return [0.1] * EMBEDDING_DIMENSIONS

    async def chat(self, messages: list[dict[str, str]]) -> ChatCompletion:
        self._record_loop()
        return ChatCompletion(content="Kaelen was exiled from Velmora. [characters/kaelen.md]")

    def _record_loop(self) -> None:
        loop = asyncio.get_running_loop()
        if self.loops and loop is not self.loops[0]:
            raise AssertionError("ChatService used multiple event loops for one async client")
        self.loops.append(loop)

    async def aclose(self) -> None:
        self.close_loops.append(asyncio.get_running_loop())


class FailingCloseChatClient(LoopRecordingChatClient):
    async def aclose(self) -> None:
        await super().aclose()
        raise RuntimeError("chat close failed")


def test_chat_service_reuses_one_event_loop_for_shared_embedding_and_chat_client(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_vector_search(
        self: HybridRetriever,
        embedding: list[float],
        *,
        workspace_id: str | None,
        limit: int,
    ) -> list[str]:
        return ["chunk_a"]

    def fake_lexical_search(
        self: HybridRetriever,
        query: str,
        *,
        workspace_id: str | None,
        limit: int,
    ) -> list[str]:
        return ["chunk_a"]

    def fake_source_for_chunk(
        self: ChunkRepository,
        chunk_id: str,
        score: float = 1.0,
    ) -> SourceReference:
        return SourceReference(
            document_id="document_a",
            chunk_id=chunk_id,
            path="characters/kaelen.md",
            heading="Kaelen",
            context="Kaelen exile",
            score=score,
        )

    monkeypatch.setattr(HybridRetriever, "_vector_search", fake_vector_search)
    monkeypatch.setattr(HybridRetriever, "_lexical_search", fake_lexical_search)
    monkeypatch.setattr(ChunkRepository, "source_for_chunk", fake_source_for_chunk)

    client = LoopRecordingChatClient()
    service = ChatService(db_session, embedding_client=client, chat_client=client)
    try:
        service.chat(ChatRequest(message="Where was Kaelen exiled from?", limit=1))
        service.chat(ChatRequest(message="Where was Kaelen exiled from?", limit=1))
    finally:
        service.close()

    assert len(client.loops) == 6
    assert len({id(loop) for loop in client.loops}) == 1


def test_chat_service_closes_owned_clients_on_shared_async_loop(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_vector_search(
        self: HybridRetriever,
        embedding: list[float],
        *,
        workspace_id: str | None,
        limit: int,
    ) -> list[str]:
        return ["chunk_a"]

    def fake_lexical_search(
        self: HybridRetriever,
        query: str,
        *,
        workspace_id: str | None,
        limit: int,
    ) -> list[str]:
        return ["chunk_a"]

    def fake_source_for_chunk(
        self: ChunkRepository,
        chunk_id: str,
        score: float = 1.0,
    ) -> SourceReference:
        return SourceReference(
            document_id="document_a",
            chunk_id=chunk_id,
            path="characters/kaelen.md",
            heading="Kaelen",
            context="Kaelen exile",
            score=score,
        )

    monkeypatch.setattr(HybridRetriever, "_vector_search", fake_vector_search)
    monkeypatch.setattr(HybridRetriever, "_lexical_search", fake_lexical_search)
    monkeypatch.setattr(ChunkRepository, "source_for_chunk", fake_source_for_chunk)

    client = LoopRecordingChatClient()
    service = ChatService(
        db_session,
        embedding_client=client,
        chat_client=client,
        close_embedding_client=True,
        close_chat_client=True,
    )

    service.chat(ChatRequest(message="Where was Kaelen exiled from?", limit=1))
    service.close()

    assert client.close_loops == [client.loops[0]]


def test_chat_service_search_cleanup_does_not_mask_search_error(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_source_for_chunk(
        self: ChunkRepository,
        chunk_id: str,
        score: float = 1.0,
    ) -> SourceReference:
        raise RuntimeError("source lookup failed")

    monkeypatch.setattr(HybridRetriever, "_vector_search", lambda *args, **kwargs: ["chunk_a"])
    monkeypatch.setattr(HybridRetriever, "_lexical_search", lambda *args, **kwargs: ["chunk_a"])
    monkeypatch.setattr(ChunkRepository, "source_for_chunk", fail_source_for_chunk)

    client = FailingCloseChatClient()
    service = ChatService(
        db_session,
        embedding_client=client,
        chat_client=client,
        close_embedding_client=True,
        close_chat_client=True,
    )

    with pytest.raises(RuntimeError, match="source lookup failed"):
        try:
            service.chat(ChatRequest(message="Where was Kaelen exiled from?", limit=1))
        except Exception:
            try:
                service.close()
            except Exception:
                pass
            raise

    assert client.close_loops == [client.loops[0]]
