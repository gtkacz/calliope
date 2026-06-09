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

# Grounding rules for the document-producing surfaces (write/edit). POLICY_TEXT is
# authored for Q&A answers: its GROUNDED/INFERRED/INVENTED markers and inline path
# citations are correct in a chat reply but would print verbatim into the canvas
# and corrupt the prose. These variants express the same fidelity contract without
# any in-body annotation, and they never emit a refusal string into the document —
# on insufficient sources they preserve the canvas instead of overwriting it.
WRITE_POLICY_TEXT: dict[CanonPolicy, str] = {
    CanonPolicy.STRICT_CANON: (
        "Do not contradict or deviate from the indexed canon sources provided below.\n"
        "Every detail you write must be traceable to those sources.\n"
        "If the indexed sources contain insufficient information to apply the instruction, "
        "preserve the current canvas exactly as-is and make no changes. "
        "NEVER refuse to produce the document.\n"
        "Do NOT invent, extrapolate, or draw on knowledge outside the provided sources."
    ),
    CanonPolicy.CANON_PLUS_INFERENCE: (
        "Write primarily from the indexed canon sources provided below.\n"
        "You may make cautious inferences when they follow directly and necessarily from the "
        "sources, but do not speculate beyond what the sources directly support.\n"
        "If neither canon nor direct inference provides enough ground to apply the instruction, "
        "preserve the current canvas exactly as-is and make no changes."
    ),
    CanonPolicy.CREATIVE_BUT_CONSISTENT: (
        "Write creatively while staying fully consistent with the indexed canon sources "
        "provided below.\n"
        "You may invent new details freely, but you must never contradict a canon source.\n"
        "If you cannot construct a consistent result, preserve the current canvas exactly as-is "
        "rather than contradicting canon."
    ),
}

# Appended last to every user message to counteract recency bias toward
# training-data knowledge over the injected sources.
_RECENCY_REMINDER = (
    "Remember: answer based on the context above. "
    "Do not introduce information not present in the sources or your explicit inferences."
)

# Write/edit counterpart to _RECENCY_REMINDER. "answer" framing primes short,
# answer-shaped output; this reframes the task as producing a full document and
# reinforces the completeness contract without over-constraining creative policies.
_WRITE_RECENCY_REMINDER = (
    "Produce the complete document based on the canvas and instruction above. "
    "The canon sources constrain consistency, not length. "
    "Reproduce every unchanged section verbatim."
)

# Static scaffold for write/edit system prompts. The forbidden-pattern list and the
# verbatim-copy mandate are the prompt-level half of the truncation fix: even with an
# explicit max_tokens, small instruction-tuned models treat "return the complete
# document" as license to abbreviate untouched sections with placeholders.
_COMPLETENESS_CONTRACT = (
    "COMPLETENESS — this is a hard rule, not a preference:\n"
    "- You MUST emit the ENTIRE document on every turn, start to finish, without exception.\n"
    "- NEVER omit, abbreviate, or stub any section, regardless of how small the instruction is.\n"
    "- The following patterns are FORBIDDEN and constitute a failure of this task:\n"
    '    "...", "[rest unchanged]", "[continue as before]", "(rest of section omitted)",\n'
    '    "[previous content]", "[section omitted for brevity]", "[unchanged]",\n'
    '    "as before", "etc.", or any other placeholder implying omitted content.\n'
    "- For every section the instruction does NOT address: copy it verbatim, "
    "character-for-character, without paraphrasing, summarising, or shortening."
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
    guidelines: str | None = None,
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

    system_content = (
        "You are Calliope, a grounded worldbuilding assistant.\n"
        f"{POLICY_TEXT[policy]}\n"
        "Cite sources by path when using canon details."
    )
    if guidelines and guidelines.strip():
        system_content += f"\n\n{_format_guidelines_block(guidelines)}"
    system_msg: dict[str, str] = {"role": "system", "content": system_content}
    user_msg: dict[str, str] = {
        "role": "user",
        "content": "\n\n".join(user_parts),
    }

    messages: list[dict[str, str]] = [system_msg]
    for turn in history or []:
        messages.append({"role": turn.role, "content": turn.content})
    messages.append(user_msg)
    return messages


# A title only needs the gist of the answer; sending a full (now up to several
# thousand token) response wastes the call and lets the answer dominate framing.
_TITLE_ANSWER_EXCERPT_CHARS = 400


def build_conversation_title_messages(
    *,
    user_message: str,
    assistant_answer: str,
) -> list[dict[str, str]]:
    answer_excerpt = assistant_answer[:_TITLE_ANSWER_EXCERPT_CHARS]
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
                f"First user prompt:\n{user_message}\n\nAssistant answer:\n{answer_excerpt}"
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
    guidelines: str | None = None,
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
    user_parts.append(_WRITE_RECENCY_REMINDER)

    system_content = (
        "You are Calliope, collaborating on a single living markdown document "
        "(the canvas).\n"
        "Your task is to apply the writer's instruction to the current canvas and "
        "return the complete revised document.\n"
        "The canvas in the user message is the sole source of document state; do not "
        "rely on conversation history for the document's prior content.\n\n"
        "OUTPUT CONTRACT — read this carefully before generating any text:\n"
        "- Return ONLY the raw markdown of the revised document, from the very first "
        "character to the very last.\n"
        "- Do NOT wrap output in code fences (no ```markdown, no ``` of any kind).\n"
        "- Do NOT add any preamble, commentary, explanation, or sign-off before or "
        "after the document.\n"
        '- Do NOT insert grounding markers, citation tags, "(inference)", '
        '"(invented)", or "[path/to/file.md]" anywhere in the document body. '
        "Canon sources constrain what you may write, not how you annotate it.\n\n"
        f"{_COMPLETENESS_CONTRACT}\n"
        "- If the canvas is empty, create the document from scratch based on the "
        "instruction and sources.\n"
        "- If you reach what feels like a natural stopping point before the document "
        "is complete: keep writing. There is no partial credit.\n\n"
        f"GROUNDING:\n{WRITE_POLICY_TEXT[policy]}"
    )
    if guidelines and guidelines.strip():
        system_content += f"\n\n{_format_guidelines_block(guidelines)}"
    system_msg: dict[str, str] = {"role": "system", "content": system_content}
    user_msg: dict[str, str] = {
        "role": "user",
        "content": "\n\n".join(user_parts),
    }

    messages: list[dict[str, str]] = [system_msg]
    for turn in history or []:
        messages.append({"role": turn.role, "content": turn.content})
    messages.append(user_msg)
    return messages


# Continuations get a dedicated, deliberately small prompt: the document tail
# anchors voice and position, the instruction anchors intent, and retrieved
# sources/history/cited documents are dropped — they shaped the document's
# structure in the first request, and re-sending them would crowd out the tail
# inside a small context window, which is the very constraint continuation
# exists to work around.
_CONTINUATION_DIRECTIVE = (
    "Continue the document from the EXACT point where it stops, even if it stops "
    "mid-sentence. Do not repeat text that is already written, do not summarise it, "
    "do not restart the document, and do not add commentary. Output only the "
    "continuation text."
)


def build_continuation_messages(
    *,
    instruction: str,
    policy: CanonPolicy,
    document_tail: str,
    guidelines: str | None = None,
) -> list[dict[str, str]]:
    system_content = (
        "You are Calliope, resuming a markdown document whose generation was cut "
        "off mid-stream.\n"
        "OUTPUT CONTRACT — read this carefully before generating any text:\n"
        "- Output ONLY the text that continues the document: no preamble, no code "
        "fences, no repetition of existing text, and no sign-off.\n"
        '- Do NOT insert grounding markers, citation tags, "(inference)", '
        '"(invented)", or "[path/to/file.md]" anywhere in the output.\n\n'
        f"GROUNDING:\n{WRITE_POLICY_TEXT[policy]}"
    )
    if guidelines and guidelines.strip():
        system_content += f"\n\n{_format_guidelines_block(guidelines)}"
    user_content = (
        f"Original instruction for the document:\n{instruction}\n\n"
        "Document so far (the beginning may be omitted; it may stop mid-sentence):\n"
        f"<<<\n{document_tail}\n>>>\n\n"
        f"{_CONTINUATION_DIRECTIVE}"
    )
    return [
        {"role": "system", "content": system_content},
        {"role": "user", "content": user_content},
    ]


def build_document_edit_messages(
    *,
    content: str,
    instruction: str,
    mode: EditMode,
    policy: CanonPolicy = CanonPolicy.CANON_PLUS_INFERENCE,
    sources: list[SourceReference] | None = None,
    guidelines: str | None = None,
) -> list[dict[str, str]]:
    if mode is EditMode.APPEND:
        mode_instruction = (
            "Return ONLY the new markdown to append (do not repeat existing content)."
        )
        # APPEND returns only the addition, so the full-document recency reminder
        # ("reproduce every unchanged section") would contradict the mode.
        recency = (
            "Base the appended markdown on the document and canon context above. "
            "The canon sources constrain consistency, not length."
        )
    else:
        mode_instruction = (
            "Return the COMPLETE revised markdown document.\n" + _COMPLETENESS_CONTRACT
        )
        recency = _WRITE_RECENCY_REMINDER

    system_content = (
        "You are Calliope, an editor for markdown documents.\n"
        f"{mode_instruction}\n\n"
        "OUTPUT CONTRACT — read this carefully before generating any text:\n"
        "- Return ONLY the resulting markdown with NO commentary and NO code fences.\n"
        '- Do NOT insert grounding markers, citation tags, "(inference)", "(invented)", '
        'or "[path/to/file.md]" anywhere in the output. Canon sources constrain '
        "consistency, not annotation.\n\n"
        f"{WRITE_POLICY_TEXT[policy]}\n\n"
        "If the instruction asks you to invent content that contradicts the document's "
        "established facts, note the contradiction and decline rather than override it."
    )
    if guidelines and guidelines.strip():
        system_content += f"\n\n{_format_guidelines_block(guidelines)}"

    user_content = f"Instruction:\n{instruction}\n\nCurrent document:\n<<<\n{content}\n>>>"

    if sources:
        source_blocks = "\n\n".join(_format_source(source) for source in sources)
        user_content += f"\n\nCanon context for this document:\n{source_blocks}"

    user_content += f"\n\n{recency}"

    return [
        {"role": "system", "content": system_content},
        {"role": "user", "content": user_content},
    ]


def _format_source(source: SourceReference) -> str:
    return f"Path: {source.path}\nHeading: {source.heading}\nContext: {source.context}"


def _format_cited_document(doc: CitedDocument) -> str:
    return f"Path: {doc.path}\nTitle: {doc.title}\nContent:\n{doc.content}"


def _format_guidelines_block(guidelines: str) -> str:
    return (
        "WORKSPACE GUIDELINES (standing creative and stylistic context for this world):\n"
        f"{guidelines.strip()}\n"
        "Apply these as background framing for tone, setting, and style. They do NOT "
        "override the grounding rules above: never invent, alter, or contradict canon to "
        "satisfy a guideline, and never emit a guideline as if it were a cited fact."
    )
