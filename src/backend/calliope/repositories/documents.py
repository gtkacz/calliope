from datetime import UTC, datetime
from typing import Any

from calliope.db.models import Chunk, Document
from calliope.domain.errors import AppError
from calliope.domain.schemas import DocumentRead
from sqlalchemy import delete, select
from sqlalchemy.orm import Session


class DocumentRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def upsert(
        self,
        *,
        workspace_id: str,
        path: str,
        title: str,
        frontmatter: dict[str, Any],
        content_hash: str,
        modified_at_ns: int,
    ) -> Document:
        document = self.session.scalar(
            select(Document).where(
                Document.workspace_id == workspace_id,
                Document.path == path,
            )
        )
        modified_at = datetime.fromtimestamp(modified_at_ns / 1_000_000_000, tz=UTC)
        indexed_at = datetime.now(UTC)

        if document is None:
            document = Document(
                workspace_id=workspace_id,
                path=path,
                title=title,
                frontmatter_json=frontmatter,
                content_hash=content_hash,
                modified_at=modified_at,
                indexed_at=indexed_at,
                deleted_at=None,
            )
            self.session.add(document)
        else:
            document.title = title
            document.frontmatter_json = frontmatter
            document.content_hash = content_hash
            document.modified_at = modified_at
            document.indexed_at = indexed_at
            document.deleted_at = None

        self.session.flush()
        return document

    def list(self, workspace_id: str | None = None) -> list[DocumentRead]:
        statement = select(Document).where(Document.deleted_at.is_(None)).order_by(Document.path)
        if workspace_id is not None:
            statement = statement.where(Document.workspace_id == workspace_id)
        documents = self.session.scalars(statement).all()
        return [self._to_read(document) for document in documents]

    def get(self, document_id: str) -> DocumentRead:
        document = self.session.get(Document, document_id)
        if document is None or document.deleted_at is not None:
            raise AppError(
                code="document_not_found",
                message="Document not found.",
                status_code=404,
                details={"document_id": document_id},
            )

        return self._to_read(document)

    def active_paths_for_workspace(self, workspace_id: str) -> set[str]:
        return set(
            self.session.scalars(
                select(Document.path).where(
                    Document.workspace_id == workspace_id,
                    Document.deleted_at.is_(None),
                )
            )
        )

    def mark_missing_deleted(self, *, workspace_id: str, current_paths: set[str]) -> int:
        statement = select(Document).where(
            Document.workspace_id == workspace_id,
            Document.deleted_at.is_(None),
        )
        if current_paths:
            statement = statement.where(Document.path.not_in(current_paths))

        stale_documents = list(self.session.scalars(statement))
        if not stale_documents:
            return 0

        stale_document_ids = [document.id for document in stale_documents]
        self.session.execute(delete(Chunk).where(Chunk.document_id.in_(stale_document_ids)))

        deleted_at = datetime.now(UTC)
        for document in stale_documents:
            document.deleted_at = deleted_at

        self.session.flush()
        return len(stale_documents)

    @staticmethod
    def _to_read(document: Document) -> DocumentRead:
        return DocumentRead(
            id=document.id,
            workspace_id=document.workspace_id,
            path=document.path,
            title=document.title,
            frontmatter=document.frontmatter_json,
            modified_at=document.modified_at,
            indexed_at=document.indexed_at,
        )
