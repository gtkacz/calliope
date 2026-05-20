from calliope.domain.enums import CanonPolicy
from calliope.domain.schemas import SourceReference

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
) -> list[dict[str, str]]:
    source_blocks = "\n\n".join(_format_source(source) for source in sources)
    if not source_blocks:
        source_blocks = "No indexed canon sources were retrieved."

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
            "content": (
                f"Question:\n{message}\n\n"
                f"Indexed canon sources:\n{source_blocks}"
            ),
        },
    ]


def _format_source(source: SourceReference) -> str:
    return (
        f"Path: {source.path}\n"
        f"Heading: {source.heading}\n"
        f"Excerpt: {source.excerpt}"
    )
