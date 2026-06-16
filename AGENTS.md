# AGENTS.md

This repository is prepared for review and extension by other AI coding agents.

## Mission

Maintain a stable, compliant pipeline that records authorized Facebook-group property post data into one Notion page.

## Hard constraints

- Do not implement stealth browsing, CAPTCHA bypass, fingerprint spoofing, cookie replay, or rate-limit circumvention.
- Prefer official APIs and authorized CSV/JSON inputs.
- Keep network tests mocked. CI must not require real Facebook or Notion tokens.
- Never commit real tokens, cookies, private exports, or personal data.
- Preserve idempotency: processed posts must not be duplicated in Notion.

## Quality gate

Before considering a change ready:

```bash
pip install -e '.[dev]'
QUALITY_REPEAT_COUNT=50 bash scripts/quality_gate.sh
```

The quality gate performs compile checks, ruff, 50 pytest iterations, sample dry-run, and Facebook probe behavior validation without tokens.

## Main extension points

- `src/fb_notion_property_logger/source.py`: Add authorized input adapters.
- `src/fb_notion_property_logger/facebook_api.py`: Maintain official Graph API probes/fetchers.
- `src/fb_notion_property_logger/parsers.py`: Improve property field extraction.
- `src/fb_notion_property_logger/notion.py`: Change Notion block layout.

## Review focus

- Authorization model for every source adapter.
- Retry behavior and failure reporting.
- Duplicate handling.
- Notion API block limits.
- Parser precision and false positives.
