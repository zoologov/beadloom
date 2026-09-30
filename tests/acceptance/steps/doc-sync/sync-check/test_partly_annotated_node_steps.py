"""Steps for `doc-sync/sync-check/partly_annotated_node_keeps_its_pairs.feature`.

BDL-076 K2, ``beadloom-oo4m``. Every step runs the real commands, ``reindex`` and
``sync-check --json`` through the CLI, against a Vue app written into a temporary
directory. The app is not this repository. It has one node whose three files sit
in three Feature-Sliced segment folders (``model/``, ``lib/``, ``ui/``), and only
the JavaScript model carries a ``beadloom:`` annotation.

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

#: The annotation in a `.js` or `.vue` file is read by the TypeScript grammar of the
#: `languages` extra. Without it no file carries an annotation, and the scenario
#: this feature exists for cannot be set up.
pytest.importorskip("tree_sitter_typescript")

scenarios("../../../doc-sync/sync-check/partly_annotated_node_keeps_its_pairs.feature")

MODEL = "src/counter/model/useCounter.js"
LIB = "src/counter/lib/format.js"
UI = "src/counter/ui/Counter.vue"
MISSPELLED = "src/counter/ui/Badge.vue"

USE_COUNTER_JS = """\
// beadloom:component=counter
import { ref } from 'vue'

export function useCounter() {
  const count = ref(0)
  return { count }
}
"""

FORMAT_JS = """\
export function formatCount(value) {
  return `#${value}`
}
"""

COUNTER_VUE = """\
<template>
  <button @click="reset">{{ label }}</button>
</template>

<script setup>
import { computed } from 'vue'
import { useCounter } from '../model/useCounter.js'
import { formatCount } from '../lib/format.js'

const { count } = useCounter()
const label = computed(() => formatCount(count.value))

function reset() {
  count.value = 0
}
</script>
"""

BADGE_VUE = """\
<template>
  <span>{{ text }}</span>
</template>

<script setup>
// beadloom:component=countr
const text = 'badge'
</script>
"""


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


def _sync_pairs(project: Path) -> list[dict[str, Any]]:
    report = json.loads(_cli(project, "sync-check", "--json", ok_codes=(0, 2)))
    return [p for p in report["pairs"] if p["ref_id"] == "counter"]


def _by_code_path(pairs: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(p["code_path"]): p for p in pairs}


@given("a Vue node of three files in three folders, only the JavaScript model annotated")
def _given_a_vue_node(world: dict[str, Any], tmp_path: Path) -> None:
    project = tmp_path / "shop"
    _write(project, MODEL, USE_COUNTER_JS)
    _write(project, LIB, FORMAT_JS)
    _write(project, UI, COUNTER_VUE)
    _write(project, ".beadloom/config.yml", "languages: [.js, .vue]\nscan_paths: [src]\n")
    nodes = [
        {"ref_id": "shop", "kind": "service", "summary": "Shop"},
        {
            "ref_id": "counter",
            "kind": "component",
            "summary": "Counter",
            "source": "src/counter/",
            "docs": ["docs/counter.md"],
        },
    ]
    edges = [{"src": "counter", "dst": "shop", "kind": "part_of"}]
    _write(
        project,
        ".beadloom/_graph/services.yml",
        yaml.safe_dump({"nodes": nodes, "edges": edges}, sort_keys=False),
    )
    _write(project, "docs/counter.md", "# Counter\n")
    world["project"] = project


@given("a fourth Vue file in the node whose annotation misspells the node")
def _given_a_misspelled_annotation(world: dict[str, Any]) -> None:
    _write(world["project"], MISSPELLED, BADGE_VUE)


@given("its sync baseline is recorded")
def _given_a_baseline(world: dict[str, Any]) -> None:
    project = world["project"]
    _git(project, "init", "-q")
    _git(project, "add", "-A")
    _git(project, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "init")
    _cli(project, "reindex", "--full")
    world["baseline"] = _by_code_path(_sync_pairs(project))


@when("the index is rebuilt and sync-check runs")
def _when_checked(world: dict[str, Any]) -> None:
    project = world["project"]
    _cli(project, "reindex", "--full")
    world["pairs"] = _sync_pairs(project)


@when("only the template of the unannotated Vue file is edited and the index is rebuilt")
def _when_the_template_is_edited(world: dict[str, Any]) -> None:
    project = world["project"]
    counter = project / UI
    text = counter.read_text(encoding="utf-8").replace("<button", '<button class="big"')
    counter.write_text(text, encoding="utf-8")
    _cli(project, "reindex")
    world["pairs"] = _sync_pairs(project)


@then("each of the three files is paired with the node's document")
def _then_three_pairs(world: dict[str, Any]) -> None:
    pairs = world["pairs"]
    assert {p["code_path"] for p in pairs} == {MODEL, LIB, UI}, pairs
    assert {p["doc_path"] for p in pairs} == {"counter.md"}, pairs


@then("sync-check reports the Vue file's pair stale and its siblings ok")
def _then_the_vue_file_is_stale(world: dict[str, Any]) -> None:
    baseline = world["baseline"]
    assert set(baseline) == {MODEL, LIB, UI}, baseline
    assert {p["status"] for p in baseline.values()} == {"ok"}, baseline
    pairs = _by_code_path(world["pairs"])
    assert pairs[UI]["status"] == "stale", pairs[UI]
    assert pairs[UI]["reason"] == "hash_changed", pairs[UI]
    for sibling in (MODEL, LIB):
        assert pairs[sibling]["status"] == "ok", pairs[sibling]


@then("sync-check names the misspelled Vue file as untracked under the node's document")
def _then_the_misspelled_file_is_named(world: dict[str, Any]) -> None:
    pairs = world["pairs"]
    assert MISSPELLED not in {p["code_path"] for p in pairs}, pairs
    flagged = [p for p in pairs if p["reason"] == "untracked_files"]
    assert flagged, pairs
    for pair in flagged:
        assert pair["status"] == "stale", pair
        assert "Badge.vue" in str(pair.get("details", "")), pair
