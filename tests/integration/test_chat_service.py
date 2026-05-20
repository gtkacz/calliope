from pathlib import Path

from sqlalchemy.orm import Session

from calliope.domain.enums import CanonPolicy
from calliope.domain.schemas import ChatRequest, WorkspaceCreate
from calliope.ingest.indexer import Reindexer
from calliope.repositories.workspaces import WorkspaceRepository
from calliope.services.chat import ChatService


class FakeEmbeddingClient:
    async def embed(self, text: str) -> list[float]:
        value = 1.0 if "Kaelen" in text else 0.1
        return [value] * 384


class FakeChatClient:
    async def chat(self, messages: list[dict[str, str]]) -> str:
        return "Kaelen was exiled from Velmora. [characters/kaelen.md]"


def test_chat_service_returns_grounded_answer_and_trace(db_session: Session) -> None:
    workspace = WorkspaceRepository(db_session).create(
        WorkspaceCreate(
            name="chat-world",
            root_path=str(Path("tests/fixtures/world").resolve()),
        )
    )
    embedding_client = FakeEmbeddingClient()
    Reindexer(db_session, embedding_client=embedding_client).reindex_workspace(workspace.id)

    service = ChatService(
        db_session,
        embedding_client=embedding_client,
        chat_client=FakeChatClient(),
    )
    try:
        response = service.chat(
            ChatRequest(
                message="Where was Kaelen exiled from?",
                policy=CanonPolicy.STRICT_CANON,
                workspace_id=workspace.id,
            )
        )
    finally:
        service.close()

    assert "Velmora" in response.answer
    assert response.sources
    assert response.trace_id.startswith("trace_")
