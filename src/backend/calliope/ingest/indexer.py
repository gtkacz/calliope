from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from calliope.ingest.chunker import chunk_document
from calliope.ingest.parser import parse_markdown_file
from calliope.ingest.scanner import scan_workspace
from calliope.repositories.chunks import ChunkRepository
from calliope.repositories.documents import DocumentRepository
from calliope.repositories.workspaces import WorkspaceRepository
from calliope.retrieval.hybrid import _AsyncRunner, aclose_client
from sqlalchemy.orm import Session


class EmbeddingClient(Protocol):
    async def embed(self, text: str) -> list[float]: ...


@dataclass(frozen=True)
class ReindexResult:
    documents_indexed: int
    chunks_indexed: int


class Reindexer:
    def __init__(
        self,
        session: Session,
        *,
        embedding_client: EmbeddingClient,
        close_embedding_client: bool = False,
    ) -> None:
        self.session = session
        self.embedding_client = embedding_client
        self._close_embedding_client = close_embedding_client
        self._async_runner: _AsyncRunner | None = None

    def reindex_workspace(self, workspace_id: str) -> ReindexResult:
        operation_error: Exception | None = None
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
            scanned_paths = {scanned.relative_path for scanned in scanned_files}

            indexed_documents = []
            for scanned in scanned_files:
                parsed = parse_markdown_file(scanned.absolute_path, scanned.relative_path)
                chunks = chunk_document(parsed)
                indexed_documents.append((scanned, parsed, chunks))

            existing_paths = document_repo.active_paths_for_workspace(workspace.id)
            if existing_paths != scanned_paths:
                document_repo.mark_missing_deleted(
                    workspace_id=workspace.id,
                    current_paths=scanned_paths,
                )

            document_texts = [
                [chunk.text for chunk in chunks] for _, _, chunks in indexed_documents
            ]
            embeddings_by_document = self._runner().run(self._embed_documents(document_texts))

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
        except Exception as exc:
            operation_error = exc
            self.session.rollback()
            raise
        finally:
            try:
                self.close()
            except Exception:
                if operation_error is None:
                    raise

    async def _embed_documents(self, document_texts: list[list[str]]) -> list[list[list[float]]]:
        return [
            [await self.embedding_client.embed(text) for text in chunk_texts]
            for chunk_texts in document_texts
        ]

    def close(self) -> None:
        cleanup_error: Exception | None = None
        runner = self._async_runner or _AsyncRunner()
        self._async_runner = runner
        try:
            if self._close_embedding_client:
                runner.run(aclose_client(self.embedding_client))
        except Exception as exc:
            cleanup_error = exc
        finally:
            try:
                runner.close()
            except Exception as exc:
                if cleanup_error is None:
                    cleanup_error = exc
            self._async_runner = None

        if cleanup_error is not None:
            raise cleanup_error

    def _runner(self) -> _AsyncRunner:
        if self._async_runner is None:
            self._async_runner = _AsyncRunner()
        return self._async_runner
