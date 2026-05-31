from __future__ import annotations

from typing import Protocol

from calliope.domain.enums import CanonPolicy, EditMode
from calliope.domain.schemas import EditProposal, EditProposalRequest, SourceReference
from calliope.prompts.builder import build_document_edit_messages
from calliope.retrieval.hybrid import _AsyncRunner, aclose_client
from calliope.services.filesystem import FilesystemService


class ChatClient(Protocol):
    async def chat(self, messages: list[dict[str, str]]) -> str: ...


class EditorService:
    def __init__(
        self,
        *,
        filesystem: FilesystemService,
        chat_client: ChatClient,
        close_chat_client: bool = False,
    ) -> None:
        self.filesystem = filesystem
        self.chat_client = chat_client
        self._async_runner = _AsyncRunner()
        self._close_chat_client = close_chat_client

    def propose(
        self,
        request: EditProposalRequest,
        *,
        policy: CanonPolicy = CanonPolicy.CANON_PLUS_INFERENCE,
        sources: list[SourceReference] | None = None,
    ) -> EditProposal:
        current = self.filesystem.read_file(request.path)
        messages = build_document_edit_messages(
            content=current.content,
            instruction=request.instruction,
            mode=request.mode,
            policy=policy,
            sources=sources,
        )
        generated = self._async_runner.run(self.chat_client.chat(messages))

        if request.mode is EditMode.APPEND:
            proposed_content = current.content.rstrip("\n") + "\n\n" + generated.strip() + "\n"
        else:
            proposed_content = generated

        return EditProposal(
            path=current.path,
            mode=request.mode,
            original_content=current.content,
            proposed_content=proposed_content,
        )

    def close(self) -> None:
        cleanup_error: Exception | None = None
        try:
            if self._close_chat_client:
                try:
                    self._async_runner.run(aclose_client(self.chat_client))
                except Exception as exc:
                    cleanup_error = exc
        finally:
            try:
                self._async_runner.close()
            except Exception as exc:
                if cleanup_error is None:
                    cleanup_error = exc

        if cleanup_error is not None:
            raise cleanup_error
