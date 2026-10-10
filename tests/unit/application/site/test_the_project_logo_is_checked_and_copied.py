"""``site.logo``: the project's own SVG or PNG, checked against the project and copied.

BDL-080 S4d (``beadloom-af99.7``), the owner's ruling of 2026-10-09: the nav of a
portal shows the adopter's logo, a file of the project named from its root and
copied into the portal's ``public/``; without one the nav shows none.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from beadloom.application.site.site_config import read_site_config
from beadloom.application.site.site_logo import copy_logo, logo_site_path, read_logo

if TYPE_CHECKING:
    from pathlib import Path


def _project(tmp_path: Path, block: str, *files: str) -> Path:
    root = tmp_path / "orders"
    (root / ".beadloom").mkdir(parents=True)
    (root / ".beadloom" / "config.yml").write_text(block, encoding="utf-8")
    for rel in files:
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_bytes(b"<svg/>")
    return root


@pytest.mark.parametrize(
    ("value", "kept"),
    [
        ("art/logo.svg", "art/logo.svg"),
        ("art/Logo.PNG", "art/Logo.PNG"),
        ("  art/logo.svg ", "art/logo.svg"),
        ("art\\logo.svg", "art/logo.svg"),
    ],
)
def test_a_relative_svg_or_png_is_kept_in_posix_form(value: str, kept: str) -> None:
    assert read_logo(value, "site.logo") == (kept, ())


@pytest.mark.parametrize(
    ("value", "word"),
    [
        ("", "an empty string"),
        (7, "is "),
        ("/srv/logo.svg", "absolute"),
        ("art/logo.jpg", "an SVG or a PNG"),
        ("art", "an SVG or a PNG"),
    ],
)
def test_a_value_of_the_wrong_shape_is_refused_by_name(value: object, word: str) -> None:
    usable, refusals = read_logo(value, "site.logo")
    assert usable is None
    assert [refusal.where for refusal in refusals] == ["site.logo"]
    assert word in refusals[0].why


#: What every refusal of ``site.logo``'s shape tells the reader to write instead.
_LOGO_REMEDIATION = (
    "write `logo:` as the path of an SVG or a PNG file relative to the project root, "
    "e.g. `docs/assets/logo.svg`"
)


@pytest.mark.parametrize(
    ("value", "why"),
    [
        ("", "`site.logo` is an empty string"),
        (7, "`site.logo` is a number"),
        (
            "/srv/logo.svg",
            "`site.logo` is an absolute path, and a logo is named from the project root",
        ),
        (
            "art/logo.jpg",
            "`site.logo` names `art/logo.jpg`, and the portal's logo is an SVG or a PNG file",
        ),
    ],
)
def test_a_refused_shape_says_what_the_value_is_and_how_to_write_a_logo(
    value: object, why: str
) -> None:
    _, refusals = read_logo(value, "site.logo")

    assert [(refusal.why, refusal.remediation) for refusal in refusals] == [
        (why, _LOGO_REMEDIATION)
    ]


def test_a_logo_that_is_not_there_is_refused_and_left_out(tmp_path: Path) -> None:
    root = _project(tmp_path, "site:\n  logo: art/logo.svg\n")
    config, refusals = read_site_config(root)
    assert config.logo == ""
    assert [(r.where, "no file is there" in r.why) for r in refusals] == [("site.logo", True)]


def test_a_logo_outside_the_project_is_refused(tmp_path: Path) -> None:
    root = _project(tmp_path, "site:\n  logo: ../logo.svg\n")
    (tmp_path / "logo.svg").write_bytes(b"<svg/>")
    _, refusals = read_site_config(root)
    assert [(r.where, "outside the project" in r.why) for r in refusals] == [("site.logo", True)]


def test_a_logo_that_is_there_is_read(tmp_path: Path) -> None:
    root = _project(tmp_path, "site:\n  logo: art/logo.svg\n", "art/logo.svg")
    config, refusals = read_site_config(root)
    assert (config.logo, refusals) == ("art/logo.svg", ())


def test_the_portal_names_the_copy_by_its_kind() -> None:
    assert logo_site_path("art/orders.SVG") == "/logo.svg"
    assert logo_site_path("art/orders.png") == "/logo.png"
    assert logo_site_path("") == ""


def test_the_logo_is_copied_byte_for_byte_and_nothing_without_one(tmp_path: Path) -> None:
    root = _project(tmp_path, "", "art/logo.svg")
    out = tmp_path / "site"
    assert copy_logo(root, "", out) is None
    copied = copy_logo(root, "art/logo.svg", out)
    assert copied == out / "public" / "logo.svg"
    assert copied.read_bytes() == b"<svg/>"
