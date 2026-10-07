"""One tree, one set of resolved imports, whichever way the index was built (``beadloom-nh7h``).

Measured on this repository on 2026-10-04: a fresh clone's ``beadloom reindex`` resolved
``tui``'s import of ``beadloom.application.graph_reads`` to ``application``; the same tree
indexed a second time resolved it to ``graph-reads``, the node whose source is that file. The
first answer of the resolver asked whether the imported file was in ``code_symbols`` or in
``file_index``. A module of re-exports holds no symbol, and a full reindex fills
``file_index`` only after the imports are resolved, while never dropping the previous run's
copy — so the answer depended on whether an index had existed before. An incremental run
read the same table one step behind, and never re-resolved an import whose target file
appeared or vanished while the importer stayed unchanged.

Each case builds the index the way an adopter does, edits the tree, and compares every row
of ``code_imports`` and every derived ``depends_on`` edge with a fresh index of a copy of the
same tree.
"""

from __future__ import annotations

import shutil
import sqlite3
from typing import TYPE_CHECKING

from beadloom.application.reindex import incremental_reindex, reindex

if TYPE_CHECKING:
    from pathlib import Path

_CONFIG = "scan_paths:\n- src\n"

_GRAPH = """\
nodes:
  - ref_id: shop
    kind: service
    summary: The project.
    source: ""
  - ref_id: app
    kind: domain
    summary: The application layer.
    source: src/shop/app/
  - ref_id: facade
    kind: feature
    summary: A read facade made of re-exports only.
    source: src/shop/app/facade.py
  - ref_id: ui
    kind: domain
    summary: The screens.
    source: src/shop/ui/
edges:
  - {src: app, dst: shop, kind: part_of}
  - {src: facade, dst: app, kind: part_of}
  - {src: ui, dst: shop, kind: part_of}
"""

#: The facade defines nothing, so ``code_symbols`` holds no row for it.
_FACADE = "from shop.app.core import load\n\n__all__ = ['load']\n"
_CORE = "def load() -> int:\n    return 1\n"
_SCREEN = "from shop.app.facade import load\n\n\ndef show() -> int:\n    return load()\n"
_SCREEN_EDITED = (
    "from shop.app.facade import load\n\n\ndef show() -> int:\n    return load() + 1\n"
)

_FACADE_PATH = "src/shop/app/facade.py"
_SCREEN_PATH = "src/shop/ui/screen.py"


def _write(root: Path, rel_path: str, text: str) -> None:
    path = root / rel_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _project(root: Path, *, with_facade: bool) -> Path:
    graph = root / ".beadloom" / "_graph"
    graph.mkdir(parents=True)
    (graph / "graph.yml").write_text(_GRAPH, encoding="utf-8")
    (root / ".beadloom" / "config.yml").write_text(_CONFIG, encoding="utf-8")
    _write(root, "src/shop/app/core.py", _CORE)
    _write(root, _SCREEN_PATH, _SCREEN)
    if with_facade:
        _write(root, _FACADE_PATH, _FACADE)
    return root


def _rows(root: Path, sql: str, params: tuple[str, ...] = ()) -> list[tuple[object, ...]]:
    conn = sqlite3.connect(root / ".beadloom" / "beadloom.db")
    try:
        return sorted(tuple(row) for row in conn.execute(sql, params).fetchall())
    finally:
        conn.close()


_IMPORTS = "SELECT file_path, line_number, import_path, resolved_ref_id FROM code_imports"
_EDGES = "SELECT src_ref_id, dst_ref_id FROM edges WHERE kind = 'depends_on'"


def _fresh_copy(root: Path, tmp_path: Path) -> Path:
    """Index a copy of *root*'s tree in a directory that never held an index."""
    fresh = tmp_path / "fresh"
    shutil.copytree(root, fresh, ignore=shutil.ignore_patterns("beadloom.db*"))
    reindex(fresh)
    return fresh


def _assert_same_as_fresh(root: Path, tmp_path: Path) -> None:
    fresh = _fresh_copy(root, tmp_path)
    assert _rows(root, _IMPORTS) == _rows(fresh, _IMPORTS)
    assert _rows(root, _EDGES) == _rows(fresh, _EDGES)


def _screen_target(root: Path) -> object:
    rows = _rows(
        root, "SELECT resolved_ref_id FROM code_imports WHERE file_path = ?", (_SCREEN_PATH,)
    )
    return rows[0][0] if len(rows) == 1 else rows


class TestAFreshIndex:
    def test_an_import_of_a_module_with_no_symbol_resolves_to_the_node_owning_that_file(
        self, tmp_path: Path
    ) -> None:
        root = _project(tmp_path / "project", with_facade=True)

        reindex(root)

        assert _screen_target(root) == "facade"
        assert ("ui", "facade") in _rows(root, _EDGES)

    def test_a_second_full_reindex_resolves_every_import_as_the_first_did(
        self, tmp_path: Path
    ) -> None:
        root = _project(tmp_path / "project", with_facade=True)
        reindex(root)
        first = _rows(root, _IMPORTS)

        reindex(root)

        assert _rows(root, _IMPORTS) == first


class TestAnIncrementalIndexEqualsAFreshOne:
    def test_after_the_imported_file_is_added_and_the_importer_is_unchanged(
        self, tmp_path: Path
    ) -> None:
        root = _project(tmp_path / "project", with_facade=False)
        reindex(root)
        assert _screen_target(root) == "app"

        _write(root, _FACADE_PATH, _FACADE)
        incremental_reindex(root)

        assert _screen_target(root) == "facade"
        _assert_same_as_fresh(root, tmp_path)

    def test_after_the_imported_file_is_added_in_the_run_that_edits_the_importer(
        self, tmp_path: Path
    ) -> None:
        root = _project(tmp_path / "project", with_facade=False)
        reindex(root)

        _write(root, _FACADE_PATH, _FACADE)
        _write(root, _SCREEN_PATH, _SCREEN_EDITED)
        incremental_reindex(root)

        assert _screen_target(root) == "facade"
        _assert_same_as_fresh(root, tmp_path)

    def test_after_the_imported_file_is_removed_and_the_importer_is_unchanged(
        self, tmp_path: Path
    ) -> None:
        root = _project(tmp_path / "project", with_facade=True)
        reindex(root)

        (root / _FACADE_PATH).unlink()
        incremental_reindex(root)

        assert _screen_target(root) == "app"
        _assert_same_as_fresh(root, tmp_path)

    def test_after_the_imported_file_is_removed_in_the_run_that_edits_the_importer(
        self, tmp_path: Path
    ) -> None:
        root = _project(tmp_path / "project", with_facade=True)
        reindex(root)

        (root / _FACADE_PATH).unlink()
        _write(root, _SCREEN_PATH, _SCREEN_EDITED)
        incremental_reindex(root)

        assert _screen_target(root) == "app"
        _assert_same_as_fresh(root, tmp_path)
