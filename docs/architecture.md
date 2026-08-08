# Architecture

FixtureForge has four explicit layers:

1. Metadata adapters read a normalized contract from a file or official DataHub MCP.
2. The compiler resolves dependencies and chooses deterministic generation rules.
3. Emitters write fixtures, typed factories, dbt tests, and a provenance manifest.
4. The verifier checks constraints independently with DuckDB and emits evidence.

The core never receives a source-row API. The MCP adapter uses an allowlist and
records every tool call. Writeback is a separate, approval-gated command.
