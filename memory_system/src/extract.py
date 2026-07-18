"""Memory extraction prompts and model orchestration."""

from __future__ import annotations

from .models import ModelRoute
from .schemas import SegmentExtraction, extraction_json_schema, validate_model_output
from .segment import TranscriptSegment


SYSTEM_PROMPT = """You extract candidate personal memory notes from transcript segments.
Return JSON only. Do not include commentary.

Each candidate memory must represent a specific decision, belief, preference, event,
question, project update, or reflection that is grounded in the provided text.
Do not invent facts. Use direct evidence quotes from the segment.
"""


def extract_memories(
    route: ModelRoute,
    segment: TranscriptSegment,
) -> SegmentExtraction:
    user_prompt = f"""Extract candidate memories from this transcript segment.

Return a JSON object with this shape:
{{
  "memories": [
    {{
      "title": "short descriptive title",
      "claim": "one concise claim grounded in the transcript",
      "evidence_quote": "short supporting quote copied from the transcript",
      "confidence": 0.0,
      "importance": 1,
      "memory_type": "decision|belief|preference|event|question|project_update|reflection",
      "suggested_links": ["Existing Note Title", "Another Note"]
    }}
  ]
}}

If there are no good candidate memories, return {{"memories": []}}.

Transcript segment #{segment.index}:
{segment.text}
"""
    raw_output = route.chat(
        [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        extra_payload={
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "candidate_memory_extraction",
                    "schema": extraction_json_schema(),
                },
            }
        },
    )
    return validate_model_output(raw_output)
