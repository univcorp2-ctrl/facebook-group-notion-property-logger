#!/usr/bin/env bash
set -euo pipefail

REPEAT_COUNT="${QUALITY_REPEAT_COUNT:-50}"
mkdir -p out

python -m compileall -q src tests
ruff check .

for i in $(seq 1 "$REPEAT_COUNT"); do
  echo "pytest iteration ${i}/${REPEAT_COUNT}"
  pytest -q
done

python -m fb_notion_property_logger sync \
  --source data/sample_posts.json \
  --dry-run \
  --output out/dry-run-result.json

set +e
python -m fb_notion_property_logger probe-facebook \
  --group-id https://www.facebook.com/groups/1281008662437696 \
  --output out/facebook-probe-without-token.json
probe_status=$?
set -e

if [[ "$probe_status" -ne 2 ]]; then
  echo "Expected probe-facebook without token to return exit code 2, got ${probe_status}" >&2
  exit 1
fi

python - <<'PY'
import json
import os
from pathlib import Path

probe = json.loads(Path('out/facebook-probe-without-token.json').read_text(encoding='utf-8'))
assert probe['token_provided'] is False
assert probe['ok'] is False
assert all('FACEBOOK_ACCESS_TOKEN' in (item.get('error') or '') for item in probe['probes'])

repeat_count = int(os.environ.get('QUALITY_REPEAT_COUNT', '50'))
report = {
    'ok': True,
    'pytest_iterations': repeat_count,
    'compileall': 'passed',
    'ruff': 'passed',
    'dry_run_artifact': 'out/dry-run-result.json',
    'facebook_probe_without_token': 'validated',
}
Path('out/quality-gate-report.json').write_text(
    json.dumps(report, ensure_ascii=False, indent=2) + '\n',
    encoding='utf-8',
)
print(json.dumps(report, ensure_ascii=False, indent=2))
PY
