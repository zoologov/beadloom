"""``init`` then ``reindex`` on the Java and Kotlin adopter fixtures: every package and import.

BDL-076 B6 (``beadloom-ujzb.15``). Measured by B3 on ``tests/fixtures/site/java``
(Maven, ``org.example.ledger.{web,service,repository,model}``) and
``tests/fixtures/site/kotlin`` (Gradle KTS, ``org.example.orchard.{routing,planner,
geo}``): ``init`` wrote nodes ``main``, ``main-java``, ``test``, ``test-java`` and
``scan_paths: [src]``, so no package was a node and the graph held none of the
four (Java) and three (Kotlin) imports between packages. Each half is held here on
its own: what ``init`` writes into the graph YAML and the config, and what
``reindex`` derives from the code through the scan paths ``init`` wrote.

The expected packages and imports are read from the fixtures' code and written in
:mod:`tests.support.adopter_portals`, never taken from the product.
"""

from __future__ import annotations

import shutil
import sqlite3
from typing import TYPE_CHECKING, Any

import pytest
import yaml
from click.testing import CliRunner

from beadloom.services.cli import main
from tests.support.adopter_portals import JAVA, KOTLIN, AdopterFixture
from tests.support.committed_project import commit_project

if TYPE_CHECKING:
    from pathlib import Path

pytest.importorskip("tree_sitter_java")
pytest.importorskip("tree_sitter_kotlin")

#: Each fixture, its source root, and its one test file with the package it tests.
_CASES = {
    "java": (
        JAVA,
        "src/main/java",
        "src/test/java/org/example/ledger/service/LedgerServiceTest.java",
        "src/main/java/org/example/ledger/service",
    ),
    "kotlin": (
        KOTLIN,
        "src/main/kotlin",
        "src/test/kotlin/org/example/orchard/planner/RoutePlannerTest.kt",
        "src/main/kotlin/org/example/orchard/planner",
    ),
}

#: The folders B3 found made into nodes: the source sets and their language roots.
_SOURCE_SET_FOLDERS = {
    "src",
    "src/main",
    "src/test",
    "src/main/java",
    "src/main/kotlin",
    "src/test/java",
    "src/test/kotlin",
}


def _beadloom(root: Path, *args: str) -> None:
    result = CliRunner().invoke(main, [*args, "--project", str(root)])
    assert result.exit_code == 0, result.output


@pytest.fixture(params=sorted(_CASES))
def case(request: pytest.FixtureRequest, tmp_path: Path) -> tuple[Path, AdopterFixture, str]:
    """The fixture, copied, committed and initialised as an adopter does it."""
    fixture = _CASES[request.param][0]
    root = tmp_path / fixture.project
    shutil.copytree(fixture.source, root)
    commit_project(root, origin=fixture.origin)
    _beadloom(root, "init", "--yes")
    return root, fixture, request.param


def _graph(root: Path) -> list[dict[str, Any]]:
    return [
        yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        for path in sorted((root / ".beadloom" / "_graph").glob("*.yml"))
    ]


def _owner_by_source(root: Path) -> dict[str, str]:
    """Each node's ref_id, keyed by its source directory without the trailing slash."""
    return {
        str(node.get("source") or "").rstrip("/"): str(node["ref_id"])
        for data in _graph(root)
        for node in data.get("nodes") or []
    }


def _expected(root: Path, fixture: AdopterFixture) -> set[tuple[str, str]]:
    owners = _owner_by_source(root)
    return {(owners[importer], owners[imported]) for importer, imported in fixture.imports}


def _yaml_depends_on(root: Path) -> set[tuple[str, str]]:
    return {
        (str(edge["src"]), str(edge["dst"]))
        for data in _graph(root)
        for edge in data.get("edges") or []
        if edge.get("kind") == "depends_on"
    }


def _indexed(root: Path, sql: str, *params: str) -> list[tuple[Any, ...]]:
    with sqlite3.connect(root / ".beadloom" / "beadloom.db") as conn:
        return [tuple(row) for row in conn.execute(sql, params).fetchall()]


def _indexed_depends_on(root: Path) -> set[tuple[str, str]]:
    rows = _indexed(root, "SELECT src_ref_id, dst_ref_id FROM edges WHERE kind = 'depends_on'")
    return {(str(src), str(dst)) for src, dst in rows}


def _drop_yaml_depends_on(root: Path) -> None:
    """Take every ``depends_on`` edge ``init`` wrote out of the graph YAML."""
    for path in sorted((root / ".beadloom" / "_graph").glob("*.yml")):
        data: dict[str, Any] = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if "edges" in data:
            data["edges"] = [e for e in data["edges"] if e.get("kind") != "depends_on"]
            path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def test_every_package_is_a_node_and_no_source_set_is(
    case: tuple[Path, AdopterFixture, str],
) -> None:
    root, fixture, _ = case
    owners = _owner_by_source(root)

    assert [module for module in fixture.modules if module not in owners] == []
    assert set(owners) & _SOURCE_SET_FOLDERS == set()


def test_init_writes_the_source_root_as_the_scan_path(
    case: tuple[Path, AdopterFixture, str],
) -> None:
    root, _, stack = case
    config = yaml.safe_load((root / ".beadloom" / "config.yml").read_text(encoding="utf-8"))

    assert config["scan_paths"] == [_CASES[stack][1]]


def test_init_writes_exactly_the_imports_into_the_graph(
    case: tuple[Path, AdopterFixture, str],
) -> None:
    root, fixture, _ = case

    assert _yaml_depends_on(root) == _expected(root, fixture)


def test_the_graph_after_init_and_reindex_holds_exactly_the_imports(
    case: tuple[Path, AdopterFixture, str],
) -> None:
    root, fixture, stack = case
    _beadloom(root, "reindex")

    assert len(_expected(root, fixture)) == {"java": 4, "kotlin": 3}[stack]
    assert _indexed_depends_on(root) == _expected(root, fixture)


def test_reindex_alone_derives_the_imports_from_the_code(
    case: tuple[Path, AdopterFixture, str],
) -> None:
    root, fixture, _ = case
    _drop_yaml_depends_on(root)
    _beadloom(root, "reindex")

    assert _indexed_depends_on(root) == _expected(root, fixture)


def test_the_test_binds_to_the_package_it_tests(
    case: tuple[Path, AdopterFixture, str],
) -> None:
    root, _, stack = case
    _beadloom(root, "reindex")
    _fixture, _root, test_file, package = _CASES[stack]

    bound = _indexed(root, "SELECT ref_id, placement FROM test_files WHERE path = ?", test_file)

    assert bound == [(_owner_by_source(root)[package], "mirror")]
