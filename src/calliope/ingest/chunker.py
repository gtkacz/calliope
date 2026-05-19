from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from calliope.ingest.parser import ParsedDocument


@dataclass(frozen=True)
class MarkdownChunk:
    text: str
    heading_path: str
    chunk_index: int
    token_count: int
    metadata: dict[str, Any]


def chunk_document(document: ParsedDocument, max_chars: int) -> list[MarkdownChunk]:
    chunks: list[MarkdownChunk] = []

    for section in document.sections:
        for text in _split_text(section.text, max_chars):
            chunks.append(
                MarkdownChunk(
                    text=text,
                    heading_path=section.heading_path,
                    chunk_index=len(chunks),
                    token_count=max(1, len(text.split())),
                    metadata={
                        "path": document.path,
                        "title": document.title,
                        "frontmatter": document.frontmatter,
                    },
                )
            )

    return chunks


def _split_text(text: str, max_chars: int) -> list[str]:
    text = text.strip()
    if not text:
        return []
    if max_chars <= 0 or len(text) <= max_chars:
        return [text]

    chunks: list[str] = []
    current = ""

    for paragraph in text.split("\n\n"):
        paragraph = paragraph.strip()
        if not paragraph:
            continue

        if len(paragraph) > max_chars:
            if current:
                chunks.append(current)
                current = ""
            chunks.extend(_split_long_text(paragraph, max_chars))
            continue

        candidate = paragraph if not current else f"{current}\n\n{paragraph}"
        if len(candidate) <= max_chars:
            current = candidate
        else:
            if current:
                chunks.append(current)
            current = paragraph

    if current:
        chunks.append(current)

    return chunks


def _split_long_text(text: str, max_chars: int) -> list[str]:
    chunks: list[str] = []
    current = ""

    for word in text.split():
        candidate = word if not current else f"{current} {word}"
        if len(candidate) <= max_chars:
            current = candidate
        else:
            if current:
                chunks.append(current)
            current = word

    if current:
        chunks.append(current)

    return chunks
