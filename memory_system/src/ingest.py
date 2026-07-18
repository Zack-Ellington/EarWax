"""Transcript file ingestion."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class TranscriptDocument:
    source_path: Path
    source_name: str
    text: str


def load_transcript(path: str | Path) -> TranscriptDocument:
    source_path = Path(path).expanduser().resolve()
    if not source_path.exists():
        raise FileNotFoundError(f"Transcript file not found: {source_path}")
    if source_path.suffix.lower() != ".txt":
        raise ValueError(f"Expected a .txt transcript file, received: {source_path.name}")

    text = source_path.read_text(encoding="utf-8")
    if not text.strip():
        raise ValueError(f"Transcript file is empty: {source_path}")

    return TranscriptDocument(
        source_path=source_path,
        source_name=source_path.stem,
        text=text,
    )
