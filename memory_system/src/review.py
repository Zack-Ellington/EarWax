"""Review-stage helpers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class ReviewResult:
    note_paths: list[Path]
    written_count: int


def ensure_review_folder(vault_path: str | Path) -> Path:
    review_dir = Path(vault_path) / "00_Inbox" / "AI Review"
    review_dir.mkdir(parents=True, exist_ok=True)
    return review_dir
