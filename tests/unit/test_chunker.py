from pathlib import Path

from calliope.ingest.chunker import chunk_document
from calliope.ingest.parser import MarkdownSection, ParsedDocument, parse_markdown_file


def test_chunk_document_preserves_heading_context() -> None:
    parsed = parse_markdown_file(
        Path("tests/fixtures/world/characters/kaelen.md"),
        "characters/kaelen.md",
    )

    chunks = chunk_document(parsed)

    exile = [chunk for chunk in chunks if chunk.heading_path.endswith("Exile")][0]
    assert "Second Winter War" in exile.text
    assert exile.metadata["path"] == "characters/kaelen.md"


def test_chunk_document_splits_overlong_single_token() -> None:
    parsed = ParsedDocument(
        path="characters/long.md",
        title="Long",
        frontmatter={"type": "character"},
        sections=[
            MarkdownSection(
                heading_path="Long",
                level=1,
                text="abcdefghij",
            )
        ],
    )

    chunks = chunk_document(parsed, max_chars=4)

    assert [chunk.text for chunk in chunks] == ["abcd", "efgh", "ij"]
    assert all(len(chunk.text) <= 4 for chunk in chunks)


def test_chunk_document_keeps_small_split_chunks_within_max_chars() -> None:
    parsed = ParsedDocument(
        path="characters/split.md",
        title="Split",
        frontmatter={"type": "character"},
        sections=[
            MarkdownSection(
                heading_path="Split",
                level=1,
                text="alpha beta gamma\ndeltazeta",
            )
        ],
    )

    chunks = chunk_document(parsed, max_chars=6)

    assert [chunk.text for chunk in chunks] == ["alpha", "beta", "gamma", "deltaz", "eta"]
    assert all(len(chunk.text) <= 6 for chunk in chunks)
