from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from .config import Config
from .models import SyncResult
from .notion import NotionClient, build_notion_blocks
from .source import SourceError, load_posts_from_file
from .state import ProcessedStore


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="fb-notion-property-logger",
        description="Append authorized property post data to a single Notion page.",
    )
    subparsers = parser.add_subparsers(dest="command")

    sync = subparsers.add_parser("sync", help="Sync posts from CSV/JSON into Notion")
    sync.add_argument("--source", type=Path, default=None, help="CSV or JSON source path")
    sync.add_argument("--state-db", type=Path, default=None, help="SQLite state database path")
    sync.add_argument("--dry-run", action="store_true", help="Do not call Notion or mark state")
    sync.add_argument("--reset-state", action="store_true", help="Clear processed state before running")
    sync.add_argument("--output", type=Path, default=None, help="Write JSON result to this path")
    sync.set_defaults(func=run_sync)

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


def run_sync(args: argparse.Namespace) -> int:
    config = Config.from_env()
    source_path = args.source or config.import_source_path
    state_db = args.state_db or config.state_db_path

    try:
        posts = load_posts_from_file(source_path)
    except SourceError as exc:
        write_output({"ok": False, "error": str(exc)}, args.output)
        return 2

    store = ProcessedStore(state_db)
    if args.reset_state:
        store.clear()

    notion: NotionClient | None = None
    if not args.dry_run:
        if not config.notion_token or not config.notion_page_id:
            write_output(
                {
                    "ok": False,
                    "error": "NOTION_TOKEN and NOTION_PAGE_ID are required unless --dry-run is used",
                },
                args.output,
            )
            return 2
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
            if args.dry_run:
                dry_run_payloads.append(
                    {
                        "key": key,
                        "url": post.url,
                        "title": title,
                        "details": details,
                        "block_count": len(blocks),
                    }
                )
                results.append(SyncResult(key=key, url=post.url, status="dry_run", title=title))
            else:
                assert notion is not None
                response = notion.append_to_page(config.notion_page_id or "", blocks)
                store.mark_processed(
                    post_key=key,
                    url=post.url,
                    source_id=post.id,
                    created_time=post.created_time,
                    notion_response_id=response.get("object"),
                )
                results.append(SyncResult(key=key, url=post.url, status="synced", title=title))
        except Exception as exc:  # noqa: BLE001 - CLI should report per-record failures.
            results.append(SyncResult(key=key, url=post.url, status="error", error=str(exc)))

    payload: dict[str, Any] = {
        "ok": not any(result.status == "error" for result in results),
        "source": str(source_path),
        "dry_run": args.dry_run,
        "processed_state_count": store.count(),
        "results": [result_to_dict(result) for result in results],
    }
    if args.dry_run:
        payload["notion_preview"] = dry_run_payloads

    write_output(payload, args.output)
    return 1 if not payload["ok"] else 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not hasattr(args, "func"):
        parser.print_help(sys.stderr)
        return 2
    return int(args.func(args))
