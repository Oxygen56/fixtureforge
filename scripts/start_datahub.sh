#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd "$(dirname "$0")/.." && pwd)"
cd "$project_root"

mapped_port="$(printenv DATAHUB_MAPPED_GMS_PORT || echo 8080)"
DATAHUB_MAPPED_GMS_PORT="$mapped_port" uv run datahub docker quickstart --version v1.6.0

echo "DataHub UI: http://localhost:9002"
echo "DataHub GMS: http://localhost:$mapped_port"
