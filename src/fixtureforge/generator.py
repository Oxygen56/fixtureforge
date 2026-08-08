"""Deterministic, metadata-aware value generation."""

from __future__ import annotations

import hashlib
import random
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from fixtureforge.models import FieldSpec

FIRST_NAMES = ("Avery", "Blake", "Casey", "Devon", "Emery", "Frankie", "Gray", "Harper")
LAST_NAMES = ("Atlas", "Birch", "Cedar", "Dover", "Elm", "Frost", "Grove", "Haven")
COUNTRIES = ("US", "CA", "GB", "DE", "FR", "JP", "AU", "BR")


def stable_rng(seed: int, table: str, field: str) -> random.Random:
    digest = hashlib.sha256(f"{seed}:{table}:{field}".encode()).digest()
    return random.Random(int.from_bytes(digest[:8], "big"))


def _kind(field: FieldSpec) -> str:
    name = field.name.lower()
    semantic = " ".join(field.tags + field.glossary_terms + [field.format or ""]).lower()
    declared = field.type.lower()
    if field.enum_values:
        return "enum"
    if "email" in name or "email" in semantic:
        return "email"
    if "phone" in name or "phone" in semantic:
        return "phone"
    if name in {"name", "full_name", "customer_name"} or "person_name" in semantic:
        return "name"
    if "country" in name:
        return "country"
    if "date" in declared or "timestamp" in declared or field.format in {"date", "date-time"}:
        return "date"
    if any(token in declared for token in ("int", "long", "bigint")):
        return "integer"
    if any(token in declared for token in ("float", "double", "decimal", "number", "numeric")):
        return "number"
    if any(token in declared for token in ("bool",)):
        return "boolean"
    return "string"


def generate_column(field: FieldSpec, table: str, count: int, seed: int) -> list[Any]:
    rng = stable_rng(seed, table, field.name)
    kind = _kind(field)
    values: list[Any] = []
    for index in range(count):
        value: Any
        if kind == "enum":
            value = field.enum_values[index % len(field.enum_values)]
        elif kind == "email":
            value = f"fixture.{table}.{index + 1}@example.test"
        elif kind == "phone":
            value = f"+1-555-{index % 1000:03d}-{(index * 97 + 1000) % 10000:04d}"
        elif kind == "name":
            first = FIRST_NAMES[index % len(FIRST_NAMES)]
            last = LAST_NAMES[(index * 3) % len(LAST_NAMES)]
            value = f"{first} {last}"
        elif kind == "country":
            value = COUNTRIES[index % len(COUNTRIES)]
        elif kind == "date":
            value = (date(2024, 1, 1) + timedelta(days=index * 7)).isoformat()
        elif kind == "integer":
            int_lower = int(field.minimum if field.minimum is not None else 1)
            int_upper = int(
                field.maximum if field.maximum is not None else int_lower + max(100, count)
            )
            value = int_lower + (index % max(1, int_upper - int_lower + 1))
        elif kind == "number":
            decimal_lower = Decimal(str(field.minimum if field.minimum is not None else 1))
            decimal_upper = Decimal(str(field.maximum if field.maximum is not None else 1000))
            span = max(Decimal("0"), decimal_upper - decimal_lower)
            fraction = Decimal(index % max(1, count)) / Decimal(max(1, count - 1))
            value = str((decimal_lower + span * fraction).quantize(Decimal("0.01")))
        elif kind == "boolean":
            value = index % 2 == 0
        else:
            value = f"{table}_{field.name}_{rng.randrange(10_000_000):07d}"
        values.append(value)

    if field.minimum is not None and values and kind in {"integer", "number"}:
        values[0] = field.minimum
    if field.maximum is not None and len(values) > 1 and kind in {"integer", "number"}:
        values[1] = field.maximum
    return values
