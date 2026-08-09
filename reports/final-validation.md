# Final validation

## Outcome

FixtureForge v0.2.0 completed the bounded goal-to-Git-to-DataHub loop against
DataHub OSS v1.6.0 and official `mcp-server-datahub` 0.6.0.

Verified live support-domain run: `build/agent-live.Ptbi3a`

- Natural-language goal interpreted into exact namespace `fiction_support`
- Search plus one-hop lineage selected 3 datasets and rejected cross-domain matches
- Source rows read: 0
- Generated artifacts: 14
- Independent live checks: 30 passed
- Negative control: one broken foreign key detected
- Repeat build: byte-identical
- Git delivery: isolated branch and commit created
- DataHub writeback: Context Document created and full fingerprint read back
- Automated tests: 27 passed
- Overall coverage including MCP adapter: 91.59 percent
- Ruff and mypy strict mode: passed

Public agent delivery: https://github.com/Oxygen56/fixtureforge/pull/1

Clean-room GitHub Actions run: https://github.com/Oxygen56/fixtureforge/actions/runs/31325742018

## Independent second-domain evidence

Retail and support operations have different schemas, governed fields, enum
policies, and relationship graphs. Both compile and verify; the live agent demo
uses support operations, while the committed MCP replay uses retail.

## Scale check

The earlier local benchmark includes generation, CSV and Parquet emission,
validation, and the negative control.

| Total rows | Duration |
|---:|---:|
| 300 | 0.8515 seconds |
| 3,000 | 1.5212 seconds |
| 30,000 | 2.2316 seconds |

These measurements are local evidence, not production throughput or adoption.

## Evidence map

| Claim | Evidence |
|---|---|
| Autonomous scope | goal, search, lineage, exact namespace receipt, event timeline |
| Real DataHub OSS | GMS 1.6.0 detected by official pinned MCP server |
| Source-row-free | allowlisted metadata tools and zero row calls |
| Governance-aware | tags and glossary terms drive generated values and dbt metadata |
| Relationship-safe | 30 live DuckDB checks plus a caught broken relation |
| Deterministic | two output inventories compare byte-identical |
| Merge-ready delivery | agent-created public branch, commit, and PR |
| Useful writeback | Context Document with Git receipt and full-fingerprint readback |

## Public release

- Repository: https://github.com/Oxygen56/fixtureforge
- Agent PR: https://github.com/Oxygen56/fixtureforge/pull/1
- Live 2:06 video: https://youtu.be/hZRhNeFJiqA
- Clean-room live workflow: https://github.com/Oxygen56/fixtureforge/actions/runs/31325742018
- Submitted project: https://devpost.com/software/fixtureforge

The current evidence proves local operation, public CI, and a reviewable Git
artifact. It does not prove production deployment, external adoption, privacy
safety, anonymization, or time savings.
