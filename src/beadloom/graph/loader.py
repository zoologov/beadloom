"""YAML graph parser and SQLite loader.

Reads ``.beadloom/_graph/*.yml`` files and populates the ``nodes`` and
``edges`` tables.  Validates ref_id uniqueness and edge integrity.
"""

# beadloom:domain=graph
# beadloom:component=graph-loader

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import yaml

from beadloom.graph.contracts import contract_key
from beadloom.graph.federation import FederationRefError, parse_ref
from beadloom.graph.graphql_surface import (
    extract_typed_surface,
    serialize_typed_surface,
)
from beadloom.graph.sdl import extract_surface
from beadloom.infrastructure.atomic_io import write_yaml_atomic

if TYPE_CHECKING:
    from collections.abc import Iterable
    from pathlib import Path


def get_node_tags(conn: sqlite3.Connection, ref_id: str) -> set[str]:
    """Extract tags from a node's ``extra`` JSON column.

    Returns an empty set when the node does not exist, has no ``extra``
    data, or has no ``tags`` key in its extra JSON.
    """
    row = conn.execute("SELECT extra FROM nodes WHERE ref_id = ?", (ref_id,)).fetchone()
    if not row:
        return set()
    raw = row[0] if isinstance(row, tuple) else row["extra"]
    if raw is None:
        return set()
    extra: dict[str, Any] = json.loads(str(raw))
    return set(extra.get("tags", []))


#: The file in ``.beadloom/_graph/`` that is not a graph file. ``rules.yml``
#: holds rules and no nodes, so a reader that walked it would either find
#: nothing or mistake a rule for a node.
#:
#: It is declared HERE, in the domain that owns the graph file format and that
#: also reads ``rules.yml`` (``graph/linter.py``), and re-exported by
#: ``onboarding.graph_files`` for the readers that go through the skip policy.
#: The direction is what makes one constant possible: ``onboarding`` may import
#: ``graph`` and the reverse is a cycle, so a constant needed on both sides can
#: only live on this one (BDL-069).
NOT_A_GRAPH_FILE = frozenset({"rules.yml"})

# Fields mapped directly to SQLite columns (not stored in ``extra``).
_NODE_DIRECT_FIELDS = frozenset({"ref_id", "kind", "summary", "source", "lifecycle"})
# ``docs`` is tracked but handled by the doc indexer (BEAD-04).
_NODE_SKIP_FIELDS = frozenset({"docs"})

# Valid lifecycle states (BDL-037 Principle 8; BDL-038 G7 adds ``external``).
# Default is ``active``; absent or unknown values fall back to ``active`` so
# existing graphs are unchanged. ``external`` marks a present-but-not-ours node
# (e.g. a native Swift/Kotlin/ObjC++/C++ bridge) so its dependents suppress DRIFT
# at the hub (the contract/edge target resolves to ``EXTERNAL``, never DRIFT).
VALID_LIFECYCLES = frozenset({"active", "planned", "deprecated", "dead", "external"})
_DEFAULT_LIFECYCLE = "active"

# Protocol whose producers carry a parsed SDL surface (BDL-038 BEAD-03).
_GRAPHQL = "graphql"


def _normalize_lifecycle(raw: object, context: str, result: GraphLoadResult) -> str:
    """Validate a ``lifecycle`` value, recording unknown values as errors.

    Returns the validated lifecycle, or ``active`` when *raw* is absent or
    invalid (the invalid case is recorded loudly — never silently dropped).
    """
    if raw is None:
        return _DEFAULT_LIFECYCLE
    value = str(raw)
    if value not in VALID_LIFECYCLES:
        result.errors.append(
            f"{context}: invalid lifecycle '{value}', "
            f"must be one of {sorted(VALID_LIFECYCLES)}; defaulting to 'active'"
        )
        return _DEFAULT_LIFECYCLE
    return value


@dataclass(frozen=True)
class NodeOrigin:
    """One node's place in a duplicate report: where it was read, what it declared.

    *where* is the reader's own word for the place — a file name for the working
    tree, ``<ref>:<path>`` for content read at a git ref — because a report that
    names two nodes has to let the reader tell them apart.
    """

    where: str
    kind: str
    source: str

    def describe(self) -> str:
        """``services.yml (kind=domain, source 'src/app/')``."""
        source = f"source '{self.source}'" if self.source else "no source"
        return f"{self.where} (kind={self.kind or '<none>'}, {source})"


@dataclass(frozen=True)
class DuplicateRefId:
    """One ``ref_id`` carried by two nodes: the one a reader keeps, and one it drops.

    A graph file carrying a ``ref_id`` twice was reduced to one node and the
    report named neither of them (BDL-UX #214). On the ordinary single-package
    src-layout the node that is dropped is the one carrying the ``source``, so
    the graph keeps an empty root and every rule over the package runs on an
    empty population — which is why the report states the CONSEQUENCE and not
    only the collision.
    """

    ref_id: str
    kept: NodeOrigin
    dropped: NodeOrigin

    def describe(self) -> str:
        """The one line a reader prints, naming both nodes and what the drop costs."""
        return (
            f"Duplicate ref_id '{self.ref_id}': kept {self.kept.describe()}, "
            f"dropped {self.dropped.describe()} — {self._what_the_drop_costs()}"
        )

    def _what_the_drop_costs(self) -> str:
        if not self.dropped.source:
            return "only the kept node is in the graph"
        lost = f"nothing under '{self.dropped.source}' is owned, checked or counted"
        if self.kept.source:
            return lost
        return f"the node that carries the source is the one dropped, so {lost}"


def _origin_of(where: str, node: Any) -> NodeOrigin:
    return NodeOrigin(
        where=where,
        kind=str(node.get("kind", "")),
        source=str(node.get("source") or ""),
    )


def unique_by_ref_id(
    nodes: Iterable[tuple[str, dict[str, Any]]],
) -> tuple[list[dict[str, Any]], list[DuplicateRefId]]:
    """Reduce nodes to one per ``ref_id`` and report every node that reduction drops.

    Each item pairs a node with the ORIGIN it was read from, so a finding can
    name the file — or the git ref — each of the two nodes came from. The first
    node under a ``ref_id`` is the one kept, which is the rule ``load_graph``
    has always followed; it is stated here so that no second reader of
    ``.beadloom/_graph/`` derives it again and gets a different answer.
    ``graph/diff.py`` did: it keyed a dict by ``ref_id`` and kept the LAST,
    silently, so a diff could describe a node the graph does not hold.

    A node that carries no ``ref_id``, or that is not a mapping at all, is kept
    and reported by nobody here: the reader that inserts it is the one that can
    say what is wrong with it, and swallowing it on the way past would replace
    one silence with another.
    """
    kept: list[dict[str, Any]] = []
    duplicates: list[DuplicateRefId] = []
    first_seen: dict[str, NodeOrigin] = {}
    for where, node in nodes:
        ref_id = str(node.get("ref_id", "")) if isinstance(node, dict) else ""
        if not ref_id:
            kept.append(node)
            continue
        origin = _origin_of(where, node)
        if ref_id in first_seen:
            duplicates.append(
                DuplicateRefId(ref_id=ref_id, kept=first_seen[ref_id], dropped=origin)
            )
            continue
        first_seen[ref_id] = origin
        kept.append(node)
    return kept, duplicates


class GraphParseError(Exception):
    """Raised when a graph YAML file cannot be parsed.

    Carries the offending file path and, when available, the source line so
    malformed YAML surfaces as a clear, actionable error instead of a silent
    empty result (see BDL-UX-Issues #86).
    """


@dataclass
class ParsedFile:
    """Result of parsing a single YAML graph file."""

    nodes: list[dict[str, Any]] = field(default_factory=list)
    edges: list[dict[str, Any]] = field(default_factory=list)


@dataclass(frozen=True)
class ForeignEdge:
    """An edge whose src or dst points at another repo (``@repo:ref_id``).

    Recorded (not inserted, not a dangling error) at single-repo load time;
    it resolves against the federated union at the hub (BDL-037).
    """

    src: str
    dst: str
    kind: str


@dataclass
class GraphLoadResult:
    """Summary of a full graph load operation."""

    nodes_loaded: int = 0
    edges_loaded: int = 0
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    foreign_edges: list[ForeignEdge] = field(default_factory=list)


def _format_yaml_error(path: Path, exc: yaml.YAMLError) -> str:
    """Build a clear, line-referenced message from a PyYAML error."""
    mark = getattr(exc, "problem_mark", None)
    if mark is not None:
        # ``mark.line`` is 0-based; report 1-based for human readability.
        return (
            f"Failed to parse graph file '{path.name}': invalid YAML at "
            f"line {mark.line + 1}, column {mark.column + 1}. "
            f"Check indentation (use spaces, not tabs) and mapping syntax."
        )
    return f"Failed to parse graph file '{path.name}': invalid YAML ({exc})."


def parse_graph_file(path: Path) -> ParsedFile:
    """Parse a single YAML graph file into nodes and edges.

    Block-style and flow-style (inline ``{ key: value }``) mappings are both
    valid YAML and parse identically. Any YAML syntax error is raised as a
    :class:`GraphParseError` naming the file and line -- never swallowed into
    a silent empty result (see BDL-UX-Issues #86).

    A file that will not DECODE is the same finding as one that will not parse,
    and was not one until BDL-069: ``read_text`` sat outside the ``try``, so a
    graph file that is not UTF-8 left `load_graph` as a raw ``UnicodeDecodeError``
    rather than as an entry in ``result.errors``. That is the one shape
    ``each_graph_file`` guards which this reader's own guards did not cover, and
    the loader's contract is to report it, not to skip it.

    A ``ref_id`` carried twice is NOT reported here, and the reason is the
    population rather than the layer: two nodes sharing a ``ref_id`` may sit in
    two different files, so the question is about the DIRECTORY and this body
    reads one file. :func:`load_graph` takes it, over every node of every file,
    through :func:`unique_by_ref_id`.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError) as exc:
        raise GraphParseError(f"Failed to read graph file '{path.name}': {exc}.") from exc
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise GraphParseError(_format_yaml_error(path, exc)) from exc

    if data is None:
        return ParsedFile()
    if not isinstance(data, dict):
        raise GraphParseError(
            f"Failed to parse graph file '{path.name}': top-level YAML must be a "
            f"mapping with 'nodes'/'edges' keys, got {type(data).__name__}."
        )

    nodes = data.get("nodes") or []
    edges = data.get("edges") or []
    if not isinstance(nodes, list):
        raise GraphParseError(
            f"Graph file '{path.name}': 'nodes' must be a list, got {type(nodes).__name__}."
        )
    if not isinstance(edges, list):
        raise GraphParseError(
            f"Graph file '{path.name}': 'edges' must be a list, got {type(edges).__name__}."
        )
    return ParsedFile(nodes=nodes, edges=edges)


def update_node_in_yaml(
    graph_dir: Path,
    conn: sqlite3.Connection,
    ref_id: str,
    *,
    summary: str | None = None,
    source: str | None = None,
) -> bool:
    """Update a node's fields in the YAML source and SQLite.

    Scans YAML files for *ref_id*, updates the specified fields in-place,
    writes the YAML back to disk, and updates the ``nodes`` table.

    Returns ``True`` if the node was found and updated.

    NOT ROUTED THROUGH ``each_graph_file``, and the reason is structural rather
    than a judgement about this body: BDL-069 measured that it reads the
    directory for NODES, so it belongs in that policy's population, and the
    policy lives in ``onboarding``, which already imports ``graph``. Importing it
    here would be a ``graph`` -> ``onboarding`` edge and a dependency cycle,
    which ``no-dependency-cycles`` refuses at error severity. So the policy's
    three guards are restated here — a file that will not read, one that will not
    parse, and one that parses to something other than a mapping are each
    skipped rather than raised on — and the duplication is what
    ``beadloom-4axf`` exists to remove by moving the policy into a layer every
    reader may import.
    """
    for yml_path in sorted(graph_dir.glob("*.yml")):
        if yml_path.name in NOT_A_GRAPH_FILE:
            continue
        try:
            data = yaml.safe_load(yml_path.read_text(encoding="utf-8"))
        except (yaml.YAMLError, UnicodeDecodeError, OSError):
            continue
        if not isinstance(data, dict):
            continue
        nodes_list: list[dict[str, Any]] = data.get("nodes") or []
        for node in nodes_list:
            if node.get("ref_id") != ref_id:
                continue

            # Update YAML node in memory.
            if summary is not None:
                node["summary"] = summary
            if source is not None:
                node["source"] = source

            # Write YAML back to disk (atomic — crash-safe; same bytes).
            write_yaml_atomic(yml_path, data, default_flow_style=False, allow_unicode=True)

            # Update SQLite.
            if summary is not None:
                conn.execute(
                    "UPDATE nodes SET summary = ? WHERE ref_id = ?",
                    (summary, ref_id),
                )
            if source is not None:
                conn.execute(
                    "UPDATE nodes SET source = ? WHERE ref_id = ?",
                    (source, ref_id),
                )
            conn.commit()
            return True

    return False


def _normalize_source(
    source: str | None,
    *,
    ref_id: str,
    project_root: Path,
    result: GraphLoadResult,
) -> str | None:
    """Resolve a declared ``source`` against disk, and report one that owns nothing.

    A directory written WITHOUT a trailing slash owned NOTHING: ownership,
    module-coverage and the sync fallback all read ``source`` as a lone file
    path, so the node contributed no ``depends_on`` edge, no sync pair, no
    symbol count and no coverage — silently, and only for an adopter, since
    Beadloom's own graph happens to use trailing slashes on all 67 sourced nodes
    (``.5``'s finding (a)). The path is STAT'ed rather than guessed: a file
    source is never widened into a directory.

    A source that names no path at all is the residual "declared thing that owns
    nothing", and it is reported here — where the path can still be checked —
    instead of surfacing later as an empty node nobody questions.
    """
    if not source:
        return source
    path = project_root / source.rstrip("/")
    if path.is_dir():
        return source if source.endswith("/") else source + "/"
    if not path.exists():
        result.warnings.append(
            f"Node '{ref_id}' declares source '{source}', which does not exist — "
            f"it owns no files, so nothing under it is checked"
        )
    return source


def load_graph(
    graph_dir: Path,
    conn: sqlite3.Connection,
    *,
    project_root: Path | None = None,
) -> GraphLoadResult:
    """Load all ``*.yml`` files from *graph_dir* into SQLite.

    Two-pass approach:
    1. Parse all files and insert nodes (collecting ref_ids).
    2. Insert edges, skipping those that reference missing nodes.

    *project_root* anchors relative GraphQL ``source_file`` paths declared on
    ``produces`` contracts (BDL-038 BEAD-03); it defaults to ``graph_dir``'s
    grandparent (``<root>/.beadloom/_graph`` -> ``<root>``).

    Returns a :class:`GraphLoadResult` with counts and diagnostics.

    NOT ROUTED THROUGH ``each_graph_file``, for two reasons that are both
    independent of each other. The structural one is the cycle
    :func:`update_node_in_yaml` states. The behavioural one is that this reader
    must REPORT the file it could not parse rather than pass over it: a graph
    file that will not parse is recorded in ``result.errors`` naming the file and
    the line, which is what stops a broken graph from loading as a silently
    smaller one (BDL-UX #86). ``each_graph_file`` skips such a file, which is the
    right answer for a reader whose caller is `init` and the wrong one here. The
    guards themselves are in :func:`parse_graph_file`, so the two shapes
    ``each_graph_file`` also guards — a file that will not read, and one that
    parses to something other than a mapping — reach the caller as findings
    rather than as tracebacks.
    """
    if project_root is None:
        project_root = graph_dir.parent.parent
    result = GraphLoadResult()

    # Collect parsed data from all YAML files, each node paired with the file it
    # was read from — a duplicate report that cannot name the two files is a
    # report an adopter cannot act on.
    read_nodes: list[tuple[str, dict[str, Any]]] = []
    all_edges: list[dict[str, Any]] = []
    for yml_path in sorted(graph_dir.glob("*.yml")):
        if yml_path.name in NOT_A_GRAPH_FILE:
            continue
        try:
            parsed = parse_graph_file(yml_path)
        except GraphParseError as exc:
            # Record the error loudly; do NOT silently yield an empty graph.
            result.errors.append(str(exc))
            continue
        read_nodes.extend((yml_path.name, node) for node in parsed.nodes)
        all_edges.extend(parsed.edges)

    # --- Pass 1: insert nodes ---
    # The reduction to one node per ref_id is REPORTED rather than performed in
    # silence (BDL-UX #214). It stays a report: the graph loads, the kept nodes
    # are the ones it always kept, and the finding goes to ``errors``, where a
    # duplicate has always been recorded — so no graph changes verdict because
    # this report was added.
    all_nodes, duplicates = unique_by_ref_id(read_nodes)
    result.errors.extend(duplicate.describe() for duplicate in duplicates)

    seen_ref_ids: set[str] = set()
    for node in all_nodes:
        ref_id: str = node.get("ref_id", "")
        if not ref_id:
            result.errors.append("Node missing ref_id, skipped")
            continue
        seen_ref_ids.add(ref_id)

        kind: str = node.get("kind", "")
        summary: str = node.get("summary", "")
        source: str | None = _normalize_source(
            node.get("source"), ref_id=ref_id, project_root=project_root, result=result
        )
        lifecycle = _normalize_lifecycle(node.get("lifecycle"), f"Node '{ref_id}'", result)

        # Everything not in direct/skip fields goes to ``extra``.
        extra: dict[str, Any] = {}
        for k, v in node.items():
            if k not in _NODE_DIRECT_FIELDS and k not in _NODE_SKIP_FIELDS:
                extra[k] = v

        try:
            conn.execute(
                "INSERT INTO nodes (ref_id, kind, summary, source, extra, lifecycle) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    ref_id,
                    kind,
                    summary,
                    source,
                    json.dumps(extra, ensure_ascii=False),
                    lifecycle,
                ),
            )
            result.nodes_loaded += 1
        except sqlite3.IntegrityError as exc:
            result.errors.append(f"Failed to insert node '{ref_id}': {exc}")

    conn.commit()

    # --- Pass 2: insert edges ---
    for edge in all_edges:
        _process_edge(edge, conn, seen_ref_ids, result, project_root)

    conn.commit()

    return result


def _classify_endpoint(raw: str, result: GraphLoadResult) -> bool | None:
    """Classify one edge endpoint ref.

    Returns ``True`` if the ref is a foreign (``@repo:id``) reference, ``False``
    if it is local, or ``None`` if it is a malformed ``@...`` (the malformed
    case is recorded in ``result.errors`` here — never silently dropped).
    """
    try:
        ref = parse_ref(raw)
    except FederationRefError as exc:
        result.errors.append(str(exc))
        return None
    return ref.is_foreign


def _process_edge(
    edge: dict[str, Any],
    conn: sqlite3.Connection,
    seen_ref_ids: set[str],
    result: GraphLoadResult,
    project_root: Path,
) -> None:
    """Classify and load a single edge (local insert vs foreign vs malformed)."""
    src: str = edge.get("src", "")
    dst: str = edge.get("dst", "")
    edge_kind: str = edge.get("kind", "")

    src_foreign = _classify_endpoint(src, result)
    dst_foreign = _classify_endpoint(dst, result)
    if src_foreign is None or dst_foreign is None:
        return  # malformed @... — already recorded as an error

    lifecycle = _normalize_lifecycle(edge.get("lifecycle"), f"Edge '{src}→{dst}'", result)
    edge_extra = _edge_extra(edge)
    _fold_graphql_surface(edge_extra, edge_kind, project_root, src, dst, result)
    contract_key = _contract_key(edge_extra)

    # A foreign endpoint makes this a cross-repo edge: persist it into the
    # ``foreign_edges`` table (resolves at the hub, surfaced by ``export``).
    # It is NOT inserted into ``edges`` (the FK cannot bind a @repo: endpoint)
    # nor flagged as a dangling node.
    if src_foreign or dst_foreign:
        result.foreign_edges.append(ForeignEdge(src=src, dst=dst, kind=edge_kind))
        _insert_foreign_edge(conn, src, dst, edge_kind, edge_extra, lifecycle, contract_key)
        return

    # Both endpoints local — original behavior, unchanged.
    if src not in seen_ref_ids:
        result.warnings.append(f"Edge src '{src}' not found in graph, skipped")
        return
    if dst not in seen_ref_ids:
        result.warnings.append(f"Edge dst '{dst}' not found in graph, skipped")
        return

    try:
        conn.execute(
            "INSERT INTO edges (src_ref_id, dst_ref_id, kind, extra, lifecycle, contract_key) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                src,
                dst,
                edge_kind,
                json.dumps(edge_extra, ensure_ascii=False),
                lifecycle,
                contract_key,
            ),
        )
        result.edges_loaded += 1
    except sqlite3.IntegrityError as exc:
        result.warnings.append(f"Failed to insert edge '{src}→{dst}': {exc}")


def _edge_extra(edge: dict[str, Any]) -> dict[str, Any]:
    """Collect an edge's non-direct fields (everything but src/dst/kind/lifecycle)."""
    return {k: v for k, v in edge.items() if k not in {"src", "dst", "kind", "lifecycle"}}


def _fold_graphql_surface(
    edge_extra: dict[str, Any],
    edge_kind: str,
    project_root: Path,
    src: str,
    dst: str,
    result: GraphLoadResult,
) -> None:
    """Fold a GraphQL producer's exposed SDL surface into its contract payload.

    For a ``produces`` edge declaring ``contract.protocol == graphql`` with a
    ``source_file``, parse the referenced SDL (relative to *project_root*) and
    store the sorted exposed names under ``contract.exposed`` (BDL-038 BEAD-03,
    G2) PLUS the TYPED Tier-A ``fields`` block (BDL-060 S2, G1a) when
    ``graphql-core`` is installed (absent the extra, the typed surface degrades to
    name-level and no ``fields`` block is emitted — honest). A missing/unreadable
    file records ``exposed: []`` plus a warning — an honest empty surface, never a
    faked confirmation. Consumer ``references`` / consumer-declared ``fields`` are
    carried through verbatim by ``_edge_extra`` (no folding needed). AMQP and plain
    edges are untouched.
    """
    contract = edge_extra.get("contract")
    if not isinstance(contract, dict) or contract.get("protocol") != _GRAPHQL:
        return
    if edge_kind != "produces" and contract.get("direction") != "produces":
        return
    source_file = contract.get("source_file")
    if not isinstance(source_file, str) or not source_file:
        contract["exposed"] = []
        return
    sdl_path = project_root / source_file
    try:
        sdl_text = sdl_path.read_text(encoding="utf-8")
    except OSError:
        result.warnings.append(
            f"Edge '{src}→{dst}': GraphQL source_file '{source_file}' "
            f"unreadable; recording exposed: []"
        )
        contract["exposed"] = []
        return
    contract["exposed"] = sorted(extract_surface(sdl_text))
    typed = extract_typed_surface(sdl_text)
    if typed.typed:
        # Only emit the typed `fields` block when the parse really had depth
        # (graphql-core present + parseable) — never fabricate a typed surface.
        contract["fields"] = serialize_typed_surface(typed)["fields"]


def _contract_key(edge_extra: dict[str, Any]) -> str:
    """Derive the contract discriminator from an edge's contract payload (#102).

    Delegates to :func:`beadloom.graph.contracts.contract_key`, so the persisted
    ``contract_key`` carries the full protocol-prefixed identity
    (``amqp:<exchange>/<routing>:<message_type>``, ``graphql:<schema>``). This
    distinguishes same-name / different-exchange contracts on one node pair
    (BDL-038 BEAD-02, G4). Plain (non-contract) edges keep ``''`` so their
    identity stays ``(src,dst,kind)``.
    """
    contract = edge_extra.get("contract")
    if isinstance(contract, dict):
        return contract_key(contract)
    return ""


def _insert_foreign_edge(
    conn: sqlite3.Connection,
    src: str,
    dst: str,
    kind: str,
    extra: dict[str, Any],
    lifecycle: str,
    contract_key: str,
) -> None:
    """Persist a cross-repo edge into ``foreign_edges`` (idempotent on its key)."""
    conn.execute(
        "INSERT OR REPLACE INTO foreign_edges "
        "(src_ref_id, dst_ref_id, kind, extra, lifecycle, contract_key) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (src, dst, kind, json.dumps(extra, ensure_ascii=False), lifecycle, contract_key),
    )
