"""Step implementations for `the_source_link_of_an_unpublished_commit.feature`.

BDL-080 S4c (``beadloom-e1xo``), BDL-UX #307. Against a real project in a real git
repository, the real reindex and the real site generator, and the real ``docs site``
command for the warning. The remote is never contacted: a step writes the
remote-tracking refs a fetch would have written, which is all the generator reads.
"""

from __future__ import annotations

import json
import sqlite3
import subprocess
from typing import TYPE_CHECKING, Any

import pytest
from click.testing import CliRunner
from pytest_bdd import given, parsers, scenarios, then, when

from beadloom.application.reindex import reindex
from beadloom.application.site.generate import generate_site
from beadloom.services.cli import main
from tests.support.tiered_project import write_zoned_import_project

if TYPE_CHECKING:
    from pathlib import Path

scenarios("../../../application/site-generation/the_source_link_of_an_unpublished_commit.feature")

#: The site's published copy of the architecture view, under the site root.
_VIEW_DATA = "public/architecture.data.json"
#: A fixed instant for the one wall-clock read `generate_site` makes.
_NOW = "2026-10-10T00:00:00+00:00"
#: Every unpublished-commit warning says this, whatever it links instead.
_UNPUBLISHED = "on no remote branch"
_IDENTITY = ("-c", "user.name=Shop Team", "-c", "user.email=team@example.invalid")


@pytest.fixture()
def world(tmp_path: Path) -> dict[str, Any]:
    return {"root": tmp_path / "shop", "site": tmp_path / "site"}


def _git(cwd: Path, *args: str) -> str:
    result = subprocess.run(  # noqa: S603 - fixed git arguments written by this step
        ["git", *args],  # noqa: S607 - the scenario drives the git on PATH, as the generator does
        cwd=cwd,
        capture_output=True,
        encoding="utf-8",
        check=True,
    )
    return result.stdout.strip()


def _committed_twice(world: dict[str, Any], branch: str) -> Path:
    project = write_zoned_import_project(world["root"])
    _git(project, "init", "-q", "-b", branch)
    _git(project, *_IDENTITY, "commit", "-q", "--allow-empty", "-m", "the first commit")
    world["first"] = _git(project, "rev-parse", "HEAD")
    _git(project, "add", "-A")
    _git(project, *_IDENTITY, "commit", "-q", "-m", "the shop")
    world["commit"] = _git(project, "rev-parse", "HEAD")
    world["project"] = project
    return project


@given(
    parsers.parse('a project committed twice on the branch "{branch}" whose origin is "{remote}"')
)
def _with_origin(world: dict[str, Any], branch: str, remote: str) -> None:
    project = _committed_twice(world, branch)
    _git(project, "remote", "add", "origin", remote)
    reindex(project)


@given(parsers.parse('a project committed twice on the branch "{branch}" with no remote'))
def _without_remote(world: dict[str, Any], branch: str) -> None:
    reindex(_committed_twice(world, branch))


def _remote_branch(world: dict[str, Any], branch: str, which: str) -> None:
    _git(world["project"], "update-ref", f"refs/remotes/origin/{branch}", world[which])


@given(parsers.parse('the remote\'s branch "{branch}" holds the last commit'))
def _holds_last(world: dict[str, Any], branch: str) -> None:
    _remote_branch(world, branch, "commit")


@given(parsers.parse('the remote\'s branch "{branch}" holds the first commit'))
def _holds_first(world: dict[str, Any], branch: str) -> None:
    _remote_branch(world, branch, "first")


@given(
    parsers.parse(
        'the branch "{branch}" tracks the remote\'s branch "{upstream}", '
        "which holds the first commit"
    )
)
def _tracks(world: dict[str, Any], branch: str, upstream: str) -> None:
    _remote_branch(world, upstream, "first")
    _git(world["project"], "config", f"branch.{branch}.remote", "origin")
    _git(world["project"], "config", f"branch.{branch}.merge", f"refs/heads/{upstream}")


@given(parsers.parse('the remote\'s default branch is "{branch}"'))
def _default_branch(world: dict[str, Any], branch: str) -> None:
    _git(
        world["project"],
        "symbolic-ref",
        "refs/remotes/origin/HEAD",
        f"refs/remotes/origin/{branch}",
    )


@when("the site is generated for the project")
def _generate(world: dict[str, Any]) -> None:
    project = world["project"]
    conn = sqlite3.connect(project / ".beadloom" / "beadloom.db")
    conn.row_factory = sqlite3.Row
    try:
        generate_site(conn, world["site"], project_root=project, now_ts=_NOW)
    finally:
        conn.close()
    data = json.loads((world["site"] / _VIEW_DATA).read_text(encoding="utf-8"))
    world["data"] = data
    world["nodes"] = {str(node["id"]): node for node in data["nodes"]}


@when("docs site generates the portal")
def _docs_site(world: dict[str, Any]) -> None:
    world["result"] = CliRunner().invoke(
        main,
        ["docs", "site", "--project", str(world["project"]), "--out", str(world["site"])],
    )


def _with_commit(world: dict[str, Any], text: str) -> str:
    return text.replace("{commit}", world["commit"])


@then(parsers.parse('the node "{ref}" links its source to "{link}"'))
def _source_link(world: dict[str, Any], ref: str, link: str) -> None:
    assert world["nodes"][ref]["source_url"] == _with_commit(world, link)


@then(parsers.parse('the node "{ref}" has no source link'))
def _no_source_link(world: dict[str, Any], ref: str) -> None:
    node = world["nodes"][ref]
    assert node["source"], "the scenario needs a node with a source"
    assert node["source_url"] == ""


@then(
    parsers.parse('the data file\'s source ref is the last commit, linked at "{linked}", {state}')
)
def _source_ref(world: dict[str, Any], linked: str, state: str) -> None:
    assert world["data"]["source_ref"] == {
        "commit": world["commit"],
        "linked": _with_commit(world, linked),
        "pushed": state == "pushed",
    }


@then("the data file carries no source ref")
def _no_source_ref(world: dict[str, Any]) -> None:
    assert "source_ref" not in world["data"]


@then("docs site succeeds")
def _succeeds(world: dict[str, Any]) -> None:
    result = world["result"]
    assert result.exit_code == 0, result.output


@then(
    parsers.parse(
        'docs site warns on stderr that the links point at "{linked}" instead of the last commit'
    )
)
def _warns_instead(world: dict[str, Any], linked: str) -> None:
    stderr = world["result"].stderr
    assert _UNPUBLISHED in stderr
    assert world["commit"][:12] in stderr
    assert f"point at {linked}" in stderr


@then(
    parsers.parse(
        'docs site warns on stderr that the links point at the last commit and names "{fix}"'
    )
)
def _warns_kept(world: dict[str, Any], fix: str) -> None:
    stderr = world["result"].stderr
    assert _UNPUBLISHED in stderr
    assert f"point at {world['commit'][:12]}" in stderr
    assert fix in stderr


@then("the warning is not in docs site's standard output")
def _not_in_stdout(world: dict[str, Any]) -> None:
    assert _UNPUBLISHED not in world["result"].stdout


@then("docs site gives no unpublished-commit warning")
def _no_warning(world: dict[str, Any]) -> None:
    assert _UNPUBLISHED not in world["result"].output
