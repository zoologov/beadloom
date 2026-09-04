"""Step implementations for BDL-068 S4 — what the commit gate says it compared.

Thin by design: every step drives the real ``beadloom scope-check`` over a real
git repository with a real index, because the defect being pinned is which
STREAM the answer arrives on. A double would report whatever the double was
told to report, and the stream is exactly what was wrong.

The module is named ``test_*`` so default pytest collection picks the scenarios
up -- the acceptance suite runs inside ``uv run pytest``, not beside it.
"""

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING, Any

import pytest
import yaml
from click.testing import CliRunner
from pytest_bdd import given, scenarios, then, when

from beadloom.services.cli import main

if TYPE_CHECKING:
    from pathlib import Path

scenarios("../features/commit_gate_verdict.feature")

#: The prefix the porcelain verdict line carries. A finding line begins with a
#: project-relative path, and no path begins with this, so a gate written in
#: shell splits the two streams without parsing either.
_MARKER = "# "

_AXES = """## Axes

> **Derived by:** `beadloom impact` over `src/alpha.py`
> **Seed:** `none`
> **Unresolved:** none

| Axis | Node | Sites | In scope | Why |
|---|---|---|---|---|
| callers | alpha | 1 — `src/alpha.py:1` | yes | the surface this work item changes |
"""


def _git(project: Path, *args: str) -> None:
    subprocess.run(  # noqa: S603
        ["git", *args],  # noqa: S607
        cwd=project,
        check=True,
        capture_output=True,
    )


@pytest.fixture
def state() -> dict[str, Any]:
    return {}


def _project(tmp_path: Path, *, axes: bool) -> Path:
    """A real repository, a real index, and one staged path of each kind."""
    project = tmp_path / "proj"
    project.mkdir()
    graph = project / ".beadloom" / "_graph"
    graph.mkdir(parents=True)
    (graph / "features.yml").write_text(
        yaml.dump(
            {
                "nodes": [
                    {"ref_id": "core", "kind": "domain", "summary": "The one context."},
                    {
                        "ref_id": "alpha",
                        "kind": "feature",
                        "summary": "The one feature.",
                        "source": "src/alpha.py",
                    },
                ],
                "edges": [{"src": "alpha", "dst": "core", "kind": "part_of"}],
            }
        ),
        encoding="utf-8",
    )
    source = project / "src"
    source.mkdir()
    (source / "alpha.py").write_text(
        "# beadloom:feature=alpha\ndef alpha() -> None:\n    pass\n", encoding="utf-8"
    )
    (project / "README.md").write_text("# proj\n", encoding="utf-8")
    if axes:
        folder = project / ".claude" / "development" / "docs" / "features" / "KEY-1"
        folder.mkdir(parents=True)
        (folder / "RFC.md").write_text(f"# RFC\n\n{_AXES}", encoding="utf-8")

    from beadloom.application.reindex import reindex

    reindex(project)

    _git(project, "init", "-b", "main")
    _git(project, "config", "user.email", "t@example.com")
    _git(project, "config", "user.name", "t")
    # An initial commit first: `git diff --cached` has no HEAD to compare
    # against in a repository with none, and the run would report GIT_SILENT
    # rather than the population the scenario is about.
    (project / ".gitignore").write_text(".beadloom/beadloom.db\n", encoding="utf-8")
    _git(project, "add", ".gitignore")
    _git(project, "commit", "-m", "base")
    _git(project, "add", "src/alpha.py", "README.md")
    return project


@given("a branch that names no work item")
def _no_work_item(state: dict[str, Any], tmp_path: Path) -> None:
    state["project"] = _project(tmp_path, axes=False)
    state["branch"] = "features/NOTHING"


@given("a work item whose declared axes reach one bounded context")
def _one_context(state: dict[str, Any], tmp_path: Path) -> None:
    state["project"] = _project(tmp_path, axes=True)
    state["branch"] = "features/KEY-1"


@when("the commit gate reads the porcelain verdict")
def _read(state: dict[str, Any]) -> None:
    result = CliRunner().invoke(
        main,
        [
            "scope-check",
            "--porcelain",
            "--project",
            str(state["project"]),
            "--branch",
            state["branch"],
        ],
    )
    lines = [line for line in result.stdout.splitlines() if line.strip()]
    state["verdict"] = [line for line in lines if line.startswith(_MARKER)]
    state["findings"] = [line for line in lines if not line.startswith(_MARKER)]


@then("the verdict says the run checked nothing, with the reason")
def _unjudged(state: dict[str, Any]) -> None:
    assert len(state["verdict"]) == 1, state["verdict"]
    line = state["verdict"][0]
    assert "NOT CHECKED" in line
    assert "names no work item" in line


@then("the run reports no finding")
def _no_finding(state: dict[str, Any]) -> None:
    assert state["findings"] == []


@then("the verdict states how many staged paths a node owns")
def _owned(state: dict[str, Any]) -> None:
    assert len(state["verdict"]) == 1, state["verdict"]
    assert "1 staged path(s) a node owns" in state["verdict"][0]


@then("the verdict states how many staged paths no node owns")
def _unowned(state: dict[str, Any]) -> None:
    assert "1 no node owns" in state["verdict"][0]


@then("the verdict line starts with a marker no reported path can begin with")
def _marker(state: dict[str, Any]) -> None:
    assert state["verdict"][0].startswith(_MARKER)
