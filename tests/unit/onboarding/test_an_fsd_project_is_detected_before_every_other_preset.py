"""The ``fsd`` preset is detected before every other one (BDL-080 S3c, RFC D4).

Feature-Sliced Design names six layer folders — ``app pages widgets features entities
shared`` — at the project root or under ``src/``. Three of them present is the layout;
fewer is a coincidence of names (a monolith has ``app/`` and ``shared/`` often enough).
The check runs before the mobile short-circuit, because a React Native or Expo project in
the FSD layout used to be read as a monolith whose layers were domains, and before the
``services/`` and ``packages/`` heuristics for the same reason.

Folder names alone are not the layout (BDL-080 S3f, the S3 review's major): a Python tree
in the clean-architecture style holds ``app/``, ``entities/`` and ``shared/`` as often as a
frontend does, and read as FSD it was given a frontend's rules and lost a node. So the
layout counts only on a frontend: the layer folders hold JavaScript, TypeScript or Vue
code, or a ``package.json`` sits at the project root or in the FSD root.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

from beadloom.onboarding.presets import FSD, FSD_LAYERS, PRESETS, detect_preset, fsd_root

if TYPE_CHECKING:
    from pathlib import Path


def _folders(root: Path, *names: str) -> None:
    for name in names:
        (root / name).mkdir(parents=True)


def _files(root: Path, *paths: str) -> None:
    for rel in paths:
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("x = 1\n", encoding="utf-8")


def test_the_six_layers_are_named_in_fsd_order() -> None:
    assert FSD_LAYERS == ("app", "pages", "widgets", "features", "entities", "shared")


def test_three_layers_under_src_are_an_fsd_project(tmp_path: Path) -> None:
    _folders(tmp_path, "src/app", "src/features", "src/shared")
    _files(tmp_path, "src/features/auth/index.ts")

    assert fsd_root(tmp_path) == "src"
    assert detect_preset(tmp_path) is FSD


def test_three_layers_at_the_root_are_an_fsd_project(tmp_path: Path) -> None:
    _folders(tmp_path, "pages", "entities", "shared")
    _files(tmp_path, "pages/home/ui/HomePage.vue")

    assert fsd_root(tmp_path) == ""
    assert detect_preset(tmp_path) is FSD


def test_two_layers_are_not_enough(tmp_path: Path) -> None:
    _folders(tmp_path, "src/app", "src/shared", "src/components")

    assert fsd_root(tmp_path) is None
    assert detect_preset(tmp_path).name == "monolith"


def test_a_layer_name_on_a_file_is_not_a_layer(tmp_path: Path) -> None:
    _folders(tmp_path, "src/app", "src/shared")
    (tmp_path / "src" / "pages").write_text("not a folder\n", encoding="utf-8")

    assert fsd_root(tmp_path) is None


def test_src_is_read_before_the_root(tmp_path: Path) -> None:
    # An Expo project keeps its router in `app/` at the root and FSD under `src/`.
    _folders(tmp_path, "app", "src/pages", "src/features", "src/entities", "src/shared")

    assert fsd_root(tmp_path) == "src"


def test_fsd_is_detected_before_the_mobile_short_circuit(tmp_path: Path) -> None:
    (tmp_path / "package.json").write_text(
        json.dumps({"dependencies": {"react-native": "0.76.0", "expo": "52.0.0"}}),
        encoding="utf-8",
    )
    _folders(tmp_path, "src/app", "src/features", "src/entities", "src/shared")

    assert detect_preset(tmp_path) is FSD


def test_fsd_is_detected_before_the_services_heuristic(tmp_path: Path) -> None:
    _folders(tmp_path, "services", "src/widgets", "src/features", "src/shared")
    _files(tmp_path, "src/shared/api/client.js")

    assert detect_preset(tmp_path) is FSD


def test_a_python_tree_with_layer_named_folders_is_a_monolith(tmp_path: Path) -> None:
    # The reviewer's probe (beadloom-jtki, major 1): fsd on 4b42e86f, monolith on main.
    _files(
        tmp_path,
        "pyproject.toml",
        "src/app/main.py",
        "src/entities/order.py",
        "src/shared/clock.py",
        "src/infrastructure/repo.py",
    )

    assert fsd_root(tmp_path) == "src"
    assert detect_preset(tmp_path).name == "monolith"


@pytest.mark.parametrize("suffix", [".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".vue"])
def test_layer_folders_holding_frontend_code_are_fsd_without_a_package_json(
    tmp_path: Path, suffix: str
) -> None:
    _folders(tmp_path, "src/app", "src/entities", "src/shared")
    _files(tmp_path, f"src/entities/user/model/user{suffix}")

    assert detect_preset(tmp_path) is FSD


@pytest.mark.parametrize("folder", ["", "src"])
def test_a_package_json_at_the_root_or_in_the_fsd_root_makes_it_fsd(
    tmp_path: Path, folder: str
) -> None:
    _folders(tmp_path, "src/pages", "src/features", "src/shared")
    _files(tmp_path, f"{folder}/package.json" if folder else "package.json")

    assert detect_preset(tmp_path) is FSD


def test_frontend_code_inside_node_modules_is_not_evidence(tmp_path: Path) -> None:
    _files(
        tmp_path,
        "src/app/main.py",
        "src/entities/order.py",
        "src/shared/node_modules/left-pad/index.js",
    )

    assert detect_preset(tmp_path).name == "monolith"


def test_the_preset_is_registered_under_its_name() -> None:
    assert PRESETS["fsd"] is FSD
    assert FSD.name == "fsd"
