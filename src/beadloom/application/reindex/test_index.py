# beadloom:domain=application
# beadloom:feature=reindex
"""Test index: record a project's test files in their own tables, bound to nodes.

This module owns the reindex step that walks ``tests/``, binds each test file to a
node by :mod:`beadloom.context_oracle.test_binding`, records it — path, kind, node,
placement, test count, imports — in ``test_files`` / ``test_imports``, and rebuilds
every node's ``extra["tests"]`` from that binding in the four-key shape its readers
expect (``framework``, ``test_files``, ``test_count``, ``coverage_estimate``).

Tests are never added to ``scan_paths``, ``code_symbols``, ``code_imports`` or
``file_index``: they must not become code. Only ``tests/`` is walked, so a mutmut
copy under ``mutants/`` is never a test of anything. A node's ``tests:`` YAML key
is read ONCE, at a full reindex, into ``test_overrides``; the ``extra["tests"]``
it arrived in is then rebuilt from the binding, which the declaration is part of.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, TypeGuard

from beadloom.context_oracle.test_binding import (
    FRAMEWORK_NONE,
    FRAMEWORK_PYTEST,
    PLACEMENT_MIRROR,
    PLACEMENT_OTHER_KIND,
    PLACEMENT_OVERRIDE,
    PLACEMENT_UNOWNED,
    PLACEMENT_UNPLACED,
    TEST_ROOT,
    BoundTestFile,
    bind_test_file,
    is_test_file,
    summarize_tests,
    union_over_descendants,
)
from beadloom.context_oracle.test_file_reader import TestFileContents, read_test_file
from beadloom.graph.import_resolver import resolve_import_to_node
from beadloom.infrastructure.db import get_meta, set_meta
from beadloom.infrastructure.scan_paths import resolve_scan_paths

if TYPE_CHECKING:
    import sqlite3
    from collections.abc import Callable, Collection
    from pathlib import Path

#: Meta key recording that the index holds the test tables. An index written
#: before them reports a different value (or none) and is rebuilt in full once,
#: because only a full rebuild reads the ``tests:`` declarations.
TEST_INDEX_VERSION_KEY = "test_index_version"
TEST_INDEX_VERSION = "1"

#: The node key a ``tests:`` declaration is stored under by the graph loader.
_TESTS_KEY = "tests"

#: Directories under ``tests/`` that hold no test source.
_SKIP_DIRS = frozenset({"__pycache__"})


@dataclass(frozen=True)
class IndexedTestFiles:
    """What one indexing pass recorded, by placement."""

    by_placement: dict[str, int] = field(default_factory=dict)

    @property
    def total(self) -> int:
        return sum(self.by_placement.values())

    @property
    def unplaced(self) -> int:
        return self.by_placement.get(PLACEMENT_UNPLACED, 0)


def record_declared_test_overrides(conn: sqlite3.Connection) -> list[str]:
    """Copy each node's ``tests:`` declaration into ``test_overrides``.

    Returns a warning for each declaration that is not a list of path strings;
    such a declaration binds nothing, and saying so is what makes it fixable.
    """
    conn.execute("DELETE FROM test_overrides")
    warnings: list[str] = []
    for row in conn.execute("SELECT ref_id, extra FROM nodes").fetchall():
        declared = _extra(row["extra"]).get(_TESTS_KEY)
        if declared is None:
            continue
        if not _is_path_list(declared):
            warnings.append(
                f"Node '{row['ref_id']}': `tests:` must be a list of path prefixes "
                "under the project root; the declaration binds nothing."
            )
            continue
        conn.executemany(
            "INSERT OR IGNORE INTO test_overrides (ref_id, prefix) VALUES (?, ?)",
            [(row["ref_id"], prefix.strip()) for prefix in declared],
        )
    conn.commit()
    return warnings


def _is_path_list(value: object) -> TypeGuard[list[str]]:
    return (
        isinstance(value, list)
        and bool(value)
        and all(isinstance(item, str) and item.strip() for item in value)
    )


def discover_test_files(project_root: Path) -> dict[str, str]:
    """Every test file under ``tests/``, by project-relative path, with its text."""
    base = project_root / TEST_ROOT
    if not base.is_dir():
        return {}
    found: dict[str, str] = {}
    for path in sorted(base.rglob("*.py")):
        relative = path.relative_to(project_root)
        if _SKIP_DIRS.intersection(relative.parts) or not is_test_file(path.name):
            continue
        if not path.is_file():
            continue
        found[relative.as_posix()] = path.read_text(encoding="utf-8", errors="replace")
    return found


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def is_test_index_current(project_root: Path, conn: sqlite3.Connection) -> bool:
    """Whether ``test_files`` holds exactly the test files on disk, unchanged."""
    on_disk = {path: _hash(text) for path, text in discover_test_files(project_root).items()}
    stored = {
        str(row["path"]): str(row["file_hash"])
        for row in conn.execute("SELECT path, file_hash FROM test_files").fetchall()
    }
    return on_disk == stored


def index_test_files(
    project_root: Path,
    conn: sqlite3.Connection,
    *,
    code_files: Collection[str],
) -> IndexedTestFiles:
    """Rebuild the test tables and every node's ``extra["tests"]`` from the binding.

    *code_files* are the project's indexed code paths, which the mirror resolves
    against. Imports are resolved by the code-import resolver, so this runs after
    ``code_symbols`` and ``file_index`` are populated. A file whose hash matches
    the one recorded is not parsed again: the incremental reindex runs this on
    every change, and re-reading an unchanged suite is the cost it must not pay.
    """
    files = discover_test_files(project_root)
    previous = _recorded_contents(conn)
    scan_paths = resolve_scan_paths(project_root)
    node_sources = [
        (str(row["ref_id"]), str(row["source"]))
        for row in conn.execute(
            "SELECT ref_id, source FROM nodes WHERE source IS NOT NULL AND source != ''"
        ).fetchall()
    ]
    overrides = [
        (str(row["ref_id"]), str(row["prefix"]))
        for row in conn.execute(
            "SELECT ref_id, prefix FROM test_overrides ORDER BY ref_id, prefix"
        ).fetchall()
    ]
    resolve = _memoised_resolver(project_root, conn, scan_paths)

    conn.execute("DELETE FROM test_files")
    conn.execute("DELETE FROM test_imports")
    bound: list[BoundTestFile] = []
    counts: dict[str, int] = {}
    for path, text in files.items():
        digest = _hash(text)
        recorded = previous.get(path)
        contents = recorded[1] if recorded and recorded[0] == digest else read_test_file(text)
        binding = bind_test_file(
            path,
            code_files=code_files,
            scan_paths=scan_paths,
            node_sources=node_sources,
            overrides=overrides,
        )
        counts[path] = contents.test_count
        conn.execute(
            "INSERT INTO test_files (path, kind, ref_id, placement, test_count, file_hash) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (path, binding.kind, binding.ref_id, binding.placement, contents.test_count, digest),
        )
        conn.executemany(
            "INSERT OR IGNORE INTO test_imports "
            "(file_path, line_number, import_path, resolved_ref_id) VALUES (?, ?, ?, ?)",
            [(path, line, module, resolve(module)) for line, module in contents.imports],
        )
        bound.append(binding)

    framework = FRAMEWORK_PYTEST if files else FRAMEWORK_NONE
    _rebuild_extra_tests(conn, bound, counts, framework=framework)
    set_meta(conn, TEST_INDEX_VERSION_KEY, TEST_INDEX_VERSION)
    conn.commit()

    by_placement: dict[str, int] = {}
    for binding in bound:
        by_placement[binding.placement] = by_placement.get(binding.placement, 0) + 1
    return IndexedTestFiles(by_placement=by_placement)


def _recorded_contents(conn: sqlite3.Connection) -> dict[str, tuple[str, TestFileContents]]:
    """What the last pass read from each test file, keyed by path, with its hash."""
    imports: dict[str, list[tuple[int, str]]] = {}
    for row in conn.execute(
        "SELECT file_path, line_number, import_path FROM test_imports"
    ).fetchall():
        imports.setdefault(str(row["file_path"]), []).append(
            (int(row["line_number"]), str(row["import_path"]))
        )
    return {
        str(row["path"]): (
            str(row["file_hash"]),
            TestFileContents(
                test_count=int(row["test_count"]),
                imports=tuple(sorted(imports.get(str(row["path"]), []))),
            ),
        )
        for row in conn.execute("SELECT path, file_hash, test_count FROM test_files").fetchall()
    }


def _memoised_resolver(
    project_root: Path, conn: sqlite3.Connection, scan_paths: list[str]
) -> Callable[[str], str | None]:
    """Resolve a dotted import to its owning node, once per import path.

    A suite imports the same few hundred modules thousands of times, and the
    resolver's answer for a Python import depends on the import path alone.
    """
    anchor = project_root / TEST_ROOT
    cache: dict[str, str | None] = {}

    def resolve(import_path: str) -> str | None:
        if import_path not in cache:
            cache[import_path] = resolve_import_to_node(
                import_path, anchor, conn, scan_paths=scan_paths
            )
        return cache[import_path]

    return resolve


def _rebuild_extra_tests(
    conn: sqlite3.Connection,
    bound: list[BoundTestFile],
    counts: dict[str, int],
    *,
    framework: str,
) -> None:
    """Write ``extra["tests"]`` for every node that has a source or declared tests."""
    direct: dict[str, set[str]] = {}
    for binding in bound:
        if binding.ref_id is not None:
            direct.setdefault(binding.ref_id, set()).add(binding.path)

    parent_children: dict[str, list[str]] = {}
    for edge in conn.execute(
        "SELECT src_ref_id, dst_ref_id FROM edges WHERE kind = 'part_of'"
    ).fetchall():
        parent_children.setdefault(str(edge["dst_ref_id"]), []).append(str(edge["src_ref_id"]))
    union = union_over_descendants(direct, parent_children)

    for row in conn.execute("SELECT ref_id, source, extra FROM nodes").fetchall():
        extra = _extra(row["extra"])
        if row["source"] is None and _TESTS_KEY not in extra:
            continue
        files = union.get(str(row["ref_id"]), frozenset())
        extra[_TESTS_KEY] = summarize_tests(files, counts, framework=framework)
        conn.execute(
            "UPDATE nodes SET extra = ? WHERE ref_id = ?",
            (json.dumps(extra, ensure_ascii=False), row["ref_id"]),
        )


def _extra(raw: object) -> dict[str, object]:
    if not isinstance(raw, str) or not raw:
        return {}
    try:
        loaded = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return loaded if isinstance(loaded, dict) else {}


def placement_counts(conn: sqlite3.Connection) -> dict[str, int]:
    """How many indexed test files each placement holds, read from ``test_files``."""
    return {
        str(row["placement"]): int(row["n"])
        for row in conn.execute(
            "SELECT placement, count(*) AS n FROM test_files GROUP BY placement"
        ).fetchall()
    }


def needs_full_test_reindex(conn: sqlite3.Connection) -> bool:
    """Whether this index predates the test tables and must be rebuilt in full."""
    return get_meta(conn, TEST_INDEX_VERSION_KEY) != TEST_INDEX_VERSION


def describe_placements(counts: dict[str, int]) -> str:
    """One line stating how many test files there are and how each was placed.

    The bound and unplaced counts are always stated, so a repository whose tests
    are not laid out yet reads differently from one whose tests bind to nothing.
    """
    bound = counts.get(PLACEMENT_MIRROR, 0) + counts.get(PLACEMENT_OVERRIDE, 0)
    parts = [f"{bound} bound to a node", f"{counts.get(PLACEMENT_UNPLACED, 0)} unplaced"]
    if counts.get(PLACEMENT_UNOWNED):
        parts.append(f"{counts[PLACEMENT_UNOWNED]} unowned")
    if counts.get(PLACEMENT_OTHER_KIND):
        parts.append(f"{counts[PLACEMENT_OTHER_KIND]} bound by other means")
    return f"{sum(counts.values())} files ({', '.join(parts)})"
