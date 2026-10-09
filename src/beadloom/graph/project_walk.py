"""A project's files, found by one walk with one skip list (BDL-080 S3f, ``beadloom-af99.14``).

The readers that find their declarations by walking the whole project — the tsconfig
files (:mod:`beadloom.graph.tsconfig_paths`) and the Expo module configs
(:mod:`beadloom.graph.expo_modules`) — read one :class:`ProjectFiles`, so a run walks the
tree once however many of them ask. Until S3f each had its own walk and its own copy of
the skip list, and an incremental reindex of a project with JavaScript imports walked the
tree twice before deciding that nothing had changed.

**Not walked:** a hidden folder (``.git``, ``.venv``, ``.expo`` …), a folder reached
through a symbolic link, and the folders of :data:`SKIPPED_DIRECTORIES`, which hold other
people's code or what a build wrote rather than the project's own declarations.
"""

# beadloom:domain=graph
# beadloom:feature=import-resolver

from __future__ import annotations

from functools import cached_property
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

#: Folders the walk never enters, beside every hidden one: installed packages
#: (``node_modules``, ``vendor``, ``Pods``, a Python ``venv``) and build output (``dist``,
#: ``build``, Cargo's and Maven's ``target``). ``.venv`` is hidden, and named all the same.
SKIPPED_DIRECTORIES = frozenset(
    {"node_modules", "dist", "build", "vendor", "Pods", "venv", ".venv", "target"}
)


def _walked(folder: Path) -> bool:
    """Whether the walk enters the folder *folder*."""
    name = folder.name
    return not (folder.is_symlink() or name.startswith(".") or name in SKIPPED_DIRECTORIES)


class ProjectFiles:
    """The file names of one project, by folder, found by one walk on first use."""

    def __init__(self, project_root: Path) -> None:
        self._root = project_root

    @cached_property
    def folders(self) -> tuple[tuple[str, tuple[str, ...]], ...]:
        """``(folder, file names)`` of every folder walked, by project-relative path.

        The root is ``""``; names are sorted, folders too. A folder that cannot be listed
        is left out, with whatever is below it.
        """
        listed: list[tuple[str, tuple[str, ...]]] = []
        pending = [self._root]
        while pending:
            current = pending.pop()
            try:
                children = list(current.iterdir())
            except OSError:
                continue
            names: list[str] = []
            for child in children:
                if not child.is_dir():
                    names.append(child.name)
                elif _walked(child):
                    pending.append(child)
            relative = current.relative_to(self._root).as_posix()
            listed.append(("" if relative == "." else relative, tuple(sorted(names))))
        return tuple(sorted(listed))

    def named(self, wanted: Callable[[str], bool]) -> tuple[str, ...]:
        """The project-relative path of every file whose name is *wanted*, sorted."""
        return tuple(
            sorted(
                f"{folder}/{name}" if folder else name
                for folder, names in self.folders
                for name in names
                if wanted(name)
            )
        )
