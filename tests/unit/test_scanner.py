from pathlib import Path

from calliope.ingest.scanner import scan_workspace


def test_scan_workspace_finds_markdown_files() -> None:
    root = Path("tests/fixtures/world")

    files = scan_workspace(root, include_globs=["**/*.md"], exclude_globs=["drafts/**"])

    assert [file.relative_path for file in files] == ["characters/kaelen.md"]
    assert files[0].absolute_path.name == "kaelen.md"
    assert files[0].content_hash


def test_scan_workspace_single_star_does_not_match_nested_segments(tmp_path: Path) -> None:
    (tmp_path / "characters" / "deep").mkdir(parents=True)
    (tmp_path / "characters" / "kaelen.md").write_text("# Kaelen\n", encoding="utf-8")
    (tmp_path / "characters" / "deep" / "note.md").write_text("# Note\n", encoding="utf-8")

    files = scan_workspace(
        tmp_path,
        include_globs=["characters/*.md"],
        exclude_globs=[],
    )

    assert [file.relative_path for file in files] == ["characters/kaelen.md"]


def test_scan_workspace_double_star_matches_nested_segments(tmp_path: Path) -> None:
    (tmp_path / "characters" / "deep").mkdir(parents=True)
    (tmp_path / "characters" / "kaelen.md").write_text("# Kaelen\n", encoding="utf-8")
    (tmp_path / "characters" / "deep" / "note.md").write_text("# Note\n", encoding="utf-8")

    files = scan_workspace(
        tmp_path,
        include_globs=["characters/**/*.md"],
        exclude_globs=[],
    )

    assert [file.relative_path for file in files] == [
        "characters/deep/note.md",
        "characters/kaelen.md",
    ]
