"""The documents each doc root finds, compared across roots."""

from __future__ import annotations

from typing import TYPE_CHECKING

from beadloom.infrastructure.doc_roots import (
    SPACES,
)

if TYPE_CHECKING:
    from pathlib import Path


def found_by_any_root(root: Path, spaces: object) -> set[str]:
    """Every file a declared root matched, spelled project-relative.

    Recomputed here from the configuration rather than asked of the code under
    test: a classifier that agrees with itself proves nothing about whether it
    lost a file (`.18`'s recount suite could reproduce M1 faithfully and agreed
    with it, which is why the reviewer had to plant a file instead).
    """
    found: set[str] = set()
    for space in SPACES:
        for pattern in spaces.roots.get(space, ()):  # type: ignore[attr-defined]
            found.update(p.relative_to(root).as_posix() for p in root.glob(pattern) if p.is_file())
    return found


def populations_by_space(root: Path, spaces: object) -> dict[str, int]:
    return {
        space: len(spaces.documents_in(root, space))  # type: ignore[attr-defined]
        for space in SPACES
    }
