# Verified sample output

`verified-output/` is a committed FixtureForge bundle generated from the
fictional retail metadata contract with seed `2026`.

It lets reviewers inspect linked CSV and Parquet fixtures, dbt-compatible
tests, typed accessors, validation evidence, file hashes, and the deliberately
broken foreign-key control without first running the project.

Reproduce it with:

    uv run fixtureforge generate \
      --input fixtures/fiction_retail.metadata.json \
      --output examples/verified-output \
      --seed 2026

    uv run fixtureforge verify --bundle examples/verified-output

This committed bundle proves deterministic compiler and verifier behavior. It
is an offline replay, not the evidence for the separate live DataHub MCP run.
All schemas and rows in this example are fictional.
