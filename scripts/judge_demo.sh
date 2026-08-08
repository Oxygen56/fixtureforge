#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd "$(dirname "$0")/.." && pwd)"
cd "$project_root"

export DATAHUB_GMS_URL="$(printenv DATAHUB_GMS_URL || echo http://localhost:8080)"
target_urn="urn:li:dataset:(urn:li:dataPlatform:postgres,fiction_retail.customers,PROD)"

mkdir -p build/evidence

uv sync --all-groups
uv run fixtureforge datahub-seed \
  --input fixtures/fiction_retail.metadata.json \
  --receipt build/evidence/datahub-seed-receipt.json
uv run fixtureforge mcp-collect \
  --input fixtures/fiction_retail.metadata.json \
  --output build/evidence/mcp-trace.json \
  2>build/evidence/mcp-server.log
uv run fixtureforge mcp-normalize \
  --trace build/evidence/mcp-trace.json \
  --policy policies/fiction_retail.generation.json \
  --output build/evidence/live-metadata.json
uv run fixtureforge generate \
  --input build/evidence/live-metadata.json \
  --output build/live-demo \
  --seed 2026
uv run fixtureforge generate \
  --input build/evidence/live-metadata.json \
  --output build/live-demo-repeat \
  --seed 2026
uv run fixtureforge compare \
  --first build/live-demo \
  --second build/live-demo-repeat
uv run fixtureforge verify --bundle build/live-demo
uv run fixtureforge mcp-writeback \
  --manifest build/live-demo/evidence/manifest.json \
  --target-urn "$target_urn" \
  --output build/evidence/mcp-writeback-trace.json \
  --approve-local-writeback \
  2>>build/evidence/mcp-server.log
uv run fixtureforge report \
  --bundle build/live-demo \
  --mcp-trace build/evidence/mcp-trace.json \
  --writeback-trace build/evidence/mcp-writeback-trace.json \
  --output build/live-demo/evidence-report.html
uv run pytest --cov=fixtureforge --cov-report=term-missing
uv run ruff check src tests
uv run mypy src

echo "FixtureForge judge demo verified."
echo "Open build/live-demo/evidence-report.html"
