from __future__ import annotations

import sqlite3
from pathlib import Path


class ProcessedStore:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        if str(self.path) != ":memory:":
            self.path.parent.mkdir(parents=True, exist_ok=True)
        self._setup()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.path)

    def _setup(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS processed_posts (
                    post_key TEXT PRIMARY KEY,
                    url TEXT NOT NULL,
                    source_id TEXT,
                    created_time TEXT,
                    notion_response_id TEXT,
                    processed_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

    def has(self, post_key: str) -> bool:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT 1 FROM processed_posts WHERE post_key = ? LIMIT 1", (post_key,)
            ).fetchone()
        return row is not None

    def mark_processed(
        self,
        post_key: str,
        url: str,
        source_id: str | None,
        created_time: str | None,
        notion_response_id: str | None,
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO processed_posts (
                    post_key, url, source_id, created_time, notion_response_id
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (post_key, url, source_id, created_time, notion_response_id),
            )

    def clear(self) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM processed_posts")

    def count(self) -> int:
        with self._connect() as conn:
            row = conn.execute("SELECT COUNT(*) FROM processed_posts").fetchone()
        return int(row[0]) if row else 0
