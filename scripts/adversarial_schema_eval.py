#!/usr/bin/env python3
"""Measure first-pass adaptation to governed schema changes."""

from __future__ import annotations

import json
import math
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from fixtureforge.evidence import write_json
from fixtureforge.models import FieldSpec, MetadataBundle
from fixtureforge.service import generate

Mutation = Callable[[dict[str, Any]], None]


def _dataset(payload: dict[str, Any], name: str) -> dict[str, Any]:
    return next(item for item in payload["datasets"] if item["name"] == name)


def _add_required_channel(payload: dict[str, Any]) -> None:
    tickets = _dataset(payload, "tickets")
    tickets["fields"].append(
        FieldSpec(
            name="channel",
            type="VARCHAR",
            nullable=False,
            enum_values=["email", "chat", "api"],
        ).model_dump(mode="json")
    )


def _add_governed_pii(payload: dict[str, Any]) -> None:
    accounts = _dataset(payload, "accounts")
    accounts["fields"].append(
        FieldSpec(
            name="billing_email",
            type="VARCHAR",
            nullable=False,
            tags=["PII"],
            glossary_terms=["email_address"],
        ).model_dump(mode="json")
    )


def _expand_enum(payload: dict[str, Any]) -> None:
    tickets = _dataset(payload, "tickets")
    status = next(field for field in tickets["fields"] if field["name"] == "status")
    status["enum_values"].append("escalated")


def _rename_relational_key(payload: dict[str, Any]) -> None:
    accounts = _dataset(payload, "accounts")
    tickets = _dataset(payload, "tickets")
    next(field for field in accounts["fields"] if field["name"] == "account_id")["name"] = (
        "customer_account_id"
    )
    accounts["primary_key"] = ["customer_account_id"]
    next(field for field in tickets["fields"] if field["name"] == "account_id")["name"] = (
        "customer_account_id"
    )
    relation = tickets["foreign_keys"][0]
    relation["fields"] = ["customer_account_id"]
    relation["references_fields"] = ["customer_account_id"]


def _reorder_fields(payload: dict[str, Any]) -> None:
    for dataset in payload["datasets"]:
        dataset["fields"].reverse()


def _break_foreign_key_target(payload: dict[str, Any]) -> None:
    _dataset(payload, "tickets")["foreign_keys"][0]["references_table"] = "missing_accounts"


def main() -> None:
    root = Path(__file__).resolve().parent.parent
    baseline = MetadataBundle.model_validate_json(
        (root / "fixtures/fiction_support.metadata.json").read_text()
    )
    compatible: list[tuple[str, Mutation | None]] = [
        ("baseline", None),
        ("required_column_added", _add_required_channel),
        ("governed_pii_column_added", _add_governed_pii),
        ("enum_expanded", _expand_enum),
        ("relational_key_renamed", _rename_relational_key),
        ("schema_fields_reordered", _reorder_fields),
    ]
    results: list[dict[str, Any]] = []
    work = root / "build" / "adversarial-schema"
    for name, mutate in compatible:
        payload = baseline.model_dump(mode="json")
        if mutate is not None:
            mutate(payload)
        metadata = MetadataBundle.model_validate(payload)
        metadata_path = work / name / "metadata.json"
        write_json(metadata_path, metadata.model_dump(mode="json"))
        started = time.perf_counter()
        manifest = generate(metadata_path, work / name / "bundle", 2026)
        elapsed = time.perf_counter() - started
        passed = bool(manifest["validation_passed"] and manifest["negative_control_detected"])
        results.append(
            {
                "scenario": name,
                "expected": "merge_ready",
                "first_pass": True,
                "passed": passed,
                "duration_seconds": round(elapsed, 4),
                "metadata_fingerprint": manifest["metadata_fingerprint"],
            }
        )

    invalid_payload = baseline.model_dump(mode="json")
    _break_foreign_key_target(invalid_payload)
    started = time.perf_counter()
    guardrail_message = ""
    try:
        MetadataBundle.model_validate(invalid_payload)
    except ValueError as error:
        guardrail_message = str(error)
    guardrail_elapsed = time.perf_counter() - started
    guardrail_caught = "unknown parent dataset: missing_accounts" in guardrail_message
    results.append(
        {
            "scenario": "foreign_key_target_missing",
            "expected": "refuse_before_generation",
            "first_pass": True,
            "passed": guardrail_caught,
            "duration_seconds": round(guardrail_elapsed, 4),
            "evidence": "unknown parent dataset: missing_accounts",
        }
    )

    compatible_results = [item for item in results if item["expected"] == "merge_ready"]
    latencies = sorted(item["duration_seconds"] for item in compatible_results)
    successes = sum(bool(item["passed"]) for item in compatible_results)
    report = {
        "method": (
            "One attempt per scenario; generation, CSV/Parquet emission, independent "
            "validation, and negative control are included in compatible-case latency."
        ),
        "compatible_schema_changes": len(compatible_results) - 1,
        "compatible_cases_including_baseline": len(compatible_results),
        "first_pass_successes": successes,
        "first_pass_success_rate": round(successes / len(compatible_results), 4),
        "guardrail_cases": 1,
        "guardrail_catches": int(guardrail_caught),
        "latency_seconds": {
            "median": round(latencies[len(latencies) // 2], 4),
            "p95": round(latencies[math.ceil(len(latencies) * 0.95) - 1], 4),
            "max": round(max(latencies), 4),
        },
        "results": results,
        "claim_boundary": (
            "Local fictional schemas on one Apple Silicon host; this is not a "
            "production reliability or throughput claim."
        ),
    }
    write_json(root / "reports/adversarial-schema-evaluation.json", report)
    lines = [
        "# Adversarial schema-change evaluation",
        "",
        report["method"],
        "",
        (
            f"First-pass success: **{successes}/{len(compatible_results)} "
            f"({report['first_pass_success_rate']:.0%})**. "
            f"Invalid-contract guardrail: **{int(guardrail_caught)}/1 caught**."
        ),
        "",
        "| Scenario | Expected | Result | Latency (s) |",
        "|---|---|:---:|---:|",
    ]
    lines.extend(
        f"| {item['scenario']} | {item['expected']} | "
        f"{'verified' if item['passed'] else 'failed'} | {item['duration_seconds']} |"
        for item in results
    )
    lines.extend(
        [
            "",
            f"Median compatible-case latency: **{report['latency_seconds']['median']} s**; "
            f"p95: **{report['latency_seconds']['p95']} s**.",
            "",
            report["claim_boundary"],
            "",
        ]
    )
    (root / "reports/adversarial-schema-evaluation.md").write_text("\n".join(lines))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
