import asyncio
from datetime import UTC, datetime
from pathlib import Path

import pytest
from calliope.config import EMBEDDING_DIMENSIONS
from calliope.db.models import ChatMessage
from calliope.domain.errors import AppError
from calliope.domain.schemas import SearchRequest, SourceReference, WorkspaceCreate
from calliope.ingest.indexer import Reindexer
from calliope.repositories.chats import ChatRepository
from calliope.repositories.chunks import ChunkRepository
from calliope.repositories.workspaces import WorkspaceRepository
from calliope.retrieval.hybrid import HybridRetriever
from calliope.services.search import SearchService
from sqlalchemy.orm import Session


class FakeEmbeddingClient:
    async def embed(self, text: str) -> list[float]:
        value = 1.0 if "Kaelen" in text else 0.1
        return [value] * EMBEDDING_DIMENSIONS


def test_search_returns_sources_for_indexed_workspace(db_session: Session) -> None:
    workspace = WorkspaceRepository(db_session).create(
        WorkspaceCreate(
            name="search-world",
            root_path=str(Path("tests/fixtures/world").resolve()),
        )
    )
    embedding_client = FakeEmbeddingClient()
    Reindexer(db_session, embedding_client=embedding_client).reindex_workspace(workspace.id)

    service = SearchService(db_session, embedding_client)
    try:
        response = service.search(
            SearchRequest(query="Kaelen exile", workspace_id=workspace.id, limit=3)
        )
    finally:
        service.close()

    assert response.sources
    assert response.sources[0].path == "characters/kaelen.md"
    assert response.session is None
    assert response.search_message is None


def test_search_service_persists_search_result_turn(
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

    service = SearchService(db_session, FakeEmbeddingClient())
    try:
        response = service.search(
            SearchRequest(query="Kaelen exile", persist=True, limit=1)
        )
    finally:
        service.close()

    assert response.session is not None
    assert response.search_message is not None
    assert response.search_message.role == "search"
    assert response.search_message.metadata["turn_kind"] == "search_result"
    assert response.search_message.metadata["query"] == "Kaelen exile"
    assert response.search_message.metadata["sources"][0]["path"] == "characters/kaelen.md"


def test_search_service_persists_into_existing_session_and_updates_summary(
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

    chat_repo = ChatRepository(db_session)
    chat_session = chat_repo.create_session(title="Existing")
    chat_session.updated_at = datetime(2025, 1, 1, tzinfo=UTC)
    db_session.commit()
    original_updated_at = chat_session.updated_at

    service = SearchService(db_session, FakeEmbeddingClient())
    try:
        response = service.search(
            SearchRequest(
                query="Kaelen exile",
                session_id=chat_session.id,
                persist=True,
                limit=1,
            )
        )
    finally:
        service.close()

    assert response.session == chat_repo.get_session_summary(chat_session.id)
    assert response.session is not None
    assert response.session.updated_at > original_updated_at
    assert response.search_message is not None
    assert response.search_message.session_id == chat_session.id
    assert response.search_message.role == "search"
    assert (
        db_session.query(ChatMessage)
        .filter_by(session_id=chat_session.id, role="search")
        .count()
        == 1
    )


def test_search_service_missing_session_id_persists_nothing(
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

    service = SearchService(db_session, FakeEmbeddingClient())
    try:
        with pytest.raises(AppError) as exc_info:
            service.search(
                SearchRequest(
                    query="Kaelen exile",
                    session_id="session_missing",
                    persist=True,
                    limit=1,
                )
            )
    finally:
        service.close()

    assert exc_info.value.code == "session_not_found"
    assert exc_info.value.details == {"session_id": "session_missing"}
    assert db_session.query(ChatMessage).count() == 0


def test_search_service_new_session_title_is_capped_at_80_chars(
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

    query = "K" * 100
    service = SearchService(db_session, FakeEmbeddingClient())
    try:
        response = service.search(SearchRequest(query=query, persist=True, limit=1))
    finally:
        service.close()

    assert response.session is not None
    assert response.session.title == "K" * 80


class LoopRecordingEmbeddingClient:
    def __init__(self) -> None:
        self.loops: list[asyncio.AbstractEventLoop] = []
        self.close_loop: asyncio.AbstractEventLoop | None = None

    async def embed(self, text: str) -> list[float]:
        loop = asyncio.get_running_loop()
        if self.loops and loop is not self.loops[0]:
            raise AssertionError("SearchService used more than one event loop for embeddings")
        self.loops.append(loop)
        return [0.1] * EMBEDDING_DIMENSIONS

    async def aclose(self) -> None:
        self.close_loop = asyncio.get_running_loop()


class FailingCloseEmbeddingClient(LoopRecordingEmbeddingClient):
    async def aclose(self) -> None:
        await super().aclose()
        raise RuntimeError("embedding close failed")


def test_search_reuses_embedding_event_loop_for_repeated_sync_calls(
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

    embedding_client = LoopRecordingEmbeddingClient()
    service = SearchService(db_session, embedding_client)

    try:
        service.search(SearchRequest(query="Kaelen exile", limit=1))
        service.search(SearchRequest(query="Kaelen exile", limit=1))
    finally:
        service.close()

    assert len(embedding_client.loops) == 2
    assert len({id(loop) for loop in embedding_client.loops}) == 1


def test_search_service_closes_owned_embedding_client_on_embedding_loop(
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

    embedding_client = LoopRecordingEmbeddingClient()
    service = SearchService(
        db_session,
        embedding_client,
        close_embedding_client=True,
    )

    service.search(SearchRequest(query="Kaelen exile", limit=1))
    service.close()

    assert embedding_client.close_loop is embedding_client.loops[0]


def test_search_route_cleanup_does_not_mask_search_error(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_vector_search(
        self: HybridRetriever,
        embedding: list[float],
        *,
        workspace_id: str | None,
        limit: int,
    ) -> list[str]:
        raise RuntimeError("search failed")

    monkeypatch.setattr(HybridRetriever, "_vector_search", fail_vector_search)

    embedding_client = FailingCloseEmbeddingClient()
    service = SearchService(
        db_session,
        embedding_client,
        close_embedding_client=True,
    )

    with pytest.raises(RuntimeError, match="search failed"):
        try:
            service.search(SearchRequest(query="Kaelen exile", limit=1))
        except Exception:
            try:
                service.close()
            except Exception:
                pass
            raise

    assert embedding_client.close_loop is embedding_client.loops[0]
