from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from .models import SourcePost
from .parsers import extract_urls, normalize_whitespace


class SourceError(ValueError):
    pass


def _coerce_attachments(value: Any) -> list[str]:
    if value is None or value == "":
        return []
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    if isinstance(value, dict):
        urls: list[str] = []
        for key in ("url", "href", "link"):
            if value.get(key):
                urls.append(str(value[key]))
        if "data" in value and isinstance(value["data"], list):
            for item in value["data"]:
                urls.extend(_coerce_attachments(item))
        return urls
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return []
        try:
            parsed = json.loads(stripped)
        except json.JSONDecodeError:
            return extract_urls(stripped) or [stripped]
        return _coerce_attachments(parsed)
    return [str(value)]


def _pick(record: dict[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = record.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return None


def normalize_record(record: dict[str, Any]) -> SourcePost:
    content = _pick(record, "content", "message", "text", "body", "description") or ""
    url = _pick(record, "post_url", "url", "permalink_url", "link")
    if not url:
        urls = extract_urls(content)
        url = urls[0] if urls else ""
    if not url and not content.strip():
        raise SourceError("record must include at least a URL or content")

    attachments = _coerce_attachments(
        record.get("attachments", record.get("attachments_json", record.get("media_urls")))
    )

    return SourcePost(
        id=_pick(record, "id", "post_id", "source_id"),
        url=url,
        content=normalize_whitespace(content),
        created_time=_pick(record, "created_time", "created_at", "posted_at", "date"),
        author=_pick(record, "author", "from", "user", "poster"),
        title=_pick(record, "title", "name"),
        attachments=attachments,
    )


def load_posts_from_json(path: Path) -> list[SourcePost]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        rows = data.get("posts", data.get("data", []))
    elif isinstance(data, list):
        rows = data
    else:
        raise SourceError("JSON source must be a list or an object with posts/data")
    if not isinstance(rows, list):
        raise SourceError("JSON posts/data must be a list")
    return [normalize_record(row) for row in rows if isinstance(row, dict)]


def load_posts_from_csv(path: Path) -> list[SourcePost]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return [normalize_record(dict(row)) for row in reader]


def load_posts_from_file(path: str | Path) -> list[SourcePost]:
    source_path = Path(path)
    if not source_path.exists():
        raise SourceError(f"source file not found: {source_path}")
    suffix = source_path.suffix.lower()
    if suffix == ".json":
        return load_posts_from_json(source_path)
    if suffix == ".csv":
        return load_posts_from_csv(source_path)
    raise SourceError("source must be .json or .csv")
