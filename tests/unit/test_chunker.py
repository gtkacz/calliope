from pathlib import Path

from calliope.ingest.chunker import chunk_document
from calliope.ingest.parser import parse_markdown_file


def test_chunk_document_preserves_heading_context() -> None:
    parsed = parse_markdown_file(
        Path("tests/fixtures/world/characters/kaelen.md"),
        "characters/kaelen.md",
    )

    chunks = chunk_document(parsed)

    exile = [chunk for chunk in chunks if chunk.heading_path.endswith("Exile")][0]
    assert "Second Winter War" in exile.text
    assert exile.metadata["path"] == "characters/kaelen.md"
