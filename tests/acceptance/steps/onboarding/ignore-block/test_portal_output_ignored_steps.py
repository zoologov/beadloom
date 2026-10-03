"""Step implementations for `onboarding/ignore-block/portal_output_ignored.feature`.

BDL-076 ``beadloom-ujzb.13``. Through the real ``beadloom init --yes`` an adopter
runs first, on a real directory, and git itself is asked whether it ignores the
portal: the claim is about what git does with the file, not about its text.
"""

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING, Any

import pytest
from click.testing import CliRunner
from pytest_bdd import given, parsers, scenarios, then, when

from beadloom.services.cli import main

if TYPE_CHECKING:
    from pathlib import Path

scenarios("../../../onboarding/ignore-block/portal_output_ignored.feature")

#: The line init writes for the portal's default directory, anchored at the project.
_PORTAL_LINE = "/site/"

#: A file `beadloom docs site` writes into its default directory.
_PORTAL_FILE = "site/index.md"

_WINDOWS_IGNORE = b"# build output\r\n/dist/\r\n*.log\r\n"


@pytest.fixture()
def world(tmp_path: Path) -> dict[str, Any]:
    return {"root": tmp_path / "acme-orders"}


def _git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603
        ["git", *args],  # noqa: S607
        cwd=root,
        capture_output=True,
        encoding="utf-8",
        check=False,
    )


def _project(world: dict[str, Any], *, git: bool) -> Path:
    root: Path = world["root"]
    (root / "src" / "orders").mkdir(parents=True)
    (root / "src" / "orders" / "__init__.py").write_text("def place() -> None: ...\n")
    if git:
        assert _git(root, "init", "-q").returncode == 0
    return root


def _ignore_file(world: dict[str, Any]) -> Path:
    path: Path = world["root"] / ".gitignore"
    return path


def _init(world: dict[str, Any], *flags: str) -> None:
    root = world["root"]
    result = CliRunner().invoke(
        main, ["init", "--yes", "--mode", "bootstrap", "--project", str(root), *flags]
    )
    assert result.exit_code == 0, result.output
    world["result"] = result


@given("a git project with source code and no .gitignore")
def _no_ignore(world: dict[str, Any]) -> None:
    _project(world, git=True)


@given("a git project with source code whose .gitignore has Windows line endings")
def _windows_ignore(world: dict[str, Any]) -> None:
    _project(world, git=True)
    _ignore_file(world).write_bytes(_WINDOWS_IGNORE)
    world["before"] = _WINDOWS_IGNORE


@given(parsers.parse('a git project with source code whose .gitignore already ignores "{line}"'))
def _covering_ignore(world: dict[str, Any], line: str) -> None:
    _project(world, git=True)
    _ignore_file(world).write_text(f"{line}\n", encoding="utf-8")
    world["covering"] = line


@given("a project with source code that is not in a git working tree")
def _outside_git(world: dict[str, Any]) -> None:
    root = _project(world, git=False)
    assert _git(root, "rev-parse", "--is-inside-work-tree").returncode != 0


@given("beadloom init has run once")
def _init_once(world: dict[str, Any]) -> None:
    _init(world)
    world["first"] = _ignore_file(world).read_bytes()


@when("beadloom init runs")
def _run_init(world: dict[str, Any]) -> None:
    _init(world)


@when("beadloom init runs again over the first")
def _run_init_again(world: dict[str, Any]) -> None:
    _init(world, "--force")


@then("git ignores a file the portal would write")
def _portal_ignored(world: dict[str, Any]) -> None:
    root = world["root"]
    target = root / _PORTAL_FILE
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("# the portal\n", encoding="utf-8")
    assert _git(root, "check-ignore", "-q", _PORTAL_FILE).returncode == 0


@then("the .gitignore names the portal directory on one line")
def _one_line(world: dict[str, Any]) -> None:
    lines = _ignore_file(world).read_text(encoding="utf-8").splitlines()
    assert lines.count(_PORTAL_LINE) == 1


@then("every line the .gitignore held before is still in it, in order")
def _kept(world: dict[str, Any]) -> None:
    assert _ignore_file(world).read_bytes().startswith(world["before"])


@then("every line of the .gitignore ends with a Windows line ending")
def _crlf(world: dict[str, Any]) -> None:
    body = _ignore_file(world).read_bytes()
    assert body.endswith(b"\r\n")
    assert body.count(b"\n") == body.count(b"\r\n")


@then("the portal line was not added")
def _not_added(world: dict[str, Any]) -> None:
    lines = _ignore_file(world).read_text(encoding="utf-8").splitlines()
    assert _PORTAL_LINE not in lines
    assert lines.count(world["covering"]) == 1


@then("the .gitignore is byte for byte the one the first init left")
def _same_bytes(world: dict[str, Any]) -> None:
    assert _ignore_file(world).read_bytes() == world["first"]


@then("no .gitignore was written")
def _no_file(world: dict[str, Any]) -> None:
    assert not _ignore_file(world).exists()
