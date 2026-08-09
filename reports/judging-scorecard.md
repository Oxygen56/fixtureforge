# Judging scorecard

This is an internal evidence review, not a prediction of official results.

| Official criterion | Current strongest evidence | Remaining risk |
|---|---|---|
| Use of DataHub | live search, lineage, schema/governance reads, structured Context Document writeback and content verification | demonstrated on local OSS, not an external tenant |
| Technical Execution | bounded agent loop, exact scope, four generated artifact types, independent validator, negative control, deterministic rebuild, Git PR | live CI must remain green and judge hardware needs about 6 GB |
| Originality | generates source-row-free multi-table fixtures from governance metadata, distinct from mutation testing or lineage impact tools | synthetic data quality depends on metadata quality |
| Real-World Usefulness | agent-created reviewable PR, retail and support domains, dbt and typed factory outputs | no external user or production adoption evidence |
| Submission Quality | public Apache-2.0 source, one-command replay/live paths, receipts, honest boundaries, and a 2:06 live evidence video | judges must follow the evidence links rather than relying on narration alone |
| Optional upstream bonus | none claimed | no accepted or reviewed upstream DataHub contribution |

## Highest-risk claim

Do not call FixtureForge anonymization, privacy-safe, production-ready, adopted,
or proven to save time. The demonstrated claim is narrower: autonomous,
source-row-free, deterministic fixture delivery from governed metadata in a
verified local DataHub environment.

## Recommended story

One goal → DataHub discovery → governed code generation → independent failure-
capable verification → real Git PR → approved structured DataHub writeback.
