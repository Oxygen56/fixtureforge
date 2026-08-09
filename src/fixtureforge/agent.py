"""Bounded autonomous loop from a natural-language goal to reviewable fixtures."""

from __future__ import annotations

import json
import re
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fixtureforge.datahub_integration import discover_official_mcp, writeback_local_evidence
from fixtureforge.evidence import write_json
from fixtureforge.gitops import initialize_review_repo, stage_generated_bundle
from fixtureforge.mcp_normalizer import normalize_to_file
from fixtureforge.service import compare_manifests, generate, verify


def interpret_goal(goal: str) -> dict[str, str]:
    """Turn a bounded natural-language request into an auditable search intent."""
    cleaned = " ".join(goal.split()).strip()
    if not cleaned:
        raise ValueError("agent goal must not be empty")
    quoted = re.findall(r'["“](.+?)["”]', cleaned)
    if quoted:
        query = quoted[-1]
    else:
        match = re.search(r"(?:matching|about|for)\s+(.+)$", cleaned, re.IGNORECASE)
        query = match.group(1).strip(" .") if match else cleaned
    return {
        "goal": cleaned,
        "datahub_query": query,
        "delivery": "merge-ready relational fixtures and developer tests",
        "safety_boundary": "metadata-only reads; mutation requires explicit approval",
    }


def _event(phase: str, status: str, evidence: str) -> dict[str, str]:
    return {
        "at": datetime.now(UTC).isoformat(),
        "phase": phase,
        "status": status,
        "evidence": evidence,
    }


def _save_run(path: Path, run: dict[str, Any]) -> None:
    write_json(path, run)


async def run_agent(
    goal: str,
    policy: Path,
    workspace: Path,
    *,
    seed: int = 2026,
    replay_trace: Path | None = None,
    git_repo: Path | None = None,
    git_destination: Path | None = None,
    approve_datahub_writeback: bool = False,
) -> dict[str, Any]:
    """Execute the plan, validate twice, and optionally create a Git commit."""
    intent = interpret_goal(goal)
    workspace.mkdir(parents=True, exist_ok=True)
    receipt_path = workspace / "agent-run.json"
    run: dict[str, Any] = {
        "agent": "FixtureForge bounded metadata-to-code agent",
        "intent": intent,
        "seed": seed,
        "mode": "recorded_mcp_replay" if replay_trace else "live_official_mcp",
        "events": [_event("plan", "completed", "natural-language goal interpreted")],
        "approval_gates": {
            "datahub_mutation": "not_requested",
            "remote_git_publish": "not_requested",
        },
        "source_rows_read": 0,
    }
    _save_run(receipt_path, run)

    trace_path = workspace / "mcp-trace.json"
    if replay_trace is None:
        trace = await discover_official_mcp(intent["datahub_query"], trace_path)
    else:
        shutil.copy2(replay_trace, trace_path)
        trace = json.loads(trace_path.read_text())
    selected = trace.get("discovery", {}).get("selected_datasets", [])
    run["events"].append(
        _event("discover", "completed", f"selected {len(selected) or 'recorded'} datasets")
    )
    _save_run(receipt_path, run)

    metadata_path = workspace / "normalized-metadata.json"
    metadata = normalize_to_file(trace_path, policy, metadata_path)
    run["selected_datasets"] = [dataset.urn for dataset in metadata.datasets]
    run["events"].append(
        _event("inspect", "completed", f"normalized {len(metadata.datasets)} datasets")
    )

    bundle = workspace / "generated"
    repeat = workspace / "generated-repeat"
    manifest = generate(metadata_path, bundle, seed)
    generate(metadata_path, repeat, seed)
    comparison = compare_manifests(bundle, repeat)
    validation = verify(bundle)
    if not comparison["identical"] or not validation["passed"]:
        raise RuntimeError("agent verification gate rejected generated artifacts")
    if not manifest["negative_control_detected"]:
        raise RuntimeError("agent negative-control gate was not exercised")
    run["events"].extend(
        [
            _event("generate", "completed", f"emitted {len(manifest['files'])} files"),
            _event("verify", "completed", "independent validation and negative control passed"),
            _event("rebuild", "completed", "second build was byte-identical"),
        ]
    )
    run["evidence"] = {
        "bundle": str(bundle),
        "metadata_fingerprint": manifest["metadata_fingerprint"],
        "files": len(manifest["files"]),
        "validation_checks": validation["checks_passed"],
        "negative_control_detected": True,
        "deterministic_rebuild": True,
    }
    if git_repo is not None:
        if git_destination is None:
            raise ValueError("git_destination is required when git_repo is supplied")
        if not git_repo.exists():
            run["git_sandbox"] = initialize_review_repo(git_repo)
        delivery = stage_generated_bundle(bundle, git_repo, git_destination, goal)
        run["git_delivery"] = delivery
        run["events"].append(
            _event("deliver", "completed", f"created commit {delivery['commit'][:12]}")
        )
    else:
        run["git_delivery"] = {"status": "not_requested"}
        run["events"].append(
            _event("deliver", "ready", "bundle passed every gate; Git commit not requested")
        )
    if approve_datahub_writeback:
        if replay_trace is not None:
            raise ValueError("DataHub writeback is unavailable in replay mode")
        target_urn = run["selected_datasets"][0]
        writeback = await writeback_local_evidence(
            bundle / "evidence" / "manifest.json",
            target_urn,
            workspace / "mcp-writeback-trace.json",
            run["git_delivery"],
        )
        run["datahub_writeback"] = writeback["writeback"]
        run["approval_gates"]["datahub_mutation"] = "approved_and_executed"
        run["events"].append(
            _event("writeback", "completed", "Context Document verified by read-after-write")
        )
    else:
        run["datahub_writeback"] = {"status": "approval_required"}
        run["events"].append(
            _event("writeback", "waiting", "no mutation performed without explicit approval")
        )
    run["status"] = "completed"
    run["finished_at"] = datetime.now(UTC).isoformat()
    _save_run(receipt_path, run)
    return run
