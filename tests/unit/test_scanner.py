from pathlib import Path

from calliope.ingest.scanner import scan_workspace


def test_scan_workspace_finds_markdown_files() -> None:
    root = Path("tests/fixtures/world")

    files = scan_workspace(root, include_globs=["**/*.md"], exclude_globs=["drafts/**"])

    assert [file.relative_path for file in files] == ["characters/kaelen.md"]
    assert files[0].absolute_path.name == "kaelen.md"
    assert files[0].content_hash
