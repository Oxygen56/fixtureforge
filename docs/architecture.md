# Architecture

FixtureForge has six explicit phases:

1. The bounded agent interprets a natural-language goal into a DataHub search intent and safety boundary.
2. The pinned official MCP Server searches DataHub, expands one-hop lineage, and inspects schema and governance metadata.
3. The compiler resolves dependencies and chooses deterministic generation rules.
4. Emitters write fixtures, typed factories, dbt tests, provenance, and a deliberately invalid control.
5. DuckDB independently validates the bundle and a second build proves byte identity.
6. The agent creates an isolated Git branch and commit, then an approval-gated Context Document in DataHub and verifies its full fingerprint.

Every phase writes an event to `agent-run.json`. The core never receives a
source-row API. MCP reads are allowlisted, Git delivery refuses dirty or unsafe
destinations, and DataHub mutation is restricted to an explicit local approval.
