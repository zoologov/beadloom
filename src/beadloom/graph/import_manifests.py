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

**The JavaScript side** (BDL-080 ``beadloom-cwzc``). A non-relative JS/TS import is resolved
through the project's tsconfig/jsconfig files (:attr:`TsConfigs.manifests`) and through the
aliases declared under ``imports.aliases:`` in ``.beadloom/config.yml``. Both are in the
fingerprint, read only when some stored import was written in JavaScript, TypeScript or a
Vue component, and only then: a project without one records what it recorded before, so
an upgrade re-resolves nothing it need not.
"""

# beadloom:domain=graph
# beadloom:feature=import-resolver

from __future__ import annotations

import hashlib
import json
from typing import TYPE_CHECKING

from beadloom.graph.go_modules import GoModules
from beadloom.graph.swift_packages import SwiftPackages
from beadloom.graph.tsconfig_paths import TsConfigs
from beadloom.infrastructure.db import get_meta, set_meta

if TYPE_CHECKING:
    import sqlite3
    from collections.abc import Sequence
    from pathlib import Path

#: The ``meta`` key the fingerprint of the last reading is stored under.
MANIFESTS_META_KEY = "import_manifests"

#: The files whose imports are resolved through a manifest: Go and Swift, as ``LIKE``
#: patterns over ``code_imports.file_path``.
_GO_FILES = "%.go"
_SWIFT_FILES = "%.swift"
_NATIVE_FILES = (_GO_FILES, _SWIFT_FILES)
#: The files whose non-relative imports are read through tsconfig and the declared aliases.
_SCRIPT_FILES = ("%.ts", "%.tsx", "%.js", "%.jsx", "%.mjs", "%.cjs", "%.vue")
#: The entry the declared aliases take in the fingerprint, named so it cannot be a path.
_ALIASES_ENTRY = "imports.aliases:"


def _digest(manifests: Sequence[object]) -> str:
    return hashlib.sha256(json.dumps(list(manifests), ensure_ascii=False).encode()).hexdigest()


def manifests_fingerprint(go_modules: GoModules, swift_packages: SwiftPackages) -> str:
    """One digest of every manifest the two readers rest on, each by path and text."""
    return _digest([*go_modules.manifests, *swift_packages.manifests])


def _holds(conn: sqlite3.Connection, patterns: Sequence[str]) -> bool:
    """Whether some stored import was written in a file matching one of *patterns*."""
    where = " OR ".join("file_path LIKE ?" for _ in patterns)
    query = f"SELECT 1 FROM code_imports WHERE {where} LIMIT 1"  # noqa: S608 - placeholders only
    return conn.execute(query, tuple(patterns)).fetchone() is not None


def resolves_through_manifests(conn: sqlite3.Connection) -> bool:
    """Whether some stored import was written in a language a manifest resolves."""
    return _holds(conn, _NATIVE_FILES) or _holds(conn, _SCRIPT_FILES)


def _readings(
    native: tuple[GoModules, SwiftPackages] | None,
    ts_configs: TsConfigs | None,
    aliases: Sequence[tuple[str, str]],
) -> str:
    """The digest of the families read: Go and Swift manifests, then the JavaScript side.

    A project with no JavaScript import digests exactly what ``beadloom-jcng`` digested,
    so its index is not resolved again on the upgrade that added the JavaScript side.
    """
    manifests: list[object] = []
    if native is not None:
        go_modules, swift_packages = native
        manifests.extend([*go_modules.manifests, *swift_packages.manifests])
    if ts_configs is not None:
        manifests.extend(ts_configs.manifests)
        if aliases:
            manifests.append([_ALIASES_ENTRY, [list(pair) for pair in aliases]])
    return _digest(manifests)


def record_manifests(
    conn: sqlite3.Connection,
    go_modules: GoModules,
    swift_packages: SwiftPackages,
    ts_configs: TsConfigs,
    aliases: Sequence[tuple[str, str]],
) -> None:
    """Store the fingerprint of the reading the stored imports were just resolved through.

    Each family is digested only when a stored import was written in its languages: the
    walks for ``go.mod``, ``Package.swift`` and tsconfig files cost a walk of the project
    each, and no answer of a project without such an import depends on them.
    """
    native = _holds(conn, _NATIVE_FILES)
    script = _holds(conn, _SCRIPT_FILES)
    if not native and not script:
        return
    current = _readings(
        (go_modules, swift_packages) if native else None,
        ts_configs if script else None,
        aliases,
    )
    set_meta(conn, MANIFESTS_META_KEY, current)


def manifests_changed(
    project_root: Path,
    conn: sqlite3.Connection,
    *,
    aliases: Sequence[tuple[str, str]] = (),
) -> bool:
    """Whether a declaration some stored import rests on differs from the one it was read in.

    ``True`` also for an index that recorded no fingerprint and holds such an import, which
    is an index written before the fingerprint existed: its answers are resolved once more.
    *aliases* are the pairs ``imports.aliases:`` declares now. A family no stored import
    is written in is not read, not even constructed.
    """
    native = _holds(conn, _NATIVE_FILES)
    script = _holds(conn, _SCRIPT_FILES)
    if not native and not script:
        return False
    current = _readings(
        (GoModules(project_root), SwiftPackages(project_root)) if native else None,
        TsConfigs(project_root) if script else None,
        aliases,
    )
    return get_meta(conn, MANIFESTS_META_KEY) != current
