"""Beadloom's PNG favicon: the SVG favicon's light-scheme glyph, for browsers that take no SVG.

BDL-080 S4e (``beadloom-af99.9``), the owner's look at S4d on 2026-10-09. The SVG
favicon is theme-adaptive: a ``prefers-color-scheme`` query inside it draws the
glyph dark (``#3c3c43``) on a light browser and light (``#dfdfd6``) on a dark one.
A PNG cannot adapt, so it carries the colour the SVG draws without the query, the
light scheme's. It is 32 by 32 pixels, the size a tab asks for at twice the
density, and is generated from the SVG by ``tests/support/render_favicon_png.mjs``.
"""

from __future__ import annotations

from importlib.resources import files

from beadloom.application.site.favicon import FAVICON_PNG_SIZE, LIGHT_GLYPH
from tests.support.png_pixels import read_png

_PACKAGE_DIR = "site_favicon"
_OPAQUE = 255


def _shipped(name: str) -> bytes:
    return files("beadloom").joinpath(_PACKAGE_DIR, name).read_bytes()


def test_the_png_is_32_pixels_square() -> None:
    image = read_png(_shipped("beadloom-favicon.png"))
    assert FAVICON_PNG_SIZE == 32
    assert (image.width, image.height) == (FAVICON_PNG_SIZE, FAVICON_PNG_SIZE)


def test_the_png_draws_the_glyph_the_svg_draws_on_a_light_browser() -> None:
    svg = _shipped("beadloom-favicon.svg").decode("utf-8")
    assert f".bl{{fill:{LIGHT_GLYPH}}}" in svg, "the SVG's light-scheme colour moved"
    image = read_png(_shipped("beadloom-favicon.png"))
    opaque = {pixel[:3] for row in image.rows for pixel in row if pixel[3] == _OPAQUE}
    red, green, blue = (int(LIGHT_GLYPH[i : i + 2], 16) for i in (1, 3, 5))
    assert opaque == {(red, green, blue)}


def test_the_png_is_a_knock_out_on_a_transparent_ground() -> None:
    image = read_png(_shipped("beadloom-favicon.png"))
    centre = FAVICON_PNG_SIZE // 2
    assert image.at(0, 0)[3] == 0, "the rounded corner is transparent"
    assert image.at(FAVICON_PNG_SIZE - 3, centre - 6)[3] == _OPAQUE, "the square is drawn"
    # The junction's bar runs right from the ring along the middle: cut out of the square.
    assert image.at(centre + 6, centre)[3] < _OPAQUE, "the glyph is knocked out"
