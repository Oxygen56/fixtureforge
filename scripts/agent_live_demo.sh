#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd "$(dirname "$0")/.." && pwd)"
cd "$project_root"

export DATAHUB_GMS_URL="$(printenv DATAHUB_GMS_URL || echo http://localhost:18080)"
workspace="$(mktemp -d "$project_root/build/agent-live.XXXXXX")"
goal='Generate merge-ready source-row-free fixtures for DataHub assets matching "fiction_support"'

uv run fixtureforge datahub-seed \
  --input fixtures/fiction_support.metadata.json \
  --receipt "$workspace/datahub-seed-receipt.json"
uv run fixtureforge agent-run \
  --goal "$goal" \
  --policy policies/fiction_support.generation.json \
  --workspace "$workspace/run" \
  --git-repo "$workspace/review-repo" \
  --git-destination generated/support-fixtures \
  --approve-datahub-writeback \
  2>"$workspace/mcp-server.log"
uv run fixtureforge agent-report \
  --run "$workspace/run/agent-run.json" \
  --output "$workspace/run/agent-report.html"
uv run pytest --cov=fixtureforge --cov-report=term-missing
uv run ruff check src tests
uv run mypy src

echo "FixtureForge live agent demo verified."
echo "Workspace: $workspace"
echo "Report: $workspace/run/agent-report.html"
