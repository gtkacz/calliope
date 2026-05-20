from typing import Annotated

from calliope.api.dependencies import get_db_session
from calliope.domain.schemas import DocumentRead, SourceReference
from calliope.repositories.chunks import ChunkRepository
from calliope.repositories.documents import DocumentRepository
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

router = APIRouter()


@router.get("/v1/documents", response_model=list[DocumentRead])
def list_documents(
    session: Annotated[Session, Depends(get_db_session)],
) -> list[DocumentRead]:
    return DocumentRepository(session).list()


@router.get("/v1/documents/{document_id}", response_model=DocumentRead)
def get_document(
    document_id: str,
    session: Annotated[Session, Depends(get_db_session)],
) -> DocumentRead:
    return DocumentRepository(session).get(document_id)


@router.get("/v1/sources/{chunk_id}", response_model=SourceReference)
def get_source(
    chunk_id: str,
    session: Annotated[Session, Depends(get_db_session)],
) -> SourceReference:
    return ChunkRepository(session).source_for_chunk(chunk_id)
