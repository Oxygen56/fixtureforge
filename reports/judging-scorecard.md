# Judging scorecard

This is an internal evidence review, not a prediction of official results.

| Official criterion | Current strongest evidence | Remaining risk |
|---|---|---|
| Use of DataHub | live search, lineage, schema/governance/ownership reads, structured Context Document writeback and content verification | demonstrated on local OSS, not an external tenant |
| Technical Execution | bounded agent loop, exact scope, four generated artifact types, independent validator, negative control, deterministic rebuild, Git PR, 6/6 compatible adversarial changes | live CI must remain green and judge hardware needs about 6 GB |
| Originality | generates source-row-free multi-table fixtures from governance metadata, distinct from mutation testing or lineage impact tools | synthetic data quality depends on metadata quality |
| Real-World Usefulness | agent-created reviewable PR, retail and support domains, dbt and typed factory outputs | no external user or production adoption evidence |
| Submission Quality | public Apache-2.0 source, one-command replay/live paths, receipts, honest boundaries | original public video is static and must be replaced with live footage |
| Optional upstream bonus | reusable DataHub fixture-generation Skill submitted as upstream PR #127 | draft contribution is not acceptance or adoption |

## Highest-risk claim

Do not call FixtureForge anonymization, privacy-safe, production-ready, adopted,
or proven to save time. The demonstrated claim is narrower: autonomous,
source-row-free, deterministic fixture delivery from governed metadata in a
verified local DataHub environment.

## Recommended story

One goal → DataHub discovery → governed code generation → independent failure-
capable verification → real Git PR → approved structured DataHub writeback.
