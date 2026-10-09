"""``init`` reads a Feature-Sliced Design tree slice by slice (BDL-080 S3c, RFC D4).

A layer folder is no node; each slice of ``pages widgets features entities`` is one;
``app`` and ``shared`` hold segments, so each is a container whose segments are its parts;
a folder beside the layers (``components``, ``hooks``) is a legacy node, because a graph
that leaves half the code out says by omission that it is not there.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from beadloom.onboarding.scanner.fsd_layout import FsdLayout, read_fsd_layout

if TYPE_CHECKING:
    from pathlib import Path


def _write(root: Path, *paths: str) -> None:
    for rel in paths:
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("export const x = 1\n", encoding="utf-8")


def _tree(root: Path) -> None:
    _write(
        root,
        "src/main.ts",
        "src/app/index.ts",
        "src/app/providers/router.ts",
        "src/pages/home/index.ts",
        "src/pages/home/ui/HomePage.vue",
        "src/features/auth/index.ts",
        "src/features/auth/model/session.ts",
        "src/entities/user/index.ts",
        "src/shared/api/index.ts",
        "src/shared/ui/button.ts",
        "src/components/LegacyButton.ts",
        "src/hooks/useCart.ts",
        "src/node_modules/pkg/index.js",
        "src/assets/logo.ts",
    )


def _by_directory(layout: FsdLayout) -> dict[str, tuple[str, str | None, str, str | None]]:
    return {
        unit.directory: (unit.name, unit.layer, unit.role, unit.parent) for unit in layout.units
    }


def test_each_slice_is_a_unit_and_no_layer_is(tmp_path: Path) -> None:
    _tree(tmp_path)

    units = _by_directory(read_fsd_layout(tmp_path))

    assert units["src/pages/home"] == ("pages-home", "pages", "slice", None)
    assert units["src/features/auth"] == ("features-auth", "features", "slice", None)
    assert units["src/entities/user"] == ("entities-user", "entities", "slice", None)
    for layer in ("src/pages", "src/features", "src/entities"):
        assert layer not in units


def test_app_and_shared_are_containers_of_their_segments(tmp_path: Path) -> None:
    _tree(tmp_path)

    units = _by_directory(read_fsd_layout(tmp_path))

    assert units["src/app"] == ("app", "app", "container", None)
    assert units["src/app/providers"] == ("app-providers", "app", "segment", "app")
    assert units["src/shared"] == ("shared", "shared", "container", None)
    assert units["src/shared/api"] == ("shared-api", "shared", "segment", "shared")
    assert units["src/shared/ui"] == ("shared-ui", "shared", "segment", "shared")


def test_folders_beside_the_layers_are_legacy_units(tmp_path: Path) -> None:
    _tree(tmp_path)

    units = _by_directory(read_fsd_layout(tmp_path))

    assert units["src/components"] == ("components", None, "legacy", None)
    assert units["src/hooks"] == ("hooks", None, "legacy", None)
    # Dependencies and asset folders are no part of the architecture.
    assert "src/node_modules" not in units
    assert "src/assets" not in units


def test_a_unit_lists_the_code_files_below_it(tmp_path: Path) -> None:
    _tree(tmp_path)

    layout = read_fsd_layout(tmp_path)
    home = next(unit for unit in layout.units if unit.name == "pages-home")

    assert home.files == ("src/pages/home/index.ts", "src/pages/home/ui/HomePage.vue")


def test_a_container_holds_the_files_none_of_its_segments_does(tmp_path: Path) -> None:
    _tree(tmp_path)

    units = {unit.name: unit for unit in read_fsd_layout(tmp_path).units}

    assert units["app"].files == ("src/app/index.ts",)
    assert units["shared"].files == ()


def test_a_slice_with_no_code_is_no_unit(tmp_path: Path) -> None:
    _tree(tmp_path)
    (tmp_path / "src" / "widgets" / "empty").mkdir(parents=True)

    names = {unit.name for unit in read_fsd_layout(tmp_path).units}

    assert "widgets-empty" not in names


def test_the_fsd_root_is_claimed_whole_under_src(tmp_path: Path) -> None:
    _tree(tmp_path)

    layout = read_fsd_layout(tmp_path)

    assert layout.root == "src"
    assert layout.claimed == frozenset({"src"})


def test_at_the_root_only_the_layers_and_the_legacy_folders_are_claimed(
    tmp_path: Path,
) -> None:
    _write(
        tmp_path,
        "pages/home/index.ts",
        "features/auth/index.ts",
        "shared/lib/index.ts",
        "components/Old.ts",
        "tests/test_x.ts",
    )

    layout = read_fsd_layout(tmp_path)

    assert layout.root == ""
    assert layout.claimed == frozenset({"pages", "features", "shared", "components"})


def test_a_project_without_the_layout_reads_empty(tmp_path: Path) -> None:
    _write(tmp_path, "src/app/index.ts", "src/lib/x.ts")

    layout = read_fsd_layout(tmp_path)

    assert layout.root is None
    assert layout.units == ()
    assert layout.claimed == frozenset()
