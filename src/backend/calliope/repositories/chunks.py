from collections.abc import Sequence

from calliope.db.models import Chunk
from calliope.domain.errors import AppError
from calliope.domain.schemas import SourceReference
from calliope.ingest.chunker import MarkdownChunk
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session


class ChunkRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def replace_for_document(
        self,
        document_id: str,
        chunks: Sequence[MarkdownChunk],
        embeddings: Sequence[list[float]],
    ) -> int:
        self.session.execute(delete(Chunk).where(Chunk.document_id == document_id))

        for chunk, embedding in zip(chunks, embeddings, strict=True):
            self.session.add(
                Chunk(
                    document_id=document_id,
                    chunk_index=chunk.chunk_index,
                    heading_path=chunk.heading_path,
                    text=chunk.text,
                    token_count=chunk.token_count,
                    metadata_json=chunk.metadata,
                    embedding=embedding,
                    search_vector=func.to_tsvector("english", chunk.text),
                )
            )

        self.session.flush()
        return len(chunks)

    def source_for_chunk(self, chunk_id: str, score: float = 1.0) -> SourceReference:
        chunk = self.session.get(Chunk, chunk_id)
        if chunk is None:
            raise AppError(
                code="chunk_not_found",
                message="Chunk not found.",
                status_code=404,
                details={"chunk_id": chunk_id},
            )

        return SourceReference(
            document_id=chunk.document_id,
            chunk_id=chunk.id,
            path=str(chunk.metadata_json.get("path", "")),
            heading=chunk.heading_path,
            excerpt=chunk.text[:300],
            score=score,
        )

    def text_for_document(self, document_id: str) -> str:
        chunks = self.session.scalars(
            select(Chunk).where(Chunk.document_id == document_id).order_by(Chunk.chunk_index)
        ).all()
        return "\n\n".join(chunk.text for chunk in chunks)

    def count(self) -> int:
        return self.session.scalar(select(func.count()).select_from(Chunk)) or 0
