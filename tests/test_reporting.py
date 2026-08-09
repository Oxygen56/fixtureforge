from __future__ import annotations

import json
from pathlib import Path

from fixtureforge.reporting import build_agent_report, build_report
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


def test_build_agent_timeline_report(tmp_path: Path) -> None:
    run = tmp_path / "agent-run.json"
    report = tmp_path / "agent-report.html"
    run.write_text(
        json.dumps(
            {
                "status": "completed",
                "intent": {"goal": "Generate fixtures", "datahub_query": "support"},
                "selected_datasets": ["urn:li:dataset:(platform,support.accounts,PROD)"],
                "events": [
                    {
                        "phase": "discover",
                        "status": "completed",
                        "evidence": "selected one dataset",
                    }
                ],
                "evidence": {
                    "files": 14,
                    "validation_checks": 30,
                    "metadata_fingerprint": "abc",
                },
                "git_delivery": {"status": "committed"},
                "datahub_writeback": {"artifact": "DataHub Context Document"},
            }
        )
    )
    result = build_agent_report(run, report)
    assert result == {"output": str(report), "events": 1, "status": "completed"}
    rendered = report.read_text()
    assert "Plan → act → verify → deliver" in rendered
    assert "DataHub Context Document" in rendered
