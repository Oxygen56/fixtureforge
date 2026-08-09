from __future__ import annotations

import asyncio
import json
from contextlib import asynccontextmanager
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from fixtureforge import datahub_integration
from fixtureforge.agent import interpret_goal, run_agent
from fixtureforge.datahub_integration import (
    _dataset_urns,
    capture_official_mcp,
    discovery_selection,
    writeback_local_evidence,
)
from fixtureforge.models import MetadataBundle


def _call(tool: str, arguments: dict[str, Any], payload: Any) -> dict[str, Any]:
    return {
        "tool": tool,
        "arguments": arguments,
        "response": {"content": [{"type": "text", "text": json.dumps(payload)}]},
    }


def _replay_trace(metadata: MetadataBundle, path: Path) -> None:
    entities: list[dict[str, Any]] = []
    calls: list[dict[str, Any]] = []
    for dataset in metadata.datasets:
        fields = [
            {
                "fieldPath": field.name,
                "nativeDataType": field.type,
                "nullable": field.nullable,
                "description": field.description,
            }
            for field in dataset.fields
        ]
        entities.append(
            {
                "urn": dataset.urn,
                "properties": {"description": dataset.description},
                "schemaMetadata": {
                    "primaryKeys": dataset.primary_key,
                    "fields": fields,
                    "foreignKeys": [
                        {
                            "sourceFields": [{"fieldPath": name} for name in relation.fields],
                            "foreignFields": [
                                {"fieldPath": name} for name in relation.references_fields
                            ],
                            "foreignDataset": {
                                "urn": next(
                                    item.urn
                                    for item in metadata.datasets
                                    if item.name == relation.references_table
                                )
                            },
                        }
                        for relation in dataset.foreign_keys
                    ],
                },
            }
        )
        calls.append(
            _call(
                "list_schema_fields",
                {"urn": dataset.urn},
                {
                    "urn": dataset.urn,
                    "fields": [
                        {
                            "fieldPath": field.name,
                            "tags": field.tags,
                            "glossaryTerms": field.glossary_terms,
                        }
                        for field in dataset.fields
                    ],
                },
            )
        )
    calls.insert(
        0,
        _call(
            "get_entities",
            {"urns": [item.urn for item in metadata.datasets]},
            entities,
        ),
    )
    path.write_text(
        json.dumps(
            {
                "calls": calls,
                "summary": {"tools_used": ["get_entities", "list_schema_fields"]},
                "discovery": {"selected_datasets": [item.urn for item in metadata.datasets]},
            }
        )
    )


def test_goal_interpretation_prefers_explicit_quoted_scope() -> None:
    intent = interpret_goal('Build safe fixtures for assets matching "support tickets"')
    assert intent["datahub_query"] == "support tickets"
    assert "metadata-only" in intent["safety_boundary"]
    with pytest.raises(ValueError, match="must not be empty"):
        interpret_goal("  ")


def test_agent_creates_verified_git_delivery(
    fixture_path: Path,
    tmp_path: Path,
) -> None:
    metadata = MetadataBundle.model_validate_json(fixture_path.read_text())
    trace = tmp_path / "trace.json"
    _replay_trace(metadata, trace)
    repo = tmp_path / "repo"
    result = asyncio.run(
        run_agent(
            'Generate source-row-free fixtures for "FixtureForge"',
            Path("policies/fiction_retail.generation.json"),
            tmp_path / "run",
            replay_trace=trace,
            git_repo=repo,
            git_destination=Path("generated/retail"),
        )
    )
    assert result["status"] == "completed"
    assert result["evidence"]["deterministic_rebuild"]
    assert result["git_delivery"]["status"] == "committed"
    assert result["datahub_writeback"] == {"status": "approval_required"}
    assert (repo / "generated/retail/evidence/manifest.json").exists()


def test_discovery_helpers_and_safety_gate(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    first = "urn:li:dataset:(urn:li:dataPlatform:postgres,a.one,PROD)"
    second = "urn:li:dataset:(urn:li:dataPlatform:postgres,a.two,PROD)"
    payload = {"searchResults": [{"entity": {"urn": second}}, {"entity": {"urn": first}}]}
    assert _dataset_urns(payload) == [first, second]
    trace = {"calls": [_call("search", {"query": "a"}, payload)]}
    assert discovery_selection(trace, 1) == [first]
    with pytest.raises(ValueError, match="non-allowlisted"):
        asyncio.run(
            capture_official_mcp(
                tmp_path / "forbidden.json",
                [("delete_entity", {"urn": first})],
            )
        )
    monkeypatch.setenv("DATAHUB_GMS_URL", "https://production.example.com")
    with pytest.raises(ValueError, match="restricted to a local"):
        asyncio.run(writeback_local_evidence(tmp_path / "missing.json", first, tmp_path / "x"))


def test_official_mcp_capture_records_identity_and_calls(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Dumpable:
        def __init__(self, payload: dict[str, Any]) -> None:
            self.payload = payload

        def model_dump(self, *, mode: str) -> dict[str, Any]:
            assert mode == "json"
            return self.payload

    class FakeSession:
        async def __aenter__(self) -> FakeSession:
            return self

        async def __aexit__(self, *_args: object) -> None:
            return None

        async def initialize(self) -> Dumpable:
            return Dumpable({"serverInfo": {"name": "datahub", "version": "test"}})

        async def list_tools(self) -> Any:
            return SimpleNamespace(
                tools=[SimpleNamespace(name="search", description="Search", inputSchema={})]
            )

        async def call_tool(self, name: str, arguments: dict[str, Any]) -> Dumpable:
            assert name == "search"
            assert arguments["query"] == "support"
            return Dumpable(
                {
                    "content": [
                        {"type": "text", "text": json.dumps({"searchResults": []})}
                    ],
                    "isError": False,
                }
            )

    @asynccontextmanager
    async def fake_stdio(_server: object) -> Any:
        yield object(), object()

    monkeypatch.setattr(datahub_integration, "stdio_client", fake_stdio)
    monkeypatch.setattr(datahub_integration, "ClientSession", lambda *_args: FakeSession())
    output = tmp_path / "trace.json"
    trace = asyncio.run(
        capture_official_mcp(output, [("search", {"query": "support"})])
    )
    assert trace["server"]["version"] == "0.6.0"
    assert trace["calls"][0]["response"]["content"][0]["parsed_json"] == {
        "searchResults": []
    }
    assert trace["summary"]["source_row_calls"] == 0
    assert output.exists()


def test_discovery_orchestrates_search_lineage_and_inspection(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = "urn:li:dataset:(urn:li:dataPlatform:postgres,support.accounts,PROD)"
    child = "urn:li:dataset:(urn:li:dataPlatform:postgres,support.tickets,PROD)"

    async def fake_capture(
        output: Path,
        calls: list[tuple[str, dict[str, Any]]],
        **_kwargs: Any,
    ) -> dict[str, Any]:
        rendered: list[dict[str, Any]] = []
        for tool, arguments in calls:
            if tool == "search":
                payload: Any = {"searchResults": [{"entity": {"urn": root}}]}
            elif tool == "get_lineage":
                payload = {"downstreams": {"searchResults": [{"entity": {"urn": child}}]}}
            elif tool == "get_entities":
                payload = [{"urn": urn} for urn in arguments["urns"]]
            else:
                payload = {"urn": arguments["urn"], "fields": []}
            rendered.append(_call(tool, arguments, payload))
        trace = {
            "calls": rendered,
            "summary": {
                "calls": len(rendered),
                "tools_used": sorted({item["tool"] for item in rendered}),
            },
        }
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(trace))
        return trace

    monkeypatch.setattr(datahub_integration, "capture_official_mcp", fake_capture)
    trace = asyncio.run(
        datahub_integration.discover_official_mcp("support", tmp_path / "final.json")
    )
    assert trace["discovery"]["search_roots"] == [root]
    assert trace["discovery"]["selected_datasets"] == [root, child]
    assert {call["tool"] for call in trace["calls"]} >= {
        "search",
        "get_lineage",
        "get_entities",
        "list_schema_fields",
    }


def test_structured_document_writeback_is_verified(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fingerprint = "a" * 64
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "metadata_fingerprint": fingerprint,
                "seed": 2026,
                "validation_passed": True,
                "negative_control_detected": True,
                "files": {"a.csv": "hash"},
            }
        )
    )
    target = "urn:li:dataset:(urn:li:dataPlatform:postgres,support.accounts,PROD)"
    document = "urn:li:document:shared-test"

    async def fake_capture(
        output: Path,
        calls: list[tuple[str, dict[str, Any]]],
        **_kwargs: Any,
    ) -> dict[str, Any]:
        tool, arguments = calls[0]
        payload: Any
        if tool == "save_document":
            assert fingerprint in arguments["content"]
            payload = {"success": True, "urn": document}
        else:
            assert tool == "grep_documents"
            payload = {"matches": [{"urn": document, "context": fingerprint}]}
        return {
            "calls": [_call(tool, arguments, payload)],
            "summary": {"calls": 1, "tools_used": [tool], "source_row_calls": 0},
            "advertised_tools": [],
        }

    monkeypatch.setenv("DATAHUB_GMS_URL", "http://localhost:18080")
    monkeypatch.setattr(datahub_integration, "capture_official_mcp", fake_capture)
    result = asyncio.run(
        writeback_local_evidence(
            manifest,
            target,
            tmp_path / "writeback.json",
            {"status": "committed", "branch": "fixtureforge/support", "commit": "abc"},
        )
    )
    assert result["writeback"]["artifact"] == "DataHub Context Document"
    assert result["writeback"]["read_after_write_verified"]
