"""``init`` then ``reindex`` on the Go adopter fixture draws the fixture's imports, and no others.

BDL-076 B5 (``beadloom-ujzb.14``). Measured by B3 on ``tests/fixtures/site/go``
(module ``example.org/tidewater``; ``cmd/tidewater`` and four packages under
``internal/``): of the seven imports between the fixture's packages the graph held
three, plus three edges the code does not have — ``api``, ``billing`` and
``catalog`` onto ``tidewater-service``, the node of ``cmd/tidewater``. Two causes,
and each half is held here on its own: ``init``'s quick scan wrote the false
edges into the graph YAML, and ``reindex`` resolved no Go import at all.

The expected pairs are read from the fixture's code and written in
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
from tests.support.adopter_portals import GO
from tests.support.committed_project import commit_project

if TYPE_CHECKING:
    from pathlib import Path

pytest.importorskip("tree_sitter_go")

#: The three edges B3 measured that the fixture's code does not have.
_FALSE_EDGES = {
    ("api", "tidewater-service"),
    ("billing", "tidewater-service"),
    ("catalog", "tidewater-service"),
}


def _beadloom(root: Path, *args: str) -> None:
    result = CliRunner().invoke(main, [*args, "--project", str(root)])
    assert result.exit_code == 0, result.output


@pytest.fixture
def project(tmp_path: Path) -> Path:
    """The Go fixture, copied, committed and initialised as an adopter does it."""
    root = tmp_path / GO.project
    shutil.copytree(GO.source, root)
    commit_project(root, origin=GO.origin)
    _beadloom(root, "init", "--yes")
    return root


def _graph_files(root: Path) -> list[Path]:
    return sorted((root / ".beadloom" / "_graph").glob("*.yml"))


def _owner_by_source(root: Path) -> dict[str, str]:
    """Each node's ref_id, keyed by its source directory without the trailing slash."""
    owners: dict[str, str] = {}
    for path in _graph_files(root):
        for node in (yaml.safe_load(path.read_text(encoding="utf-8")) or {}).get("nodes") or []:
            owners[str(node.get("source") or "").rstrip("/")] = str(node["ref_id"])
    return owners


def _expected(root: Path) -> set[tuple[str, str]]:
    owners = _owner_by_source(root)
    return {(owners[importer], owners[imported]) for importer, imported in GO.imports}


def _yaml_depends_on(root: Path) -> set[tuple[str, str]]:
    edges: set[tuple[str, str]] = set()
    for path in _graph_files(root):
        for edge in (yaml.safe_load(path.read_text(encoding="utf-8")) or {}).get("edges") or []:
            if edge.get("kind") == "depends_on":
                edges.add((str(edge["src"]), str(edge["dst"])))
    return edges


def _indexed_depends_on(root: Path) -> set[tuple[str, str]]:
    with sqlite3.connect(root / ".beadloom" / "beadloom.db") as conn:
        rows = conn.execute(
            "SELECT src_ref_id, dst_ref_id FROM edges WHERE kind = 'depends_on'"
        ).fetchall()
    return {(str(row[0]), str(row[1])) for row in rows}


def _drop_yaml_depends_on(root: Path) -> None:
    """Take every ``depends_on`` edge ``init`` wrote out of the graph YAML."""
    for path in _graph_files(root):
        data: dict[str, Any] = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if "edges" in data:
            data["edges"] = [e for e in data["edges"] if e.get("kind") != "depends_on"]
            path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def test_the_graph_after_init_and_reindex_holds_exactly_the_seven_imports(project: Path) -> None:
    _beadloom(project, "reindex")

    edges = _indexed_depends_on(project)

    assert len(_expected(project)) == len(GO.imports) == 7
    assert edges == _expected(project)
    assert edges & _FALSE_EDGES == set()


def test_init_writes_exactly_the_seven_imports_into_the_graph(project: Path) -> None:
    assert _yaml_depends_on(project) == _expected(project)


def test_reindex_alone_derives_the_seven_imports_from_the_code(project: Path) -> None:
    _drop_yaml_depends_on(project)
    _beadloom(project, "reindex")

    assert _indexed_depends_on(project) == _expected(project)


def test_only_the_standard_library_stays_unresolved(project: Path) -> None:
    _beadloom(project, "reindex")

    with sqlite3.connect(project / ".beadloom" / "beadloom.db") as conn:
        unresolved = {
            str(row[0])
            for row in conn.execute(
                "SELECT import_path FROM code_imports WHERE resolved_ref_id IS NULL"
            ).fetchall()
        }

    # Every standard-library import of the fixture's code, read from the fixture. Before
    # ``beadloom-jcng`` the extractor dropped a path with no '/', which also dropped a
    # module named so; which path names the standard library is now the resolver's answer.
    assert unresolved == {"net/http", "encoding/json", "log", "strconv", "testing"}
