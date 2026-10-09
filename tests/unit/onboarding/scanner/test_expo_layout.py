"""``init`` reads each local Expo module as its TypeScript and its native parts (BDL-080 S3b).

A folder holding ``expo-module.config.json`` is one module: a unit for its own code, and a
part for each of ``ios/`` and ``android/`` that holds native code. The Expo bridge between
them is not written here; the reindex derives it from the config
(``graph/expo_modules.py``), so what is asked here is only which units ``init`` writes.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from beadloom.onboarding.scanner.expo_layout import (
    ExpoLayout,
    expo_nodes,
    read_expo_layout,
)
from beadloom.onboarding.scanner.ref_ids import RefIdAllocator
from tests.support.expo_module_tree import write_expo_app, write_tree

if TYPE_CHECKING:
    from pathlib import Path


def _shape(layout: ExpoLayout) -> dict[str, tuple[tuple[str, ...], dict[str, tuple[str, ...]]]]:
    return {
        module.directory: (
            module.files,
            {part.platform: part.files for part in module.parts},
        )
        for module in layout.modules
    }


def test_each_module_is_its_own_code_and_one_part_per_native_folder(tmp_path: Path) -> None:
    write_expo_app(tmp_path)

    assert _shape(read_expo_layout(tmp_path)) == {
        "modules/haptic-pulse": (
            (
                "modules/haptic-pulse/index.ts",
                "modules/haptic-pulse/src/HapticPulseModule.ts",
                "modules/haptic-pulse/src/HapticPulseModule.web.ts",
            ),
            {
                "ios": ("modules/haptic-pulse/ios/HapticPulseModule.swift",),
                "android": (
                    "modules/haptic-pulse/android/src/main/java/expo/modules/hapticpulse/"
                    "HapticPulseModule.kt",
                ),
            },
        ),
        "modules/screen-lock": (
            ("modules/screen-lock/index.ts",),
            {"ios": ("modules/screen-lock/ios/ScreenLockModule.swift",)},
        ),
    }


def test_a_native_folder_holding_no_code_is_no_part(tmp_path: Path) -> None:
    write_tree(
        tmp_path,
        {
            "modules/pulse/expo-module.config.json": "{}",
            "modules/pulse/index.ts": "export {}\n",
            "modules/pulse/ios/Pulse.podspec": "Pod::Spec.new do |s| end\n",
            "modules/pulse/android/build/generated/R.kt": "class R\n",
        },
    )

    assert _shape(read_expo_layout(tmp_path)) == {
        "modules/pulse": (("modules/pulse/index.ts",), {}),
    }


def test_the_folders_it_claims_scans_and_the_languages_it_reads(tmp_path: Path) -> None:
    write_expo_app(tmp_path)

    layout = read_expo_layout(tmp_path)

    assert layout.claimed == frozenset({"modules/haptic-pulse", "modules/screen-lock"})
    assert layout.scan_paths == ("modules/haptic-pulse", "modules/screen-lock")
    assert layout.languages == frozenset({".ts", ".swift", ".kt"})


def test_a_config_at_the_root_installed_or_skipped_is_no_module_here(tmp_path: Path) -> None:
    write_tree(
        tmp_path,
        {
            "expo-module.config.json": "{}",
            "index.ts": "export {}\n",
            "node_modules/expo-camera/expo-module.config.json": "{}",
            "node_modules/expo-camera/index.ts": "export {}\n",
            "src/modules/inner/expo-module.config.json": "{}",
            "src/modules/inner/index.ts": "export {}\n",
            ".expo/cache/expo-module.config.json": "{}",
        },
    )

    assert read_expo_layout(tmp_path, skip=("src",)).modules == ()


def test_a_tree_without_a_config_is_no_layout(tmp_path: Path) -> None:
    write_tree(tmp_path, {"modules/plain/index.ts": "export {}\n"})

    assert read_expo_layout(tmp_path) == ExpoLayout()


def test_the_nodes_are_the_module_holding_its_native_parts(tmp_path: Path) -> None:
    write_expo_app(tmp_path)
    ref_ids = RefIdAllocator(["pathfinder-app", "screen-lock"])

    graph = expo_nodes(
        read_expo_layout(tmp_path), ref_ids, "pathfinder-app", lambda unit: unit.directory
    )

    assert [(n["ref_id"], n["kind"], n["source"], n["summary"]) for n in graph.nodes] == [
        ("haptic-pulse", "component", "modules/haptic-pulse/", "modules/haptic-pulse"),
        ("haptic-pulse-ios", "component", "modules/haptic-pulse/ios/", "modules/haptic-pulse/ios"),
        (
            "haptic-pulse-android",
            "component",
            "modules/haptic-pulse/android/",
            "modules/haptic-pulse/android",
        ),
        # `screen-lock` was taken, so the module is qualified by its kind.
        ("screen-lock-component", "component", "modules/screen-lock/", "modules/screen-lock"),
        (
            "screen-lock-component-ios",
            "component",
            "modules/screen-lock/ios/",
            "modules/screen-lock/ios",
        ),
    ]
    assert list(graph.edges) == [
        {"src": "haptic-pulse", "dst": "pathfinder-app", "kind": "part_of"},
        {"src": "haptic-pulse-ios", "dst": "haptic-pulse", "kind": "part_of"},
        {"src": "haptic-pulse-android", "dst": "haptic-pulse", "kind": "part_of"},
        {"src": "screen-lock-component", "dst": "pathfinder-app", "kind": "part_of"},
        {"src": "screen-lock-component-ios", "dst": "screen-lock-component", "kind": "part_of"},
    ]
