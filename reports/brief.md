# FixtureForge competition brief

## Decision

Build FixtureForge for the Metadata-Aware Code Generation & Development track.
It compiles governed DataHub metadata into deterministic test fixtures without
reading production source rows.

## Hard rules

- Deadline: 10 August 2026, 17:00 EDT; 11 August 2026, 05:00 in Shanghai.
- Use DataHub OSS and at least one official agent component.
- Publish a new public repository with Apache-2.0 at its root.
- Provide an English submission and a public, no-login video shorter than three minutes.
- Keep the project testable through 1 September 2026.
- Public publication and submission require explicit user authorization.

## Product proof

The minimum winning path is:

1. Read schema, key relations, glossary terms, tags, assertions, and lineage
   through the official DataHub MCP Server.
2. Compile deterministic multi-table CSV, Parquet, typed factories, and dbt tests.
3. Generate valid examples plus targeted boundary and negative cases.
4. Validate types, uniqueness, foreign keys, enums, nullability, and determinism.
5. Produce a provenance manifest proving which metadata was used and which
   source-row tools were never called.
6. Save the evidence back to local DataHub only after an explicit approval gate.

## Claim boundary

The defensible claim is source-row-free generation. It is not anonymization,
differential privacy, production readiness, or proof that metadata is correct.

## Competitive position

Public competitors cluster around incident remediation, schema drift, lineage
impact, and code generation. The investigated public sample contained no exact
match for metadata-constrained, source-row-free synthetic fixtures. This is a
sample-based gap, not proof that no competitor exists.

## Acceptance target

- One-command reproducible judge path.
- Real local DataHub OSS and official MCP traffic, not a mocked connector.
- At least two related tables with primary and foreign keys.
- Semantic handling for PII, enums, dates, money, and assertions.
- Same seed and metadata produce byte-identical outputs.
- A visible failure case proves the validator catches an intentionally broken fixture.
- Automated tests and a concise evidence report.
- Final public release and Devpost submission only after user authorization.
