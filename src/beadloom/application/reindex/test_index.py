# beadloom:domain=application
# beadloom:feature=reindex
"""Test index: record a project's test files in their own tables, bound to nodes.

This module owns the reindex step that finds a project's test files, binds each
to a node by :mod:`beadloom.context_oracle.test_binding`, records it — path, kind,
node, placement, test count, imports — in ``test_files`` / ``test_imports``, and
rebuilds every node's ``extra["tests"]`` from that binding in the four-key shape its
readers expect (``framework``, ``test_files``, ``test_count``, ``coverage_estimate``).

Where test files are and what makes a file one is the project's test layout
(:mod:`beadloom.context_oracle.test_layout`, BDL-074 G2): the roots it declares
are walked (``tests/`` by default), and when tests beside the code are read, the
indexed code files whose paths match a test pattern are taken from the code scan
— they are not walked again. The layout is recorded in the index
(``meta.test_layout``), so the readers that state a count can say what it was
recognised by.

Tests under a root are never added to ``scan_paths``, ``code_symbols``,
``code_imports`` or ``file_index``: they must not become code. A test beside the
code was already indexed as code by the code scan, which this step does not
change. Only the roots and the code scan are read, so a mutmut copy under
``mutants/`` is never a test of anything unless a scan path covers it. A node's
``tests:`` YAML key is read ONCE, at a full reindex, into ``test_overrides``; the
``extra["tests"]`` it arrived in is then rebuilt from the binding, which the
declaration is part of, and a declared prefix that covers no indexed test file is
reported (review ``beadloom-b9ll`` m5).
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import PurePosixPath
from typing import TYPE_CHECKING, TypeGuard

from beadloom.context_oracle.test_binding import (
    PLACEMENT_BESIDE_CODE,
    PLACEMENT_MIRROR,
    PLACEMENT_OVERRIDE,
    PLACEMENT_UNOWNED,
    PLACEMENT_UNPLACED,
    BoundTestFile,
    bind_test_file,
    name_frameworks,
    summarize_tests,
    union_over_descendants,
)
from beadloom.context_oracle.test_file_reader import TestFileContents, read_test_file
from beadloom.context_oracle.test_layout import TestLayout, load_test_layout
from beadloom.graph.import_resolver import resolve_import_to_node
from beadloom.infrastructure.db import get_meta, set_meta
from beadloom.infrastructure.repository import (
    TEST_LAYOUT_KEY,
    RecordedTestLayout,
    count_other_kind_test_files,
    count_test_files_by_placement,
    label_test_kind,
    source_covers,
)
from beadloom.infrastructure.scan_paths import resolve_scan_paths

if TYPE_CHECKING:
    import sqlite3
    from collections.abc import Callable, Collection, Iterable
    from pathlib import Path

#: Meta key recording that the index holds the test tables. An index written
#: before them reports a different value (or none) and is rebuilt in full once,
#: because only a full rebuild reads the ``tests:`` declarations.
TEST_INDEX_VERSION_KEY = "test_index_version"
TEST_INDEX_VERSION = "1"

#: The node key a ``tests:`` declaration is stored under by the graph loader.
_TESTS_KEY = "tests"

#: Directories that hold no test source: bytecode, jest snapshots (whose
#: ``x.test.ts.snap`` names match ``*.test.*``) and installed packages.
_SKIP_DIRS = frozenset({"__pycache__", "__snapshots__", "node_modules"})


@dataclass(frozen=True)
class IndexedTestFiles:
    """What one indexing pass recorded, by placement, and what it could not use."""

    by_placement: dict[str, int] = field(default_factory=dict)
    warnings: tuple[str, ...] = ()

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


def discover_test_files(
    project_root: Path,
    layout: TestLayout | None = None,
    *,
    code_files: Iterable[str] = (),
) -> dict[str, str]:
    """Every test file the layout reads, by project-relative path, with its text.

    The files under the layout's roots and the build tools' test trees it
    mirrors whose paths match a test pattern, and — when it reads tests beside
    the code — each of *code_files* (the code scan's paths) outside all of those
    whose path matches one. A file anywhere else is not read, whatever its name:
    binding it would take a guess at its node, which the owner's ruling of
    2026-09-28 excludes, so ``ctx`` and the debt report say where a test file is
    read instead (``beadloom-2mj3.15``). *layout* defaults to the one the project declares.
    """
    layout = layout if layout is not None else load_test_layout(project_root)[0]
    found: dict[str, str] = {}
    for root in (*layout.roots, *present_mirror_roots(project_root, layout)):
        if not _is_folder_as_spelled(project_root, root):
            continue
        for path in sorted((project_root / root).rglob("*")):
            relative = path.relative_to(project_root).as_posix()
            if _is_test_path(relative, layout) and path.is_file():
                found[relative] = _read(path)
    if layout.beside_code:
        for code_file in sorted(code_files):
            if code_file in found or _under_a_test_root(code_file, layout):
                continue
            path = project_root / code_file
            if _is_test_path(code_file, layout) and path.is_file():
                found[code_file] = _read(path)
    return found


def present_mirror_roots(project_root: Path, layout: TestLayout) -> tuple[str, ...]:
    """The build tools' test trees of *layout* this project has, spelled as declared."""
    return tuple(
        test_root
        for test_root, _ in layout.mirrors
        if _is_folder_as_spelled(project_root, test_root)
    )


def _recorded_layout(project_root: Path, layout: TestLayout) -> RecordedTestLayout:
    """The layout as the index records it: the roots and test trees this project has."""
    present_roots = tuple(
        root for root in layout.roots if _is_folder_as_spelled(project_root, root)
    )
    return layout.recorded(present_mirror_roots(project_root, layout), present_roots)


def _is_folder_as_spelled(project_root: Path, relative: str) -> bool:
    """Whether *relative* is a folder under *project_root*, with exactly that spelling.

    A case-insensitive disk (the macOS and Windows defaults) opens ``Tests/`` for
    ``tests``, so a Swift package's test tree would be read twice, once under each
    name, if existence were asked of the disk alone.
    """
    current = project_root
    for part in PurePosixPath(relative).parts:
        if not current.is_dir() or part not in {child.name for child in current.iterdir()}:
            return False
        current = current / part
    return current.is_dir()


def _under_a_test_root(path: str, layout: TestLayout) -> bool:
    return layout.locate(path) is not None or layout.mirror_of(path) is not None


def _is_test_path(relative: str, layout: TestLayout) -> bool:
    parts = PurePosixPath(relative).parts
    return not _SKIP_DIRS.intersection(parts) and layout.is_test_file(relative)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def is_test_index_current(project_root: Path, conn: sqlite3.Connection) -> bool:
    """Whether the test index was built under today's layout and holds today's root files.

    Asked only when no code file changed, so a test beside the code — read from
    the code scan — is unchanged by construction; the files under the roots are
    compared by hash, and the recorded layout against the one the config declares.
    """
    layout = load_test_layout(project_root)[0]
    recorded = _recorded_layout(project_root, layout)
    if get_meta(conn, TEST_LAYOUT_KEY) != recorded.encode():
        return False
    on_disk = {
        path: _hash(text) for path, text in discover_test_files(project_root, layout).items()
    }
    stored = {
        str(row["path"]): str(row["file_hash"])
        for row in conn.execute("SELECT path, file_hash FROM test_files").fetchall()
        if _under_a_test_root(str(row["path"]), layout)
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
    layout, problems = load_test_layout(project_root)
    files = discover_test_files(project_root, layout, code_files=code_files)
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
    resolve = _memoised_resolver(project_root, conn, scan_paths, layout.roots[0])

    conn.execute("DELETE FROM test_files")
    conn.execute("DELETE FROM test_imports")
    bound: list[BoundTestFile] = []
    counts: dict[str, int] = {}
    for path, text in files.items():
        digest = _hash(text)
        recorded = previous.get(path)
        contents = (
            recorded[1]
            if recorded and recorded[0] == digest
            else read_test_file(text, suffix=PurePosixPath(path).suffix)
        )
        binding = bind_test_file(
            path,
            code_files=code_files,
            scan_paths=scan_paths,
            node_sources=node_sources,
            overrides=overrides,
            layout=layout,
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

    frameworks = {path: layout.framework_of(path) or "" for path in files}
    _rebuild_extra_tests(conn, bound, counts, frameworks)
    set_meta(conn, TEST_INDEX_VERSION_KEY, TEST_INDEX_VERSION)
    set_meta(conn, TEST_LAYOUT_KEY, _recorded_layout(project_root, layout).encode())
    conn.commit()

    by_placement: dict[str, int] = {}
    for binding in bound:
        by_placement[binding.placement] = by_placement.get(binding.placement, 0) + 1
    return IndexedTestFiles(
        by_placement=by_placement,
        warnings=(*problems, *_declarations_binding_nothing(overrides, files)),
    )


def _declarations_binding_nothing(
    overrides: Iterable[tuple[str, str]], files: Collection[str]
) -> list[str]:
    """A warning for each declared ``tests:`` prefix no indexed test file sits under.

    Such a declaration is inert, and an inert declaration reads exactly like one
    that works: ``tests/e2e`` without its trailing slash names one file of that
    name, so the folder stays unplaced (review ``beadloom-b9ll`` m5).
    """
    warnings: list[str] = []
    for ref_id, prefix in overrides:
        if any(source_covers(prefix, path) for path in files):
            continue
        hint = "" if prefix.endswith("/") else " (a folder is declared with a trailing '/')"
        warnings.append(
            f"Node '{ref_id}': `tests:` prefix '{prefix}' covers no indexed test file, "
            f"so it binds nothing{hint}"
        )
    return warnings


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
    project_root: Path, conn: sqlite3.Connection, scan_paths: list[str], root: str
) -> Callable[[str], str | None]:
    """Resolve a dotted import to its owning node, once per import path.

    A suite imports the same few hundred modules thousands of times, and the
    resolver's answer for a Python import depends on the import path alone.
    """
    anchor = project_root / root
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
    frameworks: dict[str, str],
) -> None:
    """Write ``extra["tests"]`` for every node that has a source or declared tests.

    A node's framework is named from the patterns its bound files matched
    (*frameworks*, by path); a node with no bound file states the project's.
    """
    project_framework = name_frameworks(fw for fw in frameworks.values() if fw)
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
        own = name_frameworks(frameworks[path] for path in files if frameworks.get(path))
        framework = own if files else project_framework
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
    """How many indexed test files each placement holds, read from ``test_files``.

    The read itself lives in the repository, because ``ctx`` and the debt report
    state the same counts and neither may import the reindex.
    """
    return count_test_files_by_placement(conn)


def kind_counts(conn: sqlite3.Connection) -> dict[str, int]:
    """How many ``other_kind`` test files each recorded kind holds (BDL-074 F1)."""
    return count_other_kind_test_files(conn)


def needs_full_test_reindex(conn: sqlite3.Connection) -> bool:
    """Whether this index predates the test tables and must be rebuilt in full."""
    return get_meta(conn, TEST_INDEX_VERSION_KEY) != TEST_INDEX_VERSION


def describe_placements(counts: dict[str, int], kinds: dict[str, int]) -> str:
    """One line stating how many test files there are and how each was placed.

    The bound and unplaced counts are always stated, so a repository whose tests
    are not laid out yet reads differently from one whose tests bind to nothing.
    The ``other_kind`` files are named by their recorded kind (*kinds*), each with
    its count: an acceptance step file and a self-check bind differently, and one
    phrase over both was true of neither (BDL-074 F1).
    """
    beside = counts.get(PLACEMENT_BESIDE_CODE, 0)
    bound = counts.get(PLACEMENT_MIRROR, 0) + counts.get(PLACEMENT_OVERRIDE, 0) + beside
    bound_phrase = f"{bound} bound to a node" + (f" ({beside} beside the code)" if beside else "")
    parts = [bound_phrase, f"{counts.get(PLACEMENT_UNPLACED, 0)} unplaced"]
    if counts.get(PLACEMENT_UNOWNED):
        parts.append(f"{counts[PLACEMENT_UNOWNED]} unowned")
    parts.extend(f"{count} {label_test_kind(kind)}" for kind, count in sorted(kinds.items()))
    return f"{sum(counts.values())} files ({', '.join(parts)})"
