"""YAML graph parser and SQLite loader.

Reads ``.beadloom/_graph/*.yml`` files and populates the ``nodes`` and
``edges`` tables.  Validates ref_id uniqueness and edge integrity.
"""

# beadloom:domain=graph

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import yaml

from beadloom.graph.federation import FederationRefError, parse_ref

if TYPE_CHECKING:
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

# Fields mapped directly to SQLite columns (not stored in ``extra``).
_NODE_DIRECT_FIELDS = frozenset({"ref_id", "kind", "summary", "source", "lifecycle"})
# ``docs`` is tracked but handled by the doc indexer (BEAD-04).
_NODE_SKIP_FIELDS = frozenset({"docs"})

# Valid lifecycle states (BDL-037 Principle 8). Default is ``active``; absent
# or unknown values fall back to ``active`` so existing graphs are unchanged.
VALID_LIFECYCLES = frozenset({"active", "planned", "deprecated", "dead"})
_DEFAULT_LIFECYCLE = "active"


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
    """
    text = path.read_text(encoding="utf-8")
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
    """
    for yml_path in sorted(graph_dir.glob("*.yml")):
        text = yml_path.read_text(encoding="utf-8")
        data = yaml.safe_load(text)
        if data is None:
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

            # Write YAML back to disk.
            yml_path.write_text(
                yaml.dump(data, default_flow_style=False, allow_unicode=True),
                encoding="utf-8",
            )

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


def load_graph(graph_dir: Path, conn: sqlite3.Connection) -> GraphLoadResult:
    """Load all ``*.yml`` files from *graph_dir* into SQLite.

    Two-pass approach:
    1. Parse all files and insert nodes (collecting ref_ids).
    2. Insert edges, skipping those that reference missing nodes.

    Returns a :class:`GraphLoadResult` with counts and diagnostics.
    """
    result = GraphLoadResult()

    # Collect parsed data from all YAML files.
    all_nodes: list[dict[str, Any]] = []
    all_edges: list[dict[str, Any]] = []
    for yml_path in sorted(graph_dir.glob("*.yml")):
        try:
            parsed = parse_graph_file(yml_path)
        except GraphParseError as exc:
            # Record the error loudly; do NOT silently yield an empty graph.
            result.errors.append(str(exc))
            continue
        all_nodes.extend(parsed.nodes)
        all_edges.extend(parsed.edges)

    # --- Pass 1: insert nodes ---
    seen_ref_ids: set[str] = set()
    for node in all_nodes:
        ref_id: str = node.get("ref_id", "")
        if not ref_id:
            result.errors.append("Node missing ref_id, skipped")
            continue

        if ref_id in seen_ref_ids:
            result.errors.append(f"Duplicate ref_id '{ref_id}', skipped")
            continue
        seen_ref_ids.add(ref_id)

        kind: str = node.get("kind", "")
        summary: str = node.get("summary", "")
        source: str | None = node.get("source")
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
        _process_edge(edge, conn, seen_ref_ids, result)

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
) -> None:
    """Classify and load a single edge (local insert vs foreign vs malformed)."""
    src: str = edge.get("src", "")
    dst: str = edge.get("dst", "")
    edge_kind: str = edge.get("kind", "")

    src_foreign = _classify_endpoint(src, result)
    dst_foreign = _classify_endpoint(dst, result)
    if src_foreign is None or dst_foreign is None:
        return  # malformed @... — already recorded as an error

    # A foreign endpoint makes this a cross-repo edge: record it (resolves at
    # the hub), do NOT insert it locally or flag it as a dangling node.
    if src_foreign or dst_foreign:
        result.foreign_edges.append(ForeignEdge(src=src, dst=dst, kind=edge_kind))
        return

    # Both endpoints local — original behavior, unchanged.
    if src not in seen_ref_ids:
        result.warnings.append(f"Edge src '{src}' not found in graph, skipped")
        return
    if dst not in seen_ref_ids:
        result.warnings.append(f"Edge dst '{dst}' not found in graph, skipped")
        return

    lifecycle = _normalize_lifecycle(
        edge.get("lifecycle"), f"Edge '{src}→{dst}'", result
    )
    edge_extra: dict[str, Any] = {}
    for k, v in edge.items():
        if k not in {"src", "dst", "kind", "lifecycle"}:
            edge_extra[k] = v

    try:
        conn.execute(
            "INSERT INTO edges (src_ref_id, dst_ref_id, kind, extra, lifecycle) "
            "VALUES (?, ?, ?, ?, ?)",
            (src, dst, edge_kind, json.dumps(edge_extra, ensure_ascii=False), lifecycle),
        )
        result.edges_loaded += 1
    except sqlite3.IntegrityError as exc:
        result.warnings.append(f"Failed to insert edge '{src}→{dst}': {exc}")
