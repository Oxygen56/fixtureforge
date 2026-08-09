# Live video script — target 2 minutes 40 seconds

## 0:00–0:18 · Goal and problem

Show the actual terminal and type one goal: generate merge-ready source-row-free
fixtures for the `fiction_support` assets. Explain why copied rows and drifting
hand-written fixtures are both costly.

## 0:18–0:43 · Autonomous DataHub discovery

Run the live command. Show real DataHub OSS search results for accounts, tickets,
and ticket_events. Show the agent selecting exactly those three assets through
search plus lineage, with source rows read fixed at zero.

## 0:43–1:10 · Metadata drives code

Show PII email tags, primary and foreign keys, and the generated CSV, Parquet,
dbt tests, and typed factory. Emphasize that the input was a goal, not a dataset
manifest.

## 1:10–1:34 · Verification that can fail

Show all checks passing, then the deliberate broken foreign key failing. Show
the second build producing the same fingerprint.

## 1:34–1:58 · Real Git delivery

Show the branch, commit, changed-file list, and public pull request created from
the generated support-domain bundle.

## 1:58–2:25 · Useful DataHub writeback

Show the approval gate, saved Context Document, related asset, full fingerprint,
Git delivery receipt, and successful content readback through official MCP.

## 2:25–2:40 · Close

Show the agent timeline report and public CI. State the exact boundary:
source-row-free, deterministic, and locally verified; not anonymization or
production adoption.
