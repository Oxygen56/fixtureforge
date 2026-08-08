# Goal card

## Goal

Give data developers merge-ready, governed test assets generated from DataHub
metadata, with a proof that no production source rows were read.

## Non-goals

- Anonymize copied production data.
- Infer undocumented business logic.
- Replace data owners or governance review.
- Claim production readiness from a local demo.

## Winning demo

A judge selects customers and orders in local DataHub. FixtureForge reads their
metadata through the official MCP server, generates linked fixtures and tests,
detects a deliberately broken foreign key, then saves a signed evidence document
back to local DataHub after approval.

## Stop conditions

Do not publish a repository, deploy a public service, upload a video, or submit
to Devpost without explicit user authorization.
