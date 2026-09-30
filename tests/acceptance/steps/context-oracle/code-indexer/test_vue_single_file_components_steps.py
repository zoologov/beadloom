"""Steps for `context-oracle/code-indexer/vue_single_file_components.feature`.

BDL-076 J3, ``beadloom-tmxa``. Every step runs the real commands — ``reindex``,
``ctx --json`` and ``sync-check --json`` through the CLI — against a Vue app
written into a temporary directory. The app is not this repository: it has one
component per shape the indexer must read (``<script setup lang="ts">`` alone, a
plain ``<script>`` alone, and both blocks in one file) and one JavaScript module.

The project is written here rather than imported from ``tests.support``: the
acceptance suite is copied out of the repository and run standalone, where the
``tests`` package is not importable.
"""

from __future__ import annotations

import json
import subprocess
from typing import TYPE_CHECKING, Any

import pytest
import yaml
from click.testing import CliRunner
from pytest_bdd import given, scenarios, then, when

from beadloom.services.cli import main

if TYPE_CHECKING:
    from pathlib import Path

#: The script blocks are parsed by the TypeScript grammar of the `languages` extra.
pytest.importorskip("tree_sitter_typescript")

scenarios("../../../context-oracle/code-indexer/vue_single_file_components.feature")

COUNTER_VUE = """\
<template>
  <button @click="reset">{{ count }}</button>
</template>

<script setup lang="ts">
// beadloom:component=components
import { ref } from 'vue'
import { useCounter } from '../composables/useCounter.js'

const count = ref(0)

function reset(): void {
  count.value = 0
}
</script>

<style scoped>
button { color: red; }
</style>
"""

LEGACY_VUE = """\
<script>
// beadloom:component=components
export function formatLabel(value) {
  return `#${value}`
}

export default {
  name: 'Legacy',
  methods: { formatLabel },
}
</script>

<template>
  <span>{{ formatLabel(1) }}</span>
</template>
"""

BOTH_VUE = """\
<script lang="ts">
// beadloom:component=components
export const PAGE_SIZE = 20
</script>

<script setup lang="ts">
import { computed } from 'vue'

function pages(total: number): number {
  return Math.ceil(total / PAGE_SIZE)
}
</script>

<template>
  <p>{{ pages(100) }}</p>
</template>
"""

USE_COUNTER_JS = """\
// beadloom:component=composables
import { ref } from 'vue'

export const STEP = 1
export let mode = 'up'
export const double = (value) => value * 2

export function useCounter() {
  const count = ref(0)
  return { count }
}

export default useCounter

export async function loadChart() {
  return import('echarts')
}
"""

#: The function the symbol-change scenario adds to Counter's ``<script setup>``.
ADDED_FUNCTION = "\nfunction increment(): void {\n  count.value += 1\n}\n</script>"


@pytest.fixture()
def world() -> dict[str, Any]:
    return {}


def _write(root: Path, relative: str, text: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _cli(project: Path, *args: str, ok_codes: tuple[int, ...] = (0,)) -> str:
    result = CliRunner().invoke(main, [*args, "--project", str(project)])
    assert result.exit_code in ok_codes, result.output
    return result.output


def _git(project: Path, *args: str) -> None:
    subprocess.run(  # noqa: S603 - a fixed git invocation on a temporary repository
        ["git", *args],  # noqa: S607 - git is resolved from PATH, as every git step does
        cwd=project,
        check=True,
        capture_output=True,
    )


@given("a Vue app with a script setup component, a plain script component and one with both")
def _given_a_vue_app(world: dict[str, Any], tmp_path: Path) -> None:
    project = tmp_path / "shop"
    _write(project, "src/components/Counter.vue", COUNTER_VUE)
    _write(project, "src/components/Legacy.vue", LEGACY_VUE)
    _write(project, "src/components/Both.vue", BOTH_VUE)
    _write(project, "src/composables/useCounter.js", USE_COUNTER_JS)
    _write(project, ".beadloom/config.yml", "languages: [.js, .ts, .vue]\nscan_paths: [src]\n")
    nodes = [
        {"ref_id": "shop", "kind": "service", "summary": "Shop"},
        {
            "ref_id": "components",
            "kind": "component",
            "summary": "Components",
            "source": "src/components/",
            "docs": ["docs/components.md"],
        },
        {
            "ref_id": "composables",
            "kind": "component",
            "summary": "Composables",
            "source": "src/composables/",
            "docs": ["docs/composables.md"],
        },
    ]
    edges = [
        {"src": "components", "dst": "shop", "kind": "part_of"},
        {"src": "composables", "dst": "shop", "kind": "part_of"},
    ]
    _write(
        project,
        ".beadloom/_graph/services.yml",
        yaml.safe_dump({"nodes": nodes, "edges": edges}, sort_keys=False),
    )
    _write(project, "docs/components.md", "# Components\n")
    _write(project, "docs/composables.md", "# Composables\n")
    world["project"] = project


@given("its sync baseline is recorded")
def _given_a_baseline(world: dict[str, Any]) -> None:
    project = world["project"]
    _git(project, "init", "-q")
    _git(project, "add", "-A")
    _git(project, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "init")
    _cli(project, "reindex", "--full")
    world["baseline"] = _sync_pairs(project)


def _symbols_of(project: Path, ref_id: str) -> set[tuple[str, str, str, int, int]]:
    """The symbols `ctx` shows from the node's own source directory.

    A context bundle walks the node's subgraph, so it also carries the symbols of
    the neighbours it reaches; those are another scenario's subject.
    """
    _cli(project, "reindex", "--full")
    bundle = json.loads(_cli(project, "ctx", ref_id, "--json"))
    return {
        (
            str(s["file_path"]),
            str(s["symbol_name"]),
            str(s["kind"]),
            int(s["line_start"]),
            int(s["line_end"]),
        )
        for s in bundle["code_symbols"]
        if str(s["file_path"]).startswith(f"src/{ref_id}/")
    }


def _sync_pairs(project: Path) -> dict[str, dict[str, Any]]:
    report = json.loads(_cli(project, "sync-check", "--json", ok_codes=(0, 2)))
    return {str(p["code_path"]): p for p in report["pairs"]}


@when("the index is rebuilt and the context of the components node is read")
def _when_components_read(world: dict[str, Any]) -> None:
    world["symbols"] = _symbols_of(world["project"], "components")


@when("the index is rebuilt and the context of the composables node is read")
def _when_composables_read(world: dict[str, Any]) -> None:
    world["symbols"] = _symbols_of(world["project"], "composables")


@when("a function is added to the Counter script and the index is rebuilt")
def _when_a_function_is_added(world: dict[str, Any]) -> None:
    project = world["project"]
    counter = project / "src/components/Counter.vue"
    text = counter.read_text(encoding="utf-8").replace("</script>", ADDED_FUNCTION, 1)
    counter.write_text(text, encoding="utf-8")
    _cli(project, "reindex")
    world["pairs"] = _sync_pairs(project)


@when("only the style of Counter is edited and the index is rebuilt")
def _when_the_style_is_edited(world: dict[str, Any]) -> None:
    project = world["project"]
    counter = project / "src/components/Counter.vue"
    text = counter.read_text(encoding="utf-8").replace("color: red", "color: blue")
    counter.write_text(text, encoding="utf-8")
    _cli(project, "reindex")
    world["pairs"] = _sync_pairs(project)


@then("the context shows every component and its script symbols at their lines")
def _then_components(world: dict[str, Any]) -> None:
    assert world["symbols"] == {
        ("src/components/Counter.vue", "Counter", "component", 1, 19),
        ("src/components/Counter.vue", "reset", "function", 12, 14),
        ("src/components/Legacy.vue", "Legacy", "component", 1, 15),
        ("src/components/Legacy.vue", "formatLabel", "function", 3, 5),
        ("src/components/Both.vue", "Both", "component", 1, 16),
        ("src/components/Both.vue", "PAGE_SIZE", "variable", 3, 3),
        ("src/components/Both.vue", "pages", "function", 9, 11),
    }


@then("the context shows the exported constants, the let binding and the default export")
def _then_composables(world: dict[str, Any]) -> None:
    path = "src/composables/useCounter.js"
    assert world["symbols"] == {
        (path, "STEP", "variable", 4, 4),
        (path, "mode", "variable", 5, 5),
        (path, "double", "function", 6, 6),
        (path, "useCounter", "function", 8, 11),
        (path, "default", "variable", 13, 13),
        (path, "loadChart", "function", 15, 17),
    }


@then("sync-check says the other components are unverified because Counter.vue's symbols moved")
def _then_symbols_moved(world: dict[str, Any]) -> None:
    assert {p["status"] for p in world["baseline"].values()} == {"ok"}, world["baseline"]
    pairs = world["pairs"]
    assert pairs["src/components/Counter.vue"]["status"] == "stale"
    for sibling in ("src/components/Legacy.vue", "src/components/Both.vue"):
        assert pairs[sibling]["status"] == "unverified", pairs[sibling]
        assert pairs[sibling]["reason"] == "sibling_symbols_changed", pairs[sibling]
        assert "Counter.vue" in str(pairs[sibling].get("details", "")), pairs[sibling]


@then("sync-check reports Counter.vue stale by its hash and the other components ok")
def _then_hash_only(world: dict[str, Any]) -> None:
    assert {p["status"] for p in world["baseline"].values()} == {"ok"}, world["baseline"]
    pairs = world["pairs"]
    assert pairs["src/components/Counter.vue"]["status"] == "stale"
    assert pairs["src/components/Counter.vue"]["reason"] == "hash_changed"
    for sibling in ("src/components/Legacy.vue", "src/components/Both.vue"):
        assert pairs[sibling]["status"] == "ok", pairs[sibling]
