from typing import Any

from calliope.db.models import ChatMessage, ChatSession, ConversationFolder, RetrievalTrace
from calliope.domain.enums import CanonPolicy
from calliope.domain.errors import AppError
from calliope.domain.schemas import (
    ConversationFolderCreate,
    ConversationFolderPatch,
    ConversationFolderRead,
    SessionRead,
    SourceReference,
)
from sqlalchemy import select
from sqlalchemy.orm import Session


class ChatRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create_session(self, title: str | None = None) -> ChatSession:
        chat_session = ChatSession(title=title)
        self.session.add(chat_session)
        self.session.flush()
        return chat_session

    def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: dict[str, Any],
    ) -> ChatMessage:
        message = ChatMessage(
            session_id=session_id,
            role=role,
            content=content,
            metadata_json=metadata,
        )
        self.session.add(message)
        self.session.flush()
        return message

    def add_trace(
        self,
        session_id: str,
        message_id: str,
        query: str,
        policy: CanonPolicy,
        sources: list[SourceReference],
        scores: dict[str, float],
    ) -> RetrievalTrace:
        trace = RetrievalTrace(
            session_id=session_id,
            message_id=message_id,
            query=query,
            policy=policy.value,
            selected_sources_json=[source.model_dump() for source in sources],
            scores_json=scores,
        )
        self.session.add(trace)
        self.session.flush()
        return trace

    def get_session(self, session_id: str) -> SessionRead:
        return self._to_read(self.get_session_row(session_id))

    def get_session_row(self, session_id: str) -> ChatSession:
        chat_session = self.session.get(ChatSession, session_id)
        if chat_session is None:
            raise AppError(
                code="session_not_found",
                message="Chat session not found.",
                status_code=404,
                details={"session_id": session_id},
            )

        return chat_session

    def list_folders(self) -> list[ConversationFolderRead]:
        folders = self.session.scalars(
            select(ConversationFolder).order_by(
                ConversationFolder.parent_id.nullsfirst(),
                ConversationFolder.position,
                ConversationFolder.created_at,
                ConversationFolder.id,
            )
        ).all()
        return [self._folder_to_read(folder) for folder in folders]

    def create_folder(self, payload: ConversationFolderCreate) -> ConversationFolderRead:
        self._ensure_valid_parent(payload.parent_id, moving_folder_id=None)
        folder = ConversationFolder(
            name=payload.name,
            parent_id=payload.parent_id,
            position=payload.position,
        )
        self.session.add(folder)
        self.session.commit()
        self.session.refresh(folder)
        return self._folder_to_read(folder)

    def update_folder(
        self,
        folder_id: str,
        payload: ConversationFolderPatch,
    ) -> ConversationFolderRead:
        folder = self._get_folder_row(folder_id)
        if payload.parent_id is not None:
            self._ensure_valid_parent(payload.parent_id, moving_folder_id=folder_id)
        if payload.name is not None:
            folder.name = payload.name
        if payload.parent_id is not None:
            folder.parent_id = payload.parent_id
        elif "parent_id" in payload.model_fields_set:
            folder.parent_id = None
        if payload.position is not None:
            folder.position = payload.position
        self.session.commit()
        self.session.refresh(folder)
        return self._folder_to_read(folder)

    def delete_folder(self, folder_id: str) -> None:
        folder = self._get_folder_row(folder_id)
        self.session.delete(folder)
        self.session.commit()

    def _get_folder_row(self, folder_id: str) -> ConversationFolder:
        folder = self.session.get(ConversationFolder, folder_id)
        if folder is None:
            raise AppError(
                code="conversation_folder_not_found",
                message="Conversation folder not found.",
                status_code=404,
                details={"folder_id": folder_id},
            )
        return folder

    def _ensure_valid_parent(
        self,
        parent_id: str | None,
        *,
        moving_folder_id: str | None,
    ) -> None:
        if parent_id is None:
            return
        if parent_id == moving_folder_id:
            raise AppError(
                code="conversation_folder_cycle",
                message="Conversation folder cannot be its own parent.",
                status_code=400,
                details={"folder_id": moving_folder_id, "parent_id": parent_id},
            )
        parent = self.session.get(ConversationFolder, parent_id)
        if parent is None:
            raise AppError(
                code="conversation_folder_invalid_parent",
                message="Conversation folder parent does not exist.",
                status_code=400,
                details={"parent_id": parent_id},
            )
        while parent is not None:
            if parent.id == moving_folder_id:
                raise AppError(
                    code="conversation_folder_cycle",
                    message="Conversation folder parent would create a cycle.",
                    status_code=400,
                    details={"folder_id": moving_folder_id, "parent_id": parent_id},
                )
            parent = parent.parent

    @staticmethod
    def _to_read(chat_session: ChatSession) -> SessionRead:
        return SessionRead(
            id=chat_session.id,
            title=chat_session.title,
            folder_id=chat_session.folder_id,
            created_at=chat_session.created_at,
            updated_at=chat_session.updated_at,
        )

    @staticmethod
    def _folder_to_read(folder: ConversationFolder) -> ConversationFolderRead:
        return ConversationFolderRead(
            id=folder.id,
            name=folder.name,
            parent_id=folder.parent_id,
            position=folder.position,
            created_at=folder.created_at,
            updated_at=folder.updated_at,
        )
