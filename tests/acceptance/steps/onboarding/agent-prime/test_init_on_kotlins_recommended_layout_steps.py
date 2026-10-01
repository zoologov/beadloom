"""Step implementations for `onboarding/agent-prime/init_on_kotlins_recommended_layout.feature`.

BDL-076 R2 finding 6, fixed by `beadloom-ujzb.19`. The Kotlin adopter fixture's code,
laid out as Kotlin's coding conventions recommend for a pure Kotlin project: the
common root package `org.example.orchard` is dropped from every folder, the package
declarations are left as they are. The real `beadloom init --yes` and `beadloom
reindex` then run through the CLI; nothing is patched.

**FAKES PROVE FAKES.** The fixture's imports name the packages by their full
declared names (`org.example.orchard.geo.Row`), which no folder of the rearranged
tree spells, so an edge can only come from reading the declarations.
"""

from __future__ import annotations

import sqlite3
from typing import TYPE_CHECKING, Any

import pytest
import yaml
from click.testing import CliRunner
from pytest_bdd import given, parsers, scenarios, then, when

from beadloom.services.cli import main

if TYPE_CHECKING:
    from pathlib import Path

pytest.importorskip("tree_sitter_kotlin")

scenarios("../../../onboarding/agent-prime/init_on_kotlins_recommended_layout.feature")


#: The Kotlin adopter fixture (``tests/fixtures/site/kotlin``), its sources written
#: here as Kotlin's conventions lay them out: the common root package
#: ``org.example.orchard`` is in every declaration and in no folder. Written inline
#: because the suite also runs as a copy without the repository's fixtures; the
#: integration test ``test_init_on_kotlins_recommended_layout.py`` rearranges the
#: fixture itself.
_ORCHARD: dict[str, str] = {
    "settings.gradle.kts": 'rootProject.name = "orchard-routes"\n',
    "build.gradle.kts": 'plugins {\n    kotlin("jvm") version "2.0.21"\n    application\n}\n',
    "src/main/kotlin/geo/Distance.kt": (
        "package org.example.orchard.geo\n\n"
        "data class Row(val name: String, val x: Int, val y: Int)\n\n"
        "fun distance(a: Row, b: Row): Int = kotlin.math.abs(a.x - b.x)\n"
    ),
    "src/main/kotlin/planner/RoutePlanner.kt": (
        "package org.example.orchard.planner\n\n"
        "import org.example.orchard.geo.Row\n"
        "import org.example.orchard.geo.distance\n\n"
        "class RoutePlanner {\n"
        "    fun plan(start: Row, rows: List<Row>): List<Row> =\n"
        "        rows.sortedBy { distance(start, it) }\n"
        "}\n"
    ),
    "src/main/kotlin/routing/Main.kt": (
        "package org.example.orchard.routing\n\n"
        "import org.example.orchard.geo.Row\n"
        "import org.example.orchard.planner.RoutePlanner\n\n"
        'fun main() { println(RoutePlanner().plan(Row("gate", 0, 0), emptyList())) }\n'
    ),
    "src/test/kotlin/planner/RoutePlannerTest.kt": (
        "package org.example.orchard.planner\n\n"
        "import kotlin.test.Test\n"
        "import org.example.orchard.geo.Row\n\n"
        "class RoutePlannerTest {\n    @Test\n    fun plans() {}\n}\n"
    ),
}


@pytest.fixture
def state() -> dict[str, Any]:
    return {}


@given(
    parsers.parse(
        'the Kotlin adopter fixture with its root package "{package}" omitted from the folders'
    )
)
def _rearranged_fixture(tmp_path: Path, state: dict[str, Any], package: str) -> None:
    root = tmp_path / "orchard-routes"
    for rel_path, text in _ORCHARD.items():
        path = root / rel_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    declared = {text.split("\n", 1)[0] for path, text in _ORCHARD.items() if path.endswith(".kt")}
    assert all(line.startswith(f"package {package}.") for line in declared)
    assert not (root / "src/main/kotlin" / package.split(".")[0]).exists()
    state["root"] = root


def _run(state: dict[str, Any], *args: str) -> None:
    result = CliRunner().invoke(main, [*args, "--project", str(state["root"])])
    assert result.exit_code == 0, result.output


@when("beadloom init is run without prompts")
def _init(state: dict[str, Any]) -> None:
    _run(state, "init", "--yes")


@when("beadloom reindex is run")
def _reindex(state: dict[str, Any]) -> None:
    _run(state, "reindex")


def _listed(text: str) -> set[str]:
    return {part.strip().strip('"') for part in text.split(",")}


def _pairs(text: str) -> set[tuple[str, str]]:
    return {(src, dst) for src, dst in (item.split(" -> ") for item in _listed(text))}


def _graph(root: Path) -> list[dict[str, Any]]:
    return [
        yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        for path in sorted((root / ".beadloom" / "_graph").glob("*.yml"))
    ]


@then(parsers.parse("the code nodes init writes have exactly the sources {sources}"))
def _sources(state: dict[str, Any], sources: str) -> None:
    written = {
        str(node.get("source") or "")
        for data in _graph(state["root"])
        for node in data.get("nodes") or []
    }
    assert written - {""} == _listed(sources)


@then(parsers.parse("the graph init writes has exactly the depends_on edges {edges}"))
def _written_edges(state: dict[str, Any], edges: str) -> None:
    written = {
        (str(edge["src"]), str(edge["dst"]))
        for data in _graph(state["root"])
        for edge in data.get("edges") or []
        if edge.get("kind") == "depends_on"
    }
    assert written == _pairs(edges)


def _query(root: Path, sql: str, *params: str) -> list[tuple[Any, ...]]:
    with sqlite3.connect(root / ".beadloom" / "beadloom.db") as conn:
        return [tuple(row) for row in conn.execute(sql, params).fetchall()]


@then(parsers.parse('every import of a package below "{package}" in the index is resolved'))
def _own_imports_resolved(state: dict[str, Any], package: str) -> None:
    rows = _query(
        state["root"],
        "SELECT file_path, import_path, resolved_ref_id FROM code_imports"
        " WHERE import_path LIKE ?",
        f"{package}.%",
    )
    assert rows, "the index holds no import of the project's own packages"
    assert [row for row in rows if not row[2]] == []


@then(parsers.parse("the index holds exactly the depends_on edges {edges}"))
def _indexed_edges(state: dict[str, Any], edges: str) -> None:
    rows = _query(
        state["root"], "SELECT src_ref_id, dst_ref_id FROM edges WHERE kind = 'depends_on'"
    )
    assert {(str(src), str(dst)) for src, dst in rows} == _pairs(edges)


@then(parsers.parse('the test file "{path}" is bound to "{ref_id}"'))
def _bound(state: dict[str, Any], path: str, ref_id: str) -> None:
    assert _query(state["root"], "SELECT ref_id FROM test_files WHERE path = ?", path) == [
        (ref_id,)
    ]
