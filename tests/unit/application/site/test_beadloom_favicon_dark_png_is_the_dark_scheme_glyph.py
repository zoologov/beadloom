"""Beadloom's PNG favicon for a dark browser: the SVG favicon's dark-scheme glyph.

The owner's ruling of 2026-10-10 (``beadloom-e1xo``): a favicon follows the classic
rule, a light glyph on a dark browser and a dark one on a light browser. The SVG
favicon adapts by itself; a PNG cannot, so there are two, and the one a dark
browser takes, behind ``(prefers-color-scheme: dark)``, carries the colour the SVG
draws under that query. Generated from the SVG by
``tests/support/render_favicon_png.mjs`` under the dark scheme.
"""

from __future__ import annotations

from importlib.resources import files

from beadloom.application.site.favicon import DARK_SCHEME_GLYPH, FAVICON_PNG_SIZE
from tests.support.png_pixels import read_png

_PACKAGE_DIR = "site_favicon"
_DARK_PNG = "beadloom-favicon-dark.png"
_OPAQUE = 255


def _shipped(name: str) -> bytes:
    return files("beadloom").joinpath(_PACKAGE_DIR, name).read_bytes()


def test_the_dark_png_is_32_pixels_square() -> None:
    image = read_png(_shipped(_DARK_PNG))
    assert (image.width, image.height) == (FAVICON_PNG_SIZE, FAVICON_PNG_SIZE)


def test_the_dark_png_draws_the_glyph_the_svg_draws_on_a_dark_browser() -> None:
    svg = _shipped("beadloom-favicon.svg").decode("utf-8")
    query = f"@media (prefers-color-scheme: dark){{.bl{{fill:{DARK_SCHEME_GLYPH}}}}}"
    assert query in svg, "the SVG's dark-scheme colour moved"
    image = read_png(_shipped(_DARK_PNG))
    opaque = {pixel[:3] for row in image.rows for pixel in row if pixel[3] == _OPAQUE}
    red, green, blue = (int(DARK_SCHEME_GLYPH[i : i + 2], 16) for i in (1, 3, 5))
    assert opaque == {(red, green, blue)}


def test_the_dark_png_is_the_light_png_in_another_colour() -> None:
    light = read_png(_shipped("beadloom-favicon.png"))
    dark = read_png(_shipped(_DARK_PNG))
    assert [[pixel[3] for pixel in row] for row in dark.rows] == [
        [pixel[3] for pixel in row] for row in light.rows
    ]
