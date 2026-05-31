from typing import Annotated

from calliope.api.dependencies import get_db_session
from calliope.domain.schemas import DocumentContent, DocumentRead, SourceReference
from calliope.repositories.chunks import ChunkRepository
from calliope.repositories.documents import DocumentRepository
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

router = APIRouter()


@router.get("/v1/documents", response_model=list[DocumentRead])
def list_documents(
    session: Annotated[Session, Depends(get_db_session)],
    workspace_id: str | None = None,
) -> list[DocumentRead]:
    return DocumentRepository(session).list(workspace_id=workspace_id)


@router.get("/v1/documents/{document_id}", response_model=DocumentRead)
def get_document(
    document_id: str,
    session: Annotated[Session, Depends(get_db_session)],
) -> DocumentRead:
    return DocumentRepository(session).get(document_id)


@router.get("/v1/documents/{document_id}/content", response_model=DocumentContent)
def get_document_content(
    document_id: str,
    session: Annotated[Session, Depends(get_db_session)],
    chunk_id: str | None = None,
) -> DocumentContent:
    document = DocumentRepository(session).get(document_id)
    chunk_repo = ChunkRepository(session)
    passage = chunk_repo.text_for_chunk(chunk_id, document_id) if chunk_id is not None else None
    return DocumentContent(
        id=document.id,
        path=document.path,
        title=document.title,
        content=chunk_repo.text_for_document(document_id),
        passage=passage,
    )


@router.get("/v1/sources/{chunk_id}", response_model=SourceReference)
def get_source(
    chunk_id: str,
    session: Annotated[Session, Depends(get_db_session)],
) -> SourceReference:
    return ChunkRepository(session).source_for_chunk(chunk_id)
