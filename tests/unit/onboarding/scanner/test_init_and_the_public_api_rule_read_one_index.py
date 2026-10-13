"""``init`` and ``fsd-public-api`` read a slice's ``index`` with one reader (BDL-082 S2 fix).

Review S2R (``beadloom-r8y2``), minor 2: ``init`` decided whether a folder is a slice by its
own test for an ``index`` file, over the scanner's code extensions, while the public-API rule
read the import resolver's module extensions. The two sets differ in both directions, so a
folder holding only ``index.py`` was a slice to ``init`` and had no public API to the rule,
and a folder holding only ``index.mjs`` the reverse. One reader now answers for both.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from beadloom.graph.js_specifiers import MODULE_EXTENSIONS
from beadloom.graph.rules.slice_units import has_index
from beadloom.onboarding.scanner.constants import _CODE_EXTENSIONS
from beadloom.onboarding.scanner.fsd_layout import read_fsd_layout

if TYPE_CHECKING:
    from pathlib import Path

#: Every extension either reader has ever counted, so a difference shows on one of them.
_EITHER_SET = sorted(set(MODULE_EXTENSIONS) | _CODE_EXTENSIONS)


def _write(root: Path, *paths: str) -> None:
    for rel in paths:
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("export const x = 1\n", encoding="utf-8")


@pytest.mark.parametrize("extension", _EITHER_SET)
def test_a_folder_is_a_slice_of_its_group_exactly_when_the_rule_finds_its_index(
    tmp_path: Path, extension: str
) -> None:
    # `login` holds its index and a folder no standard segment is named after, so the index
    # alone decides whether `auth` is a group of slices or one slice.
    _write(
        tmp_path,
        "src/pages/home/index.ts",
        "src/shared/lib/index.ts",
        f"src/features/auth/login/index{extension}",
        "src/features/auth/login/session/token.ts",
    )

    names = {unit.name for unit in read_fsd_layout(tmp_path).units}

    read_as_a_group = "features-auth-login" in names
    assert read_as_a_group == has_index("src/features/auth/login", tmp_path), sorted(names)
