# GitHub Actions activation note

The automation used to create this repository successfully committed application code, tests, docs, and the quality gate script. However, attempts to create active workflow files under `.github/workflows/` returned:

```text
GitHub API 404: Not Found
```

The attempted workflow is preserved at:

```text
docs/ci-workflow.yml
```

## How to activate CI in an environment with workflow-write permission

Move or copy the file:

```bash
mkdir -p .github/workflows
cp docs/ci-workflow.yml .github/workflows/quality-gate.yml
git add .github/workflows/quality-gate.yml
git commit -m "Activate quality gate workflow"
git push
```

The active workflow will run:

- compile checks
- ruff
- pytest repeated at least 50 times
- sample Notion dry-run
- Facebook probe no-token behavior check
- artifact upload

## Current repository status

Until `.github/workflows/quality-gate.yml` exists, GitHub Actions will show no workflow runs. The same checks remain available locally and in Codespaces via:

```bash
QUALITY_REPEAT_COUNT=50 bash scripts/quality_gate.sh
```
