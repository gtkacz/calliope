from pathlib import Path

from calliope.ingest.parser import parse_markdown_file


def test_parse_markdown_extracts_frontmatter_and_headings() -> None:
    parsed = parse_markdown_file(
        Path("tests/fixtures/world/characters/kaelen.md"),
        "characters/kaelen.md",
    )

    assert parsed.title == "Ser Kaelen Morcant"
    assert parsed.frontmatter["type"] == "character"
    assert parsed.sections[0].heading_path == "Ser Kaelen Morcant"
    assert parsed.sections[1].heading_path == "Ser Kaelen Morcant > Biography"
    assert parsed.sections[2].heading_path == "Ser Kaelen Morcant > Biography > Exile"
