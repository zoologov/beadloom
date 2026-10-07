"""Steps shared by every import-resolver scenario: index a fixture, then read its graph.

BDL-076 J1 (`beadloom-hjr1`) and J2 (`beadloom-g9fb`). Each step module in this
folder builds its own fixture project in a ``Given``; indexing it and reading the
answer back are the same for all of them, so they live here once. Nothing is
stubbed: the real ``reindex`` runs, and ``beadloom why`` is invoked through the
CLI the way an adopter runs it.

The comparison with a fresh index of a copy of the tree is shared by every scenario
that edits a tree and updates its index (``beadloom-nh7h``, ``beadloom-jcng``).
"""

from __future__ import annotations

import json
import shutil
import sqlite3
from typing import TYPE_CHECKING, Any

import pytest
from click.testing import CliRunner
from pytest_bdd import given, parsers, then, when

from beadloom.application.reindex import reindex
from beadloom.services.cli import main

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path


def _write_project(root: Path, graph_yaml: str, config_yaml: str, files: dict[str, str]) -> None:
    """Write a fixture project: its graph, its config and its source files."""
    graph = root / ".beadloom" / "_graph"
    graph.mkdir(parents=True)
    (graph / "graph.yml").write_text(graph_yaml, encoding="utf-8")
    (root / ".beadloom" / "config.yml").write_text(config_yaml, encoding="utf-8")
    for rel_path, text in files.items():
        path = root / rel_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")


def _connect(root: Path) -> sqlite3.Connection:
    return sqlite3.connect(root / ".beadloom" / "beadloom.db")


@pytest.fixture
def write_project() -> Callable[[Path, str, str, dict[str, str]], None]:
    """The fixture writer, as a fixture: this folder's name is not an importable package."""
    return _write_project


@pytest.fixture
def state() -> dict[str, Any]:
    """What the steps hand each other: the project root."""
    return {}


@when("the project is indexed")
def _indexed(state: dict[str, Any]) -> None:
    reindex(state["root"])


@given("the project is indexed")
def _indexed_first(state: dict[str, Any]) -> None:
    reindex(state["root"])


def _dependents(root: Path, ref_id: str) -> set[str]:
    result = CliRunner().invoke(main, ["why", ref_id, "--json", "--project", str(root)])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    return {str(item["ref_id"]) for item in payload["downstream"]}


@then(parsers.parse('why on "{ref_id}" lists "{first}" and "{second}" as dependents'))
def _why_lists_two(state: dict[str, Any], ref_id: str, first: str, second: str) -> None:
    assert {first, second} <= _dependents(state["root"], ref_id)


@then(parsers.parse('why on "{ref_id}" lists "{dependent}" as a dependent'))
def _why_lists_one(state: dict[str, Any], ref_id: str, dependent: str) -> None:
    assert dependent in _dependents(state["root"], ref_id)


def _depends_on(root: Path) -> set[tuple[str, str]]:
    with _connect(root) as conn:
        rows = conn.execute(
            "SELECT src_ref_id, dst_ref_id FROM edges WHERE kind = 'depends_on'"
        ).fetchall()
    return {(str(row[0]), str(row[1])) for row in rows}


@then(parsers.parse("the depends_on edges are exactly {edges}"))
def _edges_exactly(state: dict[str, Any], edges: str) -> None:
    expected = {tuple(part.strip().split(" -> ")) for part in edges.replace('"', "").split(",")}
    assert _depends_on(state["root"]) == expected


@then(parsers.parse('no depends_on edge points at "{ref_id}"'))
def _no_edge_into(state: dict[str, Any], ref_id: str) -> None:
    assert [edge for edge in _depends_on(state["root"]) if edge[1] == ref_id] == []


def _imports(root: Path, file_path: str, import_path: str) -> list[tuple[int, str | None]]:
    with _connect(root) as conn:
        rows = conn.execute(
            "SELECT line_number, resolved_ref_id FROM code_imports "
            "WHERE file_path = ? AND import_path = ?",
            (file_path, import_path),
        ).fetchall()
    return [(int(row[0]), row[1]) for row in rows]


@then(parsers.parse('the import "{import_path}" of "{file_path}" resolves to "{ref_id}"'))
def _resolves_to(state: dict[str, Any], import_path: str, file_path: str, ref_id: str) -> None:
    assert [node for _, node in _imports(state["root"], file_path, import_path)] == [ref_id]


@then(parsers.parse('the import "{import_path}" of "{file_path}" is recorded with no node'))
def _recorded_unresolved(state: dict[str, Any], import_path: str, file_path: str) -> None:
    assert [node for _, node in _imports(state["root"], file_path, import_path)] == [None]


@then(parsers.parse('the import "{import_path}" of "{file_path}" is on line {line:d}'))
def _on_line(state: dict[str, Any], import_path: str, file_path: str, line: int) -> None:
    assert [number for number, _ in _imports(state["root"], file_path, import_path)] == [line]


_IMPORT_ROWS = "SELECT file_path, line_number, import_path, resolved_ref_id FROM code_imports"
_DEPENDS_ON_ROWS = "SELECT src_ref_id, dst_ref_id FROM edges WHERE kind = 'depends_on'"


def _sorted_rows(root: Path, sql: str) -> list[tuple[object, ...]]:
    with _connect(root) as conn:
        return sorted(tuple(row) for row in conn.execute(sql).fetchall())


@then("every resolved import and every derived edge equals a fresh index of the same tree")
def _equals_fresh(tmp_path: Path, state: dict[str, Any]) -> None:
    """Index a copy of the tree in a directory that never held an index, and compare."""
    root: Path = state["root"]
    fresh = tmp_path / "fresh"
    shutil.copytree(root, fresh, ignore=shutil.ignore_patterns("beadloom.db*"))
    reindex(fresh)
    assert _sorted_rows(root, _IMPORT_ROWS) == _sorted_rows(fresh, _IMPORT_ROWS)
    assert _sorted_rows(root, _DEPENDS_ON_ROWS) == _sorted_rows(fresh, _DEPENDS_ON_ROWS)
