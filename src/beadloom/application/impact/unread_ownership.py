# beadloom:domain=application
# beadloom:feature=impact
"""The files each node an answer names owns that this derivation did not read.

BDL-UX #284 is why this module exists. One epic ruled three axis rows out of
scope as blast radius, and all three were the sites the fix had to reach. Two
were Python and were misread. The third, ``onboarding``, was INVISIBLE: it had
surfaced as a caller, the fix lived in the ``.md.txt`` templates that node owns,
and this derivation reads ``.py`` source. The answer's unresolved population was
the one place a gap could be named, and nothing in it pointed from those files
to the node that owns them — so the row a person ruled carried no hint of them.

So the answer states, per node it names, the files that node OWNS and this
derivation did not read. Ownership is :meth:`GraphBoundary.owner_of`'s
most-specific-wins rule, asked about every file under the node's declared
source, so a file a child node owns is never counted against its parent and
"who owns this" stays one rule rather than two.

**What this is not.** It does not say the change reaches those files. Whether a
Python function reads a template is a runtime fact this derivation cannot see,
and guessing it from string literals would be a clean, confident, wrong answer.
It says the node owns surface this answer is blind to, which is the fact a person
ruling the row needs before reading a ``callers`` row as "not changed".

**The population, stated.** Every file under the node's source whose suffix is
not ``.py``, walking past the directories a tool generates rather than a person
writes. A node's linked documents are NOT counted: every node has one, they are
Markdown by construction, and ``sync-check`` already owns the question of whether
a change left them stale.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from beadloom.application.impact.unresolved import PYTHON_SUFFIX
from beadloom.infrastructure.repository import covering_prefix

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator
    from pathlib import Path

    from beadloom.application.impact.boundary import GraphBoundary

#: Directory names whose contents a tool produced: a version-control store, an
#: interpreter's or a checker's cache, a virtual environment, a package manager's
#: vendored tree. Counting them would bury a node's two templates under a
#: thousand compiled files, and no change is made by editing one.
_GENERATED_DIRECTORIES = frozenset(
    {
        ".git",
        "__pycache__",
        "node_modules",
        ".venv",
        "venv",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".tox",
    }
)

#: File names an operating system leaves in a directory it has displayed.
_OPERATING_SYSTEM_LITTER = frozenset({".DS_Store"})


@dataclass(frozen=True)
class UnreadOwnership:
    """One node, and the files it owns that this derivation did not read."""

    node: str
    #: Project-relative, sorted, so two runs over one tree state one list.
    files: tuple[str, ...]


def unread_ownership(
    boundary: GraphBoundary, nodes: Iterable[str], project_root: Path
) -> tuple[UnreadOwnership, ...]:
    """Every node in *nodes* that owns a file this derivation did not read.

    Empty when the boundary has no index: with no owner known, no ownership can
    be claimed, and the answer's ``no-graph-index`` entry already says why.
    """
    if not boundary.readable:
        return ()
    found = (
        UnreadOwnership(node, _unread_files_of(boundary, node, project_root))
        for node in sorted(set(nodes))
    )
    return tuple(owned for owned in found if owned.files)


def _unread_files_of(boundary: GraphBoundary, node: str, project_root: Path) -> tuple[str, ...]:
    """The non-Python files *node* owns, by the one ownership rule."""
    source = boundary.source_of(node)
    if source is None:
        return ()
    prefix = covering_prefix(source)
    candidates = (
        _files_under(project_root / prefix)
        if prefix.endswith("/")
        else iter([project_root / source])
    )
    relative = (
        path.relative_to(project_root).as_posix()
        for path in candidates
        if path.is_file() and path.suffix != PYTHON_SUFFIX
    )
    return tuple(sorted(path for path in relative if boundary.owner_of(path).node == node))


def _files_under(directory: Path) -> Iterator[Path]:
    """Every file under *directory*, past generated trees and without following links."""
    if not directory.is_dir():
        return
    for child in sorted(directory.iterdir()):
        if child.is_symlink():
            continue
        if child.is_dir():
            if child.name not in _GENERATED_DIRECTORIES:
                yield from _files_under(child)
        elif child.name not in _OPERATING_SYSTEM_LITTER:
            yield child
