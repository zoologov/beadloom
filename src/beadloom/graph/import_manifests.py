"""The manifests imports are resolved through, as one fingerprint (``beadloom-jcng``).

A Go import is resolved through the ``go.mod`` and ``go.work`` that govern the importing
file, and a Swift import through ``Package.swift``. Neither manifest is a source file, so an
incremental reindex, which re-reads the source files that changed, never saw an edit to one:
every import under it kept the answer it had before the edit, until the importing file was
touched or a full reindex ran. Found by BDL-076 (``beadloom-ujzb.14``, ``beadloom-ujzb.16``).

**What is recorded.** Beside the index, a fingerprint of every manifest the readers rest on
(:attr:`GoModules.manifests`, :attr:`SwiftPackages.manifests`: path and text), taken from the
same readers the run resolved its imports with, so the fingerprint and the answers describe
one reading of the tree.

**When it is read.** Only when some stored import was written in Go or Swift. The manifests
are found by walking the project, and no answer of a project without such an import can
depend on one; a Go or Swift file that appears later is a changed source file, and the run
that indexes it records the fingerprint.

A JVM package is not in this set: it is read from the files that declare it, so a layout
change moves source files, and an incremental run already resolves every stored import again
when one does (``beadloom-nh7h``).
"""

# beadloom:domain=graph
# beadloom:feature=import-resolver

from __future__ import annotations

import hashlib
import json
from typing import TYPE_CHECKING

from beadloom.graph.go_modules import GoModules
from beadloom.graph.swift_packages import SwiftPackages
from beadloom.infrastructure.db import get_meta, set_meta

if TYPE_CHECKING:
    import sqlite3
    from pathlib import Path

#: The ``meta`` key the fingerprint of the last reading is stored under.
MANIFESTS_META_KEY = "import_manifests"

#: The files whose imports are resolved through a manifest: Go and Swift, as ``LIKE``
#: patterns over ``code_imports.file_path``.
_GO_FILES = "%.go"
_SWIFT_FILES = "%.swift"


def manifests_fingerprint(go_modules: GoModules, swift_packages: SwiftPackages) -> str:
    """One digest of every manifest the two readers rest on, each by path and text."""
    manifests = [*go_modules.manifests, *swift_packages.manifests]
    return hashlib.sha256(json.dumps(manifests, ensure_ascii=False).encode()).hexdigest()


def resolves_through_manifests(conn: sqlite3.Connection) -> bool:
    """Whether some stored import was written in a language a manifest resolves."""
    row = conn.execute(
        "SELECT 1 FROM code_imports WHERE file_path LIKE ? OR file_path LIKE ? LIMIT 1",
        (_GO_FILES, _SWIFT_FILES),
    ).fetchone()
    return row is not None


def record_manifests(
    conn: sqlite3.Connection, go_modules: GoModules, swift_packages: SwiftPackages
) -> None:
    """Store the fingerprint of the reading the stored imports were just resolved through."""
    if resolves_through_manifests(conn):
        set_meta(conn, MANIFESTS_META_KEY, manifests_fingerprint(go_modules, swift_packages))


def manifests_changed(project_root: Path, conn: sqlite3.Connection) -> bool:
    """Whether a manifest some stored import rests on differs from the one it was read in.

    ``True`` also for an index that recorded no fingerprint and holds such an import, which
    is an index written before the fingerprint existed: its answers are resolved once more.
    """
    if not resolves_through_manifests(conn):
        return False
    current = manifests_fingerprint(GoModules(project_root), SwiftPackages(project_root))
    return get_meta(conn, MANIFESTS_META_KEY) != current
