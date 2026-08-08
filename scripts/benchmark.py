#!/usr/bin/env python3
"""Measure deterministic generation and verification at useful demo scales."""

from __future__ import annotations

import json
import time
from pathlib import Path

from fixtureforge.evidence import write_json
from fixtureforge.models import MetadataBundle
from fixtureforge.service import generate


def main() -> None:
    root = Path(__file__).resolve().parent.parent
    source = MetadataBundle.model_validate_json(
        (root / "fixtures/fiction_retail.metadata.json").read_text()
    )
    results = []
    for rows in (100, 1_000, 10_000):
        scaled = source.model_copy(deep=True)
        for dataset in scaled.datasets:
            dataset.rows = rows
        input_path = root / "build" / f"benchmark-{rows}.metadata.json"
        write_json(input_path, scaled.model_dump(mode="json"))
        output = root / "build" / f"benchmark-{rows}"
        started = time.perf_counter()
        manifest = generate(input_path, output, 2026)
        elapsed = time.perf_counter() - started
        size_bytes = sum(
            path.stat().st_size for path in output.rglob("*") if path.is_file()
        )
        results.append(
            {
                "rows_per_dataset": rows,
                "total_rows": rows * len(scaled.datasets),
                "duration_seconds": round(elapsed, 4),
                "bundle_bytes": size_bytes,
                "validation_passed": manifest["validation_passed"],
                "negative_control_detected": manifest["negative_control_detected"],
            }
        )
    report = {
        "environment": "local Apple Silicon Docker host, Python 3.12",
        "method": "generation, CSV and Parquet emission, independent validation, negative control",
        "results": results,
        "claim_boundary": "local benchmark; not a production throughput claim",
    }
    write_json(root / "reports" / "benchmark.json", report)
    lines = [
        "# Local benchmark",
        "",
        "Generation, CSV and Parquet emission, independent validation, and the",
        "negative control are included in every timing.",
        "",
        "| Total rows | Duration (s) | Bundle size (bytes) | Verified |",
        "|---:|---:|---:|:---:|",
    ]
    lines.extend(
        (
            f"| {result['total_rows']} | {result['duration_seconds']} | "
            f"{result['bundle_bytes']} | yes |"
        )
        for result in results
    )
    lines.extend(
        [
            "",
            "These are local measurements, not a production throughput claim.",
            "",
        ]
    )
    (root / "reports" / "benchmark.md").write_text("\n".join(lines))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
