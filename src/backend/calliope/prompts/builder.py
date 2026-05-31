from calliope.domain.enums import CanonPolicy, EditMode
from calliope.domain.schemas import CitedDocument, SourceReference

POLICY_TEXT: dict[CanonPolicy, str] = {
    CanonPolicy.STRICT_CANON: (
        "Answer only from the indexed canon sources. If the indexed canon does not contain "
        "enough information, say that the indexed canon does not contain enough information."
    ),
    CanonPolicy.CANON_PLUS_INFERENCE: (
        "Answer from indexed canon first. You may make cautious inferences when they follow "
        "directly from the sources, and you must label those inferences clearly."
    ),
    CanonPolicy.CREATIVE_BUT_CONSISTENT: (
        "Answer creatively while staying consistent with indexed canon. Do not contradict "
        "provided sources, and distinguish invention from cited canon."
    ),
}


def build_chat_messages(
    *,
    message: str,
    policy: CanonPolicy,
    sources: list[SourceReference],
    cited_documents: list[CitedDocument] | None = None,
) -> list[dict[str, str]]:
    source_blocks = "\n\n".join(_format_source(source) for source in sources)
    if not source_blocks:
        source_blocks = "No indexed canon sources were retrieved."

    user_parts: list[str] = [f"Question:\n{message}"]

    if cited_documents:
        cited_blocks = "\n\n".join(_format_cited_document(doc) for doc in cited_documents)
        user_parts.append(f"User-cited canon (treat as authoritative):\n{cited_blocks}")

    user_parts.append(f"Indexed canon sources:\n{source_blocks}")

    return [
        {
            "role": "system",
            "content": (
                "You are Calliope, a grounded worldbuilding assistant.\n"
                f"{POLICY_TEXT[policy]}\n"
                "Cite sources by path when using canon details."
            ),
        },
        {
            "role": "user",
            "content": "\n\n".join(user_parts),
        },
    ]


def build_write_messages(
    *,
    message: str,
    policy: CanonPolicy,
    canvas: str,
    sources: list[SourceReference],
    cited_documents: list[CitedDocument] | None = None,
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

    return [
        {
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
        },
        {
            "role": "user",
            "content": "\n\n".join(user_parts),
        },
    ]


def build_document_edit_messages(
    *,
    content: str,
    instruction: str,
    mode: EditMode,
) -> list[dict[str, str]]:
    if mode is EditMode.APPEND:
        mode_instruction = (
            "Return ONLY the new markdown to append (do not repeat existing content)."
        )
    else:
        mode_instruction = "Return the COMPLETE revised markdown document."

    return [
        {
            "role": "system",
            "content": (
                "You are Calliope, an editor for markdown documents.\n"
                f"{mode_instruction}\n"
                "Return ONLY the resulting markdown with NO commentary and NO code fences."
            ),
        },
        {
            "role": "user",
            "content": (f"Instruction:\n{instruction}\n\nCurrent document:\n<<<\n{content}\n>>>"),
        },
    ]


def _format_source(source: SourceReference) -> str:
    return f"Path: {source.path}\nHeading: {source.heading}\nExcerpt: {source.excerpt}"


def _format_cited_document(doc: CitedDocument) -> str:
    return f"Path: {doc.path}\nTitle: {doc.title}\nContent:\n{doc.content}"
