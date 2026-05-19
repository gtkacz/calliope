from pathlib import Path

from sqlalchemy.orm import Session

from calliope.domain.schemas import WorkspaceCreate
from calliope.ingest.indexer import Reindexer
from calliope.repositories.workspaces import WorkspaceRepository


class FakeEmbeddingClient:
    async def embed(self, text: str) -> list[float]:
        return [float(len(text) % 7)] * 384


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
