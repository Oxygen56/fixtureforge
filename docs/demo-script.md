# Video script — target 2 minutes 35 seconds

## 0:00–0:18 · Problem

Data developers need realistic test fixtures, but copying production rows creates
privacy risk and hand-written fixtures drift from the catalog. FixtureForge
turns governed DataHub metadata into merge-ready test assets without reading
source rows.

## 0:18–0:42 · Real DataHub input

Show local DataHub OSS with customers, orders, and order_items. Highlight the
primary and foreign keys, customer email PII tag, glossary terms, and downstream
lineage.

## 0:42–1:05 · Official MCP evidence

Run the judge command. Show that FixtureForge launches the official DataHub MCP
Server with mutation disabled and calls only get_entities, list_schema_fields,
and get_lineage. Point to source rows read: zero.

## 1:05–1:33 · Generated developer assets

Open generated CSV and Parquet fixtures, dbt schema tests, and typed Python
factory. Show linked customer and order identifiers, fake example.test email
addresses, enum values, and range boundaries.

## 1:33–1:55 · Independent verification

Open the report. Show all 36 DuckDB checks passing. Then show the negative
control: FixtureForge replaces one order customer ID with a missing parent and
the verifier catches the foreign-key violation.

## 1:55–2:18 · Determinism and writeback

Show the two independent builds have identical file hashes. Then show the
approval-gated MCP writeback and the read-after-write receipt in local DataHub.

## 2:18–2:35 · Close

FixtureForge gives developers governed, reviewable fixtures before production
data is available or appropriate. It is source-row-free, deterministic,
Apache-2.0, and ready to extend through new metadata adapters and emitters.
