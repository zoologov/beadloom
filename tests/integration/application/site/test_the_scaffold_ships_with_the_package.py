"""The portal scaffold is package data: in the installed package, and in the wheel.

BDL-076 B1 (``beadloom-dfwt``). Before this bead the theme, the viewer,
``package.json`` and the VitePress config existed in this repository alone, and
an adopter who wanted the portal copied them by hand. They now live under
``beadloom/site_scaffold/`` and ship with the package, so ``docs site`` writes
them from the installed version.

Two readings, because they fail differently. The package read through
``importlib.resources`` is what ``docs site`` reads at run time; the wheel is what
an adopter installs, and a build backend that drops a hidden directory such as
``.vitepress/`` would pass the first reading and fail the second.

Nothing in the scaffold may name this repository: its title, its base path or its
repository. The layer vocabulary is the project's, and the scaffold names none.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import zipfile
from importlib.resources import files
from typing import TYPE_CHECKING

import pytest

from beadloom.application.site.scaffold import MARKABLE_SUFFIXES, shipped_files
from tests.support.repository_root import REPO_ROOT

if TYPE_CHECKING:
    from pathlib import Path

#: Files the portal cannot build or be tested without, relative to the site root.
_REQUIRED = (
    ".vitepress/config.mjs",
    ".vitepress/theme/index.js",
    ".vitepress/theme/app/index.js",
    ".vitepress/theme/widgets/graph-viewer/ui/GraphViewer.vue",
    ".vitepress/theme/pages/architecture/ui/ArchitectureMap.vue",
    ".vitepress/theme/pages/landscape/ui/LandscapeMap.vue",
    "package.json",
    "package-lock.json",
    "e2e/playwright.config.js",
    "e2e/support/serve.mjs",
    "e2e/colours.spec.js",
)

#: This repository's identity, as the portal used to carry it.
_OUR_IDENTITY = ("zoologov", '"/beadloom/"', "'/beadloom/'", 'title: "Beadloom"')

#: The package-data directory inside the wheel.
_IN_WHEEL = "beadloom/site_scaffold/"


def test_the_installed_package_carries_the_scaffold() -> None:
    shipped = shipped_files()
    missing = [rel for rel in _REQUIRED if rel not in shipped]
    assert missing == []


def test_every_shipped_file_can_carry_the_generated_marker() -> None:
    unmarkable = sorted(
        rel for rel in shipped_files() if not rel.endswith(tuple(MARKABLE_SUFFIXES))
    )
    assert unmarkable == []


def test_nothing_shipped_names_this_repository() -> None:
    leaks = [
        (rel, token)
        for rel, body in shipped_files().items()
        for token in _OUR_IDENTITY
        if token in body
    ]
    assert leaks == []


def test_the_package_declares_its_node_version_and_an_exact_lock() -> None:
    shipped = shipped_files()
    package = json.loads(shipped["package.json"])
    lock = json.loads(shipped["package-lock.json"])
    assert package["engines"]["node"] == ">=20"
    assert lock["packages"][""]["engines"] == package["engines"]
    locked = lock["packages"][""]["dependencies"] | lock["packages"][""]["devDependencies"]
    declared = package["dependencies"] | package["devDependencies"]
    assert locked == declared
    # Exact pins, but for the one range the constraint names (CONTEXT: `web-worker`).
    ranged = sorted(name for name, pin in declared.items() if not pin[0].isdigit())
    assert ranged == ["web-worker"]


def test_the_scaffold_is_not_a_python_package() -> None:
    root = files("beadloom").joinpath("site_scaffold")
    assert root.is_dir()
    assert not root.joinpath("__init__.py").is_file()


def test_the_wheel_carries_every_shipped_file(tmp_path: Path) -> None:
    uv = shutil.which("uv")
    if uv is None:
        pytest.skip("uv is not on PATH, so no wheel can be built in this room")
    subprocess.run(  # noqa: S603 - a fixed build command over this repository's own source
        [uv, "build", "--wheel", "--out-dir", str(tmp_path), str(REPO_ROOT)],
        check=True,
        capture_output=True,
        encoding="utf-8",
    )
    (wheel,) = tmp_path.glob("beadloom-*.whl")
    with zipfile.ZipFile(wheel) as archive:
        in_wheel = {
            name.removeprefix(_IN_WHEEL)
            for name in archive.namelist()
            if name.startswith(_IN_WHEEL)
        }
    shipped = set(shipped_files())
    assert sorted(shipped - in_wheel) == []
    assert sorted(in_wheel - shipped) == []
    assert all(rel in in_wheel for rel in _REQUIRED)
