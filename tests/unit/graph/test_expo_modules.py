"""Unit tests for ``graph/expo_modules``: which native folders an Expo module's config links.

BDL-080 S3b (``beadloom-wbqd``), RFC D5 (e). Each case writes the files of a project and
asks which bridges its ``expo-module.config.json`` files declare. Which node owns each end,
and the edge written between them, is asked by the scenarios of
``an_expo_module_bridges_its_typescript_to_its_native_parts.feature`` and by the
integration cases of the edge refresh.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

from beadloom.graph.expo_modules import EXPO_MODULE_CONFIG, ExpoModules, NativeBridge

if TYPE_CHECKING:
    from pathlib import Path


def _module(root: Path, folder: str, config: object, *, native: tuple[str, ...] = ()) -> None:
    """Write a module folder: its config (a dict, or the raw text) and its native folders."""
    path = root / folder
    path.mkdir(parents=True, exist_ok=True)
    text = config if isinstance(config, str) else json.dumps(config)
    (path / EXPO_MODULE_CONFIG).write_text(text, encoding="utf-8")
    for platform in native:
        (path / platform).mkdir(exist_ok=True)


def _bridges(root: Path) -> list[tuple[str, str, tuple[str, ...]]]:
    return [(b.platform, b.folder, b.modules) for b in ExpoModules(root).bridges]


class TestThePlatformKeys:
    def test_apple_and_android_each_link_their_folder(self, tmp_path: Path) -> None:
        _module(
            tmp_path,
            "modules/pulse",
            {"apple": {"modules": ["PulseModule"]}, "android": {"modules": ["x.PulseModule"]}},
            native=("ios", "android"),
        )
        assert ExpoModules(tmp_path).bridges == (
            NativeBridge(
                config="modules/pulse/expo-module.config.json",
                platform="ios",
                folder="modules/pulse/ios",
                modules=("PulseModule",),
            ),
            NativeBridge(
                config="modules/pulse/expo-module.config.json",
                platform="android",
                folder="modules/pulse/android",
                modules=("x.PulseModule",),
            ),
        )

    def test_the_earlier_ios_key_is_read_when_apple_is_absent(self, tmp_path: Path) -> None:
        _module(tmp_path, "modules/lock", {"ios": {"modules": ["LockModule"]}}, native=("ios",))
        assert _bridges(tmp_path) == [("ios", "modules/lock/ios", ("LockModule",))]

    def test_apple_wins_over_ios_as_autolinking_reads_them(self, tmp_path: Path) -> None:
        _module(
            tmp_path,
            "modules/lock",
            {"apple": {"modules": ["New"]}, "ios": {"modules": ["Old"]}},
            native=("ios",),
        )
        assert _bridges(tmp_path) == [("ios", "modules/lock/ios", ("New",))]


class TestWhatLinksNothing:
    def test_a_platforms_list_that_does_not_name_the_platform(self, tmp_path: Path) -> None:
        _module(
            tmp_path,
            "modules/pulse",
            {
                "platforms": ["apple"],
                "apple": {"modules": ["A"]},
                "android": {"modules": ["b.B"]},
            },
            native=("ios", "android"),
        )
        assert _bridges(tmp_path) == [("ios", "modules/pulse/ios", ("A",))]

    def test_the_ios_platform_name_counts_for_the_ios_folder(self, tmp_path: Path) -> None:
        _module(
            tmp_path,
            "modules/lock",
            {"platforms": ["ios"], "ios": {"modules": ["L"]}},
            native=("ios",),
        )
        assert _bridges(tmp_path) == [("ios", "modules/lock/ios", ("L",))]

    @pytest.mark.parametrize(
        "block",
        [{}, {"modules": []}, {"modules": "PulseModule"}, {"modules": [1, None]}, "PulseModule"],
    )
    def test_a_block_that_names_no_module(self, tmp_path: Path, block: object) -> None:
        _module(tmp_path, "modules/pulse", {"apple": block}, native=("ios",))
        assert _bridges(tmp_path) == []

    def test_entries_that_are_not_names_are_left_out(self, tmp_path: Path) -> None:
        _module(tmp_path, "modules/pulse", {"apple": {"modules": ["A", 3, "B"]}}, native=("ios",))
        assert _bridges(tmp_path) == [("ios", "modules/pulse/ios", ("A", "B"))]

    def test_a_linked_platform_whose_folder_is_absent(self, tmp_path: Path) -> None:
        _module(tmp_path, "modules/pulse", {"android": {"modules": ["a.A"]}})
        assert _bridges(tmp_path) == []

    @pytest.mark.parametrize("text", ["", "{", "[1, 2]", '"apple"', "null"])
    def test_a_config_that_is_no_json_object(self, tmp_path: Path, text: str) -> None:
        _module(tmp_path, "modules/pulse", text, native=("ios",))
        assert _bridges(tmp_path) == []


class TestTheWalk:
    def test_every_module_of_the_project_is_found_in_path_order(self, tmp_path: Path) -> None:
        linked = {"apple": {"modules": ["M"]}}
        _module(tmp_path, "modules/zeta", linked, native=("ios",))
        _module(tmp_path, "packages/alpha", linked, native=("ios",))
        _module(tmp_path, "modules/beta", linked, native=("ios",))
        assert [folder for _, folder, _ in _bridges(tmp_path)] == [
            "modules/beta/ios",
            "modules/zeta/ios",
            "packages/alpha/ios",
        ]

    @pytest.mark.parametrize("skipped", ["node_modules/expo-camera", ".expo/x", "ios/Pods/y"])
    def test_installed_and_hidden_folders_are_not_walked(
        self, tmp_path: Path, skipped: str
    ) -> None:
        _module(tmp_path, skipped, {"apple": {"modules": ["M"]}}, native=("ios",))
        assert ExpoModules(tmp_path).bridges == ()
        assert ExpoModules(tmp_path).manifests == ()

    def test_the_manifests_are_each_config_by_path_and_text(self, tmp_path: Path) -> None:
        _module(tmp_path, "modules/pulse", "{}")
        _module(tmp_path, "modules/lock", '{"ios": {}}')
        assert ExpoModules(tmp_path).manifests == (
            ("modules/lock/expo-module.config.json", '{"ios": {}}'),
            ("modules/pulse/expo-module.config.json", "{}"),
        )


@pytest.mark.parametrize("skipped", ["venv/lib/x", ".venv/lib/x", "target/debug/x"])
def test_a_config_in_a_virtualenv_or_a_build_folder_is_not_read(
    tmp_path: Path, skipped: str
) -> None:
    # BDL-080 S3f (beadloom-af99.14): the walk skipped neither venv/ nor target/.
    _module(tmp_path, skipped, {"apple": {"modules": ["M"]}}, native=("ios",))

    assert ExpoModules(tmp_path).manifests == ()
