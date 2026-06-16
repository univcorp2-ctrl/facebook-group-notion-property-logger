from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

from .config import Config
from .facebook_api import (
    DEFAULT_FACEBOOK_API_VERSION,
    DEFAULT_GROUP_ID,
    fetch_group_feed,
    graph_posts_to_source_payload,
    probe_group_api,
)
from .models import SourcePost, SyncResult
from .notion import NotionClient, build_notion_blocks
from .source import SourceError, load_posts_from_file
from .state import ProcessedStore


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="fb-notion-property-logger",
        description="Append authorized property post data to a single Notion page.",
    )
    subparsers = parser.add_subparsers(dest="command")

    probe = subparsers.add_parser("probe-facebook", help="Check official Graph API availability")
    probe.add_argument("--group-id", default=DEFAULT_GROUP_ID, help="Facebook group ID or group URL")
    probe.add_argument("--api-version", default=DEFAULT_FACEBOOK_API_VERSION)
    probe.add_argument("--output", type=Path, default=None)
    probe.set_defaults(func=run_probe_facebook)

    fetch = subparsers.add_parser("fetch-facebook", help="Fetch group feed through official Graph API")
    fetch.add_argument("--group-id", default=DEFAULT_GROUP_ID, help="Facebook group ID or group URL")
    fetch.add_argument("--api-version", default=DEFAULT_FACEBOOK_API_VERSION)
    fetch.add_argument("--page-size", type=int, default=25)
    fetch.add_argument("--max-pages", type=int, default=20)
    fetch.add_argument("--since", default=None, help="Graph API since value, e.g. 2026-06-01")
    fetch.add_argument("--until", default=None, help="Graph API until value, e.g. 2026-06-16")
    fetch.add_argument("--output", type=Path, default=Path("data/import/posts.json"))
    fetch.set_defaults(func=run_fetch_facebook)

    sync = subparsers.add_parser("sync", help="Sync posts from CSV/JSON into Notion")
    sync.add_argument("--source", type=Path, default=None, help="CSV or JSON source path")
    sync.add_argument("--state-db", type=Path, default=None, help="SQLite state database path")
    sync.add_argument("--dry-run", action="store_true", help="Do not call Notion or mark state")
    sync.add_argument("--reset-state", action="store_true", help="Clear processed state before running")
    sync.add_argument("--output", type=Path, default=None, help="Write JSON result to this path")
    sync.set_defaults(func=run_sync)

    pipeline = subparsers.add_parser("pipeline", help="Fetch from Graph API, then sync to Notion")
    pipeline.add_argument("--group-id", default=DEFAULT_GROUP_ID)
    pipeline.add_argument("--api-version", default=DEFAULT_FACEBOOK_API_VERSION)
    pipeline.add_argument("--page-size", type=int, default=25)
    pipeline.add_argument("--max-pages", type=int, default=20)
    pipeline.add_argument("--since", default=None)
    pipeline.add_argument("--until", default=None)
    pipeline.add_argument("--source-output", type=Path, default=Path("out/facebook-posts.json"))
    pipeline.add_argument("--state-db", type=Path, default=None)
    pipeline.add_argument("--dry-run", action="store_true")
    pipeline.add_argument("--output", type=Path, default=Path("out/pipeline-result.json"))
    pipeline.set_defaults(func=run_pipeline)

    return parser


def result_to_dict(result: SyncResult) -> dict[str, Any]:
    return {
        "key": result.key,
        "url": result.url,
        "status": result.status,
        "title": result.title,
        "error": result.error,
    }


def write_output(payload: dict[str, Any], output_path: Path | None) -> None:
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(text + "\n", encoding="utf-8")
    print(text)


def run_probe_facebook(args: argparse.Namespace) -> int:
    token = os.getenv("FACEBOOK_ACCESS_TOKEN")
    probes = probe_group_api(args.group_id, token, args.api_version)
    payload = {
        "ok": all(probe.ok is True for probe in probes) if token else False,
        "group_id_or_url": args.group_id,
        "api_version": args.api_version,
        "token_provided": bool(token),
        "probes": [probe.to_dict() for probe in probes],
    }
    write_output(payload, args.output)
    return 0 if payload["ok"] else 2


def run_fetch_facebook(args: argparse.Namespace) -> int:
    token = os.getenv("FACEBOOK_ACCESS_TOKEN")
    if not token:
        write_output({"ok": False, "error": "FACEBOOK_ACCESS_TOKEN is required"}, args.output)
        return 2
    posts = fetch_group_feed(
        group_id=args.group_id,
        access_token=token,
        api_version=args.api_version,
        page_size=args.page_size,
        max_pages=args.max_pages,
        since=args.since,
        until=args.until,
    )
    payload = graph_posts_to_source_payload(posts)
    payload["ok"] = True
    payload["count"] = len(payload["posts"])
    write_output(payload, args.output)
    return 0


def sync_posts(posts: list[SourcePost], config: Config, state_db: Path, dry_run: bool) -> dict[str, Any]:
    store = ProcessedStore(state_db)
    notion: NotionClient | None = None
    if not dry_run:
        if not config.notion_token or not config.notion_page_id:
            return {"ok": False, "error": "NOTION_TOKEN and NOTION_PAGE_ID are required unless dry_run is used"}
        notion = NotionClient(config.notion_token, config.notion_version)

    results: list[SyncResult] = []
    dry_run_payloads: list[dict[str, Any]] = []
    for post in posts:
        key = post.stable_key()
        if store.has(key):
            results.append(SyncResult(key=key, url=post.url, status="skipped_duplicate"))
            continue
        try:
            title, details, blocks = build_notion_blocks(post)
            if dry_run:
                dry_run_payloads.append({"key": key, "url": post.url, "title": title, "details": details, "block_count": len(blocks)})
                results.append(SyncResult(key=key, url=post.url, status="dry_run", title=title))
            else:
                assert notion is not None
                response = notion.append_to_page(config.notion_page_id or "", blocks)
                store.mark_processed(key, post.url, post.id, post.created_time, response.get("object"))
                results.append(SyncResult(key=key, url=post.url, status="synced", title=title))
        except Exception as exc:  # noqa: BLE001
            results.append(SyncResult(key=key, url=post.url, status="error", error=str(exc)))
    payload: dict[str, Any] = {
        "ok": not any(result.status == "error" for result in results),
        "dry_run": dry_run,
        "processed_state_count": store.count(),
        "results": [result_to_dict(result) for result in results],
    }
    if dry_run:
        payload["notion_preview"] = dry_run_payloads
    return payload


def run_sync(args: argparse.Namespace) -> int:
    config = Config.from_env()
    source_path = args.source or config.import_source_path
    try:
        posts = load_posts_from_file(source_path)
    except SourceError as exc:
        write_output({"ok": False, "error": str(exc)}, args.output)
        return 2
    state_db = args.state_db or config.state_db_path
    if args.reset_state:
        ProcessedStore(state_db).clear()
    payload = sync_posts(posts, config, state_db, args.dry_run)
    payload["source"] = str(source_path)
    write_output(payload, args.output)
    return 0 if payload.get("ok") else 1


def run_pipeline(args: argparse.Namespace) -> int:
    token = os.getenv("FACEBOOK_ACCESS_TOKEN")
    if not token:
        write_output({"ok": False, "error": "FACEBOOK_ACCESS_TOKEN is required for pipeline fetch"}, args.output)
        return 2
    posts = fetch_group_feed(args.group_id, token, args.api_version, args.page_size, args.max_pages, args.since, args.until)
    source_payload = graph_posts_to_source_payload(posts)
    write_output(source_payload, args.source_output)
    from .source import normalize_record

    normalized_posts = [normalize_record(row) for row in source_payload["posts"]]
    config = Config.from_env()
    state_db = args.state_db or config.state_db_path
    sync_payload = sync_posts(normalized_posts, config, state_db, args.dry_run)
    sync_payload["facebook_fetch_count"] = len(posts)
    sync_payload["source_output"] = str(args.source_output)
    write_output(sync_payload, args.output)
    return 0 if sync_payload.get("ok") else 1


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not hasattr(args, "func"):
        parser.print_help(sys.stderr)
        return 2
    return int(args.func(args))
