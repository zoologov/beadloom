"""Step implementations for `graph/import-resolver/vue_and_dynamic_imports.feature`.

BDL-076 J2 (`beadloom-g9fb`), scope added from J3 (`beadloom-tmxa`). The fixture is
A0's two-file Vue app grown by one lazily loaded chart: a component whose
`<script setup>` imports a composable and loads a chart through `import('...')`.
The shared When/Then steps are in this folder's `conftest.py`.

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

scenarios("../../../graph/import-resolver/vue_and_dynamic_imports.feature")

_CONFIG = "scan_paths:\n- src\n"

_GRAPH = """\
nodes:
  - ref_id: counter-app
    kind: service
    summary: A Vue app.
    source: ""
  - ref_id: components
    kind: domain
    summary: The components.
    source: src/components/
  - ref_id: composables
    kind: domain
    summary: The composables.
    source: src/composables/
  - ref_id: charts
    kind: domain
    summary: The charts, loaded on demand.
    source: src/charts/
edges:
  - {src: components, dst: counter-app, kind: part_of}
  - {src: composables, dst: counter-app, kind: part_of}
  - {src: charts, dst: counter-app, kind: part_of}
"""

_FILES: dict[str, str] = {
    "src/components/Counter.vue": (
        "<template>\n"
        "  <b>{{ n }}</b>\n"
        "</template>\n"
        "<script setup>\n"
        "import { useCounter } from '../composables/useCounter.js';\n"
        "const chart = () => import('../charts/bar');\n"
        "const n = useCounter();\n"
        "</script>\n"
    ),
    "src/composables/useCounter.js": (
        "import { ref } from 'vue';\nexport function useCounter() { return ref(0); }\n"
    ),
    "src/charts/bar.ts": "export function bar(): number { return 1; }\n",
}


@given("a Vue app whose component imports a composable from its script setup block")
def _vue_app(tmp_path: Path, state: dict[str, Any], write_project: WriteProject) -> None:
    root = tmp_path / "counter-app"
    write_project(root, _GRAPH, _CONFIG, _FILES)
    state["root"] = root
