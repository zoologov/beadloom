"""The packages a project's Java and Kotlin files declare, and the folder each is in.

BDL-076 R2 finding 6 (``beadloom-fht7``). A JVM import names a package and a class
(``org.example.network.Socket``), and until this module both ``init`` and the
reindex read the package as a folder path under a source root. Kotlin's coding
conventions recommend, for a pure Kotlin project, omitting the common root package
from the folders — ``package org.example.network`` in ``src/main/kotlin/network/`` —
and on that layout the folder path names no folder: ``init`` drew no edge, the
reindex resolved no import, and nothing said why. The package declaration is what
the compiler reads, so it is what decides the package here.

**What is read.** The first ``package`` statement of a file, after comments and
file annotations (``@file:JvmName(...)``): Java's ``package a.b;`` and Kotlin's
``package a.b``, a back-quoted segment read without its quotes. A file with no
declaration is in the default package and is not read: the default package cannot
be imported from a named one.

**An import's package** is the longest dotted prefix of the import that some file
declares as its package, so a class, a member of a static import and a wildcard all
reach the package they sit in. A package no file declares — the JDK, a library —
names no folder, even where its last segments match a folder of the project.

**A package declared in several folders** (split across a Java and a Kotlin root,
across modules, or across folders of Kotlin's recommended layout) is not given to the
folder read first: that drew a false edge to it for every import of a class the other
folder holds (the re-review's finding m5, ``beadloom-ujzb.24``). The segment after the
package is read as the class the import names, and the folders holding a file named
after it (``B.kt``, ``B.java``) are the import's folders; Java requires that name of a
public class, and Kotlin's conventions ask it of a file holding one class. An import
naming no such file — a wildcard, a top-level Kotlin function, a class in a file
named otherwise — reaches every folder of the package, and a caller that needs one
folder gets none: no edge is drawn rather than a guessed one.
"""

# beadloom:domain=graph
# beadloom:feature=import-resolver

from __future__ import annotations

import re
from pathlib import PurePosixPath
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable
    from pathlib import Path

#: The extensions of the code whose packages are read.
JVM_EXTENSIONS = frozenset({".java", ".kt"})

_BLOCK_COMMENT = re.compile(r"/\*.*?\*/", re.DOTALL)
_LINE_COMMENT = re.compile(r"//[^\n]*")
_DECLARATION = re.compile(r"^[ \t]*package[ \t]+([\w.`]+)", re.MULTILINE)
#: A statement that can only follow the package declaration, so a ``package``
#: after it is not one (a property or a parameter named so).
_AFTER_PACKAGE = re.compile(r"^[ \t]*(?:import|class|interface|object|fun|public)\b", re.MULTILINE)


def declared_package(text: str) -> str | None:
    """The package the Java or Kotlin source *text* declares, ``None`` for the default one."""
    code = _LINE_COMMENT.sub("", _BLOCK_COMMENT.sub("", text))
    match = _DECLARATION.search(code)
    if match is None:
        return None
    later = _AFTER_PACKAGE.search(code)
    if later is not None and later.start() < match.start():
        return None
    return match.group(1).replace("`", "").strip(".") or None


class JvmPackages:
    """Each declared package mapped to the folders holding it; false when there is none.

    Built from ``(package, file)`` pairs: the file's folder holds the package, and
    its name (without the extension) is a class the folder answers for.
    """

    def __init__(self, files: Iterable[tuple[str, str]]) -> None:
        self._folders: dict[str, dict[str, set[str]]] = {}
        for package, file in files:
            path = PurePosixPath(file)
            held = self._folders.setdefault(package, {})
            held.setdefault(path.parent.as_posix(), set()).add(path.stem)

    def __bool__(self) -> bool:
        return bool(self._folders)

    def _declared(self, import_path: str) -> tuple[str, list[str]] | None:
        """The declared package *import_path* names, and the segments after it."""
        segments = [part for part in import_path.split(".") if part and part != "*"]
        for depth in range(len(segments), 0, -1):
            package = ".".join(segments[:depth])
            if package in self._folders:
                return package, segments[depth:]
        return None

    def package(self, import_path: str) -> str | None:
        """The project's package *import_path* names, ``None`` when the project declares none."""
        declared = self._declared(import_path)
        return declared[0] if declared is not None else None

    def folders(self, import_path: str) -> tuple[str, ...]:
        """Every folder the import can reach, sorted (see the module docstring)."""
        declared = self._declared(import_path)
        if declared is None:
            return ()
        package, rest = declared
        held = self._folders[package]
        if len(held) > 1 and rest:
            named = sorted(folder for folder, stems in held.items() if rest[0] in stems)
            if named:
                return tuple(named)
        return tuple(sorted(held))

    def directory(self, import_path: str) -> str | None:
        """The one folder of the package *import_path* names, if the project declares it.

        ``None`` too when the import reaches several folders and names none of them.
        """
        reached = self.folders(import_path)
        return reached[0] if len(reached) == 1 else None


def file_package(path: Path) -> str | None:
    """The package the file at *path* declares; ``None`` for none, or for no readable file."""
    try:
        return declared_package(path.read_text(encoding="utf-8", errors="replace"))
    except OSError:
        return None


def read_jvm_packages(project_root: Path, files: Iterable[Path]) -> JvmPackages:
    """The packages *files* declare, each with its file's project-relative path."""
    return JvmPackages(
        (package, path.relative_to(project_root).as_posix())
        for path in files
        if path.suffix in JVM_EXTENSIONS and (package := file_package(path))
    )
