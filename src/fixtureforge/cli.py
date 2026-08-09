"""FixtureForge command-line interface."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from fixtureforge.service import compare_manifests
from fixtureforge.service import generate as generate_bundle
from fixtureforge.service import verify as verify_bundle

app = typer.Typer(no_args_is_help=True, help="Metadata to merge-ready test assets.")
console = Console()


@app.command()
def generate(
    input_path: Annotated[
        Path,
        typer.Option("--input", exists=True, dir_okay=False, readable=True),
    ],
    output: Annotated[Path, typer.Option("--output")],
    seed: Annotated[int, typer.Option("--seed")] = 2026,
) -> None:
    """Generate and independently validate a fixture bundle."""
    manifest = generate_bundle(input_path, output, seed)
    console.print(json.dumps(manifest, indent=2))
    if not manifest["validation_passed"] or not manifest["negative_control_detected"]:
        raise typer.Exit(1)


@app.command()
def verify(
    bundle: Annotated[Path, typer.Option("--bundle", exists=True, file_okay=False)],
) -> None:
    """Re-run independent verification over an existing bundle."""
    result = verify_bundle(bundle)
    console.print(json.dumps(result, indent=2))
    if not result["passed"]:
        raise typer.Exit(1)


@app.command()
def compare(
    first: Annotated[Path, typer.Option("--first", exists=True, file_okay=False)],
    second: Annotated[Path, typer.Option("--second", exists=True, file_okay=False)],
) -> None:
    """Prove two independent builds are byte-identical."""
    result = compare_manifests(first, second)
    console.print(json.dumps(result, indent=2))
    if not result["identical"]:
        raise typer.Exit(1)


@app.command("datahub-seed")
def datahub_seed(
    input_path: Annotated[
        Path,
        typer.Option("--input", exists=True, dir_okay=False, readable=True),
    ],
    receipt: Annotated[Path, typer.Option("--receipt")],
) -> None:
    """Seed fictional metadata into a real local DataHub OSS instance."""
    from fixtureforge.datahub_integration import seed_local_datahub
    from fixtureforge.evidence import write_json
    from fixtureforge.service import load_metadata

    result = seed_local_datahub(load_metadata(input_path))
    write_json(receipt, result)
    console.print(json.dumps(result, indent=2))


@app.command("mcp-inspect")
def mcp_inspect(
    output: Annotated[Path, typer.Option("--output")],
) -> None:
    """Record the official server identity and live tool schemas."""
    from fixtureforge.datahub_integration import inspect_official_mcp

    result = asyncio.run(inspect_official_mcp(output))
    console.print(
        json.dumps(
            {
                "server": result["server"],
                "advertised_tools": [
                    tool["name"] for tool in result["advertised_tools"]
                ],
            },
            indent=2,
        )
    )


@app.command("mcp-collect")
def mcp_collect(
    input_path: Annotated[
        Path,
        typer.Option("--input", exists=True, dir_okay=False, readable=True),
    ],
    output: Annotated[Path, typer.Option("--output")],
) -> None:
    """Collect metadata-only evidence through the official MCP server."""
    from fixtureforge.datahub_integration import collect_official_mcp
    from fixtureforge.service import load_metadata

    result = asyncio.run(collect_official_mcp(load_metadata(input_path), output))
    console.print(json.dumps(result["summary"], indent=2))


@app.command("mcp-discover")
def mcp_discover(
    query: Annotated[str, typer.Option("--query")],
    output: Annotated[Path, typer.Option("--output")],
    max_datasets: Annotated[int, typer.Option("--max-datasets", min=1, max=50)] = 12,
) -> None:
    """Discover a bounded DataHub graph from search and lineage."""
    from fixtureforge.datahub_integration import discover_official_mcp

    result = asyncio.run(discover_official_mcp(query, output, max_datasets=max_datasets))
    console.print(json.dumps(result["discovery"], indent=2))


@app.command("mcp-normalize")
def mcp_normalize(
    trace: Annotated[
        Path,
        typer.Option("--trace", exists=True, dir_okay=False, readable=True),
    ],
    policy: Annotated[
        Path,
        typer.Option("--policy", exists=True, dir_okay=False, readable=True),
    ],
    output: Annotated[Path, typer.Option("--output")],
) -> None:
    """Normalize live MCP results into the deterministic compiler contract."""
    from fixtureforge.mcp_normalizer import normalize_to_file

    bundle = normalize_to_file(trace, policy, output)
    console.print(
        json.dumps(
            {
                "source": bundle.source,
                "datasets": [dataset.name for dataset in bundle.datasets],
                "source_rows_read": 0,
            },
            indent=2,
        )
    )


@app.command("mcp-writeback")
def mcp_writeback(
    manifest: Annotated[
        Path,
        typer.Option("--manifest", exists=True, dir_okay=False, readable=True),
    ],
    target_urn: Annotated[str, typer.Option("--target-urn")],
    output: Annotated[Path, typer.Option("--output")],
    approve_local_writeback: Annotated[
        bool,
        typer.Option("--approve-local-writeback"),
    ] = False,
) -> None:
    """Write evidence to local DataHub with an explicit approval flag."""
    if not approve_local_writeback:
        raise typer.BadParameter("local writeback requires --approve-local-writeback")
    from fixtureforge.datahub_integration import writeback_local_evidence

    trace = asyncio.run(writeback_local_evidence(manifest, target_urn, output))
    console.print(json.dumps(trace["writeback"], indent=2))


@app.command("report")
def report(
    bundle: Annotated[
        Path,
        typer.Option("--bundle", exists=True, file_okay=False),
    ],
    mcp_trace: Annotated[
        Path,
        typer.Option("--mcp-trace", exists=True, dir_okay=False),
    ],
    writeback_trace: Annotated[
        Path,
        typer.Option("--writeback-trace", exists=True, dir_okay=False),
    ],
    output: Annotated[Path, typer.Option("--output")],
) -> None:
    """Generate a self-contained visual evidence report."""
    from fixtureforge.reporting import build_report

    result = build_report(bundle, mcp_trace, writeback_trace, output)
    console.print(json.dumps(result, indent=2))


@app.command("agent-run")
def agent_run(
    goal: Annotated[str, typer.Option("--goal")],
    policy: Annotated[
        Path,
        typer.Option("--policy", exists=True, dir_okay=False, readable=True),
    ],
    workspace: Annotated[Path, typer.Option("--workspace")],
    seed: Annotated[int, typer.Option("--seed")] = 2026,
    replay_trace: Annotated[
        Path | None,
        typer.Option("--replay-trace", exists=True, dir_okay=False, readable=True),
    ] = None,
    git_repo: Annotated[
        Path | None,
        typer.Option("--git-repo", file_okay=False),
    ] = None,
    git_destination: Annotated[Path | None, typer.Option("--git-destination")] = None,
    approve_datahub_writeback: Annotated[
        bool,
        typer.Option("--approve-datahub-writeback"),
    ] = False,
) -> None:
    """Run the bounded goal-to-validated-code agent."""
    from fixtureforge.agent import run_agent

    result = asyncio.run(
        run_agent(
            goal,
            policy,
            workspace,
            seed=seed,
            replay_trace=replay_trace,
            git_repo=git_repo,
            git_destination=git_destination,
            approve_datahub_writeback=approve_datahub_writeback,
        )
    )
    console.print(
        json.dumps(
            {
                "status": result["status"],
                "query": result["intent"]["datahub_query"],
                "datasets": len(result["selected_datasets"]),
                "evidence": result["evidence"],
                "git_delivery": result["git_delivery"],
                "datahub_writeback": result["datahub_writeback"],
            },
            indent=2,
        )
    )


@app.command("agent-report")
def agent_report(
    run: Annotated[
        Path,
        typer.Option("--run", exists=True, dir_okay=False, readable=True),
    ],
    output: Annotated[Path, typer.Option("--output")],
) -> None:
    """Render a self-contained agent execution report."""
    from fixtureforge.reporting import build_agent_report

    console.print(json.dumps(build_agent_report(run, output), indent=2))


if __name__ == "__main__":
    app()
