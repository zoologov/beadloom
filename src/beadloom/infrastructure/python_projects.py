"""The Python projects a project holds, found from its scan paths.

BDL-083 S2a (RFC D6, BDL-UX #332). The room census opened ``<root>/pyproject.toml`` and
nothing else, so a monorepo whose Python project is ``backend/pyproject.toml`` declared no
interpreter and no distribution, and every verdict it gave named a room in a project that
does not exist. A Python project is a ``pyproject.toml``:

* at the project root;
* between the root and a scan path -- ``scan_paths: [backend/src]`` names the CODE, and the
  directory that packages it is ``backend``;
* anywhere under a scan path, dependency and hidden directories excluded.

A config reader beside :mod:`beadloom.infrastructure.scan_paths`, and for the same reason: a
layer that needs the answer reads it without reaching up into ``application``.
"""

# beadloom:domain=infrastructure
# beadloom:component=scan-paths

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from beadloom.infrastructure.scan_paths import resolve_scan_paths

#: The packaging file that makes a directory a Python project.
PACKAGING_FILE = "pyproject.toml"

#: Directories a search under a scan path never enters: what they hold is somebody else's
#: project, installed or vendored, and not one this project declares.
_NOT_SEARCHED = frozenset({"node_modules", "site-packages", "__pycache__", "venv"})


@dataclass(frozen=True)
class PythonProject:
    """One Python project: the directory that holds its packaging, and that file's name."""

    directory: Path
    packaging: str
    """The packaging file, POSIX and relative to the project root."""


@dataclass(frozen=True)
class CensusPackaging:
    """The packaging a room census reads, and what it chose not to read.

    ``source`` is the file's name as a reader writes it, relative to the project root, so an
    unresolved entry about it names the file to go and change.
    """

    directory: Path
    source: str
    notes: tuple[str, ...] = ()


def find_python_projects(project_root: Path) -> tuple[PythonProject, ...]:
    """Every Python project *project_root* holds: the root's first, the rest by path."""
    root = project_root.resolve()
    found: set[Path] = set()
    if (root / PACKAGING_FILE).is_file():
        found.add(root)
    for scan_path in resolve_scan_paths(project_root):
        start = (root / scan_path).resolve()
        if not start.is_relative_to(root):
            continue
        found.update(_enclosing(root, start))
        found.update(_beneath(start))
    ordered = sorted(found, key=lambda directory: (directory != root, directory.as_posix()))
    return tuple(
        PythonProject(
            directory=project_root / directory.relative_to(root),
            packaging=(directory.relative_to(root) / PACKAGING_FILE).as_posix(),
        )
        for directory in ordered
    )


def census_packaging(project_root: Path) -> CensusPackaging:
    """The packaging the room census reads: the root's, else the one project found.

    A root that holds a packaging file -- readable or not -- is read, so a project that
    packages itself at the root gets the answer it got before monorepos were looked for.
    With several projects below the root and none at it, the first by path is read and the
    others are named, because one census over several distributions is a choice the reader
    has to be able to see.
    """
    if (project_root / PACKAGING_FILE).exists():
        return CensusPackaging(directory=project_root, source=PACKAGING_FILE)
    found = find_python_projects(project_root)
    if not found:
        return CensusPackaging(directory=project_root, source=PACKAGING_FILE)
    first, rest = found[0], found[1:]
    notes: tuple[str, ...] = ()
    if rest:
        others = ", ".join(project.packaging for project in rest)
        notes = (
            f"{len(found)} Python projects are found under the scan paths and the census "
            f"reads the first; the interpreters and extras of {others} are not reported",
        )
    return CensusPackaging(directory=first.directory, source=first.packaging, notes=notes)


def _enclosing(root: Path, start: Path) -> set[Path]:
    """The directories between *root* (excluded) and *start* that hold a packaging file."""
    found: set[Path] = set()
    current = start
    while current != root and current.is_relative_to(root):
        if (current / PACKAGING_FILE).is_file():
            found.add(current)
        current = current.parent
    return found


def _beneath(start: Path) -> set[Path]:
    """The directories under *start* that hold a packaging file, pruning installed trees."""
    found: set[Path] = set()
    for directory, subdirectories, files in os.walk(start):
        subdirectories[:] = [
            name
            for name in subdirectories
            if name not in _NOT_SEARCHED and not name.startswith(".")
        ]
        if PACKAGING_FILE in files:
            found.add(Path(directory))
    return found
