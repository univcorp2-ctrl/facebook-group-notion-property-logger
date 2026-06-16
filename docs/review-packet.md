# AI agent review packet

Use this file as the entry point for independent AI-agent review.

## Review objective

Confirm whether this repository provides a stable, compliant, and maintainable path to capture property-post data from the target Facebook group into a single Notion page.

Target group:

```text
https://www.facebook.com/groups/1281008662437696
```

## Architecture summary

- Official Graph API path: `probe-facebook` and `fetch-facebook`.
- Stable fallback path: authorized CSV/JSON ingestion.
- Sync target: one Notion page using append block children.
- Duplicate control: SQLite processed-state store.
- Quality gate: compile, lint, 50 pytest repetitions, dry-run, probe error validation.

## Commands to review

```bash
pip install -e '.[dev]'
QUALITY_REPEAT_COUNT=50 bash scripts/quality_gate.sh
python -m fb_notion_property_logger probe-facebook --group-id 1281008662437696
python -m fb_notion_property_logger sync --source data/sample_posts.json --dry-run
```

## Key code files

- `src/fb_notion_property_logger/facebook_api.py`
- `src/fb_notion_property_logger/cli.py`
- `src/fb_notion_property_logger/source.py`
- `src/fb_notion_property_logger/parsers.py`
- `src/fb_notion_property_logger/notion.py`
- `src/fb_notion_property_logger/state.py`

## Review questions

1. Are all data acquisition paths authorized and non-evasive?
2. Does the Graph API fetcher preserve enough raw data for audit/replay?
3. Is duplicate handling sufficient for repeated scheduled runs?
4. Does Notion block batching respect API limits?
5. Do parser tests cover common Japanese property patterns?
6. Are failures observable through structured JSON artifacts?
7. Are the extension points clear for future adapters?

## Known platform constraint

Meta deprecated Facebook Groups API in Graph API v19 and said the removal applies to all versions after the deprecation window. Therefore, successful direct group-feed API access depends on current Meta product availability, app permissions, and group authorization. This repository detects and reports that condition rather than attempting UI scraping or evasion.
