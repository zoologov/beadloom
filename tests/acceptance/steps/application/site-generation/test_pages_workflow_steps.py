"""Step implementations for `application/site-generation/pages_workflow.feature`.

BDL-076 B2 (``beadloom-qki6``). Through the real ``beadloom docs site`` command,
against a real project directory and its real reindex, with the scaffold the
installed package ships: the workflow is read from the path an adopter commits.
"""

from __future__ import annotations

import json
import re
import subprocess
from typing import TYPE_CHECKING, Any

import pytest
import yaml
from click.testing import CliRunner
from pytest_bdd import given, parsers, scenarios, then, when

from beadloom.application.site.pages_workflow import PAGES_WORKFLOW_PATH, node_major_of
from beadloom.application.site.scaffold import shipped_files
from beadloom.services.cli import main
from tests.support.tiered_project import write_zoned_import_project

if TYPE_CHECKING:
    from pathlib import Path

    from click.testing import Result

scenarios("../../../application/site-generation/pages_workflow.feature")

_HAND_EDIT = "# the orders team deploys from its own runner\n"


@pytest.fixture()
def world(tmp_path: Path) -> dict[str, Any]:
    return {"root": tmp_path / "acme-orders"}


def _workflow_path(world: dict[str, Any]) -> Path:
    path: Path = world["root"] / PAGES_WORKFLOW_PATH
    return path


def _workflow(world: dict[str, Any]) -> dict[Any, Any]:
    data = yaml.safe_load(_workflow_path(world).read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


def _build_steps(world: dict[str, Any]) -> list[dict[str, Any]]:
    steps: list[dict[str, Any]] = _workflow(world)["jobs"]["build"]["steps"]
    return steps


def _generate(world: dict[str, Any], *flags: str) -> Result:
    result = CliRunner().invoke(main, ["docs", "site", "--project", str(world["root"]), *flags])
    assert result.exit_code == 0, result.output
    world["result"] = result
    return result


@given(parsers.parse('a project that declares the site base "{base}"'))
def _declared(world: dict[str, Any], base: str) -> None:
    project = write_zoned_import_project(world["root"])
    config = project / ".beadloom" / "config.yml"
    block = f"site:\n  base: '{base}'\n"
    config.write_text(config.read_text(encoding="utf-8") + block, encoding="utf-8")


@given("the site has been generated with the Pages workflow once")
def _generated_once(world: dict[str, Any]) -> None:
    _generate(world, "--pages-workflow")
    world["first"] = _workflow_path(world).read_bytes()


@given("the Pages workflow has been edited by hand")
def _edit(world: dict[str, Any]) -> None:
    path = _workflow_path(world)
    edited = path.read_text(encoding="utf-8") + _HAND_EDIT
    path.write_text(edited, encoding="utf-8")
    world["edited"] = edited


@when("the site is generated with the Pages workflow")
def _generate_with_workflow(world: dict[str, Any]) -> None:
    _generate(world, "--pages-workflow")


@when("the site is generated")
def _generate_plain(world: dict[str, Any]) -> None:
    _generate(world)


@when("the site is generated outside the project with the Pages workflow")
def _generate_outside(world: dict[str, Any]) -> None:
    world["outside"] = world["root"].parent / "elsewhere"
    world["result"] = CliRunner().invoke(
        main,
        [
            "docs",
            "site",
            "--project",
            str(world["root"]),
            "--out",
            str(world["outside"]),
            "--pages-workflow",
        ],
    )


@then("the generation is refused, naming --out")
def _refused(world: dict[str, Any]) -> None:
    result = world["result"]
    assert result.exit_code == 1
    assert "--out" in result.stderr


@then("no portal was written outside the project")
def _no_portal(world: dict[str, Any]) -> None:
    assert not world["outside"].exists()


@then("the Pages workflow parses as YAML")
def _parses(world: dict[str, Any]) -> None:
    assert set(_workflow(world)["jobs"]) == {"build", "deploy"}


@then(parsers.parse('the Pages workflow builds the portal for "{base}"'))
def _base(world: dict[str, Any], base: str) -> None:
    assert _workflow(world)["jobs"]["build"]["env"]["PORTAL_BASE"] == base


@then("the Pages workflow sets up the Node major the portal's package.json declares")
def _node(world: dict[str, Any]) -> None:
    declared = json.loads(shipped_files()["package.json"])["engines"]["node"]
    setup = [
        s for s in _build_steps(world) if str(s.get("uses", "")).startswith("actions/setup-node@")
    ]
    assert len(setup) == 1
    assert str(setup[0]["with"]["node-version"]) == node_major_of(declared)


@then(parsers.parse("the generation names the Pages workflow as {outcome}"))
def _named(world: dict[str, Any], outcome: str) -> None:
    assert f"Pages workflow: {PAGES_WORKFLOW_PATH.as_posix()} {outcome}" in world["result"].stdout


@then("the Pages workflow is byte for byte the one written before")
def _same_bytes(world: dict[str, Any]) -> None:
    assert _workflow_path(world).read_bytes() == world["first"]


@then("the hand edit in the Pages workflow is still on disk")
def _edit_kept(world: dict[str, Any]) -> None:
    assert _workflow_path(world).read_text(encoding="utf-8") == world["edited"]


@then("the generation reports the Pages workflow as kept, edited by hand")
def _edit_reported(world: dict[str, Any]) -> None:
    stderr = world["result"].stderr
    assert PAGES_WORKFLOW_PATH.as_posix() in stderr
    assert "edited by hand" in stderr
    assert "--pages-workflow" in stderr


@then("no Pages workflow was written")
def _nothing(world: dict[str, Any]) -> None:
    assert not _workflow_path(world).exists()
    assert "Pages workflow" not in world["result"].output


_GUARD = "github.ref_type == 'branch' && github.ref_name == github.event.repository.default_branch"
_PINNED = re.compile(r"^[\w.-]+/[\w.-]+@[0-9a-f]{40}$")


def _git(world: dict[str, Any], *args: str) -> None:
    subprocess.run(["git", *args], cwd=world["root"], check=True, capture_output=True)  # noqa: S603, S607


@given(parsers.parse("the project's git records \"{branch}\" as its remote's default branch"))
def _default_branch(world: dict[str, Any], branch: str) -> None:
    _git(world, "init", "-q", "-b", "work")
    _git(world, "add", "-A")
    _git(world, "-c", "user.name=t", "-c", "user.email=t@e", "commit", "-q", "-m", "c")
    _git(world, "update-ref", f"refs/remotes/origin/{branch}", "HEAD")
    _git(world, "symbolic-ref", "refs/remotes/origin/HEAD", f"refs/remotes/origin/{branch}")


@when("the site is generated with the Pages workflow, expecting a refusal")
def _generate_refused(world: dict[str, Any]) -> None:
    world["result"] = CliRunner().invoke(
        main, ["docs", "site", "--project", str(world["root"]), "--pages-workflow"]
    )


@then(parsers.parse('a push starts the Pages workflow only on "{branch}"'))
def _push_branch(world: dict[str, Any], branch: str) -> None:
    # PyYAML reads the bare key `on` as the boolean true; GitHub reads it as `on`.
    assert _workflow(world)[True]["push"] == {"branches": [branch]}


@then("the Pages workflow names no branch")
def _no_branch(world: dict[str, Any]) -> None:
    assert _workflow(world)[True]["push"] is None


@then("the Pages workflow builds only from a branch that is the default, never a tag")
def _guard(world: dict[str, Any]) -> None:
    assert _workflow(world)["jobs"]["build"]["if"] == _GUARD


@then("only the deploy job of the Pages workflow may write Pages or mint a token")
def _permissions(world: dict[str, Any]) -> None:
    workflow = _workflow(world)
    assert workflow["permissions"] == {}
    assert workflow["jobs"]["build"]["permissions"] == {"contents": "read", "pages": "read"}
    assert workflow["jobs"]["deploy"]["permissions"] == {"pages": "write", "id-token": "write"}


@then("every action the Pages workflow uses is pinned by a full commit")
def _pinned(world: dict[str, Any]) -> None:
    uses = [
        str(step["uses"])
        for job in _workflow(world)["jobs"].values()
        for step in job["steps"]
        if "uses" in step
    ]
    assert uses
    assert [use for use in uses if not _PINNED.match(use)] == []


@then(parsers.parse('the generation names "{branch}" as the branch the Pages workflow runs on'))
def _branch_named(world: dict[str, Any], branch: str) -> None:
    assert f"branch {branch}" in world["result"].stdout


@then("the generation says the Pages workflow names no branch, and how to give it one")
def _no_branch_said(world: dict[str, Any]) -> None:
    stderr = world["result"].stderr
    assert "names no branch" in stderr
    assert "git remote set-head origin --auto" in stderr


@then("the generation is refused, naming site.base")
def _refused_base(world: dict[str, Any]) -> None:
    result = world["result"]
    assert result.exit_code == 1
    assert "site.base" in result.stderr


@then("the Pages workflow checks out the full history before it indexes the project")
def _full_history(world: dict[str, Any]) -> None:
    steps = _build_steps(world)
    uses = [str(step.get("uses", "")) for step in steps]
    runs = [str(step.get("run", "")) for step in steps]
    checkout = next(i for i, used in enumerate(uses) if used.startswith("actions/checkout@"))
    indexing = next(i for i, run in enumerate(runs) if run.startswith("beadloom reindex"))
    assert checkout < indexing
    # 0 is "all history" to actions/checkout; its default, 1, is a single commit.
    assert steps[checkout].get("with", {}).get("fetch-depth") == 0, steps[checkout]
