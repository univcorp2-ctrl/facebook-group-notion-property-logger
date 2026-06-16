from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Config:
    notion_token: str | None
    notion_page_id: str | None
    state_db_path: Path
    import_source_path: Path
    notion_version: str = "2022-06-28"

    @classmethod
    def from_env(cls) -> "Config":
        return cls(
            notion_token=os.getenv("NOTION_TOKEN"),
            notion_page_id=os.getenv("NOTION_PAGE_ID"),
            state_db_path=Path(os.getenv("STATE_DB_PATH", ".state/processed.sqlite3")),
            import_source_path=Path(os.getenv("IMPORT_SOURCE_PATH", "data/import/posts.json")),
            notion_version=os.getenv("NOTION_VERSION", "2022-06-28"),
        )
