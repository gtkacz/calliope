from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from calliope.domain.enums import CanonPolicy
from calliope.llm.openai_compatible import ChatCompletion
from calliope.prompts.budget import estimate_messages_chars, prompt_budget_chars
from calliope.prompts.builder import build_continuation_messages
from calliope.retrieval.hybrid import _AsyncRunner

# Floor on how much document tail a continuation request keeps when the budget
# is tight. Below this the model cannot re-establish voice and position and
# tends to restart or drift; slightly exceeding a tiny budget (which the
# overflow detector will flag) is the lesser failure.
CONTINUATION_MIN_TAIL_CHARS = 4_000

# Visible to the model so a sliced tail is not mistaken for the whole document.
_TAIL_OMISSION_MARKER = "[… beginning of document omitted …]\n"

# Continuations sometimes re-emit the cut point's final words despite being told
# not to. Overlaps are only searched up to this length: anything longer means
# the model re-sent the document rather than continuing, which dedup cannot fix.
_MAX_OVERLAP_CHARS = 500


class ChatClient(Protocol):
    async def chat(self, messages: list[dict[str, str]]) -> ChatCompletion: ...


@dataclass(frozen=True)
class ContinuedCompletion:
    """A possibly multi-request generation, stitched into one result.

    `truncated` reflects only the FINAL round: earlier ceiling hits were repaired
    by continuation, so flagging them would mislabel a completed document.
    `context_overflow` is sticky across rounds because any overflowing round
    generated from a damaged prompt."""

    content: str
    truncated: bool
    context_overflow: bool
    continuation_rounds: int


def generate_with_continuation(
    *,
    runner: _AsyncRunner,
    chat_client: ChatClient,
    messages: list[dict[str, str]],
    instruction: str,
    policy: CanonPolicy,
    guidelines: str | None,
    max_rounds: int,
    prior_text: str = "",
) -> ContinuedCompletion:
    """Run a generation, chaining bounded continuation requests past the ceiling.

    Instead of demanding one giant completion — which forces a context window
    large enough for prompt + full output and prices big models out of consumer
    VRAM — each round is an independent request whose prompt holds only the
    instruction and a budget-sized tail of the document so far. The rounds are
    stitched with overlap dedup, so total output can exceed any single window.

    `prior_text` is text that precedes the generated content in the final
    document (the original file in append mode) — it feeds the tail window so
    the model continues from real document context, but is not returned."""
    completion = runner.run(chat_client.chat(messages))
    accumulated = completion.content
    context_overflow = completion.context_overflow
    rounds = 0
    while completion.truncated and rounds < max_rounds and completion.content:
        rounds += 1
        document_so_far = prior_text + accumulated
        tail = _tail_window(
            document_so_far,
            budget_chars=prompt_budget_chars(chat_client),
            instruction=instruction,
            policy=policy,
            guidelines=guidelines,
        )
        continuation_messages = build_continuation_messages(
            instruction=instruction,
            policy=policy,
            document_tail=tail,
            guidelines=guidelines,
        )
        completion = runner.run(chat_client.chat(continuation_messages))
        accumulated = _merge_continuation(accumulated, completion.content)
        context_overflow = context_overflow or completion.context_overflow
    return ContinuedCompletion(
        content=accumulated,
        truncated=completion.truncated,
        context_overflow=context_overflow,
        continuation_rounds=rounds,
    )


def _tail_window(
    document_so_far: str,
    *,
    budget_chars: int | None,
    instruction: str,
    policy: CanonPolicy,
    guidelines: str | None,
) -> str:
    if budget_chars is None:
        return document_so_far
    # Probe with an empty tail to measure the request's fixed overhead exactly
    # as the builder will emit it; the tail gets whatever budget remains.
    probe = build_continuation_messages(
        instruction=instruction,
        policy=policy,
        document_tail="",
        guidelines=guidelines,
    )
    available = max(
        budget_chars - estimate_messages_chars(probe),
        CONTINUATION_MIN_TAIL_CHARS,
    )
    if len(document_so_far) <= available:
        return document_so_far
    return _TAIL_OMISSION_MARKER + document_so_far[-available:]


def _merge_continuation(accumulated: str, continuation: str) -> str:
    """Join a continuation onto the accumulated text, deduplicating the seam.

    Models asked to continue from an exact cut often re-emit the final words or
    line before producing new text; the longest suffix of the accumulated text
    that matches the continuation's prefix is dropped once."""
    limit = min(_MAX_OVERLAP_CHARS, len(accumulated), len(continuation))
    for overlap in range(limit, 0, -1):
        if accumulated.endswith(continuation[:overlap]):
            return accumulated + continuation[overlap:]
    return accumulated + continuation
