import asyncio
from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from calliope.domain.schemas import SearchRequest, SourceReference, WorkspaceCreate
from calliope.ingest.indexer import Reindexer
from calliope.repositories.chunks import ChunkRepository
from calliope.repositories.workspaces import WorkspaceRepository
from calliope.retrieval.hybrid import HybridRetriever
from calliope.services.search import SearchService


class FakeEmbeddingClient:
    async def embed(self, text: str) -> list[float]:
        value = 1.0 if "Kaelen" in text else 0.1
        return [value] * 384


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


class LoopRecordingEmbeddingClient:
    def __init__(self) -> None:
        self.loops: list[asyncio.AbstractEventLoop] = []

    async def embed(self, text: str) -> list[float]:
        loop = asyncio.get_running_loop()
        if self.loops and loop is not self.loops[0]:
            raise AssertionError("SearchService used more than one event loop for embeddings")
        self.loops.append(loop)
        return [0.1] * 384


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
            excerpt="Kaelen exile",
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
