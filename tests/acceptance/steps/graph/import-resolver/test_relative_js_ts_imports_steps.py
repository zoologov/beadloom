"""Step implementations for `graph/import-resolver/relative_js_ts_imports.feature`.

BDL-076 J1 (`beadloom-hjr1`). Nothing here is stubbed: the real `reindex` runs
over a real project on disk, and `beadloom why` is invoked through the CLI the
way an adopter would run it, because the subject is the edge set a JS/TS project
gets and a double would agree with whatever the resolver does now.

**FAKES PROVE FAKES.** Both fixtures are projects this repository cannot be
mistaken for: `parcels` is TypeScript and `recipes` is JavaScript, and this
repository scans Python only.

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

scenarios("../../../graph/import-resolver/relative_js_ts_imports.feature")

_CONFIG = "scan_paths:\n- src\nlanguages:\n- .ts\n- .tsx\n- .js\n- .jsx\n"


def _graph(service: str, domains: tuple[str, ...]) -> str:
    """A root service with one domain per top-level folder of ``src/``."""
    lines = [
        "nodes:",
        f"  - ref_id: {service}",
        "    kind: service",
        f"    summary: The {service} service.",
        '    source: ""',
    ]
    for domain in domains:
        lines += [
            f"  - ref_id: {domain}",
            "    kind: domain",
            f"    summary: The {domain} domain.",
            f"    source: src/{domain}/",
        ]
    lines.append("edges:")
    for domain in domains:
        lines += [f"  - src: {domain}", f"    dst: {service}", "    kind: part_of"]
    return "\n".join(lines) + "\n"


#: The TypeScript package: nested folders, a `.tsx` module, an import written
#: with `.js` that names a `.ts` source, an import inside one node, a package
#: import and a relative import that names no file.
_PARCELS: dict[str, str] = {
    "src/app/main.ts": (
        "import { track } from '../tracking/track';\n"
        "import { Carrier } from '../tracking/carriers/carrier.js';\n"
        "import { money } from '../shared/money';\n"
        "import { gone } from './missing';\n"
        "export function main(): void { track(); }\n"
    ),
    "src/tracking/track.ts": (
        "import { fmtDate } from '../shared/dates';\n"
        "import { Carrier } from './carriers/carrier';\n"
        "import lodash from 'lodash';\n"
        "export function track(): void { fmtDate(); }\n"
    ),
    "src/tracking/carriers/carrier.ts": "export class Carrier {}\n",
    "src/shared/dates.ts": "export function fmtDate(): string { return ''; }\n",
    "src/shared/money.tsx": "export function money(): number { return 1; }\n",
}

#: The JavaScript package: folders entered through their index files, one of
#: them an `.mjs` the indexer does not parse but the resolver can still name, and
#: an index that re-exports its folder's parts.
_RECIPES: dict[str, str] = {
    "src/pages/home.js": (
        "import { Card } from '../ui';\n"
        "import { load } from '../data/store';\n"
        "export function home() { return Card(load()); }\n"
    ),
    "src/ui/index.js": "export { Card } from './card';\n",
    "src/ui/card/index.jsx": "export function Card(x) { return x; }\n",
    "src/data/store/index.mjs": "export function load() { return 1; }\n",
    "src/data/api.js": (
        "import { load } from './store/index.mjs';\nexport function api() { return load(); }\n"
    ),
}


def _write_project(
    write_project: WriteProject, root: Path, service: str, files: dict[str, str]
) -> None:
    domains = tuple(sorted({path.split("/")[1] for path in files}))
    write_project(root, _graph(service, domains), _CONFIG, files)


@given("a TypeScript package with nested folders and relative imports")
def _typescript_package(
    tmp_path: Path, state: dict[str, Any], write_project: WriteProject
) -> None:
    root = tmp_path / "parcels"
    _write_project(write_project, root, "parcels", _PARCELS)
    state["root"] = root


@given("a JavaScript package whose folders are entered through index files")
def _javascript_package(
    tmp_path: Path, state: dict[str, Any], write_project: WriteProject
) -> None:
    root = tmp_path / "recipes"
    _write_project(write_project, root, "recipes", _RECIPES)
    state["root"] = root
