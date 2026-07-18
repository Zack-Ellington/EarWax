"""Validation for model outputs."""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any


class ValidationError(ValueError):
    """Raised when model output cannot be validated."""


ALLOWED_MEMORY_TYPES = {
    "decision",
    "belief",
    "preference",
    "event",
    "question",
    "project_update",
    "reflection",
}


@dataclass(slots=True)
class CandidateMemory:
    title: str
    claim: str
    evidence_quote: str
    confidence: float
    importance: int
    memory_type: str
    suggested_links: list[str]


@dataclass(slots=True)
class SegmentExtraction:
    memories: list[CandidateMemory]


def validate_model_output(raw_output: str) -> SegmentExtraction:
    payload = _coerce_json(raw_output)
    if not isinstance(payload, dict):
        raise ValidationError("Model output must be a JSON object")

    memories_raw = payload.get("memories", [])
    if not isinstance(memories_raw, list):
        raise ValidationError("'memories' must be a JSON array")

    memories = [_validate_memory(item) for item in memories_raw]
    return SegmentExtraction(memories=memories)


def extraction_json_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "memories": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "claim": {"type": "string"},
                        "evidence_quote": {"type": "string"},
                        "confidence": {"type": "number"},
                        "importance": {"type": "integer"},
                        "memory_type": {"type": "string", "enum": sorted(ALLOWED_MEMORY_TYPES)},
                        "suggested_links": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                    },
                    "required": [
                        "title",
                        "claim",
                        "evidence_quote",
                        "confidence",
                        "importance",
                        "memory_type",
                        "suggested_links",
                    ],
                    "additionalProperties": False,
                },
            }
        },
        "required": ["memories"],
        "additionalProperties": False,
    }


def _coerce_json(raw_output: str) -> Any:
    trimmed = raw_output.strip()
    try:
        return json.loads(trimmed)
    except json.JSONDecodeError:
        start = trimmed.find("{")
        end = trimmed.rfind("}")
        if start == -1 or end == -1 or start >= end:
            raise ValidationError("Model output did not contain valid JSON")
        try:
            return json.loads(trimmed[start : end + 1])
        except json.JSONDecodeError as exc:
            raise ValidationError("Model output JSON could not be parsed") from exc


def _validate_memory(item: Any) -> CandidateMemory:
    if not isinstance(item, dict):
        raise ValidationError("Each memory must be a JSON object")

    title = _require_non_empty_string(item, "title", max_length=140)
    claim = _require_non_empty_string(item, "claim", max_length=1000)
    evidence_quote = _require_non_empty_string(item, "evidence_quote", max_length=600)
    memory_type = _require_non_empty_string(item, "memory_type", max_length=40)
    if memory_type not in ALLOWED_MEMORY_TYPES:
        raise ValidationError(f"Invalid memory_type '{memory_type}'")

    confidence_raw = item.get("confidence")
    if not isinstance(confidence_raw, (int, float)) or not 0 <= float(confidence_raw) <= 1:
        raise ValidationError("confidence must be a number between 0 and 1")

    importance_raw = item.get("importance")
    if not isinstance(importance_raw, int) or not 1 <= importance_raw <= 5:
        raise ValidationError("importance must be an integer between 1 and 5")

    links_raw = item.get("suggested_links", [])
    if not isinstance(links_raw, list) or any(not isinstance(link, str) for link in links_raw):
        raise ValidationError("suggested_links must be an array of strings")
    suggested_links = [link.strip() for link in links_raw if link.strip()][:8]

    return CandidateMemory(
        title=title,
        claim=claim,
        evidence_quote=evidence_quote,
        confidence=round(float(confidence_raw), 3),
        importance=importance_raw,
        memory_type=memory_type,
        suggested_links=suggested_links,
    )


def _require_non_empty_string(
    item: dict[str, Any],
    field_name: str,
    *,
    max_length: int,
) -> str:
    value = item.get(field_name)
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"{field_name} must be a non-empty string")
    normalized = " ".join(value.strip().split())
    if len(normalized) > max_length:
        raise ValidationError(f"{field_name} exceeds max length of {max_length}")
    return normalized
