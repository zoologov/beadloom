"""Beadloom's brand sources are kept in the repository, and only the monochrome icon ships.

The owner's ruling of 2026-10-10 (``beadloom-e1xo``, ruling A): Beadloom ships no colour
brand asset; the monochrome square icon is the nav logo, the favicon, the footer's
icon and the social preview. The colour sources and the traced mark are kept, not
shipped, in ``.github/brand/``, a folder no package and no portal reads, with a README
that names which file ships and where. A shipped file is its source, byte for byte.
"""

from __future__ import annotations

from tests.support.repository_root import REPO_ROOT

_BRAND = REPO_ROOT / ".github" / "brand"
_PACKAGE = REPO_ROOT / "src" / "beadloom"

#: Each source, and the files that ship from it, byte for byte.
_SHIPPED_FROM = {
    "beadloom-icon.svg": (_PACKAGE / "site_scaffold" / "public" / "brand" / "beadloom-icon.svg",),
    "beadloom-favicon.svg": (_PACKAGE / "site_favicon" / "beadloom-favicon.svg",),
    "social-preview-square.svg": (REPO_ROOT / ".github" / "social-preview.svg",),
}
#: The sources nothing ships: the colour files and the traced mark.
_SOURCES_ONLY = ("beadloom-mark.svg", "beadloom-mark-mono.svg", "beadloom-icon-gradient.svg")
_README = "README.md"


def test_the_folder_holds_the_six_sources_and_its_readme() -> None:
    held = sorted(path.name for path in _BRAND.iterdir())
    assert held == sorted((*_SHIPPED_FROM, *_SOURCES_ONLY, _README))


def test_every_shipped_brand_file_is_its_source_byte_for_byte() -> None:
    for source, shipped in _SHIPPED_FROM.items():
        for path in shipped:
            assert path.read_bytes() == (_BRAND / source).read_bytes(), path


def test_no_source_only_file_ships_in_the_package() -> None:
    names = {path.name for path in _PACKAGE.rglob("*")}
    assert not names & set(_SOURCES_ONLY)
    gradients = [
        path
        for path in _PACKAGE.rglob("*.svg")
        if "Gradient" in path.read_text(encoding="utf-8")
    ]
    assert gradients == [], "a colour brand file ships"


def test_the_readme_names_the_shipped_files_and_the_sources_only() -> None:
    readme = (_BRAND / _README).read_text(encoding="utf-8")
    for source, shipped in _SHIPPED_FROM.items():
        assert source in readme
        for path in shipped:
            assert path.relative_to(REPO_ROOT).as_posix() in readme
    for source in _SOURCES_ONLY:
        assert source in readme
    assert "sources only" in readme
