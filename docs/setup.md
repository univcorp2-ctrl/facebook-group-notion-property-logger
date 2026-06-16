# Setup guide

## Required production values

| Secret | Where to store | Purpose |
| --- | --- | --- |
| `NOTION_TOKEN` | GitHub Secrets or local env | Notion integration token |
| `NOTION_PAGE_ID` | GitHub Secrets or local env | Target single Notion page/block ID |
| `FACEBOOK_ACCESS_TOKEN` | GitHub Secrets or local env | Optional. Used only for official Graph API probe/fetch |

Do not commit real tokens, cookies, browser profiles, private exports, or personal data.

## 1. Notion setup

1. Create one Notion page for the property log.
2. Create a Notion integration.
3. Give the integration insert-content capability.
4. Share the target page with the integration.
5. Save the integration token as `NOTION_TOKEN`.
6. Save the target page ID as `NOTION_PAGE_ID`.

## 2. Facebook API setup

The target group is `1281008662437696`, from:

```text
https://www.facebook.com/groups/1281008662437696
```

Run a probe first:

```bash
export FACEBOOK_ACCESS_TOKEN='EAAB...'
python -m fb_notion_property_logger probe-facebook \
  --group-id https://www.facebook.com/groups/1281008662437696 \
  --output out/facebook-probe.json
```

If the probe succeeds, fetch posts:

```bash
python -m fb_notion_property_logger fetch-facebook \
  --group-id 1281008662437696 \
  --max-pages 20 \
  --page-size 25 \
  --output data/import/posts.json
```

If the probe fails because the official endpoint is unavailable or permissions are not granted, use the authorized fallback format below.

## 3. Authorized CSV/JSON fallback

### JSON

```json
{
  "posts": [
    {
      "id": "post-001",
      "post_url": "https://www.facebook.com/groups/1281008662437696/posts/1234567890/",
      "content": "東京都渋谷区 1LDK 賃料18万円 45㎡ 渋谷駅徒歩8分",
      "created_time": "2026-06-16T09:00:00+09:00",
      "author": "投稿者名"
    }
  ]
}
```

### CSV

```csv
id,post_url,content,created_time,author
post-001,https://www.facebook.com/groups/1281008662437696/posts/1234567890/,東京都渋谷区 1LDK 賃料18万円 45㎡ 渋谷駅徒歩8分,2026-06-16T09:00:00+09:00,投稿者名
```

## 4. Local quality gate

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
QUALITY_REPEAT_COUNT=50 bash scripts/quality_gate.sh
```

## 5. Dry-run

```bash
python -m fb_notion_property_logger sync \
  --source data/sample_posts.json \
  --dry-run \
  --output out/dry-run-result.json
```

## 6. Live Notion sync

```bash
export NOTION_TOKEN='secret_xxx'
export NOTION_PAGE_ID='xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'
python -m fb_notion_property_logger sync \
  --source data/import/posts.json \
  --output out/live-sync-result.json
```

## 7. Full pipeline when Graph API is available

```bash
export FACEBOOK_ACCESS_TOKEN='EAAB...'
export NOTION_TOKEN='secret_xxx'
export NOTION_PAGE_ID='xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'
python -m fb_notion_property_logger pipeline \
  --group-id 1281008662437696 \
  --max-pages 20 \
  --page-size 25 \
  --output out/pipeline-result.json
```
