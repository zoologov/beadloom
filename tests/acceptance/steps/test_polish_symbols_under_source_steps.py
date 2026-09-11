"""Step implementations for `features/polish_symbols_under_source.feature`.

BDL-069, `beadloom-6rgr`. Every step runs the real command against a git repository
built in a temporary directory: `init`, `reindex` and `docs polish` through the CLI,
so the symbols compared are the ones an agent is handed, read after the index the
reindex built rather than after one written by hand.

**The expected symbols are written down here, not derived.** A list checked against
what the index returns would agree with any index reader, including the one that
took a sibling's rows, so each module declares its names and the assertions read
them from this module.

**Every sibling is indexed, or the scenario proves nothing.** A reader that returns
only the package's symbols is indistinguishable from a correct one when the
siblings' symbols never reached the index, so the index is asked for them first.

The fixtures are built here rather than imported from `tests.adopter_project`, for
the reason `test_bootstrap_self_consistency_steps` records: the acceptance suite is
copied out of the repository and run standalone, where the `tests` package is not
importable.
"""

from __future__ import annotations

import json
import re
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

scenarios("../features/polish_symbols_under_source.feature")

#: The project name in the manifest; no package is called this.
PROJECT = "myapp"

#: The package whose node is polished, and the one module a single-file node takes.
PACKAGE = "ledger"
MODULE = "src/ledger/core.py"
MODULE_NODE = "recording"

#: Every file of the project, by path under the project root. `ledger_archive/`
#: and `ledger_tools.py` both start with the characters `src/ledger`, and neither
#: is inside `src/ledger/`.
FILES: dict[str, str] = {
    "src/ledger/__init__.py": '"""The ledger."""\n',
    "src/ledger/core.py": (
        "class Journal:\n    pass\n\n\n"
        "def record(amount: int) -> int:\n    return amount\n\n\n"
        "def _balance() -> int:\n    return 0\n"
    ),
    "src/ledger/rules.py": "def post(entry: str) -> str:\n    return entry\n",
    "src/ledger_archive/__init__.py": '"""The archive."""\n',
    "src/ledger_archive/core.py": "def replay(entry: str) -> str:\n    return entry\n",
    "src/ledger_tools.py": "def export(path: str) -> str:\n    return path\n",
}

#: The names each source holds, public and private.
DECLARED: dict[str, set[str]] = {
    "src/ledger/": {"Journal", "record", "_balance", "post"},
    MODULE: {"Journal", "record", "_balance"},
}
#: The names a sibling holds, which the index must carry for a scenario to bite.
SIBLING_NAMES = {"replay", "export"}

PUBLIC_API_HEADING = "## Public API"
_TABLE_ROW = re.compile(r"^\| `([^`]+)` \|")


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


def _public(names: set[str]) -> set[str]:
    return {name for name in names if not name.startswith("_")}


def _indexed_names(project: Path) -> set[str]:
    with sqlite3.connect(project / ".beadloom" / "beadloom.db") as conn:
        return {str(row[0]) for row in conn.execute("SELECT symbol_name FROM code_symbols")}


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
    "a git repository holding a package, a sibling package and a sibling module "
    "whose names start with the package's name"
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
    # Anti-vacuity: the node is the directory, and the siblings reached the index.
    assert _node_source(project, PACKAGE) == "src/ledger/"
    assert _indexed_names(project) >= SIBLING_NAMES


@given("a node whose source is one module of the package has been declared and the index rebuilt")
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
    world["names"] = {str(symbol["symbol_name"]) for symbol in node["symbols"]}


@when("beadloom docs polish is asked for the package's node")
def _when_polish_the_package(world: dict[str, Any], monkeypatch: pytest.MonkeyPatch) -> None:
    _polish(world, monkeypatch, PACKAGE)


@when("beadloom docs polish is asked for that node")
def _when_polish_the_module(world: dict[str, Any], monkeypatch: pytest.MonkeyPatch) -> None:
    _polish(world, monkeypatch, MODULE_NODE)


def _assert_exactly(names: set[str], source: str) -> None:
    assert _public(names) == _public(DECLARED[source]), sorted(names)
    assert names <= DECLARED[source], sorted(names - DECLARED[source])


@then("the symbols it names are the public symbols of the package and no others")
def _then_the_package_symbols(world: dict[str, Any]) -> None:
    _assert_exactly(world["names"], "src/ledger/")


@then("the symbols it names are the public symbols of that module and no others")
def _then_the_module_symbols(world: dict[str, Any]) -> None:
    _assert_exactly(world["names"], MODULE)


@then("the symbols it names are the ones the package's document lists in its Public API table")
def _then_the_document_agrees(world: dict[str, Any]) -> None:
    document = world["project"] / "docs" / "domains" / PACKAGE / "README.md"
    lines = document.read_text(encoding="utf-8").splitlines()
    # Anti-vacuity: a document without the table agrees with nothing.
    assert PUBLIC_API_HEADING in lines, lines
    table: set[str] = set()
    for line in lines[lines.index(PUBLIC_API_HEADING) + 1 :]:
        if line.startswith("## "):
            break
        match = _TABLE_ROW.match(line)
        if match:
            table.add(match.group(1))
    assert table, "the Public API table names no symbol, so nothing was compared"
    assert _public(world["names"]) == table
