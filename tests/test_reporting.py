from __future__ import annotations

import json
from pathlib import Path

from fixtureforge.reporting import build_report
from fixtureforge.service import generate


def test_build_self_contained_judge_report(fixture_path: Path, tmp_path: Path) -> None:
    bundle = tmp_path / "bundle"
    generate(fixture_path, bundle, 2026)
    trace = tmp_path / "mcp.json"
    writeback = tmp_path / "writeback.json"
    report = tmp_path / "report.html"
    trace.write_text(
        json.dumps(
            {
                "summary": {
                    "tools_used": [
                        "get_entities",
                        "get_lineage",
                        "list_schema_fields",
                    ]
                }
            }
        )
    )
    writeback.write_text(
        json.dumps({"writeback": {"read_after_write_verified": True}})
    )
    result = build_report(bundle, trace, writeback, report)
    rendered = report.read_text()
    assert result["datasets"] == 3
    assert result["source_rows_read"] == 0
    assert result["negative_control_detected"]
    assert "FixtureForge" in rendered
    assert "hard-coded success screen" in rendered
    assert "source-row-free customers" in rendered.lower()
