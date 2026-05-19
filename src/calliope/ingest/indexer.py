from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from sqlalchemy.orm import Session

from calliope.ingest.chunker import chunk_document
from calliope.ingest.parser import parse_markdown_file
from calliope.ingest.scanner import scan_workspace
from calliope.repositories.chunks import ChunkRepository
from calliope.repositories.documents import DocumentRepository
from calliope.repositories.workspaces import WorkspaceRepository


class EmbeddingClient(Protocol):
    async def embed(self, text: str) -> list[float]: ...


@dataclass(frozen=True)
class ReindexResult:
    documents_indexed: int
    chunks_indexed: int


class Reindexer:
    def __init__(self, session: Session, *, embedding_client: EmbeddingClient) -> None:
        self.session = session
        self.embedding_client = embedding_client

    def reindex_workspace(self, workspace_id: str) -> ReindexResult:
        try:
            workspace = WorkspaceRepository(self.session).get(workspace_id)
            document_repo = DocumentRepository(self.session)
            chunk_repo = ChunkRepository(self.session)

            documents_indexed = 0
            chunks_indexed = 0

            scanned_files = scan_workspace(
                Path(workspace.root_path),
                workspace.include_globs,
                workspace.exclude_globs,
            )

            indexed_documents = []
            for scanned in scanned_files:
                parsed = parse_markdown_file(scanned.absolute_path, scanned.relative_path)
                chunks = chunk_document(parsed)
                indexed_documents.append((scanned, parsed, chunks))

            document_texts = [
                [chunk.text for chunk in chunks] for _, _, chunks in indexed_documents
            ]
            embeddings_by_document = asyncio.run(self._embed_documents(document_texts))

            for (scanned, parsed, chunks), embeddings in zip(
                indexed_documents,
                embeddings_by_document,
                strict=True,
            ):
                document = document_repo.upsert(
                    workspace_id=workspace.id,
                    path=parsed.path,
                    title=parsed.title,
                    frontmatter=parsed.frontmatter,
                    content_hash=scanned.content_hash,
                    modified_at_ns=scanned.modified_at_ns,
                )
                chunks_indexed += chunk_repo.replace_for_document(document.id, chunks, embeddings)
                documents_indexed += 1

            self.session.commit()
            return ReindexResult(
                documents_indexed=documents_indexed,
                chunks_indexed=chunks_indexed,
            )
        except Exception:
            self.session.rollback()
            raise

    async def _embed_documents(self, document_texts: list[list[str]]) -> list[list[list[float]]]:
        return [
            [await self.embedding_client.embed(text) for text in chunk_texts]
            for chunk_texts in document_texts
        ]
