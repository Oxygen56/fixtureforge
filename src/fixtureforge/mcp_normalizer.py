"""Normalize real official-MCP responses into the compiler contract."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from fixtureforge.evidence import sha256_file, write_json
from fixtureforge.models import (
    AssertionSpec,
    DatasetSpec,
    FieldSpec,
    ForeignKeySpec,
    LineageEdge,
    MetadataBundle,
)


def _content_json(call: dict[str, Any]) -> Any:
    content = call["response"]["content"][0]
    if "parsed_json" in content:
        return content["parsed_json"]
    return json.loads(content["text"])


def _dataset_name(urn: str) -> str:
    match = re.search(r",([^,]+),[^,]+\)$", urn)
    if not match:
        raise ValueError(f"cannot parse dataset URN: {urn}")
    return match.group(1).rsplit(".", 1)[-1]


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", value).strip("_").lower()
    return "PII" if slug == "pii" else slug


def _field_overlay(
    policy: dict[str, Any],
    dataset: str,
    field: str,
) -> dict[str, Any]:
    datasets = policy.get("datasets", {})
    dataset_policy = datasets.get(dataset, {})
    return dict(dataset_policy.get("fields", {}).get(field, {}))


def _assertions(fields: list[FieldSpec], primary_key: list[str]) -> list[AssertionSpec]:
    assertions: list[AssertionSpec] = []
    for field in fields:
        if not field.nullable or field.name in primary_key:
            assertions.append(AssertionSpec(kind="not_null", field=field.name))
        if field.unique or field.name in primary_key:
            assertions.append(AssertionSpec(kind="unique", field=field.name))
        if field.enum_values:
            assertions.append(
                AssertionSpec(
                    kind="accepted_values",
                    field=field.name,
                    values=field.enum_values,
                )
            )
        if field.minimum is not None or field.maximum is not None:
            assertions.append(
                AssertionSpec(
                    kind="range",
                    field=field.name,
                    minimum=field.minimum,
                    maximum=field.maximum,
                )
            )
    return assertions


def normalize_trace(
    trace_path: Path,
    policy_path: Path,
) -> MetadataBundle:
    trace = json.loads(trace_path.read_text())
    policy = json.loads(policy_path.read_text())
    calls = trace["calls"]
    entity_call = next(call for call in calls if call["tool"] == "get_entities")
    entities: list[dict[str, Any]] = _content_json(entity_call)
    schema_calls = {
        payload["urn"]: payload
        for call in calls
        if call["tool"] == "list_schema_fields"
        for payload in [_content_json(call)]
    }
    datasets: list[DatasetSpec] = []
    for entity in entities:
        urn = entity["urn"]
        name = _dataset_name(urn)
        schema_metadata = entity["schemaMetadata"]
        detailed_fields = {
            field["fieldPath"]: field
            for field in schema_calls[urn]["fields"]
        }
        primary_key = list(schema_metadata.get("primaryKeys") or [])
        fields: list[FieldSpec] = []
        for raw_field in schema_metadata["fields"]:
            details = detailed_fields.get(raw_field["fieldPath"], raw_field)
            overlay = _field_overlay(policy, name, raw_field["fieldPath"])
            tags = [
                _slug(value)
                for value in details.get("editedTags", details.get("tags", []))
            ]
            terms = [
                _slug(value)
                for value in details.get(
                    "editedGlossaryTerms",
                    details.get("glossaryTerms", []),
                )
            ]
            fields.append(
                FieldSpec(
                    name=raw_field["fieldPath"],
                    type=raw_field.get("nativeDataType") or "VARCHAR",
                    nullable=bool(raw_field.get("nullable", True)),
                    description=raw_field.get("description") or "",
                    tags=tags,
                    glossary_terms=terms,
                    unique=raw_field["fieldPath"] in primary_key,
                    **overlay,
                )
            )
        foreign_keys = [
            ForeignKeySpec(
                fields=[
                    field["fieldPath"]
                    for field in foreign_key["sourceFields"]
                ],
                references_table=_dataset_name(
                    foreign_key["foreignDataset"]["urn"]
                ),
                references_fields=[
                    field["fieldPath"]
                    for field in foreign_key["foreignFields"]
                ],
            )
            for foreign_key in schema_metadata.get("foreignKeys") or []
        ]
        description = (
            entity.get("editableProperties", {}).get("description")
            or entity.get("properties", {}).get("description")
            or ""
        )
        rows = int(policy.get("datasets", {}).get(name, {}).get("rows", 12))
        datasets.append(
            DatasetSpec(
                urn=urn,
                name=name,
                description=description,
                rows=rows,
                fields=fields,
                primary_key=primary_key,
                foreign_keys=foreign_keys,
                assertions=_assertions(fields, primary_key),
            )
        )

    lineage: list[LineageEdge] = []
    for call in calls:
        if call["tool"] != "get_lineage":
            continue
        source = call["arguments"]["urn"]
        payload = _content_json(call)
        results = payload.get("downstreams", {}).get("searchResults", [])
        lineage.extend(
            LineageEdge(upstream=source, downstream=result["entity"]["urn"])
            for result in results
        )

    return MetadataBundle(
        source="datahub-oss-v1.6.0:official-mcp-server",
        datasets=datasets,
        lineage=lineage,
        adapter_evidence={
            "mode": "live_official_datahub_mcp",
            "mcp_trace_sha256": sha256_file(trace_path),
            "policy_overlay_sha256": sha256_file(policy_path),
            "tools_used": trace["summary"]["tools_used"],
            "source_row_tools_called": [],
            "source_rows_read": 0,
        },
    )


def normalize_to_file(trace_path: Path, policy_path: Path, output: Path) -> MetadataBundle:
    bundle = normalize_trace(trace_path, policy_path)
    write_json(output, bundle.model_dump(mode="json"))
    return bundle
