# Final local validation

## Outcome

FixtureForge completed the full local judge workflow against real DataHub OSS
v1.6.0 and the official DataHub MCP Server.

Verified run: 20260809-043312_live-e2e-v2

- Return code: 0
- End-to-end duration: 52.591 seconds
- MCP metadata calls: 7
- MCP tools used: get_entities, list_schema_fields, get_lineage
- Source rows read: 0
- Generated datasets: 3
- Generated fields: 19
- Generated rows in judge demo: 60
- Independent checks: 36 of 36 passed
- Negative control: one broken customer foreign key detected
- Repeat build: byte-identical file inventory
- Local MCP writeback: read-after-write verified
- Automated tests: 20 passed
- Core coverage: 96.93 percent
- Ruff: passed
- mypy strict mode: passed

## Scale check

The local benchmark includes generation, CSV and Parquet emission, independent
validation, and the negative control.

| Total rows | Duration |
|---:|---:|
| 300 | 0.8515 seconds |
| 3,000 | 1.5212 seconds |
| 30,000 | 2.2316 seconds |

These measurements are local evidence, not a production throughput claim.

## Evidence map

| Claim | Evidence |
|---|---|
| Real DataHub OSS | GMS version 1.6.0 detected by official MCP |
| Official agent component | mcp-server-datahub stdio initialization and tool list |
| Source-row-free | read-only allowlist, zero row tools, trace and manifest |
| Governance-aware | PII tags and glossary terms returned by list_schema_fields |
| Relationship-safe | primary keys, foreign keys, lineage, and 36 DuckDB checks |
| Not a hard-coded green screen | committed negative-control workflow |
| Deterministic | two independent output inventories compare identical |
| Writeback works | update_description plus get_entities read-after-write |

## Remaining release gates

The local product and evidence package are complete. Public repository creation,
video recording and upload, public project URL, and final Devpost submission are
external actions and remain intentionally unperformed until user authorization.
