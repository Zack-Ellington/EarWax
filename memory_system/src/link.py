"""Lightweight link helpers for future vault enrichment."""

from __future__ import annotations

from pathlib import Path
import re


WIKILINK_PATTERN = re.compile(r"\[\[([^\]]+)\]\]")


def collect_existing_note_titles(vault_path: str | Path) -> set[str]:
    vault = Path(vault_path)
    if not vault.exists():
        return set()

    titles: set[str] = set()
    for path in vault.rglob("*.md"):
        titles.add(path.stem)
    return titles


def filter_suggested_links(suggested_links: list[str], existing_titles: set[str]) -> list[str]:
    if not existing_titles:
        return suggested_links
    return [link for link in suggested_links if link in existing_titles]
