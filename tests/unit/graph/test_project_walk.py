"""The project's files, found by one walk with one skip list (BDL-080 S3f, ``beadloom-af99.14``).

The S3 review's minor 5 (``beadloom-jtki``): the tsconfig reader and the Expo module reader
each walked the whole project with their own copy of the skip list, so an incremental
reindex of a project with JavaScript imports walked it twice (77 and 84 ms on this
repository), and neither list held ``venv/`` or ``target/``, so a Python virtualenv or a
Rust build beside the app was walked too. One walk now serves both readers.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from beadloom.graph.project_walk import SKIPPED_DIRECTORIES, ProjectFiles

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path


def _touch(root: Path, *paths: str) -> None:
    for rel in paths:
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{}\n", encoding="utf-8")


def test_the_files_are_named_by_project_relative_path_sorted(tmp_path: Path) -> None:
    _touch(tmp_path, "tsconfig.json", "web/tsconfig.app.json", "web/src/main.ts")

    found = ProjectFiles(tmp_path).named(lambda name: name.startswith("tsconfig."))

    assert found == ("tsconfig.json", "web/tsconfig.app.json")


def test_each_folder_is_listed_with_its_file_names(tmp_path: Path) -> None:
    _touch(tmp_path, "b.json", "a.json", "web/c.json")

    assert ProjectFiles(tmp_path).folders == (("", ("a.json", "b.json")), ("web", ("c.json",)))


@pytest.mark.parametrize(
    "folder",
    ["node_modules", "dist", "build", "vendor", "Pods", "venv", ".venv", "target", ".cache"],
)
def test_installed_built_and_hidden_folders_are_not_walked(tmp_path: Path, folder: str) -> None:
    _touch(tmp_path, f"{folder}/tsconfig.json", f"app/{folder}/tsconfig.json")

    assert ProjectFiles(tmp_path).named(lambda name: name == "tsconfig.json") == ()


def test_the_skip_list_names_what_both_readers_skipped_and_the_virtualenvs_and_target() -> None:
    assert {"node_modules", "dist", "build", "vendor", "Pods"} <= SKIPPED_DIRECTORIES
    assert {"venv", ".venv", "target"} <= SKIPPED_DIRECTORIES


def test_a_symlinked_folder_is_not_followed(tmp_path: Path) -> None:
    _touch(tmp_path, "outside/tsconfig.json")
    (tmp_path / "app").mkdir()
    (tmp_path / "app" / "linked").symlink_to(tmp_path / "outside", target_is_directory=True)

    found = ProjectFiles(tmp_path / "app").named(lambda name: name == "tsconfig.json")

    assert found == ()


def test_the_project_is_walked_once_however_often_it_is_asked(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _touch(tmp_path, "tsconfig.json", "modules/pulse/expo-module.config.json")
    listed: list[Path] = []
    original = type(tmp_path).iterdir

    def _counting(self: Path) -> Iterator[Path]:  # a spy on the walk
        listed.append(self)
        return original(self)

    monkeypatch.setattr(type(tmp_path), "iterdir", _counting)
    files = ProjectFiles(tmp_path)
    files.named(lambda name: name == "tsconfig.json")
    files.named(lambda name: name == "expo-module.config.json")

    assert listed.count(tmp_path) == 1
