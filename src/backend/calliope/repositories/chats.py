from typing import Any

from calliope.db.models import ChatMessage, ChatSession, RetrievalTrace
from calliope.domain.enums import CanonPolicy
from calliope.domain.errors import AppError
from calliope.domain.schemas import SessionRead, SourceReference
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

    @staticmethod
    def _to_read(chat_session: ChatSession) -> SessionRead:
        return SessionRead(
            id=chat_session.id,
            title=chat_session.title,
            created_at=chat_session.created_at,
            updated_at=chat_session.updated_at,
        )
