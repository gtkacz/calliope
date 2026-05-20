from typing import Annotated

from calliope.api.dependencies import get_db_session
from calliope.domain.schemas import (
    ConversationFolderCreate,
    ConversationFolderPatch,
    ConversationFolderRead,
    SessionRead,
)
from calliope.repositories.chats import ChatRepository
from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

router = APIRouter()


@router.get("/v1/sessions/{session_id}", response_model=SessionRead)
def get_session(
    session_id: str,
    session: Annotated[Session, Depends(get_db_session)],
) -> SessionRead:
    return ChatRepository(session).get_session(session_id)


@router.get("/v1/conversation-folders", response_model=list[ConversationFolderRead])
def list_conversation_folders(
    session: Annotated[Session, Depends(get_db_session)],
) -> list[ConversationFolderRead]:
    return ChatRepository(session).list_folders()


@router.post(
    "/v1/conversation-folders",
    response_model=ConversationFolderRead,
    status_code=status.HTTP_201_CREATED,
)
def create_conversation_folder(
    payload: ConversationFolderCreate,
    session: Annotated[Session, Depends(get_db_session)],
) -> ConversationFolderRead:
    return ChatRepository(session).create_folder(payload)


@router.patch("/v1/conversation-folders/{folder_id}", response_model=ConversationFolderRead)
def update_conversation_folder(
    folder_id: str,
    payload: ConversationFolderPatch,
    session: Annotated[Session, Depends(get_db_session)],
) -> ConversationFolderRead:
    return ChatRepository(session).update_folder(folder_id, payload)


@router.delete("/v1/conversation-folders/{folder_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_conversation_folder(
    folder_id: str,
    session: Annotated[Session, Depends(get_db_session)],
) -> Response:
    ChatRepository(session).delete_folder(folder_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
