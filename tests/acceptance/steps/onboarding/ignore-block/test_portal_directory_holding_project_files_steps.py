"""Steps for `onboarding/ignore-block/portal_directory_holding_project_files.feature`.

BDL-076 R2 finding 5, fixed by ``beadloom-ujzb.19``. Through the real ``beadloom init
--yes`` on a real git repository, and git itself is asked whether a new file under
``site/`` is ignored: the harm the finding measured was a file git no longer shows.
"""

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING, Any

import pytest
from click.testing import CliRunner
from pytest_bdd import given, scenarios, then, when

from beadloom.services.cli import main

if TYPE_CHECKING:
    from pathlib import Path

scenarios("../../../onboarding/ignore-block/portal_directory_holding_project_files.feature")

#: The line init writes for the portal's default directory.
_PORTAL_LINE = "/site/"


@pytest.fixture()
def world(tmp_path: Path) -> dict[str, Any]:
    return {"root": tmp_path / "acme-web"}


def _git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603
        [  # noqa: S607
            "git",
            "-c",
            "user.name=t",
            "-c",
            "user.email=t@example.invalid",
            *args,
        ],
        cwd=root,
        capture_output=True,
        encoding="utf-8",
        check=False,
    )


def _project(world: dict[str, Any]) -> Path:
    root: Path = world["root"]
    (root / "src" / "orders").mkdir(parents=True)
    (root / "src" / "orders" / "__init__.py").write_text("def place() -> None: ...\n")
    (root / "site").mkdir()
    (root / "site" / "index.html").write_text("<h1>Acme</h1>\n", encoding="utf-8")
    assert _git(root, "init", "-q").returncode == 0
    return root


@given("a git project whose site folder holds a committed file")
def _committed_site(world: dict[str, Any]) -> None:
    root = _project(world)
    assert _git(root, "add", "-A").returncode == 0
    assert _git(root, "commit", "-q", "-m", "site").returncode == 0


@given("a git project whose site folder holds a file that is not committed yet")
def _uncommitted_site(world: dict[str, Any]) -> None:
    _project(world)


@when("beadloom init runs")
def _run_init(world: dict[str, Any]) -> None:
    root = world["root"]
    result = CliRunner().invoke(
        main, ["init", "--yes", "--mode", "bootstrap", "--project", str(root)]
    )
    assert result.exit_code == 0, result.output
    world["output"] = result.output


@then("the portal line was not added")
def _not_added(world: dict[str, Any]) -> None:
    ignore = world["root"] / ".gitignore"
    lines = ignore.read_text(encoding="utf-8").splitlines() if ignore.is_file() else []
    assert _PORTAL_LINE not in lines


@then("git does not ignore a new file in the site folder")
def _visible(world: dict[str, Any]) -> None:
    root = world["root"]
    (root / "site" / "about.html").write_text("<h1>About</h1>\n", encoding="utf-8")
    assert _git(root, "check-ignore", "-q", "site/about.html").returncode == 1
    status = _git(root, "status", "--porcelain", "--untracked-files=all").stdout
    assert "site/about.html" in status


@then("init says the site folder holds a file tracked by git and names --out")
def _says_tracked(world: dict[str, Any]) -> None:
    output = world["output"]
    assert "Not ignored: /site/" in output
    assert "1 file tracked by git" in output
    assert "--out" in output


@then("init names --out")
def _names_out(world: dict[str, Any]) -> None:
    output = world["output"]
    assert "Not ignored: /site/" in output
    assert "--out" in output
