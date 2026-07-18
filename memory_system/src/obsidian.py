"""Obsidian-compatible Markdown note generation."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
import re

from .schemas import CandidateMemory


def slugify(title: str) -> str:
    slug = title.lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = slug.strip("-")
    return slug[:80] or "untitled"


def _yaml_list(items: list[str]) -> str:
    if not items:
        return "[]"
    return "\n".join(f"  - {item}" for item in items)


def write_candidate_note(
    vault_path: str | Path,
    memory: CandidateMemory,
    *,
    source_name: str,
    segment_index: int,
    run_id: int,
) -> Path:
    vault = Path(vault_path)
    review_dir = vault / "00_Inbox" / "AI Review"
    review_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now()
    date_prefix = timestamp.strftime("%Y-%m-%d")
    slug = slugify(memory.title)
    path = review_dir / f"{date_prefix}-{slug}.md"

    suffix = 1
    while path.exists():
        path = review_dir / f"{date_prefix}-{slug}-{suffix}.md"
        suffix += 1

    links = "\n".join(f"- [[{link}]]" for link in memory.suggested_links) or "- None"
    tags = ["memory/candidate", f"memory/{memory.memory_type}"]
    body = f"""---
type: candidate_memory
memory_type: {memory.memory_type}
status: unreviewed
created: {timestamp.isoformat(timespec="seconds")}
source_name: {source_name}
segment_index: {segment_index}
run_id: {run_id}
confidence: {memory.confidence}
importance: {memory.importance}
tags:
{_yaml_list(tags)}
suggested_links:
{_yaml_list(memory.suggested_links)}
---

# {memory.title}

## Claim

{memory.claim}

## Evidence

> {memory.evidence_quote}

## Context

- Source: `{source_name}`
- Segment: `{segment_index}`
- Memory type: `{memory.memory_type}`

## Suggested links

{links}

## Review

- [ ] Confirm
- [ ] Edit
- [ ] Reject
"""

    path.write_text(body, encoding="utf-8")
    return path
