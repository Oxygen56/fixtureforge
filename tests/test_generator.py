from __future__ import annotations

from hypothesis import given
from hypothesis import strategies as st

from fixtureforge.generator import generate_column, stable_rng
from fixtureforge.models import FieldSpec


@given(st.integers(min_value=2, max_value=100))
def test_integer_values_stay_in_range(count: int) -> None:
    field = FieldSpec(name="quantity", type="INTEGER", minimum=1, maximum=10)
    values = generate_column(field, "items", count, 77)
    assert values[0] == 1
    assert values[1] == 10
    assert all(1 <= int(value) <= 10 for value in values)


def test_semantic_and_pii_generators_are_fake_and_deterministic() -> None:
    fields = [
        FieldSpec(name="email", type="VARCHAR", tags=["PII"]),
        FieldSpec(name="phone", type="VARCHAR", tags=["PII"]),
        FieldSpec(name="name", type="VARCHAR", tags=["PII"]),
        FieldSpec(name="country", type="VARCHAR"),
        FieldSpec(name="created_date", type="DATE"),
        FieldSpec(name="active", type="BOOLEAN"),
        FieldSpec(name="code", type="VARCHAR"),
    ]
    first = [generate_column(field, "customers", 4, 2026) for field in fields]
    second = [generate_column(field, "customers", 4, 2026) for field in fields]
    assert first == second
    assert all(str(value).endswith("@example.test") for value in first[0])
    assert all(str(value).startswith("+1-555-") for value in first[1])
    assert first[5] == [True, False, True, False]
    assert first[6][0].startswith("customers_code_")


def test_enum_and_decimal_boundaries() -> None:
    enum = FieldSpec(name="status", type="VARCHAR", enum_values=["new", "done"])
    money = FieldSpec(name="amount", type="DECIMAL", minimum=0.01, maximum=99.99)
    assert generate_column(enum, "orders", 3, 1) == ["new", "done", "new"]
    values = generate_column(money, "orders", 4, 1)
    assert values[0] == 0.01
    assert values[1] == 99.99


def test_stable_rng_is_scoped_to_field() -> None:
    assert stable_rng(1, "a", "x").random() == stable_rng(1, "a", "x").random()
    assert stable_rng(1, "a", "x").random() != stable_rng(1, "a", "y").random()
