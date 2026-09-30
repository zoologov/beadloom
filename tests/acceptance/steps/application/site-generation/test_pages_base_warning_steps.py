"""Step implementations for `application/site-generation/pages_base_warning.feature`.

BDL-076 ``beadloom-ujzb.13``. Through the real ``beadloom docs site`` command,
against a real project with a real git remote: the warning is read from stderr,
where an adopter meets it, and the exit code is the command's own.
"""

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING, Any

import pytest
from click.testing import CliRunner
from pytest_bdd import given, parsers, scenarios, then, when

from beadloom.services.cli import main
from tests.support.tiered_project import write_zoned_import_project

if TYPE_CHECKING:
    from pathlib import Path

scenarios("../../../application/site-generation/pages_base_warning.feature")

#: What every base warning says, whatever the repository is called.
_WARNING = "site.base"


@pytest.fixture()
def world(tmp_path: Path) -> dict[str, Any]:
    return {"root": tmp_path / "acme-orders"}


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)  # noqa: S603, S607


@given("a project that declares no site base")
def _no_base(world: dict[str, Any]) -> None:
    write_zoned_import_project(world["root"])


@given(parsers.parse('a project that declares the site base "{base}"'))
def _declared(world: dict[str, Any], base: str) -> None:
    project = write_zoned_import_project(world["root"])
    config = project / ".beadloom" / "config.yml"
    config.write_text(config.read_text(encoding="utf-8") + f"site:\n  base: {base}\n")


@given(parsers.parse('its origin remote is "{remote}"'))
def _remote(world: dict[str, Any], remote: str) -> None:
    _git(world["root"], "init", "-q")
    _git(world["root"], "remote", "add", "origin", remote)


@given("it is a git repository with no remote")
def _no_remote(world: dict[str, Any]) -> None:
    _git(world["root"], "init", "-q")


@when("the site is generated")
def _generate(world: dict[str, Any]) -> None:
    world["result"] = CliRunner().invoke(main, ["docs", "site", "--project", str(world["root"])])


@then("the generation succeeds")
def _succeeds(world: dict[str, Any]) -> None:
    result = world["result"]
    assert result.exit_code == 0, result.output


@then(parsers.parse('the generation warns on stderr that the base should be "{base}"'))
def _warns(world: dict[str, Any], base: str) -> None:
    assert f"site.base: {base}" in world["result"].stderr


@then("the warning is not in the standard output")
def _not_stdout(world: dict[str, Any]) -> None:
    assert _WARNING not in world["result"].stdout


@then("the generation gives no base warning")
def _silent(world: dict[str, Any]) -> None:
    assert _WARNING not in world["result"].output
