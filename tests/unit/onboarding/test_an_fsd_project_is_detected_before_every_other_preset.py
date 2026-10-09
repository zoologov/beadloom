"""The ``fsd`` preset is detected before every other one (BDL-080 S3c, RFC D4).

Feature-Sliced Design names six layer folders — ``app pages widgets features entities
shared`` — at the project root or under ``src/``. Three of them present is the layout;
fewer is a coincidence of names (a monolith has ``app/`` and ``shared/`` often enough).
The check runs before the mobile short-circuit, because a React Native or Expo project in
the FSD layout used to be read as a monolith whose layers were domains, and before the
``services/`` and ``packages/`` heuristics for the same reason.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from beadloom.onboarding.presets import FSD, FSD_LAYERS, PRESETS, detect_preset, fsd_root

if TYPE_CHECKING:
    from pathlib import Path


def _folders(root: Path, *names: str) -> None:
    for name in names:
        (root / name).mkdir(parents=True)


def test_the_six_layers_are_named_in_fsd_order() -> None:
    assert FSD_LAYERS == ("app", "pages", "widgets", "features", "entities", "shared")


def test_three_layers_under_src_are_an_fsd_project(tmp_path: Path) -> None:
    _folders(tmp_path, "src/app", "src/features", "src/shared")

    assert fsd_root(tmp_path) == "src"
    assert detect_preset(tmp_path) is FSD


def test_three_layers_at_the_root_are_an_fsd_project(tmp_path: Path) -> None:
    _folders(tmp_path, "pages", "entities", "shared")

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

    assert detect_preset(tmp_path) is FSD


def test_the_preset_is_registered_under_its_name() -> None:
    assert PRESETS["fsd"] is FSD
    assert FSD.name == "fsd"
