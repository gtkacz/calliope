from __future__ import annotations

from dataclasses import dataclass

from calliope.config import (
    DEFAULT_MAX_TOKENS,
    ESTIMATED_CHARS_PER_TOKEN,
    PROMPT_BUDGET_SAFETY,
)
from calliope.domain.schemas import CitedDocument, SourceReference
from calliope.prompts.builder import HistoryTurn, _format_source

# A trimmed citation keeps at least its lead, where lore documents put the
# title, summary, and key facts — better than the document vanishing entirely,
# since the user attached it deliberately.
CITED_DOCUMENT_MIN_KEEP_CHARS = 2_000

# Marker text is visible to the model so it knows the document continues beyond
# what it can see and does not treat the cut as the document's true ending.
_CITED_TRUNCATION_MARKER = "\n\n[… truncated by Calliope to fit the model's context window …]"


@dataclass(frozen=True)
class PromptTrim:
    """Record of what budget-fitting removed from a prompt."""

    dropped_sources: int = 0
    truncated_cited_documents: int = 0
    dropped_history_turns: int = 0
    # Chars still over budget after every expendable component was shed; the
    # remainder is canvas/document + contracts, which are never trimmed because
    # the model's output replaces the stored artifact (truncated input would
    # destroy the unseen tail on save).
    remaining_overage_chars: int = 0

    @property
    def trimmed(self) -> bool:
        return (
            self.dropped_sources > 0
            or self.truncated_cited_documents > 0
            or self.dropped_history_turns > 0
        )

    def as_metadata(self) -> dict[str, int]:
        fields = {
            "dropped_sources": self.dropped_sources,
            "truncated_cited_documents": self.truncated_cited_documents,
            "dropped_history_turns": self.dropped_history_turns,
            "remaining_overage_chars": self.remaining_overage_chars,
        }
        return {key: value for key, value in fields.items() if value > 0}


def prompt_budget_chars(client: object) -> int | None:
    """Character budget for the prompt side of a request sent through `client`.

    Servers reserve the requested completion length out of their context window,
    so the prompt may only use what remains. Reads the client's window and
    reservation via getattr so the service-layer ChatClient Protocols and test
    fakes stay minimal; clients that declare no window get no budget, which
    disables trimming."""
    num_ctx = getattr(client, "num_ctx", None)
    if num_ctx is None:
        return None
    sampling = getattr(client, "sampling_params", None)
    max_tokens = getattr(sampling, "max_tokens", None) if sampling is not None else None
    if max_tokens is None:
        # Without an explicit ceiling the server applies its own; reserve the
        # default Calliope would have sent rather than assuming zero.
        max_tokens = DEFAULT_MAX_TOKENS
    budget_tokens = (num_ctx - max_tokens) * PROMPT_BUDGET_SAFETY
    return max(0, int(budget_tokens * ESTIMATED_CHARS_PER_TOKEN))


def estimate_messages_chars(messages: list[dict[str, str]]) -> int:
    return sum(len(message.get("content", "")) for message in messages)


def trim_to_budget(
    *,
    overage_chars: int,
    sources: list[SourceReference],
    cited_documents: list[CitedDocument] | None,
    history: list[HistoryTurn] | None,
) -> tuple[list[SourceReference], list[CitedDocument] | None, list[HistoryTurn] | None, PromptTrim]:
    """Shed at least `overage_chars` from the expendable prompt components.

    Trim order, cheapest semantic loss first:
    1. Retrieved sources, lowest rank first — auto-selected, and rank-tail hits
       are the weakest matches.
    2. Cited documents, truncated largest-first but never below a floor —
       user-attached, so they shrink rather than disappear.
    3. History, oldest turn first — mirrors how the repository window already
       ages out turns.

    The canvas/document and the instruction are never touched here: the model's
    output replaces the stored artifact, so input it never saw would be lost on
    save. If a budget cannot be met, the remainder is reported instead."""
    need = overage_chars

    kept_sources = list(sources)
    dropped_sources = 0
    while kept_sources and need > 0:
        # Measure the exact block the builder would have emitted so the
        # accounting matches what actually leaves the prompt.
        removed = kept_sources.pop()
        need -= len(_format_source(removed)) + 2
        dropped_sources += 1

    kept_cited = list(cited_documents) if cited_documents else None
    truncated_cited = 0
    if kept_cited and need > 0:
        largest_first = sorted(
            range(len(kept_cited)),
            key=lambda index: len(kept_cited[index].content),
            reverse=True,
        )
        for index in largest_first:
            if need <= 0:
                break
            doc = kept_cited[index]
            reducible = len(doc.content) - CITED_DOCUMENT_MIN_KEEP_CHARS
            if reducible <= 0:
                continue
            cut = min(need, reducible)
            keep = len(doc.content) - cut
            # Keep the head: lore documents front-load identity and summary.
            kept_cited[index] = doc.model_copy(
                update={"content": doc.content[:keep] + _CITED_TRUNCATION_MARKER}
            )
            need -= cut
            truncated_cited += 1

    kept_history = list(history) if history else None
    dropped_history = 0
    if kept_history:
        while kept_history and need > 0:
            removed_turn = kept_history.pop(0)
            need -= len(removed_turn.content)
            dropped_history += 1

    return (
        kept_sources,
        kept_cited,
        kept_history,
        PromptTrim(
            dropped_sources=dropped_sources,
            truncated_cited_documents=truncated_cited,
            dropped_history_turns=dropped_history,
            remaining_overage_chars=max(0, need),
        ),
    )
