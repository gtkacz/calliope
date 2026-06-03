from calliope.domain.enums import EditMode
from calliope.domain.schemas import EditProposalRequest, FileContent
from calliope.llm.openai_compatible import ChatCompletion
from calliope.services.editor import EditorService


class StubFilesystem:
    def read_file(self, path: str) -> FileContent:
        return FileContent(path=path, content="# Doc\n\nBody.")


class RecordingChatClient:
    def __init__(self) -> None:
        self.calls: list[list[dict[str, str]]] = []

    async def chat(self, messages: list[dict[str, str]]) -> ChatCompletion:
        self.calls.append(messages)
        return ChatCompletion(content="A new line.")


def test_editor_service_injects_guidelines() -> None:
    client = RecordingChatClient()
    service = EditorService(filesystem=StubFilesystem(), chat_client=client)
    try:
        service.propose(
            EditProposalRequest(
                path="/notes/a.md", instruction="Add a closing line.", mode=EditMode.APPEND
            ),
            guidelines="This is a dark fantasy world.",
        )
    finally:
        service.close()

    assert "WORKSPACE GUIDELINES" in client.calls[0][0]["content"]


def test_editor_service_omits_guidelines_when_none() -> None:
    client = RecordingChatClient()
    service = EditorService(filesystem=StubFilesystem(), chat_client=client)
    try:
        service.propose(
            EditProposalRequest(
                path="/notes/a.md", instruction="Add a closing line.", mode=EditMode.APPEND
            ),
            guidelines=None,
        )
    finally:
        service.close()

    assert "WORKSPACE GUIDELINES" not in client.calls[0][0]["content"]
