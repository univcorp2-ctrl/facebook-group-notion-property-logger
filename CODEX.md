# CODEX.md

## Project intent

Build a stable, compliant property-post logger that appends authorized Facebook-related post data to a single Notion page.

## Non-goals

- Do not add browser automation that logs into Facebook.
- Do not add stealth, fingerprint, CAPTCHA, rate-limit, or bot-detection bypass logic.
- Do not commit real Notion tokens, Facebook tokens, cookies, exported private data, or personal data.

## Commands

```bash
pip install -e '.[dev]'
ruff check .
pytest
QUALITY_REPEAT_COUNT=50 bash scripts/quality_gate.sh
python -m fb_notion_property_logger sync --source data/sample_posts.json --dry-run
python -m fb_notion_property_logger probe-facebook --group-id 1281008662437696
```

## Safe extension pattern

Add new authorized input adapters behind `source.py` and keep the internal `SourcePost` model stable. Any adapter must document the permission model and data provenance.

## Definition of done

- Quality gate passes with `QUALITY_REPEAT_COUNT=50`.
- Architecture docs are updated.
- Review packet is updated.
- Secrets remain external.
