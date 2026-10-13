"""``init`` reads a slice group as the slices in it (BDL-082 S2a, RFC D2, owner's ruling 3).

feature-sliced.design, *Slices and segments*: "Closely related slices can be structurally
grouped in a folder, but they should exercise the same isolation rules as other slices —
there should be no code sharing in that folder." Before this bead a folder of slices was
read as one slice, ``features-auth``: two false "no index" errors, and ``register``
importing ``login`` was inside one node, so no rule could see it.

A folder of a sliced layer is a slice when it holds a standard segment or an ``index``; a
folder that holds neither and whose children are slices is a group. The group has no node;
each slice in it is one, named ``<layer>-<group>-<slice>``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from beadloom.onboarding.scanner.fsd_layout import FsdLayout, read_fsd_layout

if TYPE_CHECKING:
    from pathlib import Path


def _write(root: Path, *paths: str) -> None:
    for rel in paths:
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("export const x = 1\n", encoding="utf-8")


def _layers(root: Path) -> None:
    """Three layers, so the tree reads as FSD: the group is added by each case."""
    _write(root, "src/pages/home/index.ts", "src/shared/lib/index.ts", "src/app/index.ts")


def _by_directory(layout: FsdLayout) -> dict[str, tuple[str, str | None, str, str | None]]:
    return {
        unit.directory: (unit.name, unit.layer, unit.role, unit.parent) for unit in layout.units
    }


def test_the_specifications_group_is_two_slices_and_no_node(tmp_path: Path) -> None:
    _layers(tmp_path)
    _write(
        tmp_path,
        "src/features/auth/login/index.ts",
        "src/features/auth/login/ui/form.ts",
        "src/features/auth/register/index.ts",
        "src/features/auth/register/ui/form.ts",
    )

    units = _by_directory(read_fsd_layout(tmp_path))

    assert units["src/features/auth/login"] == ("features-auth-login", "features", "slice", None)
    assert units["src/features/auth/register"] == (
        "features-auth-register",
        "features",
        "slice",
        None,
    )
    assert "src/features/auth" not in units


def test_a_slice_in_a_group_lists_only_its_own_files(tmp_path: Path) -> None:
    _layers(tmp_path)
    _write(
        tmp_path,
        "src/features/auth/login/index.ts",
        "src/features/auth/login/ui/form.ts",
        "src/features/auth/register/index.ts",
    )

    units = {unit.name: unit for unit in read_fsd_layout(tmp_path).units}

    assert units["features-auth-login"].files == (
        "src/features/auth/login/index.ts",
        "src/features/auth/login/ui/form.ts",
    )
    assert units["features-auth-register"].files == ("src/features/auth/register/index.ts",)


def test_a_folder_with_a_segment_and_no_index_is_a_slice(tmp_path: Path) -> None:
    # The two tests are alternatives: Steiger's `isSlice` reads the segments alone, and a
    # slice that has not yet written its public API is still a slice.
    _layers(tmp_path)
    _write(tmp_path, "src/entities/user/model/user.ts", "src/entities/user/api/get.ts")

    units = _by_directory(read_fsd_layout(tmp_path))

    assert units["src/entities/user"] == ("entities-user", "entities", "slice", None)
    assert "src/entities/user/model" not in units


def test_a_folder_with_an_index_and_no_segment_is_a_slice(tmp_path: Path) -> None:
    _layers(tmp_path)
    _write(tmp_path, "src/widgets/header/index.vue", "src/widgets/header/parts/Logo.vue")

    units = _by_directory(read_fsd_layout(tmp_path))

    assert units["src/widgets/header"] == ("widgets-header", "widgets", "slice", None)


@pytest.mark.parametrize("index", ["index.server.ts", "index.client.ts"])
def test_a_slice_entered_by_an_environment_specific_index_is_a_slice_of_its_group(
    tmp_path: Path, index: str
) -> None:
    # `/docs/reference/public-api`, *Environment-specific Public APIs*: a slice's public API
    # can be split into files that match the runtime environment. Such a file is the
    # slice's index, so the folder holding it is a slice and the folder above is a group.
    # `login` is the group's only folder, so nothing but its index can make it a slice.
    _layers(tmp_path)
    _write(
        tmp_path,
        f"src/features/auth/login/{index}",
        "src/features/auth/login/session/token.ts",
    )

    units = _by_directory(read_fsd_layout(tmp_path))

    assert units["src/features/auth/login"] == ("features-auth-login", "features", "slice", None)


def test_a_folder_holding_neither_and_no_slice_is_still_one_slice(tmp_path: Path) -> None:
    # Code in a sliced layer is never left out of the graph: a folder with no segment, no
    # index and no slice in it is read as before, as one slice the slice rules then judge.
    _layers(tmp_path)
    _write(tmp_path, "src/features/search/search.ts", "src/features/search/parts/box.ts")

    units = _by_directory(read_fsd_layout(tmp_path))

    assert units["src/features/search"] == ("features-search", "features", "slice", None)
    assert "src/features/search/parts" not in units


def test_a_group_with_an_index_of_its_own_is_a_slice(tmp_path: Path) -> None:
    # The index is the test that wins: a folder with a public API is a slice, and its
    # folders are what stands at that slice's top, which the shape rule judges.
    _layers(tmp_path)
    _write(
        tmp_path,
        "src/features/auth/index.ts",
        "src/features/auth/login/index.ts",
        "src/features/auth/register/index.ts",
    )

    units = _by_directory(read_fsd_layout(tmp_path))

    assert units["src/features/auth"] == ("features-auth", "features", "slice", None)
    assert "src/features/auth/login" not in units


def test_a_folder_beside_the_slices_of_a_group_is_read_as_a_slice_of_it(
    tmp_path: Path,
) -> None:
    # A group shares no code. A folder in it that is not slice-shaped is still code in
    # the layer, and reading it as a slice makes an import of it from a sibling a
    # same-layer crossing, which is the violation the specification names.
    _layers(tmp_path)
    _write(
        tmp_path,
        "src/features/auth/login/index.ts",
        "src/features/auth/common/token.ts",
    )

    units = _by_directory(read_fsd_layout(tmp_path))

    assert units["src/features/auth/common"] == (
        "features-auth-common",
        "features",
        "slice",
        None,
    )


def test_a_code_file_at_a_groups_top_belongs_to_no_unit(tmp_path: Path) -> None:
    # Left to `fsd-slice-shape`, which reports code at a group's top (BDL-082 S1b).
    _layers(tmp_path)
    _write(
        tmp_path,
        "src/features/auth/shared.ts",
        "src/features/auth/login/index.ts",
        "src/features/auth/register/index.ts",
    )

    layout = read_fsd_layout(tmp_path)
    files = {path for unit in layout.units for path in unit.files}

    assert "src/features/auth/shared.ts" not in files
    assert "src/features/auth" not in _by_directory(layout)


def test_groups_are_read_one_level_deep(tmp_path: Path) -> None:
    # A group inside a group is not descended: its folder is read as one slice of the
    # outer group, so the inner folders stand at that slice's top.
    _layers(tmp_path)
    _write(
        tmp_path,
        "src/features/account/login/index.ts",
        "src/features/account/settings/profile/index.ts",
        "src/features/account/settings/billing/index.ts",
    )

    units = _by_directory(read_fsd_layout(tmp_path))

    assert units["src/features/account/settings"] == (
        "features-account-settings",
        "features",
        "slice",
        None,
    )
    assert "src/features/account/settings/profile" not in units


def test_the_unsliced_layers_hold_no_groups(tmp_path: Path) -> None:
    # `shared` and `app` hold segments; `shared/ui/button/index.ts` is a per-component
    # public API entry of the `ui` segment, not a slice (RFC D5).
    _layers(tmp_path)
    _write(tmp_path, "src/shared/ui/button/index.ts", "src/shared/ui/input/index.ts")

    units = _by_directory(read_fsd_layout(tmp_path))

    assert units["src/shared/ui"] == ("shared-ui", "shared", "segment", "shared")
    assert "src/shared/ui/button" not in units
