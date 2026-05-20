import asyncio
from collections.abc import Sequence
from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from calliope.db.models import Document
from calliope.domain.schemas import WorkspaceCreate
from calliope.ingest import indexer
from calliope.ingest.chunker import MarkdownChunk
from calliope.ingest.indexer import Reindexer
from calliope.repositories.workspaces import WorkspaceRepository


class FakeEmbeddingClient:
    async def embed(self, text: str) -> list[float]:
        return [float(len(text) % 7)] * 384


class SingleLoopEmbeddingClient:
    def __init__(self) -> None:
        self.loop_id: int | None = None
        self.close_loop_id: int | None = None

    async def embed(self, text: str) -> list[float]:
        current_loop_id = id(asyncio.get_running_loop())
        if self.loop_id is None:
            self.loop_id = current_loop_id
        elif self.loop_id != current_loop_id:
            raise RuntimeError("embedding client crossed event loops")

        return [float(len(text) % 7)] * 384

    async def aclose(self) -> None:
        self.close_loop_id = id(asyncio.get_running_loop())


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
