"""Normalized metadata contract used by all FixtureForge adapters."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class FieldSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    type: str
    nullable: bool = True
    description: str = ""
    tags: list[str] = Field(default_factory=list)
    glossary_terms: list[str] = Field(default_factory=list)
    enum_values: list[str] = Field(default_factory=list)
    minimum: float | int | None = None
    maximum: float | int | None = None
    unique: bool = False
    format: str | None = None

    @property
    def is_pii(self) -> bool:
        signals = {value.lower() for value in self.tags + self.glossary_terms}
        return bool(signals & {"pii", "personal_data", "sensitive"})


class ForeignKeySpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fields: list[str]
    references_table: str
    references_fields: list[str]

    @model_validator(mode="after")
    def matching_arity(self) -> ForeignKeySpec:
        if len(self.fields) != len(self.references_fields):
            raise ValueError("foreign-key field counts must match")
        return self


class AssertionSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["not_null", "unique", "accepted_values", "range"]
    field: str
    values: list[str] = Field(default_factory=list)
    minimum: float | int | None = None
    maximum: float | int | None = None


class DatasetSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    urn: str
    name: str
    description: str = ""
    rows: int = Field(default=12, ge=2, le=10_000)
    fields: list[FieldSpec]
    primary_key: list[str] = Field(default_factory=list)
    foreign_keys: list[ForeignKeySpec] = Field(default_factory=list)
    assertions: list[AssertionSpec] = Field(default_factory=list)

    @model_validator(mode="after")
    def references_known_fields(self) -> DatasetSpec:
        names = {field.name for field in self.fields}
        referenced = set(self.primary_key)
        for relation in self.foreign_keys:
            referenced.update(relation.fields)
        referenced.update(assertion.field for assertion in self.assertions)
        unknown = referenced - names
        if unknown:
            raise ValueError(f"unknown fields in {self.name}: {sorted(unknown)}")
        if len(names) != len(self.fields):
            raise ValueError(f"duplicate field names in {self.name}")
        return self


class LineageEdge(BaseModel):
    model_config = ConfigDict(extra="forbid")

    upstream: str
    downstream: str


class MetadataBundle(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contract_version: Literal["1.0"] = "1.0"
    source: str
    generated_at: str | None = None
    datasets: list[DatasetSpec]
    lineage: list[LineageEdge] = Field(default_factory=list)
    adapter_evidence: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_relations(self) -> MetadataBundle:
        datasets = {dataset.name: dataset for dataset in self.datasets}
        if len(datasets) != len(self.datasets):
            raise ValueError("dataset names must be unique")
        for dataset in self.datasets:
            for relation in dataset.foreign_keys:
                parent = datasets.get(relation.references_table)
                if parent is None:
                    raise ValueError(f"unknown parent dataset: {relation.references_table}")
                parent_fields = {field.name for field in parent.fields}
                unknown = set(relation.references_fields) - parent_fields
                if unknown:
                    raise ValueError(
                        f"unknown parent fields in {relation.references_table}: {sorted(unknown)}"
                    )
        return self
