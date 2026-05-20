import asyncio
from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from calliope.domain.enums import CanonPolicy
from calliope.domain.schemas import ChatRequest, SourceReference, WorkspaceCreate
from calliope.ingest.indexer import Reindexer
from calliope.repositories.chunks import ChunkRepository
from calliope.repositories.workspaces import WorkspaceRepository
from calliope.retrieval.hybrid import HybridRetriever
from calliope.services.chat import ChatService


class FakeEmbeddingClient:
    async def embed(self, text: str) -> list[float]:
        value = 1.0 if "Kaelen" in text else 0.1
        return [value] * 384


class FakeChatClient:
    async def chat(self, messages: list[dict[str, str]]) -> str:
        return "Kaelen was exiled from Velmora. [characters/kaelen.md]"


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


class LoopRecordingChatClient:
    def __init__(self) -> None:
        self.loops: list[asyncio.AbstractEventLoop] = []
        self.close_loops: list[asyncio.AbstractEventLoop] = []

    async def embed(self, text: str) -> list[float]:
        self._record_loop()
        return [0.1] * 384

    async def chat(self, messages: list[dict[str, str]]) -> str:
        self._record_loop()
        return "Kaelen was exiled from Velmora. [characters/kaelen.md]"

    def _record_loop(self) -> None:
        loop = asyncio.get_running_loop()
        if self.loops and loop is not self.loops[0]:
            raise AssertionError("ChatService used multiple event loops for one async client")
        self.loops.append(loop)

    async def aclose(self) -> None:
        self.close_loops.append(asyncio.get_running_loop())


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
            excerpt="Kaelen exile",
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

    assert len(client.loops) == 4
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
            excerpt="Kaelen exile",
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
