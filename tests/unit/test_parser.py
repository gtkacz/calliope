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


def test_parse_markdown_ignores_headings_inside_fenced_code(tmp_path: Path) -> None:
    path = tmp_path / "notes.md"
    path.write_text(
        "\n".join(
            [
                "# Notes",
                "",
                "```markdown",
                "# Not A Heading",
                "```",
                "",
                "## Real Heading",
                "Real content.",
            ]
        ),
        encoding="utf-8",
    )

    parsed = parse_markdown_file(path, "notes.md")

    assert [section.heading_path for section in parsed.sections] == [
        "Notes",
        "Notes > Real Heading",
    ]
    assert "# Not A Heading" in parsed.sections[0].text


def test_parse_markdown_does_not_close_fence_on_marker_with_text(
    tmp_path: Path,
) -> None:
    path = tmp_path / "notes.md"
    path.write_text(
        "\n".join(
            [
                "# Notes",
                "",
                "```",
                "```markdown",
                "# Not A Heading",
                "```",
                "",
                "## Real Heading",
                "Real content.",
            ]
        ),
        encoding="utf-8",
    )

    parsed = parse_markdown_file(path, "notes.md")
    heading_paths = [section.heading_path for section in parsed.sections]

    assert "Notes > Not A Heading" not in heading_paths
    assert "Notes > Real Heading" in heading_paths
