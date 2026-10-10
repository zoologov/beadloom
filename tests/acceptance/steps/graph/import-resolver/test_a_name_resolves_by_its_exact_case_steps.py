"""Step implementations for `graph/import-resolver/a_name_resolves_by_its_exact_case.feature`.

BDL-080 S3e (`beadloom-af99.12`). The real `reindex` runs over a small Vue app on disk.
On a case-sensitive filesystem (Linux) `src/app.vue` does not exist and the first two
scenarios hold by construction; they are red only where the filesystem folds case, which
is where the defect lived (macOS), and they keep the two from drifting apart again.

The shared When/Then steps are in this folder's `conftest.py`.
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

scenarios("../../../graph/import-resolver/a_name_resolves_by_its_exact_case.feature")

_CONFIG = "scan_paths:\n- src\nlanguages:\n- .ts\n- .vue\n"

_GRAPH = """nodes:
  - ref_id: storefront
    kind: service
    summary: The storefront.
    source: src/
  - ref_id: app
    kind: component
    summary: The app layer.
    source: src/app/
edges:
  - src: app
    dst: storefront
    kind: part_of
"""

_FILES: dict[str, str] = {
    "tsconfig.json": '{"compilerOptions": {"baseUrl": ".", "paths": {"@/*": ["src/*"]}}}\n',
    "src/main.ts": (
        "import { mountApp } from './app'\nimport App from './App.vue'\nmountApp(App)\n"
    ),
    "src/router.ts": "import { mountApp } from '@/app'\nexport const routes = [mountApp]\n",
    "src/App.vue": "<script setup lang=\"ts\">\nconst title = 'Store'\n</script>\n",
    "src/app/index.ts": "export function mountApp(app: unknown) { return app }\n",
}


@given("a Vue app with src/App.vue beside the folder src/app/ entered through its index")
def _vue_app(tmp_path: Path, state: dict[str, Any], write_project: WriteProject) -> None:
    root = tmp_path / "storefront"
    write_project(root, _GRAPH, _CONFIG, _FILES)
    state["root"] = root
