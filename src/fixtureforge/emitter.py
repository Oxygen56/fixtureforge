"""Write generated rows and developer artifacts."""

from __future__ import annotations

import csv
import shutil
from pathlib import Path
from typing import Any

import duckdb
import yaml

from fixtureforge.compiler import CompiledBundle
from fixtureforge.evidence import canonical_json, file_inventory, sha256_bytes, write_json
from fixtureforge.models import MetadataBundle
from fixtureforge.validator import inject_broken_foreign_key, verify_csv_bundle


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        raise ValueError("cannot emit an empty fixture")
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _write_parquet(csv_path: Path, parquet_path: Path) -> None:
    parquet_path.parent.mkdir(parents=True, exist_ok=True)
    connection = duckdb.connect(":memory:")
    try:
        csv_literal = "'" + str(csv_path.resolve()).replace("'", "''") + "'"
        parquet_literal = "'" + str(parquet_path.resolve()).replace("'", "''") + "'"
        connection.execute(
            f"COPY (SELECT * FROM read_csv_auto({csv_literal}, header=true)) "
            f"TO {parquet_literal} (FORMAT PARQUET, COMPRESSION ZSTD)"
        )
    finally:
        connection.close()


def _dbt_schema(bundle: MetadataBundle) -> dict[str, Any]:
    models: list[dict[str, Any]] = []
    for dataset in bundle.datasets:
        columns = []
        for field in dataset.fields:
            tests: list[Any] = []
            if not field.nullable or field.name in dataset.primary_key:
                tests.append("not_null")
            if field.unique or field.name in dataset.primary_key:
                tests.append("unique")
            if field.enum_values:
                tests.append({"accepted_values": {"values": field.enum_values}})
            columns.append(
                {
                    "name": field.name,
                    "description": field.description,
                    "data_tests": tests,
                    "meta": {
                        "datahub_tags": field.tags,
                        "datahub_glossary_terms": field.glossary_terms,
                    },
                }
            )
        models.append(
            {
                "name": dataset.name,
                "description": dataset.description,
                "columns": columns,
            }
        )
    return {"version": 2, "models": models}


def _factory_source(bundle: MetadataBundle) -> str:
    names = ", ".join(repr(dataset.name) for dataset in bundle.datasets)
    return (
        '"""Generated typed accessors for FixtureForge CSV seeds."""\n\n'
        "from __future__ import annotations\n\n"
        "import csv\n"
        "from pathlib import Path\n"
        "from typing import Any, Literal\n\n"
        f"DatasetName = Literal[{names}]\n\n"
        "def load_fixture(root: Path, dataset: DatasetName) -> list[dict[str, Any]]:\n"
        '    """Load a generated fixture as dictionaries."""\n'
        '    with (root / f"{dataset}.csv").open(newline="") as handle:\n'
        "        return list(csv.DictReader(handle))\n"
    )


def emit_bundle(
    metadata: MetadataBundle,
    compiled: CompiledBundle,
    output: Path,
    seed: int,
) -> dict[str, Any]:
    if output.exists():
        shutil.rmtree(output)
    csv_dir = output / "valid" / "csv"
    parquet_dir = output / "valid" / "parquet"
    for dataset in metadata.datasets:
        csv_path = csv_dir / f"{dataset.name}.csv"
        _write_csv(csv_path, compiled.rows[dataset.name])
        _write_parquet(csv_path, parquet_dir / f"{dataset.name}.parquet")

    dbt_path = output / "developer" / "schema.yml"
    dbt_path.parent.mkdir(parents=True, exist_ok=True)
    dbt_path.write_text(yaml.safe_dump(_dbt_schema(metadata), sort_keys=False))
    (output / "developer" / "factories.py").write_text(_factory_source(metadata))

    metadata_copy = output / "evidence" / "normalized-metadata.json"
    write_json(metadata_copy, metadata.model_dump(mode="json"))
    validation = verify_csv_bundle(metadata, csv_dir)
    write_json(output / "evidence" / "validation.json", validation)

    child = next(
        (
            dataset
            for dataset in metadata.datasets
            if dataset.foreign_keys
        ),
        None,
    )
    negative_result: dict[str, Any] | None = None
    if child is not None:
        negative_csv_dir = output / "negative" / "broken_foreign_key"
        shutil.copytree(csv_dir, negative_csv_dir)
        relation = child.foreign_keys[0]
        inject_broken_foreign_key(
            csv_dir / f"{child.name}.csv",
            negative_csv_dir / f"{child.name}.csv",
            relation.fields[0],
        )
        negative_result = verify_csv_bundle(metadata, negative_csv_dir)
        write_json(output / "evidence" / "negative-validation.json", negative_result)

    inventory = file_inventory(output, {"evidence/manifest.json"})
    metadata_fingerprint = sha256_bytes(
        canonical_json(metadata.model_dump(mode="json")).encode()
    )
    manifest = {
        "fixtureforge_version": "0.2.0",
        "seed": seed,
        "source_row_access": "none",
        "claim": "source-row-free",
        "claim_boundary": "not anonymization or a privacy guarantee",
        "metadata_fingerprint": metadata_fingerprint,
        "dataset_order": compiled.order,
        "generation_rules": compiled.rules,
        "files": inventory,
        "validation_passed": validation["passed"],
        "negative_control_detected": (
            negative_result is not None and not negative_result["passed"]
        ),
        "adapter_evidence": metadata.adapter_evidence,
    }
    write_json(output / "evidence" / "manifest.json", manifest)
    return manifest
