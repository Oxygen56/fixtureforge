"""Generated typed accessors for FixtureForge CSV seeds."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any, Literal

DatasetName = Literal['accounts', 'ticket_events', 'tickets']

def load_fixture(root: Path, dataset: DatasetName) -> list[dict[str, Any]]:
    """Load a generated fixture as dictionaries."""
    with (root / f"{dataset}.csv").open(newline="") as handle:
        return list(csv.DictReader(handle))
