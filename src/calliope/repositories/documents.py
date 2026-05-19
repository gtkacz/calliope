from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from calliope.db.models import Document
from calliope.domain.errors import AppError
from calliope.domain.schemas import DocumentRead


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

    def list(self) -> list[DocumentRead]:
        documents = self.session.scalars(select(Document).order_by(Document.path)).all()

        return [self._to_read(document) for document in documents]

    def get(self, document_id: str) -> DocumentRead:
        document = self.session.get(Document, document_id)
        if document is None:
            raise AppError(
                code="document_not_found",
                message="Document not found.",
                status_code=404,
                details={"document_id": document_id},
            )

        return self._to_read(document)

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
