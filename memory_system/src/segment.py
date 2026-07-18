"""Transcript segmentation helpers."""

from __future__ import annotations

from dataclasses import dataclass
import re


@dataclass(slots=True)
class TranscriptSegment:
    index: int
    text: str
    char_count: int
    word_count: int


def _normalize_whitespace(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def split_transcript(
    transcript_text: str,
    *,
    target_chars: int = 2400,
    overlap_chars: int = 240,
) -> list[TranscriptSegment]:
    normalized = _normalize_whitespace(transcript_text)
    if not normalized:
        return []

    paragraphs = [part.strip() for part in normalized.split("\n\n") if part.strip()]
    chunks: list[str] = []
    current = ""

    for paragraph in paragraphs:
        proposed = f"{current}\n\n{paragraph}".strip() if current else paragraph
        if current and len(proposed) > target_chars:
            chunks.append(current)
            overlap = current[-overlap_chars:].strip()
            current = f"{overlap}\n\n{paragraph}".strip() if overlap else paragraph
            if len(current) > target_chars:
                chunks.extend(_force_split(current, target_chars, overlap_chars))
                current = ""
        else:
            current = proposed

    if current:
        chunks.append(current)

    return [
        TranscriptSegment(
            index=index,
            text=chunk,
            char_count=len(chunk),
            word_count=len(chunk.split()),
        )
        for index, chunk in enumerate(chunks)
    ]


def _force_split(text: str, target_chars: int, overlap_chars: int) -> list[str]:
    pieces: list[str] = []
    start = 0
    while start < len(text):
        end = min(len(text), start + target_chars)
        pieces.append(text[start:end].strip())
        if end >= len(text):
            break
        start = max(end - overlap_chars, start + 1)
    return [piece for piece in pieces if piece]
