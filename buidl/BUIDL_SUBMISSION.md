# FixtureForge submission brief

## One-line pitch

Give FixtureForge a goal; it discovers governed DataHub assets and delivers
deterministic, merge-ready test assets without reading production source rows.

## Problem

Copying production rows into development creates privacy and access risk.
Hand-written fixtures avoid the copy but drift from real schemas, relationships,
and governance rules.

## Working solution

FixtureForge searches and scopes a DataHub graph through the official MCP
Server, reads schemas, keys, lineage, tags, and glossary terms, and produces
linked CSV and Parquet fixtures, dbt tests, typed Python accessors, validation
evidence, and a negative control. It then creates a reviewable Git change and,
with approval, writes a verified Context Document back to DataHub.

## Demo

- Live run: DATAHUB_GMS_URL=http://localhost:18080 make agent-live
- Recorded replay: make agent-demo
- Visual report: build/live-demo/evidence-report.html
- Final live video: build/video/fixtureforge-final-live.mp4 (2:07, 1080p)
- Public repository: https://github.com/Oxygen56/fixtureforge
- Public video: https://youtu.be/hZRhNeFJiqA
- Agent-generated PR: https://github.com/Oxygen56/fixtureforge/pull/1
- Clean-room live workflow: https://github.com/Oxygen56/fixtureforge/actions/runs/31325742018
- Ownership and adversarial-evidence PR: https://github.com/Oxygen56/fixtureforge/pull/2
- Submitted Devpost project: https://devpost.com/software/fixtureforge
- Upstream DataHub Skill contribution: https://github.com/datahub-project/datahub-skills/pull/127

## Technical architecture

The bounded agent interprets a natural-language goal, searches DataHub, expands
one-hop lineage, enforces exact namespace scope, and normalizes official MCP
metadata into a strict Pydantic contract. A deterministic compiler orders
dataset dependencies and selects semantic field generators. DuckDB independently
validates the outputs. Git delivery is isolated, and approved writeback performs
a full-fingerprint read-after-write check.

## Evidence

- Real DataHub OSS v1.6.0 and official mcp-server-datahub
- Search plus lineage discovery selected 3 support datasets and rejected cross-domain matches
- 30 of 30 independent live checks passed with zero source-row calls
- 1 intentionally broken foreign key detected
- 2 independent builds were byte-identical
- Real public agent-generated branch, commit, and pull request
- Verified DataHub Context Document writeback and full-fingerprint readback
- 27 tests passed with 91.59 percent overall coverage including the MCP adapter
- 30,000-row local benchmark completed in 2.2316 seconds
- 6/6 compatible adversarial schema changes passed on the first attempt
- 1 invalid relationship refused before generation
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
