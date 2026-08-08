# Contributing

FixtureForge welcomes focused improvements to metadata adapters, deterministic
generators, constraint validation, and developer artifact emitters.

## Development

1. Install uv and Docker.
2. Run make sync.
3. Run make test and make lint before opening a change.
4. Add a property or regression test for behavior changes.
5. Keep external claims aligned with docs/evidence-policy.md.

Generated examples must be source-row-free. Do not contribute copied production
records, credentials, secrets, or proprietary metadata.
