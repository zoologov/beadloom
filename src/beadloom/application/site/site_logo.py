# beadloom:domain=application
# beadloom:feature=site-generation
"""The project's logo in the portal's nav: ``site.logo``, checked and copied.

BDL-080 S4d (``beadloom-af99.7``), the owner's ruling of 2026-10-09. The nav of
an adopter's portal shows the ADOPTER's logo, never Beadloom's, so the logo is a
file of the project: ``site.logo`` names an SVG or a PNG by its path relative to
the project root, and ``docs site`` copies it into the portal's ``public/`` as
``logo.svg`` or ``logo.png``, which VitePress serves under the base path. A
project that declares no logo gets no nav logo.

The value is checked twice, because the two checks need different things: its
shape (a relative path with an SVG or PNG suffix) where the ``site:`` block is
read, and the file itself (inside the project, and there) against the project
root. A refusal names ``site.logo`` either way, and stops ``docs site`` before it
writes anything, as every refusal of the block does.

BDL-080 S4e (``beadloom-af99.9``): an SVG logo drawn in ``currentColor`` is
meant to take the colour of the text around it, which an image cannot inherit:
drawn as an image it is black, and invisible on the dark theme. Such a logo is
named monochrome (:func:`is_monochrome`), and the portal draws it in the text's
colour; every other logo is drawn as it is.
"""

from __future__ import annotations

import shutil
from pathlib import PurePosixPath
from typing import TYPE_CHECKING

from beadloom.doc_sync.declarations import Refusal, describe_value

if TYPE_CHECKING:
    from pathlib import Path

#: The kinds of file a logo may be, by suffix (lower-case).
LOGO_SUFFIXES = (".svg", ".png")

#: How an SVG says it is drawn in the colour of the text around it.
_TEXT_COLOUR = b"currentColor"

#: The logo's name in the portal, without its suffix, under ``public/``.
_LOGO_STEM = "logo"
_PUBLIC = "public"

_REMEDIATION = (
    "write `logo:` as the path of an SVG or a PNG file relative to the project root, "
    "e.g. `docs/assets/logo.svg`"
)


def _refusal(where: str, why: str) -> Refusal:
    return Refusal(where=where, why=f"`{where}` {why}", remediation=_REMEDIATION)


def read_logo(value: object, where: str) -> tuple[object, tuple[Refusal, ...]]:
    """*value* as a logo path in posix form, or the refusal of its shape.

    The file is not looked at here: :func:`logo_problem` does that against the
    project root.
    """
    if not (isinstance(value, str) and value.strip()):
        shown = "an empty string" if isinstance(value, str) else describe_value(value)
        return None, (_refusal(where, f"is {shown}"),)
    path = PurePosixPath(value.strip().replace("\\", "/"))
    if path.is_absolute():
        return None, (
            _refusal(where, "is an absolute path, and a logo is named from the project root"),
        )
    if path.suffix.lower() not in LOGO_SUFFIXES:
        return None, (
            _refusal(where, f"names `{path}`, and the portal's logo is an SVG or a PNG file"),
        )
    return path.as_posix(), ()


def logo_problem(project_root: Path, logo: str, where: str) -> Refusal | None:
    """The refusal of *logo* as a file of the project at *project_root*, or ``None``."""
    candidate = project_root / logo
    try:
        candidate.resolve().relative_to(project_root.resolve())
    except ValueError:
        return _refusal(where, f"names `{logo}`, which resolves outside the project root")
    if not candidate.is_file():
        return _refusal(where, f"names `{logo}`, and no file is there")
    return None


def logo_site_path(logo: str) -> str:
    """The logo's address in the portal, before the base path; ``""`` without a logo."""
    if not logo:
        return ""
    return f"/{_LOGO_STEM}{PurePosixPath(logo).suffix.lower()}"


def is_monochrome(project_root: Path, logo: str) -> bool:
    """Whether *logo* is an SVG drawn in ``currentColor``, the text's colour.

    ``False`` for a PNG and without a logo.
    """
    if PurePosixPath(logo).suffix.lower() != ".svg":
        return False
    return _TEXT_COLOUR in (project_root / logo).read_bytes()


def copy_logo(project_root: Path, logo: str, out_dir: Path) -> Path | None:
    """Copy the project's *logo* into the portal's ``public/``; the copy, or ``None``.

    The logo was checked when the ``site:`` block was read, so a missing file
    here is an error of the caller's, and raises.
    """
    if not logo:
        return None
    target = out_dir / _PUBLIC / logo_site_path(logo).lstrip("/")
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(project_root / logo, target)
    return target
