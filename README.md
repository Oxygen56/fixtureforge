# FixtureForge

FixtureForge is a bounded autonomous agent that discovers a governed DataHub
graph, generates deterministic test assets, proves them, commits them for human
review, and writes structured evidence back to DataHub — without reading
production source rows.

It turns a natural-language goal, schemas, keys, lineage, tags, glossary terms,
and explicit test policy into:

- linked CSV and Parquet fixtures;
- dbt schema tests and typed Python accessors;
- valid boundary examples and an intentionally broken negative control;
- a reviewable Git branch and commit;
- a machine-verifiable manifest and agent decision trace; and
- a self-contained visual report.

FixtureForge is a new Apache-2.0 project for the Build with DataHub hackathon,
entered in Metadata-Aware Code Generation & Development.

![FixtureForge verified evidence report](docs/assets/evidence-report.png)

## Demo

- [Submitted Devpost project](https://devpost.com/software/fixtureforge)
- [Public live demonstration video (2:07)](https://youtu.be/hZRhNeFJiqA)
- [Public source repository](https://github.com/Oxygen56/fixtureforge)
- [Agent-generated review pull request](https://github.com/Oxygen56/fixtureforge/pull/1)
- [Ownership and adversarial-evidence pull request](https://github.com/Oxygen56/fixtureforge/pull/2)
- [Upstream DataHub Skill contribution](https://github.com/datahub-project/datahub-skills/pull/127)

## The problem

Data developers need representative fixtures before a pipeline is ready. Copying
production rows creates privacy, access, and reproducibility risk. Hand-written
fixtures avoid the copy but drift from schemas, relationships, and governance.

FixtureForge treats DataHub metadata as an executable test-data specification. A
developer gives the agent a goal, not a hand-curated dataset list.

## What makes the proof credible

The judge path uses real DataHub OSS v1.6.0 and the official DataHub MCP Server,
pinned to package 0.6.0. The agent searches DataHub, expands one-hop lineage,
applies an exact namespace boundary when the goal names one, and inspects the
selected graph. Mutation remains disabled throughout discovery.

The read allowlist is `search`, `get_entities`, `list_schema_fields`, and
`get_lineage`. There is no source-row tool in the adapter. Every request and
response is recorded, hashed, and cited in the output manifest.

The agent records plan, discovery, inspection, generation, validation,
deterministic rebuild, Git delivery, and writeback as separate states. DuckDB
independently checks row counts, nullability, uniqueness, ranges, enums, and
foreign keys. FixtureForge then breaks one foreign key on purpose and proves the
same verifier rejects it.

The adversarial schema suite changes required columns, governed PII fields,
enums, relationships, and field order. All 6 compatible changes generated and
validated on the first attempt; the invalid foreign-key target was refused
before generation. These are local fictional-domain measurements, not a
production reliability claim.

## Architecture

    natural-language goal
        |
        v
    DataHub search + one-hop lineage discovery
        |
        | official MCP: schema, keys, lineage, tags, terms
        v
    normalized contract + explicit test policy
        |
        v
    deterministic constraint compiler
        |
        +--> CSV and Parquet
        +--> dbt tests
        +--> typed factories
        +--> provenance manifest
        |
        v
    independent DuckDB verifier
        |
        +--> valid bundle passes
        +--> deliberately broken bundle fails
        |
        v
    isolated Git branch + commit
        |
        v
    approved DataHub Context Document + content readback

## Quick start

Requirements: Docker, uv, and about 6 GB of free memory for the DataHub
quickstart stack.

    make sync
    DATAHUB_MAPPED_GMS_PORT=18080 make datahub
    DATAHUB_GMS_URL=http://localhost:18080 make agent-live

The command prints a unique workspace containing the agent report, MCP traces,
generated bundle, isolated review repository, Git commit, and verified DataHub
Context Document receipt. It exercises a support-ticket graph, separate from the
original retail example.

## Fast recorded replay

Evaluate the full plan-to-verification loop without Docker using committed
official-MCP responses:

    make agent-demo

This is accurately labeled as a recording, not live DataHub evidence.

## Outputs

Review the [committed verified retail sample](examples/verified-output) and the
[recorded official-MCP evidence](examples/evidence/fiction-retail-mcp-trace.json).

| Path | Purpose |
|---|---|
| valid/csv | deterministic relational fixtures |
| valid/parquet | compressed fixtures for analytical pipelines |
| developer/schema.yml | dbt-compatible tests and governance metadata |
| developer/factories.py | typed fixture loader |
| negative/broken_foreign_key | deliberate failure case |
| evidence/validation.json | independent check results |
| evidence/negative-validation.json | proof the failure was caught |
| evidence/manifest.json | hashes, provenance, rules, and claim boundary |
| agent-run.json | plan, actions, gates, Git and DataHub receipts |
| agent-report.html | visual autonomous-run timeline |

## Reproducibility and CI

The same metadata, policy, version, and seed produce byte-identical outputs.
The 27-test suite covers the replay agent, Git delivery, transport safety,
document writeback, integration, property cases, and negative controls. Overall
coverage, including the MCP adapter, is enforced at 90 percent.

Core CI evaluates both retail and support domains. A separate Live DataHub
Integration workflow starts pinned DataHub OSS and runs the complete
goal-to-Git-to-DataHub loop.

## Security model

- Read-only MCP collection is the default and tools are allowlisted.
- Search results are scope-filtered when the goal names a dataset namespace.
- DataHub mutation is disabled during collection.
- Git delivery refuses dirty repositories and out-of-repository destinations.
- Local writeback requires an explicit approval flag.
- A Context Document is searched for its full fingerprint after mutation before
  success is reported.

## Honest boundaries

Source-row-free means FixtureForge does not inspect or copy source rows. It does
not mean anonymous, privacy-safe, differentially private, compliant, or
production-ready. Metadata can itself be sensitive or wrong.

The retail replay and live support demo are fictional. The repository proves
local operation and CI behavior, not production adoption or time savings.

## Development

    make test
    make lint

See CONTRIBUTING.md, SECURITY.md, docs/evidence-policy.md, and
THIRD_PARTY_NOTICES.md.

## License

Apache License 2.0.
