"""Step implementations for the commit-gate scope suite (BDL-061 S6, BDL-UX #118).

Against a real git repository and the real CLI, deliberately. The whole subject
of these scenarios is what ``git`` reports about an index, so a double would
prove the double's contract and nothing about the defect (FAKES PROVE FAKES).

The module is named ``test_*`` so default pytest collection picks the scenarios
up — the acceptance suite runs inside ``uv run pytest``, not beside it.
"""

from __future__ import annotations

import json
import subprocess
from typing import TYPE_CHECKING, Any

import pytest
import yaml
from click.testing import CliRunner
from pytest_bdd import given, scenarios, then, when

from beadloom.application.reindex import reindex
from beadloom.services.cli import main

if TYPE_CHECKING:
    from pathlib import Path

scenarios("../features/commit_scope.feature")


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)  # noqa: S603, S607


def _write(root: Path, rel: str, text: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


@pytest.fixture()
def world(tmp_path: Path) -> dict[str, Any]:
    """A real git repository holding two independent doc-code pairs, committed."""
    root = tmp_path / "proj"
    root.mkdir()
    _write(
        root,
        ".beadloom/_graph/graph.yml",
        yaml.dump(
            {
                "nodes": [
                    {
                        "ref_id": "alpha",
                        "kind": "feature",
                        "summary": "alpha",
                        "source": "src/alpha.py",
                        "docs": ["alpha.md"],
                    },
                    {
                        "ref_id": "beta",
                        "kind": "feature",
                        "summary": "beta",
                        "source": "src/beta.py",
                        "docs": ["beta.md"],
                    },
                ]
            }
        ),
    )
    for ref in ("alpha", "beta"):
        _write(root, f"docs/{ref}.md", f"# {ref}\n\nWhat {ref} does.\n")
        _write(root, f"src/{ref}.py", f"# beadloom:feature={ref}\ndef {ref}():\n    pass\n")
    reindex(root)
    _git(root, "init", "-q", "-b", "main")
    _git(root, "config", "user.email", "test@example.invalid")
    _git(root, "config", "user.name", "Test")
    _write(root, ".gitignore", ".beadloom/beadloom.db\n")
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "baseline")
    return {"root": root, "result": None}


def _stale(world: dict[str, Any], ref: str, *, stage: bool) -> None:
    root = world["root"]
    body = f"# beadloom:feature={ref}\ndef {ref}(new_arg):\n    return new_arg\n"
    _write(root, f"src/{ref}.py", body)
    if stage:
        _git(root, "add", f"src/{ref}.py")


@given("a project with a stale doc pair whose code file is staged")
def given_staged_stale(world: dict[str, Any]) -> None:
    _stale(world, "alpha", stage=True)


@given("a second stale doc pair whose code file is modified but not staged")
def given_unstaged_stale(world: dict[str, Any]) -> None:
    _stale(world, "beta", stage=False)


@given("a project with a stale doc pair whose code file is modified but not staged")
def given_only_unstaged_stale(world: dict[str, Any]) -> None:
    _stale(world, "beta", stage=False)


@when("the doc-freshness check is scoped to what the commit stages")
def when_scoped(world: dict[str, Any]) -> None:
    world["result"] = CliRunner().invoke(
        main,
        ["sync-check", "--staged", "--json", "--project", str(world["root"])],
    )
    world["human"] = CliRunner().invoke(
        main, ["sync-check", "--staged", "--project", str(world["root"])]
    )


def _payload(world: dict[str, Any]) -> dict[str, Any]:
    return json.loads(world["result"].output)


@then("the check reports the staged pair as stale")
def then_staged_stale(world: dict[str, Any]) -> None:
    stale = [p for p in _payload(world)["pairs"] if p["status"] == "stale"]
    assert [p["ref_id"] for p in stale] == ["alpha"]


@then("the check does not report the unstaged pair as stale")
def then_unstaged_not_stale(world: dict[str, Any]) -> None:
    assert all(p["ref_id"] != "beta" for p in _payload(world)["pairs"])


@then("the check states the number of pairs it did not check")
def then_states_not_checked(world: dict[str, Any]) -> None:
    payload = _payload(world)
    assert payload["summary"]["not_checked_outside_commit"] >= 1
    assert "were not checked" in world["human"].output


@then("the check reports no stale pair")
def then_no_stale(world: dict[str, Any]) -> None:
    assert _payload(world)["summary"]["stale"] == 0
    assert world["result"].exit_code == 0
