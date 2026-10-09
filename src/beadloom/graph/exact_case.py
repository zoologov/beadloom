"""Whether a project-relative path is named in the case its folders list (BDL-080 S3e).

A filesystem that folds case (APFS and HFS+ as macOS formats them, NTFS) answers
``is_file()`` for ``src/app.vue`` when the folder holds ``src/App.vue``; a case-sensitive
one (Linux) does not. A resolver that asks ``is_file()`` alone therefore resolves one tree
two ways: ``./app`` beside ``App.vue`` and ``app/index.ts`` named App.vue on macOS and the
folder index on Linux. A path counts here only when each of its parts is a name its folder
lists exactly, which is the answer a case-sensitive filesystem gives.

**The listings are cached by the folder's modification time.** Measured on one pass over
this repository's 447 relative JS imports (macOS, APFS): 8.5 ms without the check, about
170 ms listing every folder of every resolved path, 29 to 35 ms with this cache. A
folder's ``st_mtime_ns`` changes when an entry is added, removed or renamed in it, so a
listing is reused only while the folder holds the same names, and a long-running watcher
never reads a stale one. A filesystem that keeps
whole seconds (HFS+) can miss two renames inside one second; the cost of that is one
resolution read as a case-sensitive filesystem would have read it a second earlier.
"""

# beadloom:domain=graph
# beadloom:feature=import-resolver

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

#: How many folder listings are kept before the cache starts over; a bound, not a tuning.
_MAX_LISTINGS = 4096

#: Each folder's listing, keyed by its path, with the modification time it was read at.
_listings: dict[str, tuple[int, frozenset[str]]] = {}


def _names_in(folder: Path) -> frozenset[str]:
    """The names *folder* lists, read again only when its modification time moved."""
    key = str(folder)
    mtime = folder.stat().st_mtime_ns
    cached = _listings.get(key)
    if cached is not None and cached[0] == mtime:
        return cached[1]
    if len(_listings) >= _MAX_LISTINGS:
        _listings.clear()
    names = frozenset(child.name for child in folder.iterdir())
    _listings[key] = (mtime, names)
    return names


def is_named_in_its_case(project_root: Path, relative: str) -> bool:
    """Whether each part of the POSIX path *relative* is listed exactly by its folder.

    Ask it of a path that exists: on a case-sensitive filesystem the answer is then always
    true. A part whose folder cannot be listed answers false.
    """
    folder = project_root
    for part in relative.split("/"):
        try:
            if part not in _names_in(folder):
                return False
        except OSError:
            return False
        folder = folder / part
    return True


def first_existing_file(candidates: Sequence[str], project_root: Path) -> str | None:
    """The first of *candidates* that is a file under *project_root*, named in its case.

    ``None`` when no candidate is. A candidate counts only when every part of its path
    is a name its folder lists exactly (BDL-080 S3e): on a filesystem that folds case
    (macOS, Windows) ``src/app.vue`` answers ``is_file()`` for ``src/App.vue``, and as
    the ``.vue`` candidate precedes the folder index, ``./app`` beside ``App.vue`` and
    ``app/index.ts`` resolved to App.vue there and to the index on Linux. The bundler
    agrees with Linux: Vite's default ``resolve.extensions`` holds no ``.vue``.

    The one completion of a candidate list: the resolver names its file with it, and the
    ``slice_public_api`` rule locates the file an import reached with it, so the two cannot
    name different files for one import (BDL-080 S3f).
    """
    for candidate in candidates:
        if (project_root / candidate).is_file() and is_named_in_its_case(project_root, candidate):
            return candidate
    return None
