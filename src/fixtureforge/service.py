"""Application service for file-based generation and verification."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fixtureforge.compiler import compile_bundle
from fixtureforge.emitter import emit_bundle
from fixtureforge.evidence import write_json
from fixtureforge.models import MetadataBundle
from fixtureforge.validator import verify_csv_bundle


def load_metadata(path: Path) -> MetadataBundle:
    return MetadataBundle.model_validate_json(path.read_text())


def generate(input_path: Path, output: Path, seed: int) -> dict[str, Any]:
    metadata = load_metadata(input_path)
    compiled = compile_bundle(metadata, seed)
    return emit_bundle(metadata, compiled, output, seed)


def verify(bundle_path: Path) -> dict[str, Any]:
    metadata_path = bundle_path / "evidence" / "normalized-metadata.json"
    metadata = MetadataBundle.model_validate_json(metadata_path.read_text())
    result = verify_csv_bundle(metadata, bundle_path / "valid" / "csv")
    write_json(bundle_path / "evidence" / "validation.json", result)
    return result


def compare_manifests(first: Path, second: Path) -> dict[str, Any]:
    left = json.loads((first / "evidence" / "manifest.json").read_text())
    right = json.loads((second / "evidence" / "manifest.json").read_text())
    keys = ("seed", "metadata_fingerprint", "dataset_order", "generation_rules", "files")
    differences = [key for key in keys if left.get(key) != right.get(key)]
    return {"identical": not differences, "differences": differences}
