from __future__ import annotations

import asyncio
import threading
from collections.abc import Coroutine, Sequence
from dataclasses import dataclass
from typing import Any, Protocol, TypeVar

from sqlalchemy import bindparam, func, select
from sqlalchemy.orm import Session

from calliope.db.models import Chunk, Document


class EmbeddingClient(Protocol):
    async def embed(self, text: str) -> list[float]: ...


T = TypeVar("T")


class _AsyncRunner:
    def __init__(self) -> None:
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        self._started = threading.Event()
        self._closed = False

    def run(self, coroutine: Coroutine[Any, Any, T]) -> T:
        if self._closed:
            coroutine.close()
            raise RuntimeError("Async runner is closed.")

        loop = self._ensure_loop()
        future = asyncio.run_coroutine_threadsafe(coroutine, loop)
        return future.result()

    def close(self) -> None:
        if self._closed:
            return

        self._closed = True
        if self._loop is not None:
            self._loop.call_soon_threadsafe(self._loop.stop)
        if self._thread is not None:
            self._thread.join()

    def _ensure_loop(self) -> asyncio.AbstractEventLoop:
        if self._loop is None:
            self._thread = threading.Thread(target=self._run_loop, daemon=True)
            self._thread.start()
            self._started.wait()

        if self._loop is None:
            raise RuntimeError("Async runner failed to start.")
        return self._loop

    def _run_loop(self) -> None:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        self._loop = loop
        self._started.set()
        try:
            loop.run_forever()
            loop.run_until_complete(loop.shutdown_asyncgens())
        finally:
            loop.close()

    def __del__(self) -> None:
        self.close()


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
        self._async_runner = _AsyncRunner()

    def retrieve(
        self,
        query: str,
        *,
        workspace_id: str | None = None,
        limit: int = 8,
    ) -> list[FusedHit]:
        embedding = self._async_runner.run(self.embedding_client.embed(query))
        search_limit = limit * 2
        vector_ids = self._vector_search(embedding, workspace_id=workspace_id, limit=search_limit)
        lexical_ids = self._lexical_search(query, workspace_id=workspace_id, limit=search_limit)

        return fuse_ranked_results(vector_ids, lexical_ids)[:limit]

    def close(self) -> None:
        self._async_runner.close()

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
        rank = func.ts_rank_cd(Chunk.search_vector, ts_query)
        statement = (
            select(Chunk.id)
            .join(Document)
            .where(Chunk.search_vector.op("@@")(ts_query))
            .order_by(rank.desc(), Chunk.id.asc())
            .limit(limit)
        )
        if workspace_id is not None:
            statement = statement.where(Document.workspace_id == workspace_id)

        return list(self.session.scalars(statement, {"query": query}))
