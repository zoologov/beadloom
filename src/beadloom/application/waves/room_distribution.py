"""The Python project a clean room measures, and the hint that runs its suite there.

BDL-083 S2b (RFC D6, BDL-UX #333). Measured on the first outside adopter's monorepo,
anonymised as ``tests/fixtures/monorepo``: the project's Python lives in ``backend/`` with its
own ``pyproject.toml`` and ``uv.lock``, and ``clean-room`` printed this repository's layout
as the way to measure in the room — ``PYTHONPATH=<room>/src``, ``-m pytest <room>/tests`` and
``import beadloom`` — three things that room does not hold. The hint was a template, so it was
correct on exactly one project.

**Which project.** A room is built to measure a bead's files, so the project measured is the
one that OWNS the carried files: the deepest Python project (a ``pyproject.toml`` found by
:func:`~beadloom.infrastructure.python_projects.find_python_projects`) whose directory holds
a carried path. When the carried files fall into several projects, the one holding the most
is chosen and the rest are named, because one room builds one environment and a choice the
reader cannot see is a verdict about a project nobody named. When no carried file falls into
any project, the room measures the project the room census reads, which is the answer this
command gave before monorepos were looked for.

**The hint is read from that project, never from a template.** Its sources are ``src`` when
the project keeps one and the project's directory otherwise; the import check names the first
package found there, since its only job is to show the import resolves under the room; the
suite runs over the ``testpaths`` the project's own pytest configuration declares, or over
the project's directory, which is where pytest itself would start. A project with no
importable package gets no import line rather than one naming a package it does not have.
"""

# beadloom:feature=wave-plan

from __future__ import annotations

import re
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from beadloom.application.waves.room_env import room_python
from beadloom.infrastructure.python_projects import (
    PACKAGING_FILE,
    census_packaging,
    find_python_projects,
)

#: How the project root is named among the project directories: the POSIX spelling of "here".
ROOT_DIRECTORY = "."

#: The lock file a project's environment is installed from when it keeps one.
LOCK_FILE = "uv.lock"

#: The directory a project keeps its sources in, when it uses the ``src`` layout.
_SOURCES_DIR = "src"

#: Directory names under the sources that hold no package to import.
_NOT_PACKAGES = frozenset({"tests", "test", "docs", "build", "dist"})

#: Where a project keeps the environment its suite runs under, POSIX first.
_TREE_INTERPRETERS = (
    Path(".venv") / "bin" / "python",
    Path(".venv") / "Scripts" / "python.exe",
)

#: The pytest table of a ``pyproject.toml``, up to the next table header. Read without a TOML
#: parser for the reason :mod:`beadloom.application.rooms` states: ``tomllib`` is 3.11+.
_PYTEST_TABLE_RE = re.compile(
    r"^\[tool\.pytest\.ini_options\]\s*$(.*?)(?=^\[|\Z)", re.MULTILINE | re.DOTALL
)
_TESTPATHS_RE = re.compile(r"^\s*testpaths\s*=\s*(\[[^\]]*\]|\"[^\"]*\"|'[^']*')", re.MULTILINE)
_QUOTED_RE = re.compile(r"""["']([^"']+)["']""")

_TEXT_CODEC = "utf-8"


@dataclass(frozen=True)
class RoomDistribution:
    """The Python project a room measures, and how it was chosen.

    ``directory`` is POSIX and relative to the project root, :data:`ROOT_DIRECTORY` for the
    root itself. ``lock`` is the lock file beside the packaging, POSIX and relative to the
    root, or ``None`` when the project keeps none.
    """

    directory: str
    packaging: str
    lock: str | None
    why: str
    notes: tuple[str, ...] = ()

    def under(self, root: Path) -> Path:
        """The project's directory inside *root*: a checkout or a room."""
        return Path(root) if self.directory == ROOT_DIRECTORY else Path(root) / self.directory


def owning_distribution(project_root: Path, carry: tuple[str, ...] = ()) -> RoomDistribution:
    """The Python project that owns the carried files, or the one the census reads."""
    root = Path(project_root)
    directories = [_relative(root, project.directory) for project in find_python_projects(root)]
    owners = Counter(
        owner for owner in (_owner(named, directories) for named in carry) if owner is not None
    )
    if not owners:
        packaging = census_packaging(root)
        directory = _relative(root, packaging.directory)
        return _distribution(
            root,
            directory,
            why=(
                "no carried file belongs to a Python project, so the room measures the one "
                "the room census reads"
            ),
            notes=packaging.notes,
        )
    ranked = sorted(owners.items(), key=lambda item: (-item[1], directories.index(item[0])))
    chosen, count = ranked[0]
    notes: tuple[str, ...] = ()
    if len(ranked) > 1:
        others = ", ".join(_packaging_of(directory) for directory, _ in ranked[1:])
        notes = (
            f"the carried files also belong to {others}; one room builds one environment, "
            "so a verdict on those files here is not taken under their own project's",
        )
    return _distribution(
        root,
        chosen,
        why=f"it owns {count} of the {len(carry)} carried file(s)",
        notes=notes,
    )


def room_invocation(
    path: Path,
    *,
    project_root: Path | None = None,
    distribution: RoomDistribution | None = None,
) -> tuple[str, ...]:
    """How to run the measured project's suite IN the room, and how to check that you did.

    The measured trap the import line closes (found building the room for
    ``beadloom-67t1``): with an editable install, running the suite from inside the room
    under the project's environment imports the TREE's source, and the first attempt showed
    it in a warning path rather than in a failure — a green that is a measurement of the tree
    wearing a room's name. ``PYTHONPATH`` pointing at the room's own sources fixes it, and
    the import line is the check: it must print a path under the room. ``PYTHONPATH`` is
    kept under the room's own interpreter too, where it is redundant, because the line whose
    output is the check is the evidence.

    *distribution* defaults to the project at the room's root, which is this repository's
    own arrangement and the one a room built without a project in view assumes.
    """
    room = Path(path)
    directory = distribution.directory if distribution is not None else ROOT_DIRECTORY
    measured = room if directory == ROOT_DIRECTORY else room / directory
    interpreter = interpreter_for(project_root, room=room, directory=directory)
    sources = measured / _SOURCES_DIR if (measured / _SOURCES_DIR).is_dir() else measured
    lines: list[str] = []
    package = _first_package(sources)
    if package is not None:
        lines.append(
            f"PYTHONPATH={sources} {interpreter} -c "
            f'"import {package}; print({package}.__file__)"  # must print a path under {room}'
        )
    targets = " ".join(str(measured / tests) for tests in _test_paths(measured)) or str(measured)
    lines.append(f"PYTHONPATH={sources} {interpreter} -m pytest {targets}")
    return tuple(lines)


def interpreter_for(
    project_root: Path | None, *, room: Path | None = None, directory: str = ROOT_DIRECTORY
) -> str:
    """The interpreter a verdict in the room is taken under.

    The room's own comes first when it has one: isolating the FILES and leaving the
    interpreter to the machine is BDL-UX #256, where a correctly-named room returned a
    verdict decided by whatever happened to be installed. Then the environment the measured
    project keeps beside itself in the tree, then the one at the tree's root.

    ``sys.executable`` is the last resort and the wrong answer often enough to say so: under
    a ``uv tool`` install it is the tool's own interpreter, which holds neither ``pytest``
    nor the project's dependencies, so a hint naming it could not be run at all (found by
    using this command on its own bead).
    """
    if room is not None:
        own = room_python(room, directory)
        if own is not None:
            return str(own)
    tree = tree_interpreter(project_root, directory)
    return tree if tree is not None else sys.executable


def tree_interpreter(project_root: Path | None, directory: str = ROOT_DIRECTORY) -> str | None:
    """The environment the measured project keeps in the tree, or the root's, or ``None``."""
    if project_root is None:
        return None
    root = Path(project_root)
    places = [root / directory] if directory != ROOT_DIRECTORY else []
    for place in [*places, root]:
        for relative in _TREE_INTERPRETERS:
            candidate = place / relative
            if candidate.exists():
                return str(candidate)
    return None


def _distribution(
    root: Path, directory: str, *, why: str, notes: tuple[str, ...]
) -> RoomDistribution:
    lock = (PurePosixPath(directory) / LOCK_FILE).as_posix()
    return RoomDistribution(
        directory=directory,
        packaging=_packaging_of(directory),
        lock=lock if (root / lock).is_file() else None,
        why=why,
        notes=notes,
    )


def _packaging_of(directory: str) -> str:
    return (PurePosixPath(directory) / PACKAGING_FILE).as_posix()


def _relative(root: Path, directory: Path) -> str:
    """*directory* as a POSIX path relative to *root*, :data:`ROOT_DIRECTORY` for the root."""
    relative = Path(directory).resolve().relative_to(root.resolve()).as_posix()
    return relative or ROOT_DIRECTORY


def _owner(named: str, directories: list[str]) -> str | None:
    """The deepest project directory that holds the carried path *named*."""
    path = PurePosixPath(named.replace("\\", "/"))
    holding = [
        directory
        for directory in directories
        if directory == ROOT_DIRECTORY or path.is_relative_to(directory)
    ]
    return max(holding, key=_depth, default=None)


def _depth(directory: str) -> int:
    """How many directories below the root *directory* is; the root is 0."""
    return 0 if directory == ROOT_DIRECTORY else len(PurePosixPath(directory).parts)


def _first_package(sources: Path) -> str | None:
    """The first importable name under *sources*: a package by name, else a module."""
    if not sources.is_dir():
        return None
    entries = sorted(sources.iterdir(), key=lambda entry: entry.name)
    for entry in entries:
        if (
            entry.is_dir()
            and entry.name.isidentifier()
            and entry.name not in _NOT_PACKAGES
            and (entry / "__init__.py").is_file()
        ):
            return entry.name
    for entry in entries:
        if (
            entry.is_file()
            and entry.suffix == ".py"
            and entry.stem.isidentifier()
            and not entry.stem.startswith(("_", "test", "conftest", "setup"))
        ):
            return entry.stem
    return None


def _test_paths(measured: Path) -> tuple[str, ...]:
    """The ``testpaths`` the project's pytest configuration declares, or nothing."""
    try:
        text = (measured / PACKAGING_FILE).read_text(encoding=_TEXT_CODEC)
    except (OSError, UnicodeDecodeError):
        return ()
    table = _PYTEST_TABLE_RE.search(text)
    if table is None:
        return ()
    declared = _TESTPATHS_RE.search(table.group(1))
    if declared is None:
        return ()
    return tuple(_QUOTED_RE.findall(declared.group(1)))
