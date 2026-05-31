from calliope.domain.enums import CanonPolicy
from calliope.domain.schemas import SourceReference
from calliope.prompts.builder import build_chat_messages, build_conversation_title_messages


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


def test_build_conversation_title_messages_asks_for_short_plain_title() -> None:
    messages = build_conversation_title_messages(
        user_message="Where was Kaelen exiled from?",
        assistant_answer="Kaelen was exiled from Velmora.",
    )

    assert [message["role"] for message in messages] == ["system", "user"]
    assert "short title" in messages[0]["content"]
    assert "no quotes" in messages[0]["content"].lower()
    assert "Where was Kaelen exiled from?" in messages[1]["content"]
    assert "Kaelen was exiled from Velmora." in messages[1]["content"]
