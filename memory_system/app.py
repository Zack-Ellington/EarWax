"""CLI entry point for the EarWax transcript-to-note workflow."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

from src.db import PipelineDB
from src.extract import extract_memories
from src.ingest import load_transcript
from src.link import collect_existing_note_titles, filter_suggested_links
from src.models import ModelError, ModelRoute
from src.obsidian import write_candidate_note
from src.review import ensure_review_folder
from src.runtime import (
    default_model_name,
    default_model_path,
    default_server_executable,
    default_venv_python,
    ensure_runtime_ready,
)
from src.schemas import ValidationError
from src.segment import split_transcript


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Process a transcript into candidate Obsidian notes through llama.cpp."
    )
    parser.add_argument("transcript", help="Path to the input transcript .txt file")
    parser.add_argument(
        "--vault-path",
        nargs="+",
        required=True,
        help="Path to the Obsidian vault root",
    )
    parser.add_argument(
        "--db-path",
        default="data/memory.db",
        help="SQLite path for pipeline state (default: data/memory.db)",
    )
    parser.add_argument(
        "--model",
        default=default_model_name(),
        help="Model name exposed by the local llama.cpp server",
    )
    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:8080",
        help="OpenAI-compatible llama.cpp server URL (default: http://127.0.0.1:8080)",
    )
    parser.add_argument(
        "--expected-python",
        default=default_venv_python(),
        help="Expected Python interpreter path for the local venv",
    )
    parser.add_argument(
        "--server-exe",
        default=default_server_executable(),
        help="Path to the llama.cpp server executable used for runtime diagnostics",
    )
    parser.add_argument(
        "--model-path",
        default=default_model_path(),
        help="Path to the GGUF model that should be served by llama.cpp",
    )
    parser.add_argument(
        "--segment-chars",
        type=int,
        default=2400,
        help="Target character count per transcript segment",
    )
    parser.add_argument(
        "--overlap-chars",
        type=int,
        default=240,
        help="Overlap size between neighboring transcript segments",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    vault_arg = " ".join(args.vault_path).strip()
    ensure_runtime_ready(
        expected_python=args.expected_python,
        server_executable=args.server_exe,
        model_path=args.model_path,
        base_url=args.base_url,
        model_name=args.model,
        original_argv=argv if argv is not None else sys.argv[1:],
    )

    transcript = load_transcript(args.transcript)
    segments = split_transcript(
        transcript.text,
        target_chars=args.segment_chars,
        overlap_chars=args.overlap_chars,
    )
    if not segments:
        raise ValueError("No transcript segments were produced")

    vault_path = Path(vault_arg).expanduser().resolve()
    ensure_review_folder(vault_path)

    db_path = Path(args.db_path)
    if not db_path.is_absolute():
        db_path = CURRENT_DIR / db_path

    database = PipelineDB(db_path)
    run_id = database.create_run(str(transcript.source_path), len(segments))
    model = ModelRoute(name=args.model, base_url=args.base_url)
    existing_titles = collect_existing_note_titles(vault_path)

    success_count = 0
    failure_count = 0

    try:
        for segment in segments:
            extraction = extract_memories(model, segment)
            note_paths: list[str] = []

            for memory in extraction.memories:
                memory.suggested_links = filter_suggested_links(
                    memory.suggested_links,
                    existing_titles,
                )
                note_path = write_candidate_note(
                    vault_path,
                    memory,
                    source_name=transcript.source_name,
                    segment_index=segment.index,
                    run_id=run_id,
                )
                note_paths.append(str(note_path))
                existing_titles.add(note_path.stem)

            database.record_segment_status(
                run_id=run_id,
                segment_index=segment.index,
                status="completed",
                transcript_excerpt=segment.text,
                note_paths=note_paths,
            )
            success_count += 1

        database.mark_run_complete(
            run_id,
            success_count=success_count,
            failure_count=failure_count,
        )
    except (ModelError, ValidationError, ValueError) as exc:
        failure_count += 1
        database.record_segment_status(
            run_id=run_id,
            segment_index=segment.index if "segment" in locals() else -1,
            status="failed",
            transcript_excerpt=segment.text if "segment" in locals() else "",
            error_message=str(exc),
        )
        database.mark_run_failed(run_id, str(exc))
        print(f"Pipeline failed: {exc}", file=sys.stderr)
        return 1

    print(
        f"Run {run_id} completed. Processed {success_count} segments and wrote candidate notes to "
        f"{vault_path / '00_Inbox' / 'AI Review'}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
