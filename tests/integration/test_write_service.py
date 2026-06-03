import pytest
from calliope.config import EMBEDDING_DIMENSIONS
from calliope.domain.enums import CanonPolicy
from calliope.domain.schemas import SourceReference, WorkspaceCreate, WriteRequest
from calliope.llm.openai_compatible import ChatCompletion
from calliope.repositories.chunks import ChunkRepository
from calliope.repositories.workspaces import WorkspaceRepository
from calliope.retrieval.hybrid import HybridRetriever
from calliope.services.write import WriteService
from sqlalchemy.orm import Session


class FakeEmbeddingClient:
    async def embed(self, text: str) -> list[float]:
        return [0.1] * EMBEDDING_DIMENSIONS


class RecordingChatClient:
    def __init__(self) -> None:
        self.calls: list[list[dict[str, str]]] = []

    async def chat(self, messages: list[dict[str, str]]) -> ChatCompletion:
        self.calls.append(messages)
        return ChatCompletion(content="# Revised\n\nBody.")


def _patch_retrieval(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(HybridRetriever, "_vector_search", lambda *a, **k: ["chunk_a"])
    monkeypatch.setattr(HybridRetriever, "_lexical_search", lambda *a, **k: ["chunk_a"])
    monkeypatch.setattr(
        ChunkRepository,
        "source_for_chunk",
        lambda self, chunk_id, score=1.0: SourceReference(
            document_id="document_a",
            chunk_id=chunk_id,
            path="characters/kaelen.md",
            heading="Kaelen",
            context="Kaelen exile",
            score=score,
        ),
    )


def test_write_service_injects_workspace_guidelines(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_retrieval(monkeypatch)
    workspace = WorkspaceRepository(db_session).create(
        WorkspaceCreate(
            name="write-guided",
            root_path="/tmp/write-guided",
            guidelines="This is a dark fantasy world.",
        )
    )
    client = RecordingChatClient()
    service = WriteService(db_session, embedding_client=FakeEmbeddingClient(), chat_client=client)
    try:
        service.write(
            WriteRequest(
                message="Expand the intro.",
                canvas="# Title",
                policy=CanonPolicy.CREATIVE_BUT_CONSISTENT,
                workspace_id=workspace.id,
                limit=1,
            )
        )
    finally:
        service.close()

    assert "WORKSPACE GUIDELINES" in client.calls[0][0]["content"]


def test_write_service_omits_guidelines_when_toggle_off(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_retrieval(monkeypatch)
    workspace = WorkspaceRepository(db_session).create(
        WorkspaceCreate(
            name="write-guided-off",
            root_path="/tmp/write-guided-off",
            guidelines="This is a dark fantasy world.",
        )
    )
    client = RecordingChatClient()
    service = WriteService(db_session, embedding_client=FakeEmbeddingClient(), chat_client=client)
    try:
        service.write(
            WriteRequest(
                message="Expand the intro.",
                canvas="# Title",
                workspace_id=workspace.id,
                apply_guidelines=False,
                limit=1,
            )
        )
    finally:
        service.close()

    assert "WORKSPACE GUIDELINES" not in client.calls[0][0]["content"]
