# FixtureForge submission brief

## One-line pitch

Compile governed DataHub metadata into deterministic, merge-ready test assets
without reading production source rows.

## Problem

Copying production rows into development creates privacy and access risk.
Hand-written fixtures avoid the copy but drift from real schemas, relationships,
and governance rules.

## Working solution

FixtureForge reads schemas, keys, lineage, tags, and glossary terms from DataHub
OSS through the official MCP Server. It produces linked CSV and Parquet fixtures,
dbt tests, typed Python accessors, validation evidence, and a negative control.

## Demo

- Local run: DATAHUB_GMS_URL=http://localhost:8080 make judge
- Visual report: build/live-demo/evidence-report.html
- Local video draft: build/video/fixtureforge-demo-draft.mp4 (2:26, 1080p)
- Public repository and video: added only after authorized release

## Technical architecture

Official MCP metadata is normalized into a strict Pydantic contract. A
deterministic compiler topologically orders dataset dependencies and selects
semantic field generators. DuckDB independently validates the outputs. A
separate localhost-only command writes the evidence fingerprint through MCP and
performs a read-after-write check.

## Evidence

- Real DataHub OSS v1.6.0 and official mcp-server-datahub
- 7 metadata-only MCP calls and zero source-row calls
- 36 of 36 independent checks passed
- 1 intentionally broken foreign key detected
- 2 independent builds had identical file inventories
- 20 tests passed with 96.93 percent core coverage
- 30,000-row local benchmark completed in 2.2316 seconds
- Strict type and lint checks passed

## Judging rubric mapping

- Technological implementation: live OSS, official MCP, compiler, multi-format
  output, independent verifier, deterministic proof, and writeback
- Design: one-command run and a self-contained evidence report
- Potential impact: removes the need to copy production rows for fixture creation
- Quality of idea: metadata is compiled into executable developer assets
- Adherence: new Apache-2.0 project, English materials, disclosures, official MCP
- Open-source bonus: CI, tests, contribution guide, and security policy

## Claim boundary

Source-row-free is not an anonymization, privacy, compliance, adoption, or
production-readiness claim.
