"""Centralized read queries over the graph-index SQLite tables.

# beadloom:domain=infrastructure
# beadloom:component=repository

One responsibility: **named, typed reads of the graph index** (the
``nodes`` / ``edges`` / ``docs`` / ``sync_state`` / ``code_symbols`` tables).
Before this seam, the same row queries — most notably
``SELECT ref_id, kind, summary FROM nodes`` (~16 copies) — were inlined across
services, domains, and the TUI. Centralizing them here removes the duplication
and gives every caller the same typed result objects (:class:`NodeRow`,
:class:`EdgeRow`, :class:`SymbolRow`) instead of bare ``sqlite3.Row`` tuples.

These are pure reads: each function takes an open connection and returns plain
dataclasses, so the module stays in the lowest (infrastructure) layer and is
consumed downward (domains / application / services). The TUI reaches it through
the :mod:`beadloom.application.graph_reads` facade, never directly — the
``tui-no-direct-infra`` boundary forbids a presentation->infrastructure import.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Collection, Iterable, Mapping


@dataclass(frozen=True)
class NodeRow:
    """A graph node row (``ref_id``, ``kind``, ``summary``, optional ``source``)."""

    ref_id: str
    kind: str
    summary: str
    source: str | None = None


@dataclass(frozen=True)
class EdgeRow:
    """A graph edge row (``src_ref_id`` -> ``dst_ref_id`` with ``kind``)."""

    src_ref_id: str
    dst_ref_id: str
    kind: str


@dataclass(frozen=True)
class SymbolRow:
    """A code-symbol row (``symbol_name``, ``kind``, ``line_start``)."""

    symbol_name: str
    kind: str
    line_start: int


# --- Node reads -------------------------------------------------------------

_NODE_COLS = "SELECT ref_id, kind, summary FROM nodes"
_NODE_SOURCE_COLS = "SELECT ref_id, kind, summary, source FROM nodes"


def _node(row: sqlite3.Row, *, with_source: bool = False) -> NodeRow:
    """Map a ``nodes`` row to a :class:`NodeRow`."""
    return NodeRow(
        ref_id=str(row["ref_id"]),
        kind=str(row["kind"]),
        summary=str(row["summary"]),
        source=row["source"] if with_source else None,
    )


def get_all_nodes(conn: sqlite3.Connection) -> list[NodeRow]:
    """Return every node ordered by ``(kind, ref_id)``."""
    rows = conn.execute(f"{_NODE_COLS} ORDER BY kind, ref_id").fetchall()
    return [_node(r) for r in rows]


def get_node(conn: sqlite3.Connection, ref_id: str) -> NodeRow | None:
    """Return the node with *ref_id*, or ``None`` if absent."""
    row = conn.execute(f"{_NODE_COLS} WHERE ref_id = ?", (ref_id,)).fetchone()
    return None if row is None else _node(row)


def get_node_with_source(conn: sqlite3.Connection, ref_id: str) -> NodeRow | None:
    """Return the node with *ref_id* including its ``source`` path, or ``None``."""
    row = conn.execute(f"{_NODE_SOURCE_COLS} WHERE ref_id = ?", (ref_id,)).fetchone()
    return None if row is None else _node(row, with_source=True)


def get_nodes_by_kind(conn: sqlite3.Connection, kind: str) -> list[NodeRow]:
    """Return every node of *kind* ordered by ``ref_id``."""
    rows = conn.execute(
        f"{_NODE_COLS} WHERE kind = ? ORDER BY ref_id", (kind,)
    ).fetchall()
    return [_node(r) for r in rows]


def get_source_paths(conn: sqlite3.Connection) -> list[str]:
    """Return all non-empty node ``source`` paths."""
    rows = conn.execute(
        "SELECT source FROM nodes WHERE source IS NOT NULL AND source != ''"
    ).fetchall()
    return [str(r["source"]) for r in rows]


def get_node_sources(conn: sqlite3.Connection) -> dict[str, str]:
    """Return ``{ref_id: source}`` for every node with a non-blank ``source``."""
    rows = conn.execute(
        "SELECT ref_id, source FROM nodes WHERE source IS NOT NULL"
    ).fetchall()
    out: dict[str, str] = {}
    for row in rows:
        src = str(row["source"])
        if src.strip():
            out[str(row["ref_id"])] = src
    return out


# --- Edge reads -------------------------------------------------------------


def get_all_edges(conn: sqlite3.Connection) -> list[EdgeRow]:
    """Return every edge ordered by ``src_ref_id``."""
    rows = conn.execute(
        "SELECT src_ref_id, dst_ref_id, kind FROM edges ORDER BY src_ref_id"
    ).fetchall()
    return [
        EdgeRow(str(r["src_ref_id"]), str(r["dst_ref_id"]), str(r["kind"]))
        for r in rows
    ]


def get_part_of_children(conn: sqlite3.Connection, ref_id: str) -> list[NodeRow]:
    """Return the child nodes of *ref_id* via ``part_of`` edges, ordered by ``ref_id``."""
    rows = conn.execute(
        "SELECT n.ref_id, n.kind, n.summary "
        "FROM edges e JOIN nodes n ON e.src_ref_id = n.ref_id "
        "WHERE e.dst_ref_id = ? AND e.kind = 'part_of' "
        "ORDER BY n.ref_id",
        (ref_id,),
    ).fetchall()
    return [_node(r) for r in rows]


def get_part_of_containers(conn: sqlite3.Connection) -> dict[str, list[str]]:
    """Return ``{ref_id: [the nodes it is part_of]}`` for every node with a container."""
    rows = conn.execute(
        "SELECT src_ref_id, dst_ref_id FROM edges WHERE kind = 'part_of' "
        "ORDER BY src_ref_id, dst_ref_id"
    ).fetchall()
    containers: dict[str, list[str]] = {}
    for row in rows:
        containers.setdefault(str(row["src_ref_id"]), []).append(str(row["dst_ref_id"]))
    return containers


def get_outgoing_edges(conn: sqlite3.Connection, ref_id: str) -> list[EdgeRow]:
    """Return edges leaving *ref_id* ordered by ``(kind, dst_ref_id)``."""
    rows = conn.execute(
        "SELECT dst_ref_id, kind FROM edges WHERE src_ref_id = ? "
        "ORDER BY kind, dst_ref_id",
        (ref_id,),
    ).fetchall()
    return [EdgeRow(ref_id, str(r["dst_ref_id"]), str(r["kind"])) for r in rows]


def get_incoming_edges(conn: sqlite3.Connection, ref_id: str) -> list[EdgeRow]:
    """Return edges entering *ref_id* ordered by ``(kind, src_ref_id)``."""
    rows = conn.execute(
        "SELECT src_ref_id, kind FROM edges WHERE dst_ref_id = ? "
        "ORDER BY kind, src_ref_id",
        (ref_id,),
    ).fetchall()
    return [EdgeRow(str(r["src_ref_id"]), ref_id, str(r["kind"])) for r in rows]


def count_edges_touching(conn: sqlite3.Connection, ref_id: str) -> int:
    """Return the number of edges with *ref_id* as either endpoint."""
    row = conn.execute(
        "SELECT count(*) FROM edges WHERE src_ref_id = ? OR dst_ref_id = ?",
        (ref_id, ref_id),
    ).fetchone()
    return int(row[0])


# --- Doc reads --------------------------------------------------------------


def get_doc_ref_ids(conn: sqlite3.Connection) -> set[str]:
    """Return the set of ``ref_id``s that have at least one associated doc."""
    rows = conn.execute(
        "SELECT DISTINCT ref_id FROM docs WHERE ref_id IS NOT NULL"
    ).fetchall()
    return {str(r["ref_id"]) for r in rows}


def count_docs(conn: sqlite3.Connection) -> int:
    """Return the total number of indexed docs."""
    row = conn.execute("SELECT count(*) FROM docs").fetchone()
    return int(row[0])


def count_docs_for_ref(conn: sqlite3.Connection, ref_id: str) -> int:
    """Return the number of docs associated with *ref_id*."""
    row = conn.execute(
        "SELECT count(*) FROM docs WHERE ref_id = ?", (ref_id,)
    ).fetchone()
    return int(row[0])


def get_docs_for_ref(conn: sqlite3.Connection, ref_id: str) -> list[tuple[str, str]]:
    """Return ``(path, kind)`` pairs for docs associated with *ref_id*, by path."""
    rows = conn.execute(
        "SELECT path, kind FROM docs WHERE ref_id = ? ORDER BY path", (ref_id,)
    ).fetchall()
    return [(str(r["path"]), str(r["kind"])) for r in rows]


# --- Sync-state reads -------------------------------------------------------
#
# A ``sync_state`` row is a PAIR: one document AND one code file, so three code
# files of one package give three stale pairs over one README. Nineteen surfaces
# read this table and report a number, under four different populations, and all
# four were called "stale docs" (BDL-069 `beadloom-rqma.5`). The count and the
# word for it are therefore produced HERE, together, and a population that is not
# pairs is a differently named function — never an argument to the same one.


@dataclass(frozen=True)
class StaleCount:
    """A count of stale things together with the noun for what was counted.

    Built through :meth:`of_pairs` rather than directly, so the number and the
    word for it cannot be separated at a call site: a surface that has the count
    already (the gate's result list, the TUI's sync provider) asks the same class
    for the sentence as a surface that queried for it.
    """

    count: int
    noun: str

    @classmethod
    def of_pairs(cls, count: int) -> StaleCount:
        """*count* doc-code PAIRS — one ``sync_state`` row each."""
        return cls(count=count, noun="pair")

    @property
    def phrase(self) -> str:
        """``3 stale pair(s)`` — the one spelling every surface prints."""
        return f"{self.count} stale {self.noun}(s)"


def count_stale_pairs(
    conn: sqlite3.Connection, ref_ids: Collection[str] | None = None
) -> StaleCount:
    """Count ``sync_state`` rows marked ``stale`` — one row per doc-code pair.

    *ref_ids* narrows the count to those nodes. ``None`` means every node; an
    EMPTY collection counts nothing, because a caller asking about no node
    (``beadloom why`` on a node with no dependents) is not asking about all of
    them.
    """
    if ref_ids is None:
        row = conn.execute(
            "SELECT count(*) FROM sync_state WHERE status = 'stale'"
        ).fetchone()
    elif not ref_ids:
        return StaleCount.of_pairs(0)
    else:
        placeholders = ",".join("?" for _ in ref_ids)
        row = conn.execute(
            f"SELECT count(*) FROM sync_state "  # noqa: S608 — placeholders only
            f"WHERE ref_id IN ({placeholders}) AND status = 'stale'",
            tuple(ref_ids),
        ).fetchone()
    return StaleCount.of_pairs(int(row[0]) if row is not None else 0)


def stale_node_refs(conn: sqlite3.Connection) -> list[str]:
    """The NODES that own at least one stale pair, by ``ref_id``.

    A different population from :func:`count_stale_pairs` and therefore a
    different function: one node with three stale pairs is one entry here and
    three there. A caller that wants one item per node reaches for this name and
    cannot arrive at a pair count by accident.
    """
    rows = conn.execute(
        "SELECT DISTINCT ref_id FROM sync_state WHERE status = 'stale' ORDER BY ref_id"
    ).fetchall()
    return [str(r["ref_id"]) for r in rows]


def get_stale_pairs_for_ref(
    conn: sqlite3.Connection, ref_id: str
) -> list[tuple[str, str]]:
    """Return ``(doc_path, code_path)`` pairs marked ``stale`` for *ref_id*."""
    rows = conn.execute(
        "SELECT doc_path, code_path FROM sync_state "
        "WHERE ref_id = ? AND status = 'stale'",
        (ref_id,),
    ).fetchall()
    return [(str(r["doc_path"]), str(r["code_path"])) for r in rows]


# --- Code-symbol reads ------------------------------------------------------


def get_symbols_for_source(
    conn: sqlite3.Connection, source: str
) -> list[SymbolRow]:
    """Return symbols whose ``file_path`` matches a node *source* prefix.

    A directory source (``src/dom/``) matches every file beneath it via a
    ``LIKE`` prefix; a file source (``src/dom/feat.py``) matches exactly.
    """
    pattern = source + "%" if source.endswith("/") else source
    rows = conn.execute(
        "SELECT symbol_name, kind, line_start FROM code_symbols "
        "WHERE file_path LIKE ? ORDER BY file_path, line_start",
        (pattern,),
    ).fetchall()
    return [
        SymbolRow(str(r["symbol_name"]), str(r["kind"]), int(r["line_start"]))
        for r in rows
    ]


# --- Node file ownership ----------------------------------------------------
#
# A node's ``source`` is a path PREFIX, and graphs nest: ``src/pkg/`` (a domain)
# holds ``src/pkg/feature/`` (a feature) holds ``src/pkg/feature/impl.py``.
# Attributing by raw prefix counts a child's files against its parent too, so
# carving a subpackage into its own node never relieves the parent — the exact
# remedy a size limit exists to prompt (BDL-UX #144). The rule below is the
# single answer every counter, sizer and linker must share:
#
#   **a file belongs to exactly one node — the most specific one whose source
#   covers it.**


_FACADE_FILENAME = "__init__.py"


def covering_prefix(source: str) -> str:
    """The path prefix a node *source* covers, normalised to end with ``/``.

    A directory source covers everything beneath it. A package façade
    (``pkg/__init__.py``) covers its PACKAGE: the façade only re-exports, so
    treating it as a lone file reports an empty node for a package full of code
    (BDL-UX #157). Any other file source covers only itself, which
    :func:`source_covers` handles separately.

    Public since BDL-061.50: ownership is the rule by which the linter now
    attributes an imported-FROM file to a node, so the two must not each keep
    their own copy of it.
    """
    if source.endswith("/"):
        return source
    if source.endswith(f"/{_FACADE_FILENAME}"):
        return source[: -len(_FACADE_FILENAME)]
    return source


def source_covers(source: str, file_path: str) -> bool:
    """Whether a node *source* covers *file_path* at all (ignoring specificity)."""
    prefix = covering_prefix(source)
    if prefix.endswith("/"):
        return file_path.startswith(prefix)
    return file_path == source


def most_specific_owner(
    sources: Iterable[tuple[str, str]], file_path: str
) -> str | None:
    """The ref_id among *sources* that owns *file_path*, or ``None``.

    *sources* is ``(ref_id, source)`` pairs. Among the sources that cover the
    file, the one with the longest covering prefix wins; on a tie the FIRST pair
    wins, so a caller whose pairs can tie orders them. A blank source owns
    nothing. Pure, so a path that is not in any index — a test file's mirrored
    code path, a declared ``tests:`` prefix — is owned by the same rule
    (BDL-074 C1).
    """
    best: tuple[int, str] | None = None
    for ref_id, source in sources:
        if not source or not source_covers(source, file_path):
            continue
        specificity = len(covering_prefix(source))
        if best is None or specificity > best[0]:
            best = (specificity, ref_id)
    return best[1] if best is not None else None


#: The ``placement`` values ``test_files`` holds (BDL-074 C1). Defined here, below
#: both domains that read them: ``context_oracle.test_binding`` assigns a placement
#: and ``graph.rules.test_binding`` judges it, and a vocabulary two peers share
#: belongs below both rather than in whichever wrote it down first (C3).
#: Bound by the mirror of its path.
PLACEMENT_MIRROR = "mirror"
#: Bound by a node's ``tests:`` declaration.
PLACEMENT_OVERRIDE = "override"
#: Under a mirrored kind folder, and no node owns the code its path names.
PLACEMENT_UNOWNED = "unowned"
#: Not under a kind folder: the layout has not reached it, so it binds to nothing.
PLACEMENT_UNPLACED = "unplaced"
#: Under a kind folder whose binding is not the mirror.
PLACEMENT_OTHER_KIND = "other_kind"
#: Inside a node's source, outside every test root: bound to the node covering it
#: (BDL-074 G2) — ``foo_test.go`` beside ``foo.go``, ``test_x.py`` beside ``x.py``.
PLACEMENT_BESIDE_CODE = "beside_code"
#: Directly under a test root, in a layout that declares ``flat_tests``: bound to the
#: node owning the module its name names — ``tests/test_x.py`` names ``x.py``
#: (BDL-078 ``beadloom-76mk``).
PLACEMENT_NAMED = "named"
#: Directly under a test root, in a layout that declares ``flat_tests``, named after
#: no module one node owns: bound to the one node its imports reach (``beadloom-76mk``).
PLACEMENT_IMPORTED = "imported"

#: The ``kind`` values an ``other_kind`` file carries, beside the placement vocabulary
#: for the same reason (BDL-074 F1): the binding assigns them and the rule engine names
#: them, so a count by kind is read from the index rather than inferred from a folder.
#: An acceptance step file runs scenarios, which bind to a node by their ``@node:`` tag.
KIND_ACCEPTANCE = "acceptance"
#: A self-check tests the project's own files and configuration, and binds to no node
#: by design: a sanctioned kind, not a file the layout has yet to reach.
KIND_SELF_CHECK = "self_check"

#: How a kind is named in a sentence; a kind without an entry is named as recorded.
_KIND_LABELS = {KIND_ACCEPTANCE: "acceptance step", KIND_SELF_CHECK: "self-check"}
#: The kind stated for an ``other_kind`` row that recorded none.
KIND_UNRECORDED = "unrecorded"


def label_test_kind(kind: str) -> str:
    """The words a count of *kind* files is stated in: ``3 self-check file(s)``."""
    return _KIND_LABELS.get(kind, kind)


#: The ``meta`` key the reindex records its test layout under (BDL-074 G2).
TEST_LAYOUT_KEY = "test_layout"


@dataclass(frozen=True)
class RecordedTestLayout:
    """The layout a reindex recognised test files by, as it recorded it in the index.

    Kept beside the placement vocabulary for the same reason: the binding writes it
    and the rule engine states it, and neither may import the other. *kind_prefixes*
    are each kind's folders under every root (``tests/unit/``); *declared_kinds* the
    kinds whose folder the project's config declares rather than defaults;
    *frameworks* the names of the pattern groups a file path is matched against;
    *mirror_roots* the build tools' test trees the project has (``src/test/java``);
    *patterns* each group's patterns, in the order they are matched — empty in a
    record written before ``beadloom-2mj3.15``, which named the groups alone;
    *absent_roots* the roots in force the project does not have, so a reader names
    the roots that exist and can say which were looked for (``beadloom-2mj3.17``);
    *flat_tests* whether a Python test directly under a root binds by the module it
    names, then by its imports — off in a record written before ``beadloom-76mk``.
    """

    kind_prefixes: Mapping[str, tuple[str, ...]]
    declared_kinds: frozenset[str]
    beside_code: bool
    roots: tuple[str, ...]
    frameworks: tuple[str, ...]
    mirror_roots: tuple[str, ...] = ()
    patterns: tuple[tuple[str, tuple[str, ...]], ...] = ()
    absent_roots: tuple[str, ...] = ()
    flat_tests: bool = False

    def encode(self) -> str:
        """The record as the JSON the ``meta`` table holds."""
        return json.dumps(
            {
                "kind_prefixes": {kind: list(p) for kind, p in sorted(self.kind_prefixes.items())},
                "declared_kinds": sorted(self.declared_kinds),
                "beside_code": self.beside_code,
                "roots": list(self.roots),
                "frameworks": list(self.frameworks),
                "mirror_roots": list(self.mirror_roots),
                "patterns": [[name, list(group)] for name, group in self.patterns],
                "absent_roots": list(self.absent_roots),
                "flat_tests": self.flat_tests,
            },
            sort_keys=True,
        )


def read_test_layout(conn: sqlite3.Connection) -> RecordedTestLayout | None:
    """The test layout the last reindex recorded, or ``None`` when it recorded none.

    ``None`` for an index written before BDL-074 G2, or one whose record does not
    parse: the reader then states that the layout is unknown rather than a default.
    """
    try:
        row = conn.execute("SELECT value FROM meta WHERE key = ?", (TEST_LAYOUT_KEY,)).fetchone()
    except sqlite3.OperationalError:
        return None
    if row is None:
        return None
    try:
        raw = json.loads(str(row[0]))
        return RecordedTestLayout(
            kind_prefixes={
                str(kind): tuple(str(p) for p in prefixes)
                for kind, prefixes in raw["kind_prefixes"].items()
            },
            declared_kinds=frozenset(str(kind) for kind in raw["declared_kinds"]),
            beside_code=bool(raw["beside_code"]),
            roots=tuple(str(root) for root in raw["roots"]),
            frameworks=tuple(str(name) for name in raw["frameworks"]),
            mirror_roots=tuple(str(root) for root in raw.get("mirror_roots", ())),
            patterns=tuple(
                (str(name), tuple(str(pattern) for pattern in group))
                for name, group in raw.get("patterns", ())
            ),
            absent_roots=tuple(str(root) for root in raw.get("absent_roots", ())),
            flat_tests=bool(raw.get("flat_tests", False)),
        )
    except (json.JSONDecodeError, KeyError, TypeError, AttributeError):
        return None


def count_test_files_by_placement(conn: sqlite3.Connection) -> dict[str, int]:
    """How many indexed test files each placement holds, read from ``test_files``.

    Empty for an index written before the test tables existed (BDL-074 C1): such
    an index has recorded no placement, and ``ctx`` opens it without creating the
    schema, so the absent table is a fact about the index, not an error.
    """
    try:
        rows = conn.execute(
            "SELECT placement, count(*) AS n FROM test_files GROUP BY placement"
        ).fetchall()
    except sqlite3.OperationalError:
        return {}
    return {str(row["placement"]): int(row["n"]) for row in rows}


def read_unbound_test_files(conn: sqlite3.Connection) -> list[tuple[str, str]]:
    """Each indexed test file bound to no node and placed by no kind folder, with its placement.

    By path. The ``other_kind`` files are left out: a kind folder places them and
    they bind to no node by design, so they are not files the binding could not
    place (BDL-078 ``beadloom-76mk``). Empty for an index without the test tables,
    as :func:`count_test_files_by_placement` is.
    """
    try:
        rows = conn.execute(
            "SELECT path, placement FROM test_files "
            "WHERE ref_id IS NULL AND placement != ? ORDER BY path",
            (PLACEMENT_OTHER_KIND,),
        ).fetchall()
    except sqlite3.OperationalError:
        return []
    return [(str(row[0]), str(row[1])) for row in rows]


def count_other_kind_test_files(conn: sqlite3.Connection) -> dict[str, int]:
    """How many ``other_kind`` test files each recorded kind holds, from ``test_files``.

    The files no mirror binds, by what they are: an acceptance step file and a
    self-check bind to no node for different reasons, and a count that merged them
    would state neither. Empty for an index without the test tables, as
    :func:`count_test_files_by_placement` is.
    """
    try:
        rows = conn.execute(
            "SELECT kind, count(*) FROM test_files WHERE placement = ? GROUP BY kind",
            (PLACEMENT_OTHER_KIND,),
        ).fetchall()
    except sqlite3.OperationalError:
        return {}
    return {KIND_UNRECORDED if row[0] is None else str(row[0]): int(row[1]) for row in rows}


def get_owning_ref_id(
    conn: sqlite3.Connection, file_path: str
) -> str | None:
    """Return the ref_id of the node that OWNS *file_path*, or ``None``.

    Ownership is most-specific-wins: among the nodes whose source covers the
    file, the one with the longest covering prefix. Ties cannot occur — two
    nodes with the same source would be the same scope.
    """
    rows = conn.execute(
        "SELECT ref_id, source FROM nodes WHERE source IS NOT NULL AND source != ''"
    ).fetchall()
    return most_specific_owner(
        ((str(row["ref_id"]), str(row["source"])) for row in rows), file_path
    )


def owns_file(conn: sqlite3.Connection, ref_id: str, file_path: str) -> bool:
    """Whether *ref_id* is the node that owns *file_path* (most specific wins)."""
    return get_owning_ref_id(conn, file_path) == ref_id


def _owned_file_clause(
    conn: sqlite3.Connection, source: str
) -> tuple[str, tuple[str, ...]]:
    """SQL fragment + params selecting the files a node with *source* owns.

    Built as "under my prefix, and not under any strictly-more-specific node's
    prefix" so the exclusion happens in SQL rather than by post-filtering every
    symbol row.
    """
    prefix = covering_prefix(source)
    if prefix.endswith("/"):
        clause = "file_path LIKE ?"
        params: list[str] = [f"{prefix}%"]
    else:
        clause = "file_path = ?"
        params = [source]

    rows = conn.execute(
        "SELECT source FROM nodes WHERE source IS NOT NULL AND source != ''"
    ).fetchall()
    for row in rows:
        other = str(row["source"])
        other_prefix = covering_prefix(other)
        if other_prefix == prefix:
            continue
        # Strictly more specific: covered by me, and longer than my prefix.
        if not other_prefix.startswith(prefix):
            continue
        if other_prefix.endswith("/"):
            clause += " AND file_path NOT LIKE ?"
            params.append(f"{other_prefix}%")
        else:
            clause += " AND file_path != ?"
            params.append(other)
    return clause, tuple(params)


def count_symbols_owned_by_node(conn: sqlite3.Connection, ref_id: str) -> int:
    """Count the symbols in the files *ref_id* owns (nested nodes excluded).

    This is what a size limit must measure: the code the node itself holds, so
    that splitting a subpackage out genuinely relieves it.
    """
    row = conn.execute(
        "SELECT source FROM nodes WHERE ref_id = ?", (ref_id,)
    ).fetchone()
    if row is None or not row["source"]:
        return 0
    clause, params = _owned_file_clause(conn, str(row["source"]))
    count = conn.execute(
        f"SELECT count(*) FROM code_symbols WHERE {clause}",  # noqa: S608
        params,
    ).fetchone()
    return int(count[0])


def count_files_owned_by_node(conn: sqlite3.Connection, ref_id: str) -> int:
    """Count the indexed FILES *ref_id* owns (nested nodes excluded).

    The file-count sibling of :func:`count_symbols_owned_by_node`, over
    ``file_index`` rather than ``code_symbols``.
    """
    row = conn.execute(
        "SELECT source FROM nodes WHERE ref_id = ?", (ref_id,)
    ).fetchone()
    if row is None or not row["source"]:
        return 0
    clause, params = _owned_file_clause(conn, str(row["source"]))
    count = conn.execute(
        f"SELECT count(*) FROM file_index WHERE {clause.replace('file_path', 'path')}",  # noqa: S608
        params,
    ).fetchone()
    return int(count[0])


def get_owned_code_files(conn: sqlite3.Connection, ref_id: str) -> list[tuple[str, str]]:
    """Return ``(path, hash)`` for the indexed CODE files *ref_id* owns.

    The same most-specific-source ownership rule as the counters above, so a
    node never claims a nested node's files. Used to pair a node's doc with its
    code when no symbol carries the node's annotation — without it a node that
    declares ``docs:`` could contribute no sync pair at all and still be
    reported as clean (BDL-UX #146).

    Read from ``file_index``, not ``code_symbols``, since BDL-061.50: the #146
    fallback was itself keyed on SYMBOLS, so a module holding no top-level
    ``def``/``class`` — a pure re-export facade — was unreachable by BOTH the
    annotation path and the fallback, and ``sync-check`` reported it as "no
    indexed code" while the index held it (review .7 MAJOR 3). A file with no
    symbol is still a file whose content can change under a doc.
    """
    row = conn.execute(
        "SELECT source FROM nodes WHERE ref_id = ?", (ref_id,)
    ).fetchone()
    if row is None or not row["source"]:
        return []
    clause, params = _owned_file_clause(conn, str(row["source"]))
    rows = conn.execute(
        "SELECT path, hash FROM file_index "  # noqa: S608
        f"WHERE kind = 'code' AND {clause.replace('file_path', 'path')} ORDER BY path",
        params,
    ).fetchall()
    return [(str(r["path"]), str(r["hash"])) for r in rows]


def get_owned_symbols(conn: sqlite3.Connection, ref_id: str) -> list[SymbolRow]:
    """Return the symbols in the files *ref_id* owns (nested nodes excluded)."""
    row = conn.execute(
        "SELECT source FROM nodes WHERE ref_id = ?", (ref_id,)
    ).fetchone()
    if row is None or not row["source"]:
        return []
    clause, params = _owned_file_clause(conn, str(row["source"]))
    rows = conn.execute(
        "SELECT symbol_name, kind, line_start FROM code_symbols "  # noqa: S608
        f"WHERE {clause} ORDER BY file_path, line_start",
        params,
    ).fetchall()
    return [
        SymbolRow(str(r["symbol_name"]), str(r["kind"]), int(r["line_start"]))
        for r in rows
    ]


# --- Search fallback --------------------------------------------------------


def search_nodes_like(
    conn: sqlite3.Connection, query: str, *, limit: int
) -> list[NodeRow]:
    """Return nodes whose ``ref_id`` or ``summary`` matches *query* (SQL LIKE).

    The non-FTS5 fallback used by search when the FTS5 index is unavailable.
    """
    like_pattern = f"%{query}%"
    rows = conn.execute(
        f"{_NODE_COLS} WHERE ref_id LIKE ? OR summary LIKE ? "
        "ORDER BY ref_id LIMIT ?",
        (like_pattern, like_pattern, limit),
    ).fetchall()
    return [_node(r) for r in rows]
