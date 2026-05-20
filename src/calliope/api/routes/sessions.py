from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from calliope.api.dependencies import get_db_session
from calliope.domain.schemas import SessionRead
from calliope.repositories.chats import ChatRepository

router = APIRouter()


@router.get("/v1/sessions/{session_id}", response_model=SessionRead)
def get_session(
    session_id: str,
    session: Annotated[Session, Depends(get_db_session)],
) -> SessionRead:
    return ChatRepository(session).get_session(session_id)
