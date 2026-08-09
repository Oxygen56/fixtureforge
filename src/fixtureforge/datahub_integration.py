"""Real DataHub OSS seeding and official MCP evidence capture."""

from __future__ import annotations

import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from fixtureforge.evidence import write_json
from fixtureforge.models import MetadataBundle

MCP_SERVER_VERSION = "0.6.0"
READ_ONLY_TOOLS = frozenset({"search", "get_entities", "list_schema_fields", "get_lineage"})


def seed_local_datahub(metadata: MetadataBundle) -> dict[str, Any]:  # pragma: no cover
    """Upsert the fictional metadata contract into a local DataHub instance."""
    from datahub.metadata.schema_classes import (
        ForeignKeyConstraintClass,
        SchemaMetadataClass,
    )
    from datahub.metadata.urns import CorpUserUrn, SchemaFieldUrn
    from datahub.sdk.dataset import Dataset
    from datahub.sdk.glossary_term import GlossaryTerm
    from datahub.sdk.main_client import DataHubClient
    from datahub.sdk.tag import Tag

    client = DataHubClient.from_env(datahub_component="fixtureforge")
    client.test_connection()
    emitted: list[str] = []
    datasets = {dataset.name: dataset for dataset in metadata.datasets}
    tags = sorted(
        {
            tag
            for dataset in metadata.datasets
            for tag in [*dataset.tags, *(tag for field in dataset.fields for tag in field.tags)]
        }
    )
    terms = sorted(
        {
            term
            for dataset in metadata.datasets
            for term in [
                *dataset.glossary_terms,
                *(term for field in dataset.fields for term in field.glossary_terms),
            ]
        }
    )
    for tag in tags:
        client.entities.upsert(
            Tag(
                name=tag,
                display_name=tag.replace("_", " ").title(),
                description="FixtureForge demo governance tag.",
            )
        )
    for term in terms:
        client.entities.upsert(
            GlossaryTerm(
                id=term,
                display_name=term.replace("_", " ").title(),
                definition="FixtureForge fictional demonstration glossary term.",
            )
        )
    for dataset in metadata.datasets:
        qualified_name = dataset.urn.split(",", 2)[1]
        schema = [(field.name, field.type, field.description) for field in dataset.fields]
        entity = Dataset(
            platform="postgres",
            name=qualified_name,
            env="PROD",
            description=dataset.description,
            display_name=f"FixtureForge · {qualified_name}",
            owners=[CorpUserUrn.from_string(owner) for owner in dataset.owners],
            tags=[f"urn:li:tag:{tag}" for tag in dataset.tags],
            terms=[f"urn:li:glossaryTerm:{term}" for term in dataset.glossary_terms],
            schema=schema,
            upstreams=[
                datasets[relation.references_table].urn for relation in dataset.foreign_keys
            ],
            custom_properties={
                "fixtureforge_source": "fictional metadata only",
                "fixtureforge_source_rows": "never accessed",
            },
        )
        by_name = {field.field_path: field for field in entity.schema}
        for field in dataset.fields:
            schema_field = by_name[field.name]
            for tag in field.tags:
                schema_field.add_tag(f"urn:li:tag:{tag}")
            for term in field.glossary_terms:
                schema_field.add_term(f"urn:li:glossaryTerm:{term}")
        schema_metadata = next(
            mcp.aspect for mcp in entity.as_mcps() if mcp.aspectName == "schemaMetadata"
        )
        if not isinstance(schema_metadata, SchemaMetadataClass):
            raise TypeError("DataHub SDK did not produce schema metadata")
        schema_metadata.primaryKeys = dataset.primary_key or None
        for aspect_field in schema_metadata.fields:
            aspect_field.isPartOfKey = aspect_field.fieldPath in dataset.primary_key
        schema_metadata.foreignKeys = [
            ForeignKeyConstraintClass(
                name=(f"fixtureforge_{dataset.name}_{'_'.join(relation.fields)}_fk"),
                sourceFields=[str(SchemaFieldUrn(dataset.urn, field)) for field in relation.fields],
                foreignFields=[
                    str(
                        SchemaFieldUrn(
                            datasets[relation.references_table].urn,
                            field,
                        )
                    )
                    for field in relation.references_fields
                ],
                foreignDataset=datasets[relation.references_table].urn,
            )
            for relation in dataset.foreign_keys
        ] or None
        client.entities.upsert(entity)
        emitted.append(str(entity.urn))
    return {
        "status": "seeded",
        "target": os.environ.get("DATAHUB_GMS_URL", "http://localhost:8080"),
        "datasets": emitted,
        "source_rows_emitted": 0,
    }


def _response_payload(result: Any) -> Any:
    dumped = result.model_dump(mode="json")
    for content in dumped.get("content", []):
        text = content.get("text")
        if isinstance(text, str):
            try:
                content["parsed_json"] = json.loads(text)
            except json.JSONDecodeError:
                pass
    return dumped


async def capture_official_mcp(
    output: Path,
    calls: list[tuple[str, dict[str, Any]]],
    *,
    allowed_tools: frozenset[str] = READ_ONLY_TOOLS,
    mutation_enabled: bool = False,
    document_tools_enabled: bool = False,
) -> dict[str, Any]:
    """Call the official server through stdio and save an auditable trace."""
    forbidden = sorted({name for name, _ in calls} - allowed_tools)
    if forbidden:
        raise ValueError(f"non-allowlisted MCP tools requested: {forbidden}")
    environment = {
        **os.environ,
        "DATAHUB_GMS_URL": os.environ.get("DATAHUB_GMS_URL", "http://localhost:8080"),
        "TOOLS_IS_MUTATION_ENABLED": str(mutation_enabled).lower(),
        "TOOLS_IS_USER_ENABLED": "false",
        "SAVE_DOCUMENT_TOOL_ENABLED": str(document_tools_enabled).lower(),
        "DATAHUB_MCP_DOCUMENT_TOOLS_DISABLED": str(not document_tools_enabled).lower(),
    }
    server = StdioServerParameters(
        command="uvx",
        args=[f"mcp-server-datahub=={MCP_SERVER_VERSION}"],
        env=environment,
    )
    trace: dict[str, Any] = {
        "server": {
            "distribution": "mcp-server-datahub",
            "version": MCP_SERVER_VERSION,
            "repository": "https://github.com/acryldata/mcp-server-datahub",
            "transport": "stdio",
        },
        "policy": {
            "allowed_tools": sorted(allowed_tools),
            "mutation_enabled": mutation_enabled,
            "document_tools_enabled": document_tools_enabled,
            "source_row_tools_available": False,
        },
        "advertised_tools": [],
        "calls": [],
    }
    async with stdio_client(server) as (reader, writer):
        async with ClientSession(reader, writer) as session:
            initialize = await session.initialize()
            trace["initialize"] = initialize.model_dump(mode="json")
            listing = await session.list_tools()
            trace["advertised_tools"] = [
                {
                    "name": tool.name,
                    "description": tool.description,
                    "inputSchema": tool.inputSchema,
                }
                for tool in listing.tools
            ]
            available = {tool.name for tool in listing.tools}
            missing = sorted({name for name, _ in calls} - available)
            if missing:
                raise RuntimeError(f"official MCP server is missing required tools: {missing}")
            for name, arguments in calls:
                result = await session.call_tool(name, arguments)
                trace["calls"].append(
                    {
                        "tool": name,
                        "arguments": arguments,
                        "response": _response_payload(result),
                    }
                )
    trace["summary"] = {
        "calls": len(trace["calls"]),
        "tools_used": sorted({call["tool"] for call in trace["calls"]}),
        "source_row_calls": 0,
    }
    write_json(output, trace)
    return trace


async def inspect_official_mcp(output: Path) -> dict[str, Any]:
    return await capture_official_mcp(output, [])


async def collect_official_mcp(
    metadata: MetadataBundle,
    output: Path,
) -> dict[str, Any]:
    calls: list[tuple[str, dict[str, Any]]] = [
        ("get_entities", {"urns": [dataset.urn for dataset in metadata.datasets]})
    ]
    for dataset in metadata.datasets:
        calls.append(("list_schema_fields", {"urn": dataset.urn}))
        calls.append(
            (
                "get_lineage",
                {
                    "urn": dataset.urn,
                    "upstream": False,
                    "max_hops": 1,
                },
            )
        )
    return await capture_official_mcp(output, calls)


def _dataset_urns(payload: Any) -> list[str]:
    """Find dataset URNs in any official-MCP response without assuming one shape."""
    found: set[str] = set()

    def visit(value: Any) -> None:
        if isinstance(value, dict):
            urn = value.get("urn")
            if isinstance(urn, str) and urn.startswith("urn:li:dataset:("):
                found.add(urn)
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)

    visit(payload)
    return sorted(found)


def _urns(payload: Any, prefix: str) -> list[str]:
    found: set[str] = set()

    def visit(value: Any) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                if key == "urn" and isinstance(child, str) and child.startswith(prefix):
                    found.add(child)
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)
        elif isinstance(value, str) and value.startswith(prefix):
            found.add(value)

    visit(payload)
    return sorted(found)


def discovery_selection(trace: dict[str, Any], limit: int = 12) -> list[str]:
    """Derive the bounded dataset working set from search and lineage evidence."""
    selected: set[str] = set()
    for call in trace.get("calls", []):
        if call.get("tool") in {"search", "get_lineage"}:
            selected.update(_dataset_urns(_response_payload_from_trace(call)))
    return sorted(selected)[:limit]


def _scope_selection(query: str, urns: list[str]) -> list[str]:
    """Prefer an exact namespace match when the goal names one explicitly."""
    token = query.strip().lower()
    if not re.fullmatch(r"[a-z0-9_.-]+", token):
        return urns
    scoped = [urn for urn in urns if token in urn.lower()]
    return scoped or urns


async def discover_official_mcp(
    query: str,
    output: Path,
    *,
    max_datasets: int = 12,
) -> dict[str, Any]:
    """Search DataHub, expand one-hop lineage, then inspect the selected graph."""
    if not query.strip():
        raise ValueError("a non-empty DataHub search query is required")
    search_call = ("search", {"query": query, "offset": 0, "num_results": max_datasets})
    with tempfile.TemporaryDirectory(prefix="fixtureforge-discovery-") as directory:
        search_trace = await capture_official_mcp(Path(directory) / "search.json", [search_call])
        roots = _scope_selection(query, discovery_selection(search_trace, max_datasets))
        if not roots:
            raise RuntimeError(f"DataHub search returned no datasets for query: {query}")
        lineage_calls = [
            (
                "get_lineage",
                {"urn": urn, "upstream": upstream, "max_hops": 1, "max_results": 100},
            )
            for urn in roots
            for upstream in (True, False)
        ]
        probe = await capture_official_mcp(
            Path(directory) / "lineage.json",
            [search_call, *lineage_calls],
        )
        selected = _scope_selection(query, discovery_selection(probe, max_datasets))
    calls: list[tuple[str, dict[str, Any]]] = [search_call, *lineage_calls]
    calls.append(("get_entities", {"urns": selected}))
    for urn in selected:
        calls.append(("list_schema_fields", {"urn": urn}))
    trace = await capture_official_mcp(output, calls)
    trace["discovery"] = {
        "query": query,
        "search_roots": roots,
        "selected_datasets": selected,
        "max_datasets": max_datasets,
        "selection_rule": (
            "search results plus one-hop upstream/downstream lineage, sorted and capped"
        ),
        "source_rows_read": 0,
    }
    write_json(output, trace)
    return trace


async def writeback_local_evidence(
    manifest_path: Path,
    target_urn: str,
    output: Path,
    delivery: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Write evidence to a local demo entity and verify it through MCP."""
    gms_url = os.environ.get("DATAHUB_GMS_URL", "http://localhost:8080")
    host = urlparse(gms_url).hostname
    if host not in {"localhost", "127.0.0.1", "::1"}:
        raise ValueError("writeback is restricted to a local DataHub instance")
    manifest = json.loads(manifest_path.read_text())
    fingerprint = manifest["metadata_fingerprint"]
    delivery_lines = ""
    delivery_state = "ready for Git review"
    if delivery and delivery.get("status") == "committed":
        delivery_lines = f"- Git branch: {delivery['branch']}\n- Git commit: {delivery['commit']}\n"
        delivery_state = "committed for Git review"
    content = (
        "# FixtureForge generation evidence\n\n"
        f"- Metadata fingerprint: {fingerprint}\n"
        f"- Seed: {manifest['seed']}\n"
        f"- Validation passed: {manifest['validation_passed']}\n"
        f"- Negative control detected: {manifest['negative_control_detected']}\n"
        f"- Generated files: {len(manifest['files'])}\n"
        f"{delivery_lines}"
        f"- Delivery state: {delivery_state}\n"
        "- Source rows read: 0\n"
    )
    with tempfile.TemporaryDirectory(prefix="fixtureforge-writeback-") as directory:
        document_trace = await capture_official_mcp(
            Path(directory) / "document.json",
            [
                (
                    "save_document",
                    {
                        "document_type": "Context",
                        "title": f"FixtureForge evidence · {fingerprint[:12]}",
                        "content": content,
                        "related_assets": [target_urn],
                        "topics": ["fixture-generation", "data-quality", "source-row-free"],
                    },
                )
            ],
            allowed_tools=frozenset({"save_document"}),
            mutation_enabled=True,
            document_tools_enabled=True,
        )
        document_response = document_trace["calls"][0]["response"]
        document_payload = _response_payload_from_trace(document_trace["calls"][0])
        document_urns = _urns(document_payload, "urn:li:document:")
        if document_response.get("isError") or not document_urns:
            raise RuntimeError("official MCP document writeback returned no document URN")
        document_urn = document_urns[0]
        read_trace = await capture_official_mcp(
            Path(directory) / "readback.json",
            [
                (
                    "grep_documents",
                    {
                        "urns": [document_urn],
                        "pattern": fingerprint,
                        "context_chars": 120,
                        "max_matches_per_doc": 2,
                    },
                )
            ],
            allowed_tools=frozenset({"grep_documents"}),
            document_tools_enabled=True,
        )
    trace = document_trace
    trace["calls"].extend(read_trace["calls"])
    trace["summary"] = {
        "calls": len(trace["calls"]),
        "tools_used": sorted({call["tool"] for call in trace["calls"]}),
        "source_row_calls": 0,
    }
    readback = _response_payload_from_trace(trace["calls"][1])
    rendered = json.dumps(readback, ensure_ascii=False)
    verified = fingerprint in rendered
    trace["writeback"] = {
        "target": target_urn,
        "document_urn": document_urn,
        "artifact": "DataHub Context Document",
        "local_only": True,
        "metadata_fingerprint": fingerprint,
        "read_after_write_verified": verified,
    }
    write_json(output, trace)
    if not verified:
        raise RuntimeError("read-after-write did not contain the evidence fingerprint")
    return trace


def _response_payload_from_trace(call: dict[str, Any]) -> Any:
    content = call["response"]["content"][0]
    if "parsed_json" in content:
        return content["parsed_json"]
    return json.loads(content["text"])
