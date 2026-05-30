import asyncio
from collections.abc import Sequence
from pathlib import Path

import pytest
from calliope.config import EMBEDDING_DIMENSIONS
from calliope.db.models import Chunk, Document
from calliope.domain.schemas import SearchRequest, WorkspaceCreate
from calliope.ingest import indexer
from calliope.ingest.chunker import MarkdownChunk
from calliope.ingest.indexer import Reindexer
from calliope.repositories.workspaces import WorkspaceRepository
from calliope.services.search import SearchService
from sqlalchemy import func, select
from sqlalchemy.orm import Session


class FakeEmbeddingClient:
    async def embed(self, text: str) -> list[float]:
        return [float(len(text) % 7)] * EMBEDDING_DIMENSIONS


class SingleLoopEmbeddingClient:
    def __init__(self) -> None:
        self.loop_id: int | None = None
        self.close_loop_id: int | None = None
        self.closed = False

    async def embed(self, text: str) -> list[float]:
        current_loop_id = id(asyncio.get_running_loop())
        if self.loop_id is None:
            self.loop_id = current_loop_id
        elif self.loop_id != current_loop_id:
            raise RuntimeError("embedding client crossed event loops")

        return [float(len(text) % 7)] * EMBEDDING_DIMENSIONS

    async def aclose(self) -> None:
        self.close_loop_id = id(asyncio.get_running_loop())
        self.closed = True


class FailingCloseEmbeddingClient(FakeEmbeddingClient):
    def __init__(self) -> None:
        self.closed = False

    async def aclose(self) -> None:
        self.closed = True
        raise RuntimeError("embedding close failed")


def test_reindex_workspace_persists_documents_and_chunks(db_session: Session) -> None:
    workspace = WorkspaceRepository(db_session).create(
        WorkspaceCreate(
            name="world",
            root_path=str(Path("tests/fixtures/world").resolve()),
        )
    )

    result = Reindexer(db_session, embedding_client=FakeEmbeddingClient()).reindex_workspace(
        workspace.id
    )

    assert result.documents_indexed == 1
    assert result.chunks_indexed >= 3


def test_reindex_workspace_prunes_deleted_markdown_file(
    db_session: Session,
    tmp_path: Path,
) -> None:
    note = tmp_path / "lore.md"
    note.write_text(
        "# Vanished Archive\n\n"
        "The citrine astrolabe belongs to the hidden observatory.\n\n"
        "## Inventory\n\n"
        "Only the vanished archive mentions the citrine astrolabe.\n",
        encoding="utf-8",
    )
    workspace = WorkspaceRepository(db_session).create(
        WorkspaceCreate(name="prune-world", root_path=str(tmp_path))
    )
    embedding_client = FakeEmbeddingClient()

    first_result = Reindexer(db_session, embedding_client=embedding_client).reindex_workspace(
        workspace.id
    )

    document = db_session.scalar(
        select(Document).where(Document.workspace_id == workspace.id, Document.path == "lore.md")
    )
    assert document is not None
    assert document.deleted_at is None
    assert first_result.documents_indexed == 1
    assert first_result.chunks_indexed > 0
    assert (
        db_session.scalar(select(Chunk).where(Chunk.document_id == document.id).limit(1))
        is not None
    )

    note.unlink()

    second_result = Reindexer(db_session, embedding_client=embedding_client).reindex_workspace(
        workspace.id
    )
    db_session.refresh(document)
    stale_chunk_count = db_session.scalar(
        select(func.count()).select_from(Chunk).where(Chunk.document_id == document.id)
    )
    service = SearchService(db_session, embedding_client)
    try:
        search_response = service.search(
            SearchRequest(
                query="citrine astrolabe",
                workspace_id=workspace.id,
                limit=3,
            )
        )
    finally:
        service.close()

    assert second_result.documents_indexed == 0
    assert second_result.chunks_indexed == 0
    assert document.deleted_at is not None
    assert stale_chunk_count == 0
    assert search_response.sources == []


def test_reindex_workspace_reuses_one_event_loop_for_chunk_embeddings(
    db_session: Session,
) -> None:
    workspace = WorkspaceRepository(db_session).create(
        WorkspaceCreate(
            name="loop-world",
            root_path=str(Path("tests/fixtures/world").resolve()),
        )
    )

    result = Reindexer(
        db_session,
        embedding_client=SingleLoopEmbeddingClient(),
    ).reindex_workspace(workspace.id)

    assert result.documents_indexed == 1
    assert result.chunks_indexed >= 3


def test_reindex_workspace_closes_owned_embedding_client_on_embedding_loop(
    db_session: Session,
) -> None:
    workspace = WorkspaceRepository(db_session).create(
        WorkspaceCreate(
            name="close-loop-world",
            root_path=str(Path("tests/fixtures/world").resolve()),
        )
    )
    embedding_client = SingleLoopEmbeddingClient()

    result = Reindexer(
        db_session,
        embedding_client=embedding_client,
        close_embedding_client=True,
    ).reindex_workspace(workspace.id)

    assert result.documents_indexed == 1
    assert embedding_client.close_loop_id == embedding_client.loop_id


def test_reindex_workspace_closes_owned_embedding_client_before_embedding_failures(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace = WorkspaceRepository(db_session).create(
        WorkspaceCreate(
            name="parse-fail-world",
            root_path=str(Path("tests/fixtures/world").resolve()),
        )
    )
    embedding_client = SingleLoopEmbeddingClient()

    def fail_parse(absolute_path: Path, relative_path: str) -> object:
        raise RuntimeError("parse failed before embedding")

    monkeypatch.setattr(indexer, "parse_markdown_file", fail_parse)

    with pytest.raises(RuntimeError, match="parse failed before embedding"):
        Reindexer(
            db_session,
            embedding_client=embedding_client,
            close_embedding_client=True,
        ).reindex_workspace(workspace.id)

    assert embedding_client.closed


def test_reindex_workspace_cleanup_does_not_mask_original_error(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace = WorkspaceRepository(db_session).create(
        WorkspaceCreate(
            name="parse-fail-close-fail-world",
            root_path=str(Path("tests/fixtures/world").resolve()),
        )
    )
    embedding_client = FailingCloseEmbeddingClient()

    def fail_parse(absolute_path: Path, relative_path: str) -> object:
        raise RuntimeError("parse failed before embedding")

    monkeypatch.setattr(indexer, "parse_markdown_file", fail_parse)

    with pytest.raises(RuntimeError, match="parse failed before embedding"):
        Reindexer(
            db_session,
            embedding_client=embedding_client,
            close_embedding_client=True,
        ).reindex_workspace(workspace.id)

    assert embedding_client.closed


def test_reindex_workspace_rolls_back_flushes_when_reindex_fails(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace = WorkspaceRepository(db_session).create(
        WorkspaceCreate(
            name="rollback-world",
            root_path=str(Path("tests/fixtures/world").resolve()),
        )
    )
    original_replace = indexer.ChunkRepository.replace_for_document

    def fail_after_flush(
        self: indexer.ChunkRepository,
        document_id: str,
        chunks: Sequence[MarkdownChunk],
        embeddings: Sequence[list[float]],
    ) -> int:
        original_replace(self, document_id, chunks, embeddings)
        raise RuntimeError("chunk write failed after flush")

    monkeypatch.setattr(indexer.ChunkRepository, "replace_for_document", fail_after_flush)

    with pytest.raises(RuntimeError, match="chunk write failed after flush"):
        Reindexer(db_session, embedding_client=FakeEmbeddingClient()).reindex_workspace(
            workspace.id
        )

    persisted_document = db_session.scalar(
        select(Document).where(Document.workspace_id == workspace.id)
    )
    assert persisted_document is None
