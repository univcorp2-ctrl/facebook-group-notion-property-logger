from __future__ import annotations

import hashlib
from dataclasses import dataclass, field


@dataclass(frozen=True)
class SourcePost:
    id: str | None
    url: str
    content: str
    created_time: str | None = None
    author: str | None = None
    title: str | None = None
    attachments: list[str] = field(default_factory=list)

    def stable_key(self) -> str:
        """Return a deterministic key for duplicate detection."""
        base = self.url.strip() or f"{self.id or ''}:{self.content[:200]}"
        return hashlib.sha256(base.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class SyncResult:
    key: str
    url: str
    status: str
    title: str | None = None
    error: str | None = None
