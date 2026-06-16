# Quality gates

## Objective acceptance criteria

A change is review-ready only when all checks pass:

1. `python -m compileall -q src tests`
2. `ruff check .`
3. `pytest -q` repeated at least 50 times
4. sample Notion dry-run succeeds
5. Facebook probe without token returns a controlled, documented error
6. no real external network is required for tests
7. no secret-like values are committed

Run:

```bash
QUALITY_REPEAT_COUNT=50 bash scripts/quality_gate.sh
```

The script writes:

- `out/quality-gate-report.json`
- `out/dry-run-result.json`
- `out/facebook-probe-without-token.json`

## Why repeat pytest 50 times?

The code has parsing, idempotency, retry, and CLI behavior where accidental nondeterminism would be harmful. Repeating the test suite 50 times catches flaky behavior before the repository is treated as production-ready.

## What is not tested in CI

- Real Facebook Graph API access, because it requires a real token and permissions.
- Real Notion writes, because CI should not mutate a user's workspace by default.

Those live checks are available as explicit CLI commands and should be run only with authorized secrets.
