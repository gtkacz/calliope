from typing import Any

from sqlalchemy.dialects import postgresql

from calliope.retrieval.hybrid import HybridRetriever, fuse_ranked_results


def test_fuse_ranked_results_combines_vector_and_lexical_rankings() -> None:
    vector_ids = ["chunk_a", "chunk_b", "chunk_c"]
    lexical_ids = ["chunk_c", "chunk_a"]

    hits = fuse_ranked_results(vector_ids, lexical_ids, k=60)

    assert hits[0].chunk_id == "chunk_a"
    assert hits[0].score > hits[-1].score


class FakeSession:
    def __init__(self) -> None:
        self.statement: Any | None = None
        self.params: Any | None = None

    def scalars(self, statement: Any, params: Any | None = None) -> list[str]:
        self.statement = statement
        self.params = params
        return []


class FakeEmbeddingClient:
    async def embed(self, text: str) -> list[float]:
        return [0.1] * 384


def test_lexical_search_orders_by_relevance_with_stable_tie_breaker() -> None:
    session = FakeSession()
    retriever = HybridRetriever(session, FakeEmbeddingClient())  # type: ignore[arg-type]

    retriever._lexical_search("Kaelen exile", workspace_id=None, limit=4)

    assert session.params == {"query": "Kaelen exile"}
    assert session.statement is not None
    compiled = str(
        session.statement.compile(
            dialect=postgresql.dialect(),
            compile_kwargs={"literal_binds": False},
        )
    )
    assert "ORDER BY ts_rank_cd(chunks.search_vector, plainto_tsquery" in compiled
    assert "DESC, chunks.id" in compiled
