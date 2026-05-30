from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from fnmatch import fnmatchcase
from hashlib import sha256
from pathlib import Path

from calliope.domain.constants import VERSION_STORE_DIRNAME


@dataclass(frozen=True)
class ScannedFile:
    absolute_path: Path
    relative_path: str
    content_hash: str
    modified_at_ns: int


def scan_workspace(
    root: Path,
    include_globs: Sequence[str],
    exclude_globs: Sequence[str],
) -> list[ScannedFile]:
    root = root.resolve()
    files: list[ScannedFile] = []

    for path in sorted(candidate for candidate in root.rglob("*") if candidate.is_file()):
        relative_path = path.relative_to(root).as_posix()
        # Never index Calliope's own version-history store.
        if relative_path.split("/", 1)[0] == VERSION_STORE_DIRNAME:
            continue
        if not _matches_any(relative_path, include_globs):
            continue
        if _matches_any(relative_path, exclude_globs):
            continue

        content = path.read_bytes()
        files.append(
            ScannedFile(
                absolute_path=path,
                relative_path=relative_path,
                content_hash=sha256(content).hexdigest(),
                modified_at_ns=path.stat().st_mtime_ns,
            )
        )

    return files


def _matches_any(relative_path: str, globs: Sequence[str]) -> bool:
    return any(_matches(relative_path, pattern) for pattern in globs)


def _matches(relative_path: str, pattern: str) -> bool:
    return _match_segments(relative_path.split("/"), pattern.split("/"))


def _match_segments(path_parts: list[str], pattern_parts: list[str]) -> bool:
    if not pattern_parts:
        return not path_parts

    pattern_part = pattern_parts[0]
    if pattern_part == "**":
        return _match_segments(path_parts, pattern_parts[1:]) or (
            bool(path_parts) and _match_segments(path_parts[1:], pattern_parts)
        )

    return (
        bool(path_parts)
        and fnmatchcase(path_parts[0], pattern_part)
        and _match_segments(
            path_parts[1:],
            pattern_parts[1:],
        )
    )
