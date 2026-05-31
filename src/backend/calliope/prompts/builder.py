from __future__ import annotations

from dataclasses import dataclass

from calliope.domain.enums import CanonPolicy, EditMode
from calliope.domain.schemas import CitedDocument, SourceReference

POLICY_TEXT: dict[CanonPolicy, str] = {
    CanonPolicy.STRICT_CANON: (
        "Answer ONLY from the indexed canon sources provided below.\n"
        "Every factual claim must be drawn from a source in this context.\n"
        "Cite the source path inline, e.g. [characters/kaelen.md].\n"
        "If the indexed canon does not contain enough information to answer, "
        'respond with exactly: "The indexed canon does not contain enough information '
        'to answer this question."\n'
        "Do NOT invent, extrapolate, or draw on outside knowledge."
    ),
    CanonPolicy.CANON_PLUS_INFERENCE: (
        "Answer primarily from the indexed canon sources provided below.\n"
        "You may make cautious inferences when they follow DIRECTLY and NECESSARILY "
        "from the sources.\n"
        "FORMAT CONTRACT:\n"
        "  GROUNDED: [cite path, e.g. characters/kaelen.md] — state the canon fact.\n"
        "  INFERRED: (inference) — clearly label every non-citation inference with '(inference)'.\n"
        "If neither canon nor direct inference can answer the question, respond with: "
        '"The indexed canon does not contain enough information; I cannot answer reliably."\n'
        "Do NOT speculate beyond what the sources directly support."
    ),
    CanonPolicy.CREATIVE_BUT_CONSISTENT: (
        "Answer creatively while staying CONSISTENT with the indexed canon sources.\n"
        "FORMAT CONTRACT:\n"
        "  GROUNDED: [cite path, e.g. characters/kaelen.md] — use this marker for any detail "
        "drawn from the provided sources.\n"
        "  INVENTED: (invented) — use this marker on every detail you create that has no source "
        "in the provided context.\n"
        "Never contradict a cited source.\n"
        "If you cannot construct a consistent creative answer, "
        "say so rather than contradicting canon."
    ),
}

# Appended last to every user message to counteract recency bias toward
# training-data knowledge over the injected sources.
_RECENCY_REMINDER = (
    "Remember: answer based on the context above. "
    "Do not introduce information not present in the sources or your explicit inferences."
)


@dataclass(frozen=True)
class HistoryTurn:
    role: str  # "user" | "assistant"
    content: str


def build_chat_messages(
    *,
    message: str,
    policy: CanonPolicy,
    sources: list[SourceReference],
    cited_documents: list[CitedDocument] | None = None,
    history: list[HistoryTurn] | None = None,
) -> list[dict[str, str]]:
    source_blocks = "\n\n".join(_format_source(source) for source in sources)
    if not source_blocks:
        source_blocks = "No indexed canon sources were retrieved."

    user_parts: list[str] = [f"Question:\n{message}"]

    if cited_documents:
        cited_blocks = "\n\n".join(_format_cited_document(doc) for doc in cited_documents)
        user_parts.append(f"User-cited canon (treat as authoritative):\n{cited_blocks}")

    user_parts.append(f"Indexed canon sources:\n{source_blocks}")
    user_parts.append(_RECENCY_REMINDER)

    system_msg: dict[str, str] = {
        "role": "system",
        "content": (
            "You are Calliope, a grounded worldbuilding assistant.\n"
            f"{POLICY_TEXT[policy]}\n"
            "Cite sources by path when using canon details."
        ),
    }
    user_msg: dict[str, str] = {
        "role": "user",
        "content": "\n\n".join(user_parts),
    }

    messages: list[dict[str, str]] = [system_msg]
    for turn in history or []:
        messages.append({"role": turn.role, "content": turn.content})
    messages.append(user_msg)
    return messages


def build_conversation_title_messages(
    *,
    user_message: str,
    assistant_answer: str,
) -> list[dict[str, str]]:
    return [
        {
            "role": "system",
            "content": (
                "Create a short title for this conversation.\n"
                "Return only the title, 2-6 words, no quotes, no markdown, "
                "and no trailing punctuation."
            ),
        },
        {
            "role": "user",
            "content": (
                f"First user prompt:\n{user_message}\n\n"
                f"Assistant answer:\n{assistant_answer}\n\n"
                "Title:"
            ),
        },
    ]


def build_write_messages(
    *,
    message: str,
    policy: CanonPolicy,
    canvas: str,
    sources: list[SourceReference],
    cited_documents: list[CitedDocument] | None = None,
    history: list[HistoryTurn] | None = None,
) -> list[dict[str, str]]:
    source_blocks = "\n\n".join(_format_source(source) for source in sources)
    if not source_blocks:
        source_blocks = "No indexed canon sources were retrieved."

    canvas_block = canvas if canvas else "(empty — create the document from scratch)"
    user_parts: list[str] = [
        f"Current canvas:\n<<<\n{canvas_block}\n>>>",
        f"Instruction:\n{message}",
    ]

    if cited_documents:
        cited_blocks = "\n\n".join(_format_cited_document(doc) for doc in cited_documents)
        user_parts.append(f"User-cited canon (treat as authoritative):\n{cited_blocks}")

    user_parts.append(f"Indexed canon sources:\n{source_blocks}")
    user_parts.append(_RECENCY_REMINDER)

    system_msg: dict[str, str] = {
        "role": "system",
        "content": (
            "You are Calliope, collaborating on a single living markdown document "
            "(the canvas).\n"
            "Apply the user instruction to the current canvas and return ONLY the "
            "complete revised markdown.\n"
            "Return NO commentary and NO code fences.\n"
            f"{POLICY_TEXT[policy]}\n"
            "Cite sources by path where canon is used."
        ),
    }
    user_msg: dict[str, str] = {
        "role": "user",
        "content": "\n\n".join(user_parts),
    }

    messages: list[dict[str, str]] = [system_msg]
    for turn in history or []:
        messages.append({"role": turn.role, "content": turn.content})
    messages.append(user_msg)
    return messages


def build_document_edit_messages(
    *,
    content: str,
    instruction: str,
    mode: EditMode,
    policy: CanonPolicy = CanonPolicy.CANON_PLUS_INFERENCE,
    sources: list[SourceReference] | None = None,
) -> list[dict[str, str]]:
    if mode is EditMode.APPEND:
        mode_instruction = (
            "Return ONLY the new markdown to append (do not repeat existing content)."
        )
    else:
        mode_instruction = "Return the COMPLETE revised markdown document."

    system_content = (
        "You are Calliope, an editor for markdown documents.\n"
        f"{mode_instruction}\n"
        f"{POLICY_TEXT[policy]}\n"
        "Return ONLY the resulting markdown with NO commentary and NO code fences.\n"
        "If the instruction asks you to invent content that contradicts the document's "
        "established facts, note the contradiction and decline rather than override it."
    )

    user_content = f"Instruction:\n{instruction}\n\nCurrent document:\n<<<\n{content}\n>>>"

    if sources:
        source_blocks = "\n\n".join(_format_source(source) for source in sources)
        user_content += f"\n\nCanon context for this document:\n{source_blocks}"

    user_content += f"\n\n{_RECENCY_REMINDER}"

    return [
        {"role": "system", "content": system_content},
        {"role": "user", "content": user_content},
    ]


def _format_source(source: SourceReference) -> str:
    return f"Path: {source.path}\nHeading: {source.heading}\nContext: {source.context}"


def _format_cited_document(doc: CitedDocument) -> str:
    return f"Path: {doc.path}\nTitle: {doc.title}\nContent:\n{doc.content}"
