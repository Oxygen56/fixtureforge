.PHONY: sync test lint demo judge datahub

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

judge:
	./scripts/judge_demo.sh

datahub:
	./scripts/start_datahub.sh
