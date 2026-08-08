from __future__ import annotations

import pytest
from pydantic import ValidationError

from fixtureforge.compiler import dependency_order
from fixtureforge.models import FieldSpec, MetadataBundle


def test_pii_signal_is_case_insensitive() -> None:
    field = FieldSpec(name="mail", type="string", tags=["PII"])
    assert field.is_pii
    assert not FieldSpec(name="public", type="string").is_pii


def test_fixture_relations_and_order(metadata: MetadataBundle) -> None:
    assert dependency_order(metadata) == ["customers", "orders", "order_items"]


def test_unknown_parent_fails_closed(metadata: MetadataBundle) -> None:
    payload = metadata.model_dump()
    payload["datasets"][1]["foreign_keys"][0]["references_table"] = "missing"
    with pytest.raises(ValidationError, match="unknown parent"):
        MetadataBundle.model_validate(payload)


def test_unknown_local_field_fails_closed(metadata: MetadataBundle) -> None:
    payload = metadata.model_dump()
    payload["datasets"][0]["primary_key"] = ["missing"]
    with pytest.raises(ValidationError, match="unknown fields"):
        MetadataBundle.model_validate(payload)


def test_duplicate_dataset_fails_closed(metadata: MetadataBundle) -> None:
    payload = metadata.model_dump()
    payload["datasets"].append(payload["datasets"][0])
    with pytest.raises(ValidationError, match="dataset names must be unique"):
        MetadataBundle.model_validate(payload)


def test_foreign_key_arity_fails_closed(metadata: MetadataBundle) -> None:
    payload = metadata.model_dump()
    payload["datasets"][1]["foreign_keys"][0]["references_fields"].append("email")
    with pytest.raises(ValidationError, match="field counts must match"):
        MetadataBundle.model_validate(payload)


def test_cycle_fails_closed(metadata: MetadataBundle) -> None:
    payload = metadata.model_dump()
    payload["datasets"][0]["foreign_keys"] = [
        {
            "fields": ["customer_id"],
            "references_table": "order_items",
            "references_fields": ["order_item_id"],
        }
    ]
    cyclic = MetadataBundle.model_validate(payload)
    with pytest.raises(ValueError, match="cyclic"):
        dependency_order(cyclic)
