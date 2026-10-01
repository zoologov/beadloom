"""``init`` then ``reindex`` on the Kotlin adopter fixture laid out as Kotlin recommends.

BDL-076 R2 finding 6 (``beadloom-fht7``), fixed by ``beadloom-ujzb.19``. Kotlin's
coding conventions recommend, for a pure Kotlin project, omitting the common root
package from the folders. The reviewer measured that on such a project ``init`` drew
no ``depends_on`` edge and ``reindex`` resolved no import. Here the fixture
``tests/fixtures/site/kotlin`` itself is copied and rearranged that way — every file
under ``org/example/orchard/`` moved up to its language folder, the declarations
untouched — and the same expectations its standard layout meets are held: every
package a node, every import between packages an edge, the test bound by mirror.
"""

from __future__ import annotations

import shutil
import sqlite3
from typing import TYPE_CHECKING, Any

import pytest
import yaml
from click.testing import CliRunner

from beadloom.services.cli import main
from tests.support.adopter_portals import KOTLIN
from tests.support.committed_project import commit_project

if TYPE_CHECKING:
    from pathlib import Path

pytest.importorskip("tree_sitter_kotlin")

#: The root package Kotlin's conventions leave out of the folders.
_ROOT_PACKAGE = ("org", "example", "orchard")


def _moved(path: str) -> str:
    """*path* of the fixture as it lies once the root package is out of the folders."""
    return path.replace("/".join(_ROOT_PACKAGE) + "/", "").replace("/".join(_ROOT_PACKAGE), "")


def _beadloom(root: Path, *args: str) -> None:
    result = CliRunner().invoke(main, [*args, "--project", str(root)])
    assert result.exit_code == 0, result.output


@pytest.fixture
def root(tmp_path: Path) -> Path:
    """The fixture, copied, rearranged, committed and initialised as an adopter does it."""
    project = tmp_path / KOTLIN.project
    shutil.copytree(KOTLIN.source, project)
    for language_root in sorted(project.glob("src/*/kotlin")):
        package_root = language_root.joinpath(*_ROOT_PACKAGE)
        for child in sorted(package_root.iterdir()):
            shutil.move(str(child), str(language_root / child.name))
        shutil.rmtree(language_root / _ROOT_PACKAGE[0])
    assert not list(project.rglob("orchard"))
    commit_project(project, origin=KOTLIN.origin)
    _beadloom(project, "init", "--yes")
    return project


def _owner_by_source(root: Path) -> dict[str, str]:
    return {
        str(node.get("source") or "").rstrip("/"): str(node["ref_id"])
        for path in sorted((root / ".beadloom" / "_graph").glob("*.yml"))
        for node in (yaml.safe_load(path.read_text(encoding="utf-8")) or {}).get("nodes") or []
    }


def _expected(root: Path) -> set[tuple[str, str]]:
    owners = _owner_by_source(root)
    return {(owners[_moved(src)], owners[_moved(dst)]) for src, dst in KOTLIN.imports}


def _yaml_depends_on(root: Path) -> set[tuple[str, str]]:
    return {
        (str(edge["src"]), str(edge["dst"]))
        for path in sorted((root / ".beadloom" / "_graph").glob("*.yml"))
        for edge in (yaml.safe_load(path.read_text(encoding="utf-8")) or {}).get("edges") or []
        if edge.get("kind") == "depends_on"
    }


def _indexed(root: Path, sql: str, *params: str) -> list[tuple[Any, ...]]:
    with sqlite3.connect(root / ".beadloom" / "beadloom.db") as conn:
        return [tuple(row) for row in conn.execute(sql, params).fetchall()]


def test_every_package_of_the_fixture_is_a_node(root: Path) -> None:
    owners = _owner_by_source(root)

    assert [m for m in (_moved(module) for module in KOTLIN.modules) if m not in owners] == []


def test_init_writes_every_import_between_packages_as_an_edge(root: Path) -> None:
    assert len(_expected(root)) == 3
    assert _yaml_depends_on(root) == _expected(root)


def test_reindex_resolves_every_import_of_the_project_and_holds_the_same_edges(
    root: Path,
) -> None:
    _beadloom(root, "reindex")

    own = _indexed(
        root,
        "SELECT import_path, resolved_ref_id FROM code_imports WHERE import_path LIKE ?",
        "org.example.orchard.%",
    )
    rows = _indexed(root, "SELECT src_ref_id, dst_ref_id FROM edges WHERE kind = 'depends_on'")
    assert own
    assert [row for row in own if not row[1]] == []
    assert {(str(src), str(dst)) for src, dst in rows} == _expected(root)


def test_the_test_binds_to_the_package_it_tests(root: Path) -> None:
    _beadloom(root, "reindex")

    bound = _indexed(
        root,
        "SELECT ref_id, placement FROM test_files WHERE path = ?",
        "src/test/kotlin/planner/RoutePlannerTest.kt",
    )

    assert bound == [(_owner_by_source(root)["src/main/kotlin/planner"], "mirror")]
