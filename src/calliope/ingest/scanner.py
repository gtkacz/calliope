from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from fnmatch import fnmatchcase
from hashlib import sha256
from pathlib import Path


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
    return fnmatchcase(relative_path, pattern) or (
        pattern.startswith("**/") and fnmatchcase(relative_path, pattern.removeprefix("**/"))
    )
