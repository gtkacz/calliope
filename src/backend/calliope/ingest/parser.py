from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import frontmatter

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")
_FENCE_RE = re.compile(r"^[ ]{0,3}(`{3,}|~{3,})")
_CLOSING_FENCE_RE = re.compile(r"^[ ]{0,3}(`{3,}|~{3,})[ \t]*$")


@dataclass(frozen=True)
class MarkdownSection:
    heading_path: str
    level: int
    text: str


@dataclass(frozen=True)
class ParsedDocument:
    path: str
    title: str
    frontmatter: dict[str, Any]
    sections: list[MarkdownSection]


def parse_markdown_file(path: Path, relative_path: str) -> ParsedDocument:
    post = frontmatter.loads(path.read_text(encoding="utf-8"))
    body = post.content
    metadata = dict(post.metadata)
    title = str(metadata.get("name") or _first_h1(body) or path.stem)

    return ParsedDocument(
        path=relative_path,
        title=title,
        frontmatter=metadata,
        sections=_split_sections(body, title),
    )


def _first_h1(markdown: str) -> str | None:
    fence: tuple[str, int] | None = None
    for line in markdown.splitlines():
        fence = _update_fence(line, fence)
        if fence is not None:
            continue

        match = _HEADING_RE.match(line)
        if match and len(match.group(1)) == 1:
            return match.group(2).strip()
    return None


def _split_sections(markdown: str, title: str) -> list[MarkdownSection]:
    sections: list[MarkdownSection] = []
    heading_stack: dict[int, str] = {}
    current_heading_path: str | None = None
    current_level = 1
    current_lines: list[str] = []
    fence: tuple[str, int] | None = None

    for line in markdown.splitlines():
        previous_fence = fence
        fence = _update_fence(line, fence)
        match = _HEADING_RE.match(line) if previous_fence is None and fence is None else None
        if match is not None:
            if current_heading_path is not None:
                sections.append(
                    MarkdownSection(
                        heading_path=current_heading_path,
                        level=current_level,
                        text="\n".join(current_lines).strip(),
                    )
                )

            current_level = len(match.group(1))
            heading_stack = {
                level: heading for level, heading in heading_stack.items() if level < current_level
            }
            heading_stack[current_level] = match.group(2).strip()
            current_heading_path = " > ".join(
                heading_stack[level] for level in sorted(heading_stack)
            )
            current_lines = []
            continue

        if current_heading_path is None:
            if line.strip():
                current_heading_path = title
                current_level = 1
        if current_heading_path is not None:
            current_lines.append(line)

    if current_heading_path is not None:
        sections.append(
            MarkdownSection(
                heading_path=current_heading_path,
                level=current_level,
                text="\n".join(current_lines).strip(),
            )
        )

    return sections


def _update_fence(line: str, fence: tuple[str, int] | None) -> tuple[str, int] | None:
    match = _FENCE_RE.match(line) if fence is None else _CLOSING_FENCE_RE.match(line)
    if match is None:
        return fence

    marker = match.group(1)
    marker_char = marker[0]
    marker_length = len(marker)

    if fence is None:
        return marker_char, marker_length

    fence_char, fence_length = fence
    if marker_char == fence_char and marker_length >= fence_length:
        return None

    return fence
