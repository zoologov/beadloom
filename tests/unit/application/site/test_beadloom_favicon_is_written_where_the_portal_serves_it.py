"""Beadloom's favicon is written into the portal it serves, a folder that may not exist yet.

BDL-080 S4e (``beadloom-af99.9``) and S4c (``beadloom-e1xo``): a portal without a
logo of its own takes Beadloom's favicon, the theme-adaptive SVG and the two PNGs,
copied from the package into ``public/brand/`` on every run that uses them.
"""

from __future__ import annotations

from importlib.resources import files
from typing import TYPE_CHECKING

from beadloom.application.site.favicon import write_beadloom_favicon

if TYPE_CHECKING:
    from pathlib import Path

_NAMES = ("beadloom-favicon.svg", "beadloom-favicon.png", "beadloom-favicon-dark.png")


def test_the_three_files_are_copied_into_a_portal_folder_that_does_not_exist_yet(
    tmp_path: Path,
) -> None:
    out_dir = tmp_path / "not-yet" / "site"

    written = write_beadloom_favicon(out_dir)

    brand = out_dir / "public" / "brand"
    assert written == [brand / name for name in _NAMES]
    shipped = files("beadloom").joinpath("site_favicon")
    assert [path.read_bytes() for path in written] == [
        shipped.joinpath(name).read_bytes() for name in _NAMES
    ]
