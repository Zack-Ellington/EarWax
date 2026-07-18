"""SQLite state tracking for pipeline runs and segments."""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
import sqlite3


class PipelineDB:
    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_schema()

    @contextmanager
    def connect(self):
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    def create_run(self, source_path: str, segment_count: int) -> int:
        with self.connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO pipeline_runs (source_path, segment_count, status)
                VALUES (?, ?, 'running')
                """,
                (source_path, segment_count),
            )
            return int(cursor.lastrowid)

    def mark_run_complete(self, run_id: int, *, success_count: int, failure_count: int) -> None:
        with self.connect() as connection:
            connection.execute(
                """
                UPDATE pipeline_runs
                SET status = 'completed',
                    completed_at = CURRENT_TIMESTAMP,
                    success_count = ?,
                    failure_count = ?
                WHERE id = ?
                """,
                (success_count, failure_count, run_id),
            )

    def mark_run_failed(self, run_id: int, error_message: str) -> None:
        with self.connect() as connection:
            connection.execute(
                """
                UPDATE pipeline_runs
                SET status = 'failed',
                    completed_at = CURRENT_TIMESTAMP,
                    last_error = ?
                WHERE id = ?
                """,
                (error_message[:1000], run_id),
            )

    def record_segment_status(
        self,
        *,
        run_id: int,
        segment_index: int,
        status: str,
        transcript_excerpt: str,
        note_paths: list[str] | None = None,
        error_message: str | None = None,
    ) -> None:
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO segment_status (
                    run_id,
                    segment_index,
                    status,
                    transcript_excerpt,
                    note_paths,
                    error_message
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    segment_index,
                    status,
                    transcript_excerpt[:500],
                    "\n".join(note_paths or []),
                    error_message[:1000] if error_message else None,
                ),
            )

    def _ensure_schema(self) -> None:
        with self.connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS pipeline_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_path TEXT NOT NULL,
                    segment_count INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    success_count INTEGER NOT NULL DEFAULT 0,
                    failure_count INTEGER NOT NULL DEFAULT 0,
                    last_error TEXT,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    completed_at TEXT
                );

                CREATE TABLE IF NOT EXISTS segment_status (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id INTEGER NOT NULL,
                    segment_index INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    transcript_excerpt TEXT,
                    note_paths TEXT,
                    error_message TEXT,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (run_id) REFERENCES pipeline_runs(id)
                );
                """
            )
