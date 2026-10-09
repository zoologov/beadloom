# beadloom:domain=application
# beadloom:feature=site-generation
"""The portal's favicon: the project's logo when it has one of its own, Beadloom's otherwise.

BDL-080 S4e (``beadloom-af99.9``), the owner's look at S4d on 2026-10-09. The
favicon of an adopter's portal is the adopter's: a project that declares
``site.logo`` gets that file as its favicon, as it is, an SVG or a PNG. Only a
project without a logo gets Beadloom's, so the Beadloom mark appears on an
adopter's portal in the footer alone.

Beadloom's favicon is the square icon, theme-adaptive: an SVG whose
``prefers-color-scheme`` query draws the glyph :data:`LIGHT_GLYPH` on a light
browser and light on a dark one, and a PNG of :data:`FAVICON_PNG_SIZE` pixels for
the browsers that take no SVG favicon (Safari), which carries the light scheme's
colour because a PNG cannot adapt. A logo that IS Beadloom's icon, byte for byte,
takes that favicon too: the theme-adaptive form of the same mark, where the
icon as it is would draw black on a dark tab.

The owner's ruling of 2026-10-10 (``beadloom-e1xo``): the classic rule, a dark
glyph on a light browser and a light glyph on a dark one. The SVG does it by
itself; for the PNG a second one, drawn in :data:`DARK_SCHEME_GLYPH`, is linked
behind the media query :data:`DARK_SCHEME`, after the first, so a dark browser
that matches the query takes it.

The three files are package data under ``beadloom/site_favicon/``, not scaffold
files: the scaffold marks every file it ships with a text comment, and a PNG
cannot carry one. They are written into ``public/brand/`` on every run that uses
them, as the logo is copied, and a project replaces them under ``.beadloom/site/``.
"""

from __future__ import annotations

from importlib.resources import files
from pathlib import PurePosixPath
from typing import TYPE_CHECKING

from beadloom.application.site.site_logo import logo_site_path

if TYPE_CHECKING:
    from pathlib import Path

#: The glyph's colour on a light browser, the colour the PNG carries.
LIGHT_GLYPH = "#3c3c43"

#: The glyph's colour on a dark browser, the colour the dark scheme's PNG carries.
DARK_SCHEME_GLYPH = "#dfdfd6"

#: The media query the dark scheme's PNG is linked behind.
DARK_SCHEME = "(prefers-color-scheme: dark)"

#: The PNG's width and height in pixels: a tab's 16 points at twice the density.
FAVICON_PNG_SIZE = 32

#: Where the package keeps Beadloom's favicon.
_PACKAGE_DIR = "site_favicon"
#: Beadloom's icon as the scaffold ships it; a logo that is this file is Beadloom's.
_BEADLOOM_ICON = ("site_scaffold", "public", "brand", "beadloom-icon.svg")
#: Where the favicon is written in a portal, under ``public/``.
_BRAND_DIR = "brand"
_SVG = "beadloom-favicon.svg"
_PNG = "beadloom-favicon.png"
_DARK_PNG = "beadloom-favicon-dark.png"

#: The media type a favicon link names, by the file's suffix.
_TYPES = {".svg": "image/svg+xml", ".png": "image/png"}


def _beadloom_favicons() -> list[dict[str, str]]:
    png = {"type": _TYPES[".png"], "sizes": f"{FAVICON_PNG_SIZE}x{FAVICON_PNG_SIZE}"}
    return [
        {"href": f"/{_BRAND_DIR}/{_SVG}", "type": _TYPES[".svg"]},
        {"href": f"/{_BRAND_DIR}/{_PNG}", **png},
        {"href": f"/{_BRAND_DIR}/{_DARK_PNG}", **png, "media": DARK_SCHEME},
    ]


def uses_beadloom_favicon(project_root: Path, logo: str) -> bool:
    """Whether the portal's favicon is Beadloom's: no logo, or a logo that is Beadloom's icon.

    *logo* is ``site.logo`` relative to *project_root*, ``""`` without one, and
    was checked to be a file when the ``site:`` block was read.
    """
    if not logo:
        return True
    icon = files("beadloom")
    for part in _BEADLOOM_ICON:
        icon = icon.joinpath(part)
    return (project_root / logo).read_bytes() == icon.read_bytes()


def favicons_of(project_root: Path, logo: str) -> list[dict[str, str]]:
    """The portal's favicons, each ``{href, type[, sizes[, media]]}``, *href* before the base."""
    if uses_beadloom_favicon(project_root, logo):
        return _beadloom_favicons()
    suffix = PurePosixPath(logo).suffix.lower()
    return [{"href": logo_site_path(logo), "type": _TYPES[suffix]}]


def write_beadloom_favicon(out_dir: Path) -> list[Path]:
    """Write Beadloom's favicon, the SVG and the two PNGs, into the portal; the copies."""
    shipped = files("beadloom").joinpath(_PACKAGE_DIR)
    written: list[Path] = []
    for name in (_SVG, _PNG, _DARK_PNG):
        target = out_dir / "public" / _BRAND_DIR / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(shipped.joinpath(name).read_bytes())
        written.append(target)
    return written
