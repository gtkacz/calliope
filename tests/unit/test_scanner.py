from pathlib import Path

from calliope.ingest.scanner import preview_workspace_globs, scan_workspace


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


def test_preview_workspace_globs_matches_scanner_without_reading_contents(tmp_path: Path) -> None:
    (tmp_path / "nested").mkdir()
    (tmp_path / "included.md").write_text("included", encoding="utf-8")
    (tmp_path / "nested" / "ignored.md").write_text("ignored", encoding="utf-8")
    (tmp_path / ".calliope-git").mkdir()
    (tmp_path / ".calliope-git" / "history.md").write_text("never previewed", encoding="utf-8")

    preview = preview_workspace_globs(
        tmp_path,
        include_globs=["**/*.md"],
        exclude_globs=["nested/**"],
    )

    assert preview.visited_count == 3
    assert preview.included_paths == ["included.md"]
    assert preview.ignored_paths == [".calliope-git/history.md", "nested/ignored.md"]
    assert not preview.truncated


def test_preview_workspace_globs_skips_directory_symlinks_and_honors_cap(tmp_path: Path) -> None:
    external = tmp_path.parent / f"{tmp_path.name}-external"
    external.mkdir()
    (external / "outside.md").write_text("outside", encoding="utf-8")
    (tmp_path / "linked").symlink_to(external, target_is_directory=True)
    for index in range(3):
        (tmp_path / f"{index}.md").write_text("x", encoding="utf-8")

    preview = preview_workspace_globs(
        tmp_path,
        include_globs=["**/*.md"],
        exclude_globs=[],
        max_files=2,
    )

    assert preview.visited_count == 2
    assert preview.truncated
    assert all("linked" not in path for path in preview.included_paths)
