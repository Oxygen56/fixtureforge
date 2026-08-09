.PHONY: sync test lint demo agent-demo agent-live judge datahub

sync:
	uv sync --all-groups

test:
	uv run pytest --cov=fixtureforge --cov-report=term-missing

lint:
	uv run ruff check src tests
	uv run mypy src

demo:
	uv run fixtureforge generate --input fixtures/fiction_retail.metadata.json --output build/demo --seed 2026
	uv run fixtureforge verify --bundle build/demo

agent-demo:
	uv run fixtureforge agent-run --goal 'Generate merge-ready source-row-free fixtures for DataHub assets matching "FixtureForge"' --policy policies/fiction_retail.generation.json --workspace build/agent-replay --replay-trace examples/evidence/fiction-retail-mcp-trace.json
	uv run fixtureforge agent-report --run build/agent-replay/agent-run.json --output build/agent-replay/agent-report.html

agent-live:
	./scripts/agent_live_demo.sh

judge:
	./scripts/judge_demo.sh

datahub:
	./scripts/start_datahub.sh
