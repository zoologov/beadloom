"""A git repository whose history reaches main only through squash merges.

BDL-078 F-activity (`beadloom-lw56`). On a squash-merged history every change
lands as one commit, whatever it was: a branch of ten commits and a one-line fix
are both "1 commit". The fixture below is built so that a commit count cannot
tell its nodes apart and a count of changed lines can.

Layout (node -> source), all under ``src/app/``, with ``app`` the box holding
the other five and ``core`` the box holding ``parser``:

==========  ====================  ==============================================
node        source                history (days before ``now``)
==========  ====================  ==============================================
app         src/app               the box: its own file is never touched again
core        src/app/core          a box: no file of its own changes
parser      src/app/core/parser   one squash, 5 days ago: 300 lines added
api         src/app/api           one squash, 10 days ago, of a 10-commit branch
ui          src/app/ui            the same squash as ``parser``: 2 lines added
config      src/app/config        one commit 45 days ago: quiet
legacy      src/app/legacy        nothing since the first commit, 120 days ago
==========  ====================  ==============================================

Every node holds a file from the first commit, so a node with no change is one
whose file stood still, not one that does not exist.
"""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

#: ``ref_id -> source`` for the fixture's nodes.
SOURCES: dict[str, str] = {
    "app": "src/app",
    "core": "src/app/core",
    "parser": "src/app/core/parser",
    "api": "src/app/api",
    "ui": "src/app/ui",
    "config": "src/app/config",
    "legacy": "src/app/legacy",
}

#: ``child -> its containers`` (the ``part_of`` edges).
CONTAINERS: dict[str, list[str]] = {
    "core": ["app"],
    "parser": ["core"],
    "api": ["app"],
    "ui": ["app"],
    "config": ["app"],
    "legacy": ["app"],
}

#: Lines each squash adds, per node, and the size of the branch behind the api squash.
PARSER_LINES = 300
UI_LINES = 2
API_BRANCH_COMMITS = 10

_AUTHOR = "Squash Author"
_EMAIL = "squash@example.invalid"


@dataclass(frozen=True)
class SquashMergedRepo:
    """The repository and the instant its dates are measured from."""

    root: Path
    now: datetime


def run_git(root: Path, *args: str, when: datetime | None = None) -> None:
    env = dict(os.environ)
    if when is not None:
        stamp = when.isoformat()
        env["GIT_AUTHOR_DATE"] = stamp
        env["GIT_COMMITTER_DATE"] = stamp
    subprocess.run(  # noqa: S603
        ["git", *args],  # noqa: S607
        cwd=str(root),
        capture_output=True,
        check=True,
        env=env,
    )


def _append(root: Path, rel: str, lines: int, tag: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.writelines(f"{tag} {i}\n" for i in range(lines))


def init_repo(root: Path) -> None:
    """An empty repository on ``main`` with a fixed identity."""
    root.mkdir(parents=True, exist_ok=True)
    run_git(root, "init", "-q", "-b", "main")
    run_git(root, "config", "user.email", _EMAIL)
    run_git(root, "config", "user.name", _AUTHOR)
    run_git(root, "config", "commit.gpgsign", "false")


def commit_lines(
    root: Path, rel: str, lines: int, *, when: datetime, message: str = "change"
) -> None:
    """Append *lines* lines to *rel* and commit them at *when*."""
    _append(root, rel, lines, message)
    run_git(root, "add", "-A")
    run_git(root, "commit", "-q", "-m", message, when=when)


def _squash(root: Path, branch: str, *, when: datetime, message: str) -> None:
    run_git(root, "checkout", "-q", "main")
    run_git(root, "merge", "-q", "--squash", branch)
    run_git(root, "commit", "-q", "-m", message, when=when)
    run_git(root, "branch", "-q", "-D", branch)


def build_squash_merged_repo(root: Path, *, now: datetime | None = None) -> SquashMergedRepo:
    """Write the repository the module docstring describes, under *root*."""
    now = now or datetime.now(tz=timezone.utc)
    init_repo(root)

    first = now - timedelta(days=120)
    for ref_id, source in SOURCES.items():
        _append(root, f"{source}/{ref_id}.py", 5, "first")
    run_git(root, "add", "-A")
    run_git(root, "commit", "-q", "-m", "first", when=first)

    commit_lines(root, "src/app/config/config.py", 4, when=now - timedelta(days=45))

    run_git(root, "checkout", "-q", "-b", "api-branch")
    for i in range(API_BRANCH_COMMITS):
        commit_lines(
            root, "src/app/api/api.py", 1, when=now - timedelta(days=12, hours=-i), message="api"
        )
    _squash(root, "api-branch", when=now - timedelta(days=10), message="api (#1)")

    run_git(root, "checkout", "-q", "-b", "parser-branch")
    commit_lines(root, "src/app/core/parser/parser.py", PARSER_LINES, when=now - timedelta(days=6))
    commit_lines(root, "src/app/ui/ui.py", UI_LINES, when=now - timedelta(days=6))
    _squash(root, "parser-branch", when=now - timedelta(days=5), message="parser (#2)")

    return SquashMergedRepo(root=root, now=now)


def write_graph(root: Path) -> None:
    """Declare the fixture's nodes and their ``part_of`` edges as a Beadloom graph."""
    graph_dir = root / ".beadloom" / "_graph"
    graph_dir.mkdir(parents=True, exist_ok=True)
    (root / "docs").mkdir(exist_ok=True)
    nodes = "".join(
        f"  - ref_id: {ref_id}\n    kind: {'domain' if ref_id == 'app' else 'feature'}\n"
        f'    summary: "{ref_id}"\n    source: {source}\n'
        for ref_id, source in SOURCES.items()
    )
    edges = "".join(
        f"  - src: {child}\n    dst: {parent}\n    kind: part_of\n"
        for child, parents in CONTAINERS.items()
        for parent in parents
    )
    (graph_dir / "nodes.yml").write_text(f"nodes:\n{nodes}edges:\n{edges}", encoding="utf-8")


def build_squash_merged_project(root: Path, *, now: datetime | None = None) -> SquashMergedRepo:
    """The repository with its graph declared: a project a reindex can run over."""
    repo = build_squash_merged_repo(root, now=now)
    write_graph(root)
    return repo
