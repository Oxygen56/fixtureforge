from __future__ import annotations

from pathlib import Path

import pytest

from fixtureforge.models import MetadataBundle


@pytest.fixture
def fixture_path() -> Path:
    return Path("fixtures/fiction_retail.metadata.json")


@pytest.fixture
def metadata(fixture_path: Path) -> MetadataBundle:
    return MetadataBundle.model_validate_json(fixture_path.read_text())
