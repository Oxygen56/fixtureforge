# Adversarial schema-change evaluation

One attempt per scenario; generation, CSV/Parquet emission, independent validation, and negative control are included in compatible-case latency.

First-pass success: **6/6 (100%)**. Invalid-contract guardrail: **1/1 caught**.

| Scenario | Expected | Result | Latency (s) |
|---|---|:---:|---:|
| baseline | merge_ready | verified | 2.988 |
| required_column_added | merge_ready | verified | 1.1494 |
| governed_pii_column_added | merge_ready | verified | 2.4092 |
| enum_expanded | merge_ready | verified | 2.0574 |
| relational_key_renamed | merge_ready | verified | 4.4119 |
| schema_fields_reordered | merge_ready | verified | 2.8801 |
| foreign_key_target_missing | refuse_before_generation | verified | 0.0016 |

Median compatible-case latency: **2.8801 s**; p95: **4.4119 s**.

Local fictional schemas on one Apple Silicon host; this is not a production reliability or throughput claim.
