from __future__ import annotations

import json
from pathlib import Path

import pytest

from fixtureforge.mcp_normalizer import normalize_to_file, normalize_trace


def _call(tool: str, arguments: dict[str, object], payload: object) -> dict[str, object]:
    return {
        "tool": tool,
        "arguments": arguments,
        "response": {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(payload),
                }
            ]
        },
    }


def _write_trace(path: Path) -> None:
    parent_urn = "urn:li:dataset:(urn:li:dataPlatform:postgres,shop.customers,PROD)"
    child_urn = "urn:li:dataset:(urn:li:dataPlatform:postgres,shop.orders,PROD)"
    parent = {
        "urn": parent_urn,
        "properties": {"description": "Customers"},
        "ownership": {"owners": [{"owner": {"urn": "urn:li:corpuser:data-platform"}}]},
        "tags": {
            "tags": [
                {
                    "tag": {
                        "urn": "urn:li:tag:Critical",
                        "properties": {"name": "Critical"},
                    }
                }
            ]
        },
        "glossaryTerms": {
            "terms": [
                {
                    "term": {
                        "urn": "urn:li:glossaryTerm:Customer",
                        "properties": {"name": "Customer"},
                    }
                }
            ]
        },
        "domain": {"domain": {"urn": "urn:li:domain:commerce"}},
        "schemaMetadata": {
            "primaryKeys": ["customer_id"],
            "fields": [
                {
                    "fieldPath": "customer_id",
                    "nativeDataType": "BIGINT",
                    "nullable": False,
                },
                {
                    "fieldPath": "email",
                    "nativeDataType": "VARCHAR",
                    "nullable": False,
                    "description": "Email",
                },
            ],
        },
    }
    child = {
        "urn": child_urn,
        "editableProperties": {"description": "Orders"},
        "schemaMetadata": {
            "primaryKeys": ["order_id"],
            "fields": [
                {
                    "fieldPath": "order_id",
                    "nativeDataType": "BIGINT",
                    "nullable": False,
                },
                {
                    "fieldPath": "customer_id",
                    "nativeDataType": "BIGINT",
                    "nullable": False,
                },
                {
                    "fieldPath": "status",
                    "nativeDataType": "VARCHAR",
                    "nullable": False,
                },
            ],
            "foreignKeys": [
                {
                    "sourceFields": [{"fieldPath": "customer_id"}],
                    "foreignFields": [{"fieldPath": "customer_id"}],
                    "foreignDataset": {"urn": parent_urn},
                }
            ],
        },
    }
    calls = [
        _call("get_entities", {"urns": [parent_urn, child_urn]}, [parent, child]),
        _call(
            "list_schema_fields",
            {"urn": parent_urn},
            {
                "urn": parent_urn,
                "fields": [
                    {"fieldPath": "customer_id"},
                    {
                        "fieldPath": "email",
                        "editedTags": ["Pii"],
                        "editedGlossaryTerms": ["Email Address"],
                    },
                ],
            },
        ),
        _call(
            "list_schema_fields",
            {"urn": child_urn},
            {
                "urn": child_urn,
                "fields": [
                    {"fieldPath": "order_id"},
                    {"fieldPath": "customer_id", "tags": ["Foreign Key"]},
                    {"fieldPath": "status"},
                ],
            },
        ),
        _call(
            "get_lineage",
            {"urn": parent_urn},
            {"downstreams": {"searchResults": [{"entity": {"urn": child_urn}}]}},
        ),
    ]
    path.write_text(
        json.dumps(
            {
                "calls": calls,
                "summary": {
                    "tools_used": [
                        "get_entities",
                        "get_lineage",
                        "list_schema_fields",
                    ]
                },
            }
        )
    )


def test_normalize_live_trace_with_policy(tmp_path: Path) -> None:
    trace = tmp_path / "trace.json"
    policy = tmp_path / "policy.json"
    output = tmp_path / "metadata.json"
    _write_trace(trace)
    policy.write_text(
        json.dumps(
            {
                "datasets": {
                    "customers": {
                        "rows": 4,
                        "fields": {"email": {"format": "email"}},
                    },
                    "orders": {
                        "rows": 6,
                        "fields": {"status": {"enum_values": ["pending", "paid"]}},
                    },
                }
            }
        )
    )
    bundle = normalize_to_file(trace, policy, output)
    customers, orders = bundle.datasets
    assert customers.rows == 4
    assert customers.fields[1].tags == ["PII"]
    assert customers.fields[1].glossary_terms == ["email_address"]
    assert customers.owners == ["urn:li:corpuser:data-platform"]
    assert customers.tags == ["critical"]
    assert customers.glossary_terms == ["customer"]
    assert customers.domain == "urn:li:domain:commerce"
    assert orders.foreign_keys[0].references_table == "customers"
    assert orders.fields[2].enum_values == ["pending", "paid"]
    assert bundle.lineage[0].upstream == customers.urn
    assert bundle.adapter_evidence["source_rows_read"] == 0
    assert output.exists()


def test_invalid_dataset_urn_is_rejected(tmp_path: Path) -> None:
    trace = tmp_path / "trace.json"
    policy = tmp_path / "policy.json"
    _write_trace(trace)
    payload = json.loads(trace.read_text())
    payload["calls"][0]["response"]["content"][0]["text"] = json.dumps(
        [
            {
                "urn": "not-a-dataset-urn",
                "schemaMetadata": {"fields": []},
            }
        ]
    )
    trace.write_text(json.dumps(payload))
    policy.write_text("{}")
    with pytest.raises(ValueError, match="cannot parse dataset URN"):
        normalize_trace(trace, policy)
