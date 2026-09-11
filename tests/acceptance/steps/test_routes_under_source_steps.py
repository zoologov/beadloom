"""Step implementations for `features/routes_under_source.feature`.

BDL-069, `beadloom-rqma.4`. Every step runs the real command against a git repository
built in a temporary directory: `init`, `reindex` and `docs polish` through the CLI,
so the routes compared are the ones an agent is handed, read from the `nodes.extra`
the reindex wrote rather than from one written by hand.

**The expected routes are written down here, not derived.** A list checked against
what the index returns would agree with any attribution, including the one that gave
a node its sibling's routes, so each module declares what it serves and the
assertions read that declaration.

**The sibling's route is extracted, or the scenario proves nothing.** A node that
names only its own routes is indistinguishable from a correct one when the sibling's
route never reached the index, so the index is asked for it first.

The fixtures are built here rather than imported from `tests.adopter_project`, for
the reason `test_bootstrap_self_consistency_steps` records: the acceptance suite is
copied out of the repository and run standalone, where the `tests` package is not
importable.
"""

from __future__ import annotations

import json
import sqlite3
import subprocess
from typing import TYPE_CHECKING, Any

import pytest
import yaml
from click.testing import CliRunner
from pytest_bdd import given, scenarios, then, when

from beadloom.services.cli import main

if TYPE_CHECKING:
    from pathlib import Path

scenarios("../features/routes_under_source.feature")

#: The project name in the manifest; no package is called this.
PROJECT = "myapp"

#: The package whose node is polished, and the one module a single-file node takes.
PACKAGE = "ledger"
MODULE = "src/ledger/api.py"
MODULE_NODE = "recording"

_FASTAPI = "from fastapi import FastAPI\n\napp = FastAPI()\n\n\n"
_RECORD = '@app.post("/record")\ndef record() -> None:\n    pass\n'
_REPLAY = '@app.get("/replay")\ndef replay() -> None:\n    pass\n'

#: Every file of the project, by path under the project root. `ledger_archive/`
#: starts with the characters `src/ledger` and is not inside `src/ledger/`.
FILES: dict[str, str] = {
    "src/ledger/__init__.py": '"""The ledger."""\n',
    MODULE: _FASTAPI + _RECORD,
    "src/ledger/core.py": "def balance() -> int:\n    return 0\n",
    "src/ledger_archive/__init__.py": '"""The archive."""\n',
    "src/ledger_archive/api.py": _FASTAPI + _REPLAY,
}

#: The routes each source serves, as (method, path, file).
SERVED: dict[str, set[tuple[str, str, str]]] = {
    "src/ledger/": {("POST", "/record", MODULE)},
    MODULE: {("POST", "/record", MODULE)},
}
#: The route the sibling serves, which the index must carry for a scenario to bite.
SIBLING_ROUTE = ("GET", "/replay", "src/ledger_archive/api.py")


@pytest.fixture()
def world() -> dict[str, Any]:
    return {}


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)  # noqa: S603, S607


def _cli(project: Path, monkeypatch: pytest.MonkeyPatch, *args: str) -> str:
    monkeypatch.chdir(project)
    result = CliRunner().invoke(main, [*args, "--project", str(project)])
    assert result.exit_code == 0, result.output
    return result.output


def _routes(raw: list[dict[str, Any]]) -> set[tuple[str, str, str]]:
    return {(str(r["method"]), str(r["path"]), str(r["file"])) for r in raw}


def _every_stored_route(project: Path) -> set[tuple[str, str, str]]:
    with sqlite3.connect(project / ".beadloom" / "beadloom.db") as conn:
        extras = [json.loads(row[0] or "{}") for row in conn.execute("SELECT extra FROM nodes")]
    return {route for extra in extras for route in _routes(extra.get("routes", []))}


def _graph_file_with_nodes(project: Path) -> Path:
    for path in sorted((project / ".beadloom" / "_graph").glob("*.yml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if data.get("nodes"):
            return path
    raise AssertionError("init wrote no graph file holding nodes")


def _node_source(project: Path, ref_id: str) -> str | None:
    data = yaml.safe_load(_graph_file_with_nodes(project).read_text(encoding="utf-8"))
    for node in data["nodes"]:
        if node["ref_id"] == ref_id:
            return str(node.get("source") or "")
    return None


@given(
    "a git repository holding a package and a sibling package whose name starts with "
    "the package's name, each serving one route"
)
def _given_a_repository(world: dict[str, Any], tmp_path: Path) -> None:
    project = tmp_path / PROJECT
    for relative, text in FILES.items():
        path = project / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    (project / "pyproject.toml").write_text(
        f'[project]\nname = "{PROJECT}"\nversion = "0.1.0"\n', encoding="utf-8"
    )
    _git(project, "init", "-q", "-b", "main")
    _git(project, "config", "user.email", "test@example.invalid")
    _git(project, "config", "user.name", "Test")
    _git(project, "add", "-A")
    _git(project, "commit", "-q", "-m", "the code before beadloom")
    world["project"] = project


@given("beadloom init has been run without prompts on it and the index rebuilt")
def _given_init_and_reindex(world: dict[str, Any], monkeypatch: pytest.MonkeyPatch) -> None:
    project = world["project"]
    _cli(project, monkeypatch, "init", "--yes", "--mode", "bootstrap")
    _cli(project, monkeypatch, "reindex")
    # Anti-vacuity: the node is the directory, and the sibling's route was extracted.
    assert _node_source(project, PACKAGE) == "src/ledger/"
    assert SIBLING_ROUTE in _every_stored_route(project)


@given("a node whose source is the package's route module has been declared and the index rebuilt")
def _given_a_single_file_node(world: dict[str, Any], monkeypatch: pytest.MonkeyPatch) -> None:
    project = world["project"]
    graph_file = _graph_file_with_nodes(project)
    data = yaml.safe_load(graph_file.read_text(encoding="utf-8"))
    data["nodes"].append(
        {"ref_id": MODULE_NODE, "kind": "feature", "source": MODULE, "summary": "Recording"}
    )
    data.setdefault("edges", []).append({"src": MODULE_NODE, "dst": PACKAGE, "kind": "part_of"})
    graph_file.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    _cli(project, monkeypatch, "reindex")
    assert _node_source(project, MODULE_NODE) == MODULE


def _polish(world: dict[str, Any], monkeypatch: pytest.MonkeyPatch, ref_id: str) -> None:
    output = _cli(
        world["project"], monkeypatch, "docs", "polish", "--ref-id", ref_id, "--format", "json"
    )
    (node,) = json.loads(output)["nodes"]
    world["routes"] = _routes(node.get("routes") or [])


@when("beadloom docs polish is asked for the package's node")
def _when_polish_the_package(world: dict[str, Any], monkeypatch: pytest.MonkeyPatch) -> None:
    _polish(world, monkeypatch, PACKAGE)


@when("beadloom docs polish is asked for that node")
def _when_polish_the_module(world: dict[str, Any], monkeypatch: pytest.MonkeyPatch) -> None:
    _polish(world, monkeypatch, MODULE_NODE)


@then("the routes it names are the routes the package serves and no others")
def _then_the_package_routes(world: dict[str, Any]) -> None:
    assert world["routes"] == SERVED["src/ledger/"], sorted(world["routes"])


@then("the routes it names are the routes that module serves and no others")
def _then_the_module_routes(world: dict[str, Any]) -> None:
    assert world["routes"] == SERVED[MODULE], sorted(world["routes"])
