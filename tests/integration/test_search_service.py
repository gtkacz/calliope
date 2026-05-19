from pathlib import Path

from sqlalchemy.orm import Session

from calliope.domain.schemas import SearchRequest, WorkspaceCreate
from calliope.ingest.indexer import Reindexer
from calliope.repositories.workspaces import WorkspaceRepository
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

    response = SearchService(db_session, embedding_client).search(
        SearchRequest(query="Kaelen exile", workspace_id=workspace.id, limit=3)
    )

    assert response.sources
    assert response.sources[0].path == "characters/kaelen.md"
