"""Steps for `onboarding/ignore-block/portal_directory_holding_our_own_portal.feature`.

BDL-076, the re-review's finding m4, fixed by ``beadloom-ujzb.24``. Through the real
``beadloom init --yes``, ``beadloom docs site`` and ``beadloom init --yes --force`` on a
real git repository; git itself is asked whether a new file under ``site/`` is ignored.

**FAKES PROVE FAKES.** The portal is the one ``docs site`` writes, not files named like
it, so the scenario holds the scaffold's marker as ``docs site`` writes it.
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

scenarios("../../../onboarding/ignore-block/portal_directory_holding_our_own_portal.feature")

#: The line init writes for the portal's default directory.
_PORTAL_LINE = "/site/"


@pytest.fixture()
def world(tmp_path: Path) -> dict[str, Any]:
    return {"root": tmp_path / "acme-orders"}


def _git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603
        ["git", "-c", "user.name=t", "-c", "user.email=t@example.invalid", *args],  # noqa: S607
        cwd=root,
        capture_output=True,
        encoding="utf-8",
        check=False,
    )


def _beadloom(root: Path, *args: str) -> str:
    result = CliRunner().invoke(main, [*args, "--project", str(root)])
    assert result.exit_code == 0, result.output
    return result.output


def _project_with_a_portal(world: dict[str, Any], *, committed_page: bool) -> None:
    root: Path = world["root"]
    (root / "src" / "orders").mkdir(parents=True)
    (root / "src" / "orders" / "__init__.py").write_text("def place() -> None: ...\n")
    assert _git(root, "init", "-q").returncode == 0
    if committed_page:
        (root / "site").mkdir()
        (root / "site" / "index.html").write_text("<h1>Acme</h1>\n", encoding="utf-8")
        assert _git(root, "add", "site/index.html").returncode == 0
        assert _git(root, "commit", "-q", "-m", "our page").returncode == 0
    _beadloom(root, "init", "--yes")
    _beadloom(root, "docs", "site")
    # The ignore file is the project's: it names no site folder now.
    (root / ".gitignore").write_text("/dist/\n", encoding="utf-8")
    assert (root / "site" / "package.json").is_file()


@given(
    "a git project whose site folder holds the portal beadloom docs site wrote, "
    "and no ignore line for it"
)
def _portal_only(world: dict[str, Any]) -> None:
    _project_with_a_portal(world, committed_page=False)


@given(
    "a git project whose site folder holds a committed file and the portal "
    "beadloom docs site wrote"
)
def _portal_and_a_page(world: dict[str, Any]) -> None:
    _project_with_a_portal(world, committed_page=True)


@when("beadloom init runs again with --force")
def _init_again(world: dict[str, Any]) -> None:
    world["output"] = _beadloom(world["root"], "init", "--yes", "--force")


def _ignore_lines(world: dict[str, Any]) -> list[str]:
    return (world["root"] / ".gitignore").read_text(encoding="utf-8").splitlines()


@then("the portal line was added")
def _added(world: dict[str, Any]) -> None:
    assert _PORTAL_LINE in _ignore_lines(world)


@then("the portal line was not added")
def _not_added(world: dict[str, Any]) -> None:
    assert _PORTAL_LINE not in _ignore_lines(world)


@then("git ignores a new file in the site folder")
def _ignored(world: dict[str, Any]) -> None:
    root = world["root"]
    (root / "site" / "extra.md").write_text("# Extra\n", encoding="utf-8")
    assert _git(root, "check-ignore", "-q", "site/extra.md").returncode == 0


@then("init says it ignored the portal")
def _says_ignored(world: dict[str, Any]) -> None:
    assert "Ignored: /site/ (the portal `beadloom docs site` writes)" in world["output"]


@then("init says the site folder holds files tracked by git")
def _says_tracked(world: dict[str, Any]) -> None:
    output = world["output"]
    assert "Not ignored: /site/" in output
    assert "tracked by git" in output


@then("init makes no node and no scan path of the site folder")
def _not_source(world: dict[str, Any]) -> None:
    root = world["root"]
    config = yaml.safe_load((root / ".beadloom" / "config.yml").read_text(encoding="utf-8"))
    assert not [path for path in config["scan_paths"] if path.split("/")[0] == "site"]
    sources = [
        str(node.get("source") or "")
        for path in sorted((root / ".beadloom" / "_graph").glob("*.yml"))
        for node in (yaml.safe_load(path.read_text(encoding="utf-8")) or {}).get("nodes") or []
    ]
    assert not [source for source in sources if source.startswith("site/")]


@then("init says it did not scan the site folder")
def _says_not_scanned(world: dict[str, Any]) -> None:
    lines = [line for line in world["output"].splitlines() if "Not scanned: site/" in line]
    assert len(lines) == 1, world["output"]
    assert "beadloom docs site" in lines[0]
