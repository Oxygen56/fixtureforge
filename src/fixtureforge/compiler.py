"""Compile normalized metadata into deterministic rows."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from fixtureforge.generator import generate_column
from fixtureforge.models import DatasetSpec, MetadataBundle


@dataclass(frozen=True)
class CompiledBundle:
    order: list[str]
    rows: dict[str, list[dict[str, Any]]]
    rules: dict[str, dict[str, str]]


def dependency_order(bundle: MetadataBundle) -> list[str]:
    parents = {
        dataset.name: {relation.references_table for relation in dataset.foreign_keys}
        for dataset in bundle.datasets
    }
    order: list[str] = []
    while parents:
        ready = sorted(name for name, needs in parents.items() if not needs)
        if not ready:
            raise ValueError(f"cyclic foreign-key dependencies: {sorted(parents)}")
        order.extend(ready)
        for name in ready:
            parents.pop(name)
        for needs in parents.values():
            needs.difference_update(ready)
    return order


def _compile_dataset(
    dataset: DatasetSpec,
    compiled: dict[str, list[dict[str, Any]]],
    seed: int,
) -> tuple[list[dict[str, Any]], dict[str, str]]:
    columns = {
        field.name: generate_column(field, dataset.name, dataset.rows, seed)
        for field in dataset.fields
    }
    rules = {field.name: "metadata_semantic_generator" for field in dataset.fields}

    for key in dataset.primary_key:
        columns[key] = [index + 1 for index in range(dataset.rows)]
        rules[key] = "sequential_primary_key"

    for relation in dataset.foreign_keys:
        parent_rows = compiled[relation.references_table]
        for child_field, parent_field in zip(
            relation.fields, relation.references_fields, strict=True
        ):
            columns[child_field] = [
                parent_rows[index % len(parent_rows)][parent_field]
                for index in range(dataset.rows)
            ]
            rules[child_field] = (
                f"foreign_key:{relation.references_table}.{parent_field}"
            )

    rows = [
        {field.name: columns[field.name][index] for field in dataset.fields}
        for index in range(dataset.rows)
    ]
    return rows, rules


def compile_bundle(bundle: MetadataBundle, seed: int) -> CompiledBundle:
    datasets = {dataset.name: dataset for dataset in bundle.datasets}
    order = dependency_order(bundle)
    compiled: dict[str, list[dict[str, Any]]] = {}
    rules: dict[str, dict[str, str]] = {}
    for name in order:
        compiled[name], rules[name] = _compile_dataset(datasets[name], compiled, seed)
    return CompiledBundle(order=order, rows=compiled, rules=rules)
