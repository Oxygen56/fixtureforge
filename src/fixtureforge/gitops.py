"""Safe Git delivery for agent-generated artifacts."""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path
from typing import Any


def _git(repo: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", *arguments],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug[:48] or "generated-fixtures"


def initialize_review_repo(repo: Path) -> dict[str, str]:
    """Create an isolated review repository without touching the caller's project."""
    if repo.exists():
        raise ValueError("review repository path must not already exist")
    repo.mkdir(parents=True)
    _git(repo, "init", "-b", "main")
    _git(repo, "config", "user.name", "FixtureForge Agent")
    _git(repo, "config", "user.email", "fixtureforge@example.invalid")
    (repo / "README.md").write_text("# FixtureForge generated-artifact review\n")
    _git(repo, "add", "README.md")
    _git(repo, "commit", "-m", "Initialize review repository")
    return {"repo": str(repo.resolve()), "branch": "main"}


def stage_generated_bundle(
    bundle: Path,
    repo: Path,
    destination: Path,
    goal: str,
) -> dict[str, Any]:
    """Create a reviewable branch and commit inside an explicitly supplied repo."""
    repo = repo.resolve()
    bundle = bundle.resolve()
    if _git(repo, "rev-parse", "--show-toplevel") != str(repo):
        raise ValueError("git delivery requires the repository root")
    if _git(repo, "status", "--porcelain"):
        raise ValueError("git delivery refuses a dirty repository")
    target = (repo / destination).resolve()
    if repo not in target.parents or target == repo:
        raise ValueError("git delivery destination must stay inside the repository")
    if target.exists():
        raise ValueError(f"git delivery destination already exists: {destination}")
    branch = f"fixtureforge/{slugify(goal)}"
    _git(repo, "checkout", "-b", branch)
    shutil.copytree(bundle, target)
    relative = target.relative_to(repo)
    _git(repo, "add", "--", str(relative))
    _git(repo, "-c", "core.whitespace=cr-at-eol", "diff", "--cached", "--check")
    _git(repo, "commit", "-m", f"FixtureForge: {goal}")
    commit = _git(repo, "rev-parse", "HEAD")
    files = _git(repo, "diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD").splitlines()
    return {
        "status": "committed",
        "branch": branch,
        "commit": commit,
        "destination": str(relative),
        "files": files,
        "review_command": f"git show --stat {commit}",
        "publish_command": f"git push -u origin {branch}",
    }
