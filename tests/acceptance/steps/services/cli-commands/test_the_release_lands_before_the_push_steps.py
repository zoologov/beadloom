"""Step implementations for a push that does not land the hold of the bead it lands.

BDL-083 S2g (``beadloom-89gm``). Thin: each scenario commits an export of the shape bd
1.0.4 writes (measured in an isolated rig: a held slot reads ``status: in_progress``,
``metadata.holder`` and ``labels: [gt:slot]``), installs the hooks ``install-hooks``
writes, and runs the pre-push hook as git would — with the pushed ref on its input.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from beadloom.application.landing_slot import LANDING_SEQUENCE
from tests.support.committed_project import commit_project, git
from tests.support.hook_runner import install_hooks, run_hook, tools

if TYPE_CHECKING:
    from pathlib import Path

scenarios("../../../services/cli-commands/the_release_lands_before_the_push.feature")

_ZERO = "0" * 40
_IDENTITY = ("-c", "user.name=Test Committer", "-c", "user.email=committer@example.invalid")


@pytest.fixture()
def world(tmp_path: Path) -> dict[str, Any]:
    """One mutable bag the steps share, kept explicit rather than global."""
    return {"workdir": tmp_path, "root": None, "tip": None, "run": None}


@given("a repository with the composed hooks installed")
def _a_repository(world: dict[str, Any]) -> None:
    root = world["workdir"] / "repo"
    (root / ".beadloom").mkdir(parents=True)
    (root / "README.md").write_text("a repository\n", encoding="utf-8")
    commit_project(root)
    install_hooks(root)
    world["root"] = root


def _commit_export(world: dict[str, Any], bead: str, holder: str | None) -> None:
    slot: dict[str, Any] = {
        "_type": "issue",
        "id": "rig-merge-slot",
        "title": "Merge Slot",
        "status": "open",
        "labels": ["gt:slot"],
    }
    if holder is not None:
        slot.update(status="in_progress", metadata={"holder": holder})
    root = world["root"]
    (root / ".beads").mkdir(exist_ok=True)
    rows = [{"_type": "issue", "id": bead, "status": "in_progress"}, slot]
    (root / ".beads" / "issues.jsonl").write_text(
        "".join(json.dumps(row, separators=(",", ":")) + "\n" for row in rows),
        encoding="utf-8",
    )
    git(root, "add", ".beads/issues.jsonl")
    git(root, *_IDENTITY, "commit", "-q", "--no-verify", "-m", f"feat: the work\n\nBead: {bead}")
    world["tip"] = git(root, "rev-parse", "HEAD")


@given(
    parsers.parse('a commit bound to "{bead}" whose export holds the merge slot for "{holder}"')
)
def _held(world: dict[str, Any], bead: str, holder: str) -> None:
    _commit_export(world, bead, holder)


@given(parsers.parse('a commit bound to "{bead}" whose export shows the merge slot free'))
def _free(world: dict[str, Any], bead: str) -> None:
    _commit_export(world, bead, None)


@when("the pre-push hook runs for that commit with beadloom on its PATH")
def _push(world: dict[str, Any]) -> None:
    pushed = f"refs/heads/f {world['tip']} refs/heads/f {_ZERO}\n"
    path = tools(world["workdir"], beadloom=True)
    world["run"] = run_hook(world["root"], "pre-push", path, stdin=pushed)


def _said(world: dict[str, Any]) -> str:
    run = world["run"]
    return f"{run.stdout}{run.stderr}"


@then("the hook exits non-zero")
def _non_zero(world: dict[str, Any]) -> None:
    assert world["run"].returncode != 0, _said(world)


@then("the hook names the sequence acquire, commit, release, export, push")
def _names_the_sequence(world: dict[str, Any]) -> None:
    assert LANDING_SEQUENCE in _said(world), _said(world)


@then(parsers.parse('the hook names the release "{release}"'))
def _names_the_release(world: dict[str, Any], release: str) -> None:
    assert release in _said(world), _said(world)


@then("the Gate did not run")
def _gate_not_run(world: dict[str, Any]) -> None:
    assert "Running Beadloom Gate" not in _said(world), _said(world)


@then("the Gate ran")
def _gate_ran(world: dict[str, Any]) -> None:
    assert "Running Beadloom Gate" in _said(world), _said(world)


@then("the hook says the landing lock is clean")
def _clean(world: dict[str, Any]) -> None:
    assert "Landing lock: clean" in _said(world), _said(world)


@then(parsers.parse('the hook names "{holder}" as the holder'))
def _names_the_holder(world: dict[str, Any], holder: str) -> None:
    assert holder in _said(world), _said(world)
