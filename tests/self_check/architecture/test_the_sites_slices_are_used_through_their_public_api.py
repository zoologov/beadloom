"""Every import that leaves a slice of this repository's site theme goes through its ``index.js``.

Feature-Sliced Design (BDL-076): a slice is used only through its public API.
The ``site-fsd-layers`` rule judges the direction of imports between slice
nodes, and cannot see an import inside one node. ``shared`` is one node and
holds several segments (``lib``, ``ui``, ``theme-tokens``…), so an import from
one segment into another segment's file passed every check while every other
cross-segment import went through the segment's index (BDL-076 R1 finding n1).

The unit an import may not reach into is a slice of ``pages``, ``widgets``,
``features`` and ``entities``, a segment of ``shared``, and the ``app`` layer.
The files are read from ``REPO_ROOT``, never from the index.
"""

from __future__ import annotations

import re
from pathlib import PurePosixPath

from tests.support.repository_root import REPO_ROOT

#: The theme, relative to the repository root.
_THEME = REPO_ROOT / "site" / ".vitepress" / "theme"

#: The layers whose second path part is a slice or a segment, and the layer
#: that is one unit whole.
_SLICED_LAYERS = frozenset({"pages", "widgets", "features", "entities", "shared"})
_WHOLE_LAYERS = frozenset({"app"})

#: A module's public API.
_PUBLIC_API = "index.js"

#: A relative specifier in a static import or re-export, or a literal dynamic import.
_RELATIVE_IMPORT = re.compile(
    r"""(?:\bfrom\s*|\bimport\s*\(\s*|\bimport\s+)["'](\.{1,2}/[^"']+)["']"""
)


def _unit_of(path: PurePosixPath) -> tuple[str, ...]:
    """The slice, segment or layer a theme file belongs to, as its path parts."""
    parts = path.parts
    if parts and parts[0] in _SLICED_LAYERS and len(parts) > 2:
        return parts[:2]
    if parts and parts[0] in _WHOLE_LAYERS:
        return parts[:1]
    return ()


def _resolve(importer: PurePosixPath, specifier: str) -> PurePosixPath:
    parts: list[str] = list(importer.parent.parts)
    for part in PurePosixPath(specifier).parts:
        if part == "..":
            parts.pop()
        elif part != ".":
            parts.append(part)
    return PurePosixPath(*parts)


def _imports_past_a_public_api() -> list[str]:
    reached: list[str] = []
    for file in sorted([*_THEME.rglob("*.js"), *_THEME.rglob("*.vue")]):
        importer = PurePosixPath(file.relative_to(_THEME).as_posix())
        text = file.read_text(encoding="utf-8")
        for specifier in _RELATIVE_IMPORT.findall(text):
            target = _resolve(importer, specifier)
            unit = _unit_of(target)
            if not unit or unit == _unit_of(importer):
                continue
            if target != PurePosixPath(*unit, _PUBLIC_API):
                reached.append(f"{importer} imports {target}")
    return reached


def test_the_theme_has_files_to_judge() -> None:
    files = [*_THEME.rglob("*.js"), *_THEME.rglob("*.vue")]

    assert len(files) > 50


def test_an_import_across_slices_or_segments_goes_through_the_index() -> None:
    assert _imports_past_a_public_api() == []
