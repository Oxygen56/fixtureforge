# Devpost submission draft

## Tagline

Compile governed DataHub metadata into deterministic test fixtures — without
reading production source rows.

## Inspiration

Data teams routinely choose between two bad test-data workflows: copy production
rows and inherit privacy risk, or hand-write fixtures that drift from schemas and
relationships. DataHub already contains the specification developers need.

## What it does

FixtureForge reads schema, keys, lineage, tags, and glossary terms from DataHub
through the official MCP Server. It combines that governed context with explicit
test-generation bounds, then emits linked CSV and Parquet fixtures, dbt tests,
typed Python accessors, and a provenance manifest.

An independent DuckDB verifier checks every generated constraint. A deliberate
broken-foreign-key control proves the verifier is real. A separate,
approval-gated MCP command writes the evidence fingerprint back to local DataHub
and verifies it with a read-after-write call.

## How we built it

FixtureForge is a Python 3.12 application using the official DataHub MCP Server,
DataHub OSS v1.6.0, MCP Python SDK, Pydantic, DuckDB, Typer, and uv. The compiler
topologically orders foreign-key dependencies and scopes its pseudo-random
generators by seed, dataset, and field.

## Challenges

The hardest part was making the privacy claim auditable rather than rhetorical.
We separated metadata collection from source data by construction, allowlisted
MCP tools, recorded every call, added a narrow claim boundary, and used an
independent verifier plus a negative control.

## Accomplishments

- real DataHub OSS and official MCP end-to-end integration;
- three linked datasets and nineteen governed fields;
- deterministic CSV, Parquet, dbt, and typed factory outputs;
- 36 independent checks and a caught negative control;
- byte-identical repeat builds;
- approval-gated MCP writeback with read-after-write verification;
- Apache-2.0 release with automated tests and an evidence-first security model.

## What we learned

Metadata is useful executable context, but it is not automatically correct.
FixtureForge therefore preserves provenance, separates explicit test policy from
catalog facts, and never upgrades source-row-free into an anonymization or
compliance claim.

## What is next

Add adapters for DataHub Assertions and structured properties, more emitters for
Spark and Great Expectations, graph-wide selection, and pull-request automation
that presents generated fixtures for human review.

## Built with

DataHub OSS, official DataHub MCP Server, Python, MCP SDK, Pydantic, DuckDB,
Typer, uv, pytest, Hypothesis, Ruff, and mypy.
