"""Step implementations for `an_expo_module_bridges_its_typescript_to_its_native_parts.feature`.

BDL-080 S3b (`beadloom-wbqd`). Nothing is stubbed: the real `reindex` and
`incremental_reindex` run over the synthetic Expo app of `tests/support/expo_module_tree.py`,
with a graph written by hand, so what is measured is the derivation and not `init`. The
shared When steps are in this folder's `conftest.py`.
"""

from __future__ import annotations

import json
import shutil
import sqlite3
from typing import TYPE_CHECKING, Any

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from beadloom.application.reindex import incremental_reindex, reindex
from tests.support.expo_module_tree import EXPO_APP_TREE, HAPTIC_PULSE, SCREEN_LOCK

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    WriteProject = Callable[[Path, str, str, dict[str, str]], None]

pytest.importorskip("tree_sitter_typescript")

scenarios(
    "../../../graph/import-resolver/"
    "an_expo_module_bridges_its_typescript_to_its_native_parts.feature"
)

_CONFIG = "scan_paths:\n- app\n- src\n- modules\nlanguages:\n- .ts\n- .tsx\n- .swift\n- .kt\n"

#: A node per module, and the folders that get a node of their own in the scenario that has them.
_MODULE_NODES = {
    "screens": "app",
    "frontend": "src",
    "haptic-pulse": HAPTIC_PULSE,
    "screen-lock": SCREEN_LOCK,
}
_NATIVE_NODES = {
    "haptic-pulse-ios": f"{HAPTIC_PULSE}/ios",
    "haptic-pulse-android": f"{HAPTIC_PULSE}/android",
    "screen-lock-ios": f"{SCREEN_LOCK}/ios",
}

_DERIVED_USES = (
    "SELECT src_ref_id, dst_ref_id, extra FROM edges "
    "WHERE kind = 'uses' AND json_extract(extra, '$.derived') = 'expo-module'"
)


def _graph(nodes: dict[str, str]) -> str:
    """A root service and one component per source folder, each ``part_of`` the root."""
    lines = [
        "nodes:",
        "  - ref_id: pathfinder-app",
        "    kind: service",
        "    summary: The app.",
        '    source: ""',
    ]
    for ref_id, source in nodes.items():
        lines += [
            f"  - ref_id: {ref_id}",
            "    kind: component",
            f"    summary: The {ref_id} part.",
            f"    source: {source}/",
        ]
    lines.append("edges:")
    for ref_id in nodes:
        lines += [f"  - src: {ref_id}", "    dst: pathfinder-app", "    kind: part_of"]
    return "\n".join(lines) + "\n"


def _write(
    tmp_path: Path,
    state: dict[str, Any],
    write_project: WriteProject,
    nodes: dict[str, str],
    tree: dict[str, str],
) -> None:
    root = tmp_path / "pathfinder-app"
    write_project(root, _graph(nodes), _CONFIG, tree)
    state["root"] = root


@given("an Expo app with a node for each module and for each native folder")
def _with_native_nodes(tmp_path: Path, state: dict[str, Any], write_project: WriteProject) -> None:
    _write(tmp_path, state, write_project, {**_MODULE_NODES, **_NATIVE_NODES}, EXPO_APP_TREE)


@given("an Expo app with a node for each module and no node for its native folders")
def _without_native_nodes(
    tmp_path: Path, state: dict[str, Any], write_project: WriteProject
) -> None:
    _write(tmp_path, state, write_project, _MODULE_NODES, EXPO_APP_TREE)


@given("an Expo app whose module holds an android folder its config does not link")
def _unlinked_android(tmp_path: Path, state: dict[str, Any], write_project: WriteProject) -> None:
    tree = {
        **EXPO_APP_TREE,
        f"{SCREEN_LOCK}/android/src/main/java/expo/modules/screenlock/Unused.kt": (
            "package expo.modules.screenlock\n\nclass Unused\n"
        ),
    }
    nodes = {
        **_MODULE_NODES,
        **_NATIVE_NODES,
        "screen-lock-android": f"{SCREEN_LOCK}/android",
    }
    _write(tmp_path, state, write_project, nodes, tree)


@when(parsers.parse('the android block is removed from the config of "{module}"'))
def _android_removed(state: dict[str, Any], module: str) -> None:
    config = state["root"] / module / "expo-module.config.json"
    data = json.loads(config.read_text(encoding="utf-8"))
    data.pop("android")
    data["platforms"] = [p for p in data["platforms"] if p != "android"]
    config.write_text(json.dumps(data), encoding="utf-8")


@when("the index is updated incrementally")
def _incremental(state: dict[str, Any]) -> None:
    incremental_reindex(state["root"])


def _rows(root: Path) -> list[tuple[str, str, dict[str, Any]]]:
    with sqlite3.connect(root / ".beadloom" / "beadloom.db") as conn:
        rows = conn.execute(_DERIVED_USES).fetchall()
    return sorted((str(src), str(dst), json.loads(extra)) for src, dst, extra in rows)


def _pairs(root: Path) -> set[tuple[str, str]]:
    return {(src, dst) for src, dst, _ in _rows(root)}


@then(parsers.parse("the derived uses edges are exactly {edges}"))
def _exactly(state: dict[str, Any], edges: str) -> None:
    expected = {tuple(part.strip().split(" -> ")) for part in edges.replace('"', "").split(",")}
    assert _pairs(state["root"]) == expected


@then(
    parsers.parse(
        'the uses edge "{src} -> {dst}" was read from "{config}" for "{platform}", '
        'naming "{module}"'
    )
)
def _provenance(
    state: dict[str, Any], src: str, dst: str, config: str, platform: str, module: str
) -> None:
    extras = [extra for s, d, extra in _rows(state["root"]) if (s, d) == (src, dst)]
    assert extras == [
        {"derived": "expo-module", "config": config, "platform": platform, "modules": [module]}
    ]


@then(parsers.parse('no uses edge points at "{ref_id}"'))
def _none_into(state: dict[str, Any], ref_id: str) -> None:
    with sqlite3.connect(state["root"] / ".beadloom" / "beadloom.db") as conn:
        rows = conn.execute(
            "SELECT src_ref_id FROM edges WHERE kind = 'uses' AND dst_ref_id = ?", (ref_id,)
        ).fetchall()
    assert rows == []


@then("the project has no derived uses edge")
def _no_derived(state: dict[str, Any]) -> None:
    assert _rows(state["root"]) == []


@then("every derived uses edge equals a fresh index of the same tree")
def _equals_fresh(tmp_path: Path, state: dict[str, Any]) -> None:
    root: Path = state["root"]
    fresh = tmp_path / "fresh"
    shutil.copytree(root, fresh, ignore=shutil.ignore_patterns("beadloom.db*"))
    reindex(fresh)
    assert _rows(root) == _rows(fresh)
