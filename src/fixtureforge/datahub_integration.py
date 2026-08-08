"""Real DataHub OSS seeding and official MCP evidence capture."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from fixtureforge.evidence import write_json
from fixtureforge.models import MetadataBundle

READ_ONLY_TOOLS = frozenset({"get_entities", "list_schema_fields", "get_lineage"})


def seed_local_datahub(metadata: MetadataBundle) -> dict[str, Any]:
    """Upsert the fictional metadata contract into a local DataHub instance."""
    from datahub.metadata.schema_classes import (
        ForeignKeyConstraintClass,
        SchemaMetadataClass,
    )
    from datahub.metadata.urns import SchemaFieldUrn
    from datahub.sdk.dataset import Dataset
    from datahub.sdk.glossary_term import GlossaryTerm
    from datahub.sdk.main_client import DataHubClient
    from datahub.sdk.tag import Tag

    client = DataHubClient.from_env(datahub_component="fixtureforge")
    client.test_connection()
    emitted: list[str] = []
    datasets = {dataset.name: dataset for dataset in metadata.datasets}
    tags = sorted(
        {tag for dataset in metadata.datasets for field in dataset.fields for tag in field.tags}
    )
    terms = sorted(
        {
            term
            for dataset in metadata.datasets
            for field in dataset.fields
            for term in field.glossary_terms
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
                definition="FixtureForge fictional retail glossary term.",
            )
        )
    for dataset in metadata.datasets:
        schema = [
            (field.name, field.type, field.description)
            for field in dataset.fields
        ]
        entity = Dataset(
            platform="postgres",
            name=f"fiction_retail.{dataset.name}",
            env="PROD",
            description=dataset.description,
            display_name=f"FixtureForge · {dataset.name}",
            schema=schema,
            upstreams=[
                datasets[relation.references_table].urn
                for relation in dataset.foreign_keys
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
            mcp.aspect
            for mcp in entity.as_mcps()
            if mcp.aspectName == "schemaMetadata"
        )
        if not isinstance(schema_metadata, SchemaMetadataClass):
            raise TypeError("DataHub SDK did not produce schema metadata")
        schema_metadata.primaryKeys = dataset.primary_key or None
        for aspect_field in schema_metadata.fields:
            aspect_field.isPartOfKey = aspect_field.fieldPath in dataset.primary_key
        schema_metadata.foreignKeys = [
            ForeignKeyConstraintClass(
                name=(
                    f"fixtureforge_{dataset.name}_{'_'.join(relation.fields)}_fk"
                ),
                sourceFields=[
                    str(SchemaFieldUrn(dataset.urn, field))
                    for field in relation.fields
                ],
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
        "SAVE_DOCUMENT_TOOL_ENABLED": "false",
        "DATAHUB_MCP_DOCUMENT_TOOLS_DISABLED": "true",
    }
    server = StdioServerParameters(
        command="uvx",
        args=["mcp-server-datahub"],
        env=environment,
    )
    trace: dict[str, Any] = {
        "server": {
            "distribution": "mcp-server-datahub",
            "repository": "https://github.com/acryldata/mcp-server-datahub",
            "transport": "stdio",
        },
        "policy": {
            "allowed_tools": sorted(allowed_tools),
            "mutation_enabled": mutation_enabled,
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


async def writeback_local_evidence(
    manifest_path: Path,
    target_urn: str,
    output: Path,
) -> dict[str, Any]:
    """Write evidence to a local demo entity and verify it through MCP."""
    gms_url = os.environ.get("DATAHUB_GMS_URL", "http://localhost:8080")
    host = urlparse(gms_url).hostname
    if host not in {"localhost", "127.0.0.1", "::1"}:
        raise ValueError("writeback is restricted to a local DataHub instance")
    manifest = json.loads(manifest_path.read_text())
    fingerprint = manifest["metadata_fingerprint"]
    description = (
        "Fictional retail dataset used by the FixtureForge local demonstration.\n\n"
        "## FixtureForge evidence\n\n"
        f"- Metadata fingerprint: {fingerprint}\n"
        f"- Seed: {manifest['seed']}\n"
        f"- Validation passed: {manifest['validation_passed']}\n"
        f"- Negative control detected: {manifest['negative_control_detected']}\n"
        "- Source rows read: 0\n"
    )
    trace = await capture_official_mcp(
        output,
        [
            (
                "update_description",
                {
                    "entity_urn": target_urn,
                    "operation": "replace",
                    "description": description,
                },
            ),
            ("get_entities", {"urns": [target_urn]}),
        ],
        allowed_tools=frozenset({"update_description", "get_entities"}),
        mutation_enabled=True,
    )
    update_response = trace["calls"][0]["response"]
    if update_response.get("isError"):
        raise RuntimeError("official MCP writeback returned an error")
    readback = _response_payload_from_trace(trace["calls"][1])
    rendered = json.dumps(readback, ensure_ascii=False)
    verified = fingerprint in rendered
    trace["writeback"] = {
        "target": target_urn,
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
