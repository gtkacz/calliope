from calliope.domain.enums import CanonPolicy
from calliope.domain.schemas import SourceReference
from calliope.prompts.builder import build_chat_messages


def test_build_chat_messages_includes_strict_policy_and_sources() -> None:
    source = SourceReference(
        document_id="document_1",
        chunk_id="chunk_1",
        path="characters/kaelen.md",
        heading="Kaelen",
        context="Kaelen was exiled from Velmora.",
        score=0.9,
    )

    messages = build_chat_messages(
        message="Who exiled Kaelen?",
        policy=CanonPolicy.STRICT_CANON,
        sources=[source],
    )

    assert messages[0]["role"] == "system"
    assert "indexed canon does not contain enough information" in messages[0]["content"]
    assert "characters/kaelen.md" in messages[1]["content"]
