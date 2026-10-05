"""Step implementations for `an_import_resolves_the_same_however_the_index_was_built.feature`.

BDL-078 (`beadloom-nh7h`). The fixture holds the shape measured on this repository: a
module made of re-exports, which has no symbol, sourced as a node of its own inside the
domain folder that holds it. The index is built the way an adopter builds it, edited, and
compared with a fresh index of a copy of the same tree. The shared When/Then steps are in
this folder's `conftest.py`.

The module is named `test_*` so default pytest collection picks the scenarios up.
"""

from __future__ import annotations

import shutil
import sqlite3
from typing import TYPE_CHECKING, Any

from pytest_bdd import given, scenarios, then, when

from beadloom.application.reindex import incremental_reindex, reindex

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    WriteProject = Callable[[Path, str, str, dict[str, str]], None]

scenarios(
    "../../../graph/import-resolver/an_import_resolves_the_same_however_the_index_was_built.feature"
)

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

_FACADE_PATH = "src/shop/app/facade.py"
_FACADE = "from shop.app.core import load\n\n__all__ = ['load']\n"

_FILES: dict[str, str] = {
    "src/shop/app/core.py": "def load() -> int:\n    return 1\n",
    "src/shop/ui/screen.py": (
        "from shop.app.facade import load\n\n\ndef show() -> int:\n    return load()\n"
    ),
}

_IMPORTS = "SELECT file_path, line_number, import_path, resolved_ref_id FROM code_imports"
_EDGES = "SELECT src_ref_id, dst_ref_id FROM edges WHERE kind = 'depends_on'"


def _rows(root: Path, sql: str) -> list[tuple[object, ...]]:
    conn = sqlite3.connect(root / ".beadloom" / "beadloom.db")
    try:
        return sorted(tuple(row) for row in conn.execute(sql).fetchall())
    finally:
        conn.close()


@given("a project whose screen imports a facade module that only re-exports")
def _with_facade(tmp_path: Path, state: dict[str, Any], write_project: WriteProject) -> None:
    root = tmp_path / "shop"
    write_project(root, _GRAPH, _CONFIG, {**_FILES, _FACADE_PATH: _FACADE})
    state["root"] = root


@given("a project whose screen imports a facade module that does not exist yet")
def _without_facade(tmp_path: Path, state: dict[str, Any], write_project: WriteProject) -> None:
    root = tmp_path / "shop"
    write_project(root, _GRAPH, _CONFIG, _FILES)
    state["root"] = root


@given("the project is indexed")
def _indexed_first(state: dict[str, Any]) -> None:
    reindex(state["root"])


@when("the facade module is written and the index is updated")
def _facade_written(state: dict[str, Any]) -> None:
    (state["root"] / _FACADE_PATH).write_text(_FACADE, encoding="utf-8")
    incremental_reindex(state["root"])


@when("the facade module is deleted and the index is updated")
def _facade_deleted(state: dict[str, Any]) -> None:
    (state["root"] / _FACADE_PATH).unlink()
    incremental_reindex(state["root"])


@then("every resolved import and every derived edge equals a fresh index of the same tree")
def _equals_fresh(tmp_path: Path, state: dict[str, Any]) -> None:
    root: Path = state["root"]
    fresh = tmp_path / "fresh"
    shutil.copytree(root, fresh, ignore=shutil.ignore_patterns("beadloom.db*"))
    reindex(fresh)
    assert _rows(root, _IMPORTS) == _rows(fresh, _IMPORTS)
    assert _rows(root, _EDGES) == _rows(fresh, _EDGES)
