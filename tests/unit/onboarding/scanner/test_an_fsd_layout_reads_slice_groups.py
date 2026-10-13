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


def test_a_group_inside_a_group_beside_a_slice_is_read_as_its_slices(tmp_path: Path) -> None:
    # BDL-082 S2 fix (review S2R minor 3): groups are read at any depth. Until the fix the
    # inner group was one slice of the outer one, `features-account-settings`, so the
    # inner folders stood at that slice's top and an import between them was inside it.
    _layers(tmp_path)
    _write(
        tmp_path,
        "src/features/account/login/index.ts",
        "src/features/account/settings/profile/index.ts",
        "src/features/account/settings/billing/index.ts",
    )

    units = _by_directory(read_fsd_layout(tmp_path))

    assert units["src/features/account/settings/profile"] == (
        "features-account-settings-profile",
        "features",
        "slice",
        None,
    )
    assert units["src/features/account/settings/billing"][0] == (
        "features-account-settings-billing"
    )
    assert units["src/features/account/login"][0] == "features-account-login"
    assert "src/features/account/settings" not in units


def test_a_group_holding_only_a_group_is_read_as_the_slices_below_it(tmp_path: Path) -> None:
    # The sub-case S2R measured: `a` holds nothing but the group `b`, and the whole of `a`
    # was ONE slice, `features-a`, so `c` importing `d` was no edge at all.
    _layers(tmp_path)
    _write(tmp_path, "src/features/a/b/c/index.ts", "src/features/a/b/d/index.ts")

    units = _by_directory(read_fsd_layout(tmp_path))

    assert units["src/features/a/b/c"] == ("features-a-b-c", "features", "slice", None)
    assert units["src/features/a/b/d"] == ("features-a-b-d", "features", "slice", None)
    assert "src/features/a" not in units
    assert "src/features/a/b" not in units


def test_groups_are_read_at_any_depth(tmp_path: Path) -> None:
    _layers(tmp_path)
    _write(tmp_path, "src/entities/a/b/c/d/index.ts", "src/entities/a/b/c/e/model/e.ts")

    names = {unit.name for unit in read_fsd_layout(tmp_path).units}

    assert {"entities-a-b-c-d", "entities-a-b-c-e"} <= names
    assert names.isdisjoint({"entities-a", "entities-a-b", "entities-a-b-c"})


def test_a_slice_inside_a_slice_is_not_read_as_a_group(tmp_path: Path) -> None:
    # Descent stops at a slice: what stands inside one is that slice's own code, which the
    # shape rule judges, however slice-shaped its folders look.
    _layers(tmp_path)
    _write(
        tmp_path,
        "src/features/a/b/index.ts",
        "src/features/a/b/parts/c/index.ts",
        "src/features/a/b/parts/d/index.ts",
    )

    units = _by_directory(read_fsd_layout(tmp_path))

    assert units["src/features/a/b"][0] == "features-a-b"
    assert not any(directory.startswith("src/features/a/b/") for directory in units)


def test_a_linked_folder_inside_a_group_is_not_descended(tmp_path: Path) -> None:
    # Reading groups at any depth follows folders down; a link back up the tree would
    # never end. A linked folder is read as one slice, as a folder with no slice in it is.
    _layers(tmp_path)
    _write(tmp_path, "src/features/a/b/index.ts", "src/features/a/c/index.ts")
    try:
        (tmp_path / "src/features/a/loop").symlink_to(tmp_path / "src/features/a")
    except OSError:
        pytest.skip("this filesystem cannot create a symbolic link")

    units = _by_directory(read_fsd_layout(tmp_path))

    assert units["src/features/a/b"][0] == "features-a-b"
    assert units["src/features/a/loop"][0] == "features-a-loop"
    assert not any(directory.startswith("src/features/a/loop/") for directory in units)


def test_the_unsliced_layers_hold_no_groups(tmp_path: Path) -> None:
    # `shared` and `app` hold segments; `shared/ui/button/index.ts` is a per-component
    # public API entry of the `ui` segment, not a slice (RFC D5).
    _layers(tmp_path)
    _write(tmp_path, "src/shared/ui/button/index.ts", "src/shared/ui/input/index.ts")

    units = _by_directory(read_fsd_layout(tmp_path))

    assert units["src/shared/ui"] == ("shared-ui", "shared", "segment", "shared")
    assert "src/shared/ui/button" not in units
