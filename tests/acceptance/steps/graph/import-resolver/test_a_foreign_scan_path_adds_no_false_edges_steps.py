"""Step implementations for `a_foreign_scan_path_adds_no_false_edges.feature`.

BDL-076 J2 (`beadloom-g9fb`). The fixture reproduces the shape A0 measured on this
repository: a JavaScript theme that is a scan path of its own, owned by a node whose
source lies ABOVE that scan path (`web/` here, `site/` there). A Python import the
project cannot place used to be prefixed with the theme's path and walked up to
that node. The shared When/Then steps are in this folder's `conftest.py`.

The module is named `test_*` so default pytest collection picks the scenarios up.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest
from pytest_bdd import given, scenarios

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    WriteProject = Callable[[Path, str, str, dict[str, str]], None]

pytest.importorskip("tree_sitter_typescript")

scenarios("../../../graph/import-resolver/a_foreign_scan_path_adds_no_false_edges.feature")

_CONFIG = "scan_paths:\n- src\n- web/theme\n"

_GRAPH = """\
nodes:
  - ref_id: mixed
    kind: service
    summary: A Python service with a JavaScript theme.
    source: ""
  - ref_id: api
    kind: domain
    summary: The HTTP handlers.
    source: src/api/
  - ref_id: store
    kind: domain
    summary: The storage.
    source: src/store/
  - ref_id: site
    kind: domain
    summary: The documentation site.
    source: web/
  - ref_id: pages
    kind: feature
    summary: The theme's pages.
    source: web/theme/pages/
  - ref_id: widgets
    kind: feature
    summary: The theme's widgets.
    source: web/theme/widgets/
edges:
  - {src: api, dst: mixed, kind: part_of}
  - {src: store, dst: mixed, kind: part_of}
  - {src: site, dst: mixed, kind: part_of}
  - {src: pages, dst: site, kind: part_of}
  - {src: widgets, dst: site, kind: part_of}
"""

#: `typing` and `pathlib` name no project module; `widgets.card` names a folder that
#: exists only under the JavaScript scan path; `store.db` is the one real import.
_FILES: dict[str, str] = {
    "src/api/handlers.py": (
        "import typing\nimport pathlib\nimport widgets.card\nfrom store.db import save\n"
    ),
    "src/store/db.py": "import sqlite3\n\n\ndef save() -> None:\n    pass\n",
    "web/theme/index.js": "import { home } from './pages/home.js';\n",
    "web/theme/pages/home.js": (
        "import { Card } from '../widgets/card.js';\nimport { ref } from 'vue';\n"
        "export function home() { return Card(ref(0)); }\n"
    ),
    "web/theme/widgets/card.js": "export function Card(x) { return x; }\n",
}


@given("a Python service beside a JavaScript theme that is its own scan path")
def _mixed_project(tmp_path: Path, state: dict[str, Any], write_project: WriteProject) -> None:
    root = tmp_path / "mixed"
    write_project(root, _GRAPH, _CONFIG, _FILES)
    state["root"] = root
