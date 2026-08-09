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

Adversarial schema evaluation (local Apple Silicon, fictional metadata):

- Compatible changes: 6/6 generated and validated on the first attempt
- Invalid foreign-key target: 1/1 refused before generation
- Compatible-case latency: 1.1494 to 4.4119 seconds per one-attempt run
- Live ownership: the official MCP normalized the same owner for all 3 support datasets

The later exact-asset ownership read succeeded, but its combined follow-on run
timed out while the local DataHub search service was degraded. It is not counted
as a second successful end-to-end writeback; the complete live run above remains
the writeback evidence.

Public agent delivery: https://github.com/Oxygen56/fixtureforge/pull/1

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
| Ownership-aware | official MCP normalized the owner on all 3 live support datasets |
| Schema-change resilience | 6/6 compatible adversarial changes passed first attempt; invalid relationship refused |
| Relationship-safe | 30 live DuckDB checks plus a caught broken relation |
| Deterministic | two output inventories compare byte-identical |
| Merge-ready delivery | agent-created public branch, commit, and PR |
| Useful writeback | Context Document with Git receipt and full-fingerprint readback |

## Public release

- Repository: https://github.com/Oxygen56/fixtureforge
- Agent PR: https://github.com/Oxygen56/fixtureforge/pull/1
- Ownership and adversarial-evidence PR: https://github.com/Oxygen56/fixtureforge/pull/2
- Upstream DataHub Skill PR: https://github.com/datahub-project/datahub-skills/pull/127
- Current video: https://youtu.be/hZRhNeFJiqA
- Submitted project: https://devpost.com/software/fixtureforge

The current evidence proves local operation, public CI, and a reviewable Git
artifact. It does not prove production deployment, external adoption, privacy
safety, anonymization, or time savings.
