"""Independent DuckDB verification for generated bundles."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

import duckdb

from fixtureforge.models import MetadataBundle


def _identifier(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def _literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _count(connection: duckdb.DuckDBPyConnection, query: str) -> int:
    result = connection.execute(query).fetchone()
    return int(result[0]) if result else 0


def _load_tables(
    connection: duckdb.DuckDBPyConnection,
    bundle: MetadataBundle,
    csv_dir: Path,
) -> None:
    for dataset in bundle.datasets:
        path = (csv_dir / f"{dataset.name}.csv").resolve()
        connection.execute(
            f"CREATE TABLE {_identifier(dataset.name)} AS "
            f"SELECT * FROM read_csv_auto({_literal(str(path))}, header=true, all_varchar=true)"
        )


def verify_csv_bundle(bundle: MetadataBundle, csv_dir: Path) -> dict[str, Any]:
    connection = duckdb.connect(":memory:")
    checks: list[dict[str, Any]] = []
    try:
        _load_tables(connection, bundle, csv_dir)
        for dataset in bundle.datasets:
            table = _identifier(dataset.name)
            actual_rows = _count(connection, f"SELECT COUNT(*) FROM {table}")
            checks.append(
                {
                    "check": "row_count",
                    "dataset": dataset.name,
                    "expected": dataset.rows,
                    "actual": actual_rows,
                    "passed": actual_rows == dataset.rows,
                }
            )

            non_null = {
                field.name for field in dataset.fields if not field.nullable
            } | set(dataset.primary_key)
            for field_name in sorted(non_null):
                violations = _count(
                    connection,
                    f"SELECT COUNT(*) FROM {table} "
                    f"WHERE {_identifier(field_name)} IS NULL "
                    f"OR TRIM({_identifier(field_name)}) = ''",
                )
                checks.append(
                    {
                        "check": "not_null",
                        "dataset": dataset.name,
                        "field": field_name,
                        "violations": violations,
                        "passed": violations == 0,
                    }
                )

            unique_sets = [dataset.primary_key] if dataset.primary_key else []
            unique_sets.extend([[field.name] for field in dataset.fields if field.unique])
            for fields in unique_sets:
                columns = ", ".join(_identifier(field) for field in fields)
                violations = _count(
                    connection,
                    f"SELECT COUNT(*) FROM (SELECT {columns}, COUNT(*) AS n "
                    f"FROM {table} GROUP BY {columns} HAVING COUNT(*) > 1)",
                )
                checks.append(
                    {
                        "check": "unique",
                        "dataset": dataset.name,
                        "fields": fields,
                        "violations": violations,
                        "passed": violations == 0,
                    }
                )

            for field in dataset.fields:
                if field.enum_values:
                    allowed = ", ".join(_literal(value) for value in field.enum_values)
                    violations = _count(
                        connection,
                        f"SELECT COUNT(*) FROM {table} "
                        f"WHERE {_identifier(field.name)} NOT IN ({allowed})",
                    )
                    checks.append(
                        {
                            "check": "accepted_values",
                            "dataset": dataset.name,
                            "field": field.name,
                            "violations": violations,
                            "passed": violations == 0,
                        }
                    )
                if field.minimum is not None or field.maximum is not None:
                    conditions: list[str] = [
                        f"TRY_CAST({_identifier(field.name)} AS DOUBLE) IS NULL"
                    ]
                    if field.minimum is not None:
                        conditions.append(
                            f"TRY_CAST({_identifier(field.name)} AS DOUBLE) < {field.minimum}"
                        )
                    if field.maximum is not None:
                        conditions.append(
                            f"TRY_CAST({_identifier(field.name)} AS DOUBLE) > {field.maximum}"
                        )
                    violations = _count(
                        connection,
                        f"SELECT COUNT(*) FROM {table} WHERE {' OR '.join(conditions)}",
                    )
                    checks.append(
                        {
                            "check": "range",
                            "dataset": dataset.name,
                            "field": field.name,
                            "violations": violations,
                            "passed": violations == 0,
                        }
                    )

            for relation in dataset.foreign_keys:
                parent = _identifier(relation.references_table)
                join = " AND ".join(
                    f"c.{_identifier(child)} = p.{_identifier(parent_field)}"
                    for child, parent_field in zip(
                        relation.fields, relation.references_fields, strict=True
                    )
                )
                parent_probe = _identifier(relation.references_fields[0])
                violations = _count(
                    connection,
                    f"SELECT COUNT(*) FROM {table} c LEFT JOIN {parent} p ON {join} "
                    f"WHERE p.{parent_probe} IS NULL",
                )
                checks.append(
                    {
                        "check": "foreign_key",
                        "dataset": dataset.name,
                        "fields": relation.fields,
                        "references": (
                            f"{relation.references_table}."
                            + ",".join(relation.references_fields)
                        ),
                        "violations": violations,
                        "passed": violations == 0,
                    }
                )
    finally:
        connection.close()
    passed = all(check["passed"] for check in checks)
    return {
        "status": "verified" if passed else "violations_found",
        "passed": passed,
        "checks_total": len(checks),
        "checks_passed": sum(bool(check["passed"]) for check in checks),
        "checks": checks,
    }


def inject_broken_foreign_key(source: Path, target: Path, field: str) -> None:
    with source.open(newline="") as handle:
        rows = list(csv.DictReader(handle))
        fieldnames = list(rows[0]) if rows else []
    if not rows or field not in fieldnames:
        raise ValueError(f"cannot corrupt missing field: {field}")
    rows[0][field] = "__fixtureforge_missing_parent__"
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
