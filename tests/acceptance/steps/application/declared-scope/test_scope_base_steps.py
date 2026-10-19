"""Step implementations for `application/declared-scope/scope_base.feature`.

BDL-083 S1d (``beadloom-fgu8``). Thin: each step builds the shape of BDL-UX #330 on a
real checkout of the monorepo fixture — the trunk, a parent branch that edits two
frontend files and is not merged, and a work item cut from it that edits the backend —
and runs the real ``beadloom ci`` or ``beadloom scope-check`` over it, because the
finding is about what those commands print. The pull request's environment is set by
``monkeypatch``, never inherited from the job the suite itself runs in.
"""

from __future__ import annotations

import json
import shutil
from typing import TYPE_CHECKING, Any

import pytest
from click.testing import CliRunner
from pytest_bdd import given, scenarios, then, when

from beadloom.application.guards.contract import ClaimedBead
from beadloom.application.reindex import reindex
from beadloom.services.cli import main
from tests.support.committed_project import commit_project, git
from tests.support.package_under_test import SHIPPED_FROM

if TYPE_CHECKING:
    from pathlib import Path

scenarios("../../../application/declared-scope/scope_base.feature")

#: The two frontend files the parent branch changed, which the work item never touched.
_PARENT_FILES = frozenset(
    {"frontend/src/widgets/kpi-panel/ui/KpiPanel.ts", "frontend/src/shared/lib/percent.ts"}
)

#: The backend file the work item changed, inside the axis it declares.
_OWN_FILE = "backend/src/digest/sections.py"

#: The work item, its branch and the branch it was cut from.
_WORK_ITEM = "W2"
_BRANCH = "features/W2"
_PARENT = "features/W1"

#: The work item's bead, named in its commit as bd links a commit to an issue.
_BEAD = "bd-w2"

#: The work item's declared axes: the digest, and nothing of the frontend.
_RFC = """# RFC: W2

## Axes

> **Derived by:** `beadloom impact` over `backend/src/digest/sections.py`
> **Seed:** `digest`
> **Unresolved:** none

| Axis | Node | Sites | In scope | Why |
|---|---|---|---|---|
| callers | `digest` | 1 — `sections.py:1` | yes | the digest is this work |
"""

#: The CI variables a pull or merge request job sets, cleared before each scenario.
_CI_VARIABLES = (
    "GITHUB_HEAD_REF",
    "GITHUB_BASE_REF",
    "CI_MERGE_REQUEST_SOURCE_BRANCH_NAME",
    "CI_MERGE_REQUEST_TARGET_BRANCH_NAME",
)

#: A committer identity, so a commit does not depend on the machine's git configuration.
_IDENTITY = ("-c", "user.name=Test Committer", "-c", "user.email=committer@example.invalid")


@pytest.fixture()
def world(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """One mutable bag the steps share, in an environment no CI variable reaches."""
    for variable in _CI_VARIABLES:
        monkeypatch.delenv(variable, raising=False)
    return {"workdir": tmp_path, "root": None, "monkeypatch": monkeypatch}


def _edit(root: Path, path: str, line: str) -> None:
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    existing = target.read_text(encoding="utf-8") if target.exists() else ""
    target.write_text(existing + line, encoding="utf-8")
    git(root, "add", path)


@given("the monorepo fixture with a work item on a branch cut from an unmerged branch")
def _stacked(world: dict[str, Any]) -> None:
    # Copied from the checkout the package under test ships from, as the ownership
    # scenarios do: a copied suite has no repository root of its own to find it in.
    root = world["workdir"] / "metrics-desk"
    shutil.copytree(SHIPPED_FROM / "tests" / "fixtures" / "monorepo", root)
    commit_project(root)
    git(root, "branch", "-M", "main")
    git(root, "switch", "-q", "-c", _PARENT)
    for path in sorted(_PARENT_FILES):
        _edit(root, path, "// the parent work item's change\n")
    git(root, *_IDENTITY, "commit", "-q", "-m", "the parent work item")
    git(root, "switch", "-q", "-c", _BRANCH)
    _edit(root, f".claude/development/docs/features/{_WORK_ITEM}/RFC.md", _RFC)
    _edit(root, _OWN_FILE, "# the work item's change\n")
    git(root, *_IDENTITY, "commit", "-q", "-m", f"the work item ({_BEAD})")
    world["root"] = root


@given("the work item's bead is claimed")
def _claimed(world: dict[str, Any]) -> None:
    # The one double: the tracker adapter, so a scenario needs no beads database.
    from beadloom.services import guard_probes

    claimed = (ClaimedBead(id=_BEAD, title=_BEAD, declaration="refs: digest"),)
    world["monkeypatch"].setattr(
        guard_probes.BdWorkTracker, "claimed_beads", lambda _self: claimed
    )


@given("the checkout is a detached HEAD, as a pull request's CI job has it")
def _detached(world: dict[str, Any]) -> None:
    git(world["root"], "checkout", "-q", "--detach")


def _gate(world: dict[str, Any]) -> None:
    result = CliRunner().invoke(main, ["ci", "--project", str(world["root"]), "--format", "json"])
    world["gate"] = json.loads(result.stdout)


def _scope_check(world: dict[str, Any], *extra: str) -> None:
    # The Gate reindexes before it judges; scope-check reads the index it is given.
    reindex(world["root"])
    project = ["--project", str(world["root"])]
    world["human"] = CliRunner().invoke(main, ["scope-check", *project, *extra]).stdout
    machine = CliRunner().invoke(main, ["scope-check", *project, *extra, "--json"])
    world["scope"] = json.loads(machine.stdout)


@when("the gate judges the branch against its declared axes")
def _the_gate(world: dict[str, Any]) -> None:
    _gate(world)


@when("scope-check is asked to judge the branch against the trunk named by hand")
def _by_hand(world: dict[str, Any]) -> None:
    _scope_check(world, "--base", "main")


@when("the gate judges the checkout with the pull request's head branch in its environment")
def _the_gate_in_a_pull_request(world: dict[str, Any]) -> None:
    world["monkeypatch"].setenv("GITHUB_HEAD_REF", _BRANCH)
    world["monkeypatch"].setenv("GITHUB_BASE_REF", "main")
    _gate(world)


@when("scope-check judges the checkout with the merge request's source branch in its environment")
def _scope_check_in_a_merge_request(world: dict[str, Any]) -> None:
    world["monkeypatch"].setenv("CI_MERGE_REQUEST_SOURCE_BRANCH_NAME", _BRANCH)
    _scope_check(world, "--base")


def _step(world: dict[str, Any]) -> dict[str, Any]:
    steps = [step for step in world["gate"]["steps"] if step["name"] == "scope-check"]
    assert steps, world["gate"]
    step: dict[str, Any] = steps[0]
    return step


def _outside(findings: list[dict[str, Any]]) -> frozenset[str]:
    return frozenset(location["file"] for finding in findings for location in finding["locations"])


@then("no path of the parent branch is reported outside the axes")
def _none_of_the_parent_s(world: dict[str, Any]) -> None:
    step = _step(world)
    assert step["status"] == "PASS", step
    assert not (_outside(step["findings"]) & _PARENT_FILES), step


@then("the scope-check line names the merge-base with the parent branch")
def _names_the_merge_base(world: dict[str, Any]) -> None:
    summary = _step(world)["summary"]
    assert f"the merge-base with {_PARENT}" in summary, summary


@then("it says 2 files were attributed to the parent branch")
def _counts_the_parent_s(world: dict[str, Any]) -> None:
    summary = _step(world)["summary"]
    assert "2 file(s) attributed to the parent branch" in summary, summary


@then("the ownership report's base is the base the scope-check line names")
def _ownership_base(world: dict[str, Any]) -> None:
    base = world["gate"]["ownership"]["base"]
    assert base, world["gate"]["ownership"]
    assert git(world["root"], "rev-parse", base) == git(
        world["root"], "merge-base", "HEAD", _PARENT
    )
    assert f"against {base}" in _step(world)["summary"]


@then("the parent branch's 2 files are reported outside the axes")
def _parent_s_again(world: dict[str, Any]) -> None:
    paths = frozenset(finding["path"] for finding in world["scope"]["findings"])
    assert paths == _PARENT_FILES, world["scope"]


@then("the header says the base was named by hand")
def _named_by_hand(world: dict[str, Any]) -> None:
    assert world["scope"]["base"]["kind"] == "explicit", world["scope"]
    assert "main (named by the caller" in world["human"], world["human"]


@then("the scope-check step judged the work item's paths rather than skipping")
def _judged_in_ci(world: dict[str, Any]) -> None:
    step = _step(world)
    assert step["status"] == "PASS", step
    assert f"the axes {_WORK_ITEM} declares" in step["summary"], step


@then("the header names the work item the merge request's branch names")
def _names_the_work_item(world: dict[str, Any]) -> None:
    assert world["scope"]["checked"], world["scope"]
    assert world["scope"]["work_item"] == _WORK_ITEM
    assert f"Declared axes ({_WORK_ITEM}, against " in world["human"], world["human"]
