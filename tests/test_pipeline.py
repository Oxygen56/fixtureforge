from __future__ import annotations

import csv
import json
from pathlib import Path

from fixtureforge.compiler import compile_bundle
from fixtureforge.evidence import canonical_json, file_inventory, sha256_bytes
from fixtureforge.models import MetadataBundle
from fixtureforge.service import compare_manifests, generate, load_metadata, verify
from fixtureforge.validator import inject_broken_foreign_key, verify_csv_bundle


def test_compile_preserves_keys_and_relationships(metadata: MetadataBundle) -> None:
    result = compile_bundle(metadata, 2026)
    customers = result.rows["customers"]
    orders = result.rows["orders"]
    items = result.rows["order_items"]
    customer_ids = {row["customer_id"] for row in customers}
    order_ids = {row["order_id"] for row in orders}
    assert {row["customer_id"] for row in orders} <= customer_ids
    assert {row["order_id"] for row in items} <= order_ids
    assert len(customer_ids) == len(customers)


def test_full_bundle_is_valid_deterministic_and_has_negative_control(
    fixture_path: Path,
    tmp_path: Path,
) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    manifest = generate(fixture_path, first, 2026)
    generate(fixture_path, second, 2026)
    assert manifest["validation_passed"]
    assert manifest["negative_control_detected"]
    assert manifest["source_row_access"] == "none"
    assert compare_manifests(first, second) == {
        "identical": True,
        "differences": [],
    }
    assert verify(first)["passed"]
    assert (first / "valid/parquet/orders.parquet").stat().st_size > 0
    assert "DatasetName = Literal" in (first / "developer/factories.py").read_text()
    assert "datahub_tags" in (first / "developer/schema.yml").read_text()


def test_compare_reports_different_seed(fixture_path: Path, tmp_path: Path) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    generate(fixture_path, first, 1)
    generate(fixture_path, second, 2)
    comparison = compare_manifests(first, second)
    assert not comparison["identical"]
    assert "seed" in comparison["differences"]


def test_validator_detects_broken_relation(
    metadata: MetadataBundle,
    fixture_path: Path,
    tmp_path: Path,
) -> None:
    output = tmp_path / "bundle"
    generate(fixture_path, output, 5)
    csv_dir = output / "valid/csv"
    broken_dir = tmp_path / "broken"
    broken_dir.mkdir()
    for path in csv_dir.glob("*.csv"):
        target = broken_dir / path.name
        target.write_bytes(path.read_bytes())
    inject_broken_foreign_key(
        csv_dir / "orders.csv",
        broken_dir / "orders.csv",
        "customer_id",
    )
    result = verify_csv_bundle(metadata, broken_dir)
    assert not result["passed"]
    assert any(
        check["check"] == "foreign_key" and check["violations"] == 1
        for check in result["checks"]
    )


def test_validator_detects_null_duplicate_enum_and_range(
    metadata: MetadataBundle,
    fixture_path: Path,
    tmp_path: Path,
) -> None:
    output = tmp_path / "bundle"
    generate(fixture_path, output, 5)
    csv_dir = output / "valid/csv"
    customers_path = csv_dir / "customers.csv"
    with customers_path.open(newline="") as handle:
        rows = list(csv.DictReader(handle))
        fields = list(rows[0])
    rows[0]["customer_id"] = ""
    rows[1]["email"] = rows[2]["email"]
    rows[3]["segment"] = "unknown"
    with customers_path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    items_path = csv_dir / "order_items.csv"
    with items_path.open(newline="") as handle:
        items = list(csv.DictReader(handle))
        item_fields = list(items[0])
    items[0]["quantity"] = "999"
    with items_path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=item_fields)
        writer.writeheader()
        writer.writerows(items)
    result = verify_csv_bundle(metadata, csv_dir)
    failed = {check["check"] for check in result["checks"] if not check["passed"]}
    assert {"not_null", "unique", "accepted_values", "range"} <= failed


def test_evidence_helpers(fixture_path: Path, tmp_path: Path) -> None:
    metadata = load_metadata(fixture_path)
    text = canonical_json(metadata.model_dump(mode="json"))
    assert sha256_bytes(text.encode()) == sha256_bytes(text.encode())
    file = tmp_path / "a.txt"
    file.write_text("evidence")
    assert file_inventory(tmp_path) == {
        "a.txt": sha256_bytes(b"evidence"),
    }
    assert json.loads(json.dumps(metadata.model_dump()))["source"].startswith("datahub")
