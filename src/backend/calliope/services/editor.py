from __future__ import annotations

from typing import Protocol

from calliope.config import DEFAULT_MAX_CONTINUATION_ROUNDS
from calliope.domain.enums import CanonPolicy, EditMode
from calliope.domain.schemas import EditProposal, EditProposalRequest, SourceReference
from calliope.llm.openai_compatible import ChatCompletion
from calliope.prompts.budget import estimate_messages_chars, prompt_budget_chars, trim_to_budget
from calliope.prompts.builder import build_document_edit_messages
from calliope.retrieval.hybrid import _AsyncRunner, aclose_client
from calliope.services.continuation import generate_with_continuation
from calliope.services.filesystem import FilesystemService


class ChatClient(Protocol):
    async def chat(self, messages: list[dict[str, str]]) -> ChatCompletion: ...


class EditorService:
    def __init__(
        self,
        *,
        filesystem: FilesystemService,
        chat_client: ChatClient,
        close_chat_client: bool = False,
        max_continuation_rounds: int = DEFAULT_MAX_CONTINUATION_ROUNDS,
    ) -> None:
        self.filesystem = filesystem
        self.chat_client = chat_client
        self._async_runner = _AsyncRunner()
        self._close_chat_client = close_chat_client
        self._max_continuation_rounds = max_continuation_rounds

    def propose(
        self,
        request: EditProposalRequest,
        *,
        policy: CanonPolicy = CanonPolicy.CANON_PLUS_INFERENCE,
        sources: list[SourceReference] | None = None,
        guidelines: str | None = None,
    ) -> EditProposal:
        current = self.filesystem.read_file(request.path)
        messages = build_document_edit_messages(
            content=current.content,
            instruction=request.instruction,
            mode=request.mode,
            policy=policy,
            sources=sources,
            guidelines=guidelines,
        )
        # Sources are the only expendable component of an edit prompt; the
        # document and instruction are never trimmed because the proposal
        # replaces the file on apply. A document that alone exceeds the budget
        # is caught at generation time by the overflow detector instead.
        budget = prompt_budget_chars(self.chat_client)
        if budget is not None and sources:
            overage = estimate_messages_chars(messages) - budget
            if overage > 0:
                kept_sources, _, _, _ = trim_to_budget(
                    overage_chars=overage,
                    sources=list(sources),
                    cited_documents=None,
                    history=None,
                )
                sources = kept_sources or None
                messages = build_document_edit_messages(
                    content=current.content,
                    instruction=request.instruction,
                    mode=request.mode,
                    policy=policy,
                    sources=sources,
                    guidelines=guidelines,
                )

        prior_text = ""
        if request.mode is EditMode.APPEND:
            # Mirrors the assembly below so the continuation tail sees the seam
            # exactly as it will exist in the proposed document.
            prior_text = current.content.rstrip("\n") + "\n\n"
        completion = generate_with_continuation(
            runner=self._async_runner,
            chat_client=self.chat_client,
            messages=messages,
            instruction=request.instruction,
            policy=policy,
            guidelines=guidelines,
            max_rounds=self._max_continuation_rounds,
            prior_text=prior_text,
        )
        generated = completion.content

        if request.mode is EditMode.APPEND:
            proposed_content = current.content.rstrip("\n") + "\n\n" + generated.strip() + "\n"
        else:
            proposed_content = generated

        return EditProposal(
            path=current.path,
            mode=request.mode,
            original_content=current.content,
            proposed_content=proposed_content,
            truncated=completion.truncated,
            context_overflow=completion.context_overflow,
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
