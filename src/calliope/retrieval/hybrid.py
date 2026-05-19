from __future__ import annotations

import asyncio
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

from sqlalchemy import bindparam, func, select
from sqlalchemy.orm import Session

from calliope.db.models import Chunk, Document


class EmbeddingClient(Protocol):
    async def embed(self, text: str) -> list[float]: ...


@dataclass(frozen=True)
class FusedHit:
    chunk_id: str
    score: float


def fuse_ranked_results(
    vector_ids: Sequence[str],
    lexical_ids: Sequence[str],
    k: int = 60,
) -> list[FusedHit]:
    scores: dict[str, float] = {}

    for ranked_ids in (vector_ids, lexical_ids):
        for rank, chunk_id in enumerate(ranked_ids, start=1):
            scores[chunk_id] = scores.get(chunk_id, 0.0) + (1.0 / (k + rank))

    return [
        FusedHit(chunk_id=chunk_id, score=score)
        for chunk_id, score in sorted(scores.items(), key=lambda item: item[1], reverse=True)
    ]


class HybridRetriever:
    def __init__(self, session: Session, embedding_client: EmbeddingClient) -> None:
        self.session = session
        self.embedding_client = embedding_client

    def retrieve(
        self,
        query: str,
        *,
        workspace_id: str | None = None,
        limit: int = 8,
    ) -> list[FusedHit]:
        embedding = asyncio.run(self.embedding_client.embed(query))
        search_limit = limit * 2
        vector_ids = self._vector_search(embedding, workspace_id=workspace_id, limit=search_limit)
        lexical_ids = self._lexical_search(query, workspace_id=workspace_id, limit=search_limit)

        return fuse_ranked_results(vector_ids, lexical_ids)[:limit]

    def _vector_search(
        self,
        embedding: list[float],
        *,
        workspace_id: str | None,
        limit: int,
    ) -> list[str]:
        statement = (
            select(Chunk.id)
            .join(Document)
            .where(Chunk.embedding.is_not(None))
            .order_by(Chunk.embedding.l2_distance(embedding))
            .limit(limit)
        )
        if workspace_id is not None:
            statement = statement.where(Document.workspace_id == workspace_id)

        return list(self.session.scalars(statement))

    def _lexical_search(
        self,
        query: str,
        *,
        workspace_id: str | None,
        limit: int,
    ) -> list[str]:
        ts_query = func.plainto_tsquery("english", bindparam("query"))
        statement = (
            select(Chunk.id)
            .join(Document)
            .where(Chunk.search_vector.op("@@")(ts_query))
            .limit(limit)
        )
        if workspace_id is not None:
            statement = statement.where(Document.workspace_id == workspace_id)

        return list(self.session.scalars(statement, {"query": query}))
