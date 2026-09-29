"""Step implementations for `graph/import-resolver/relative_js_ts_imports.feature`.

BDL-076 J1 (`beadloom-hjr1`). Nothing here is stubbed: the real `reindex` runs
over a real project on disk, and `beadloom why` is invoked through the CLI the
way an adopter would run it, because the subject is the edge set a JS/TS project
gets and a double would agree with whatever the resolver does now.

**FAKES PROVE FAKES.** Both fixtures are projects this repository cannot be
mistaken for: `parcels` is TypeScript and `recipes` is JavaScript, and this
repository scans Python only.

The module is named `test_*` so default pytest collection picks the scenarios up.
"""

from __future__ import annotations

import json
import sqlite3
from typing import TYPE_CHECKING, Any

import pytest
from click.testing import CliRunner
from pytest_bdd import given, parsers, scenarios, then, when

from beadloom.application.reindex import reindex
from beadloom.services.cli import main

if TYPE_CHECKING:
    from pathlib import Path

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


def _write_project(root: Path, service: str, files: dict[str, str]) -> None:
    domains = tuple(sorted({path.split("/")[1] for path in files}))
    graph = root / ".beadloom" / "_graph"
    graph.mkdir(parents=True)
    (graph / "graph.yml").write_text(_graph(service, domains), encoding="utf-8")
    (root / ".beadloom" / "config.yml").write_text(_CONFIG, encoding="utf-8")
    for rel_path, text in files.items():
        path = root / rel_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")


def _connect(root: Path) -> sqlite3.Connection:
    return sqlite3.connect(root / ".beadloom" / "beadloom.db")


@pytest.fixture
def state() -> dict[str, Any]:
    """What the steps hand each other: the project root."""
    return {}


@given("a TypeScript package with nested folders and relative imports")
def _typescript_package(tmp_path: Path, state: dict[str, Any]) -> None:
    root = tmp_path / "parcels"
    _write_project(root, "parcels", _PARCELS)
    state["root"] = root


@given("a JavaScript package whose folders are entered through index files")
def _javascript_package(tmp_path: Path, state: dict[str, Any]) -> None:
    root = tmp_path / "recipes"
    _write_project(root, "recipes", _RECIPES)
    state["root"] = root


@when("the project is indexed")
def _indexed(state: dict[str, Any]) -> None:
    reindex(state["root"])


def _dependents(root: Path, ref_id: str) -> set[str]:
    result = CliRunner().invoke(main, ["why", ref_id, "--json", "--project", str(root)])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    return {str(item["ref_id"]) for item in payload["downstream"]}


@then(parsers.parse('why on "{ref_id}" lists "{first}" and "{second}" as dependents'))
def _why_lists_two(state: dict[str, Any], ref_id: str, first: str, second: str) -> None:
    assert {first, second} <= _dependents(state["root"], ref_id)


@then(parsers.parse('why on "{ref_id}" lists "{dependent}" as a dependent'))
def _why_lists_one(state: dict[str, Any], ref_id: str, dependent: str) -> None:
    assert dependent in _dependents(state["root"], ref_id)


@then(parsers.parse("the depends_on edges are exactly {edges}"))
def _edges_exactly(state: dict[str, Any], edges: str) -> None:
    expected = {tuple(part.strip().split(" -> ")) for part in edges.replace('"', "").split(",")}
    with _connect(state["root"]) as conn:
        actual = set(
            conn.execute(
                "SELECT src_ref_id, dst_ref_id FROM edges WHERE kind = 'depends_on'"
            ).fetchall()
        )
    assert actual == expected


def _resolved(root: Path, file_path: str, import_path: str) -> list[str | None]:
    with _connect(root) as conn:
        rows = conn.execute(
            "SELECT resolved_ref_id FROM code_imports WHERE file_path = ? AND import_path = ?",
            (file_path, import_path),
        ).fetchall()
    return [row[0] for row in rows]


@then(parsers.parse('the import "{import_path}" of "{file_path}" resolves to "{ref_id}"'))
def _resolves_to(state: dict[str, Any], import_path: str, file_path: str, ref_id: str) -> None:
    assert _resolved(state["root"], file_path, import_path) == [ref_id]


@then(parsers.parse('the import "{import_path}" of "{file_path}" is recorded with no node'))
def _recorded_unresolved(state: dict[str, Any], import_path: str, file_path: str) -> None:
    assert _resolved(state["root"], file_path, import_path) == [None]
