"""YAML graph parser and SQLite loader.

Reads ``.beadloom/_graph/*.yml`` files and populates the ``nodes`` and
``edges`` tables.  Validates ref_id uniqueness and edge integrity.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import yaml

if TYPE_CHECKING:
    from pathlib import Path

# Fields mapped directly to SQLite columns (not stored in ``extra``).
_NODE_DIRECT_FIELDS = frozenset({"ref_id", "kind", "summary", "source"})
# ``docs`` is tracked but handled by the doc indexer (BEAD-04).
_NODE_SKIP_FIELDS = frozenset({"docs"})


@dataclass
class ParsedFile:
    """Result of parsing a single YAML graph file."""

    nodes: list[dict[str, Any]] = field(default_factory=list)
    edges: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class GraphLoadResult:
    """Summary of a full graph load operation."""

    nodes_loaded: int = 0
    edges_loaded: int = 0
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def parse_graph_file(path: Path) -> ParsedFile:
    """Parse a single YAML graph file into nodes and edges."""
    text = path.read_text(encoding="utf-8")
    data = yaml.safe_load(text)
    if data is None:
        return ParsedFile()

    nodes: list[dict[str, Any]] = data.get("nodes") or []
    edges: list[dict[str, Any]] = data.get("edges") or []
    return ParsedFile(nodes=nodes, edges=edges)


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
        parsed = parse_graph_file(yml_path)
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

        # Everything not in direct/skip fields goes to ``extra``.
        extra: dict[str, Any] = {}
        for k, v in node.items():
            if k not in _NODE_DIRECT_FIELDS and k not in _NODE_SKIP_FIELDS:
                extra[k] = v

        try:
            conn.execute(
                "INSERT INTO nodes (ref_id, kind, summary, source, extra) "
                "VALUES (?, ?, ?, ?, ?)",
                (ref_id, kind, summary, source, json.dumps(extra, ensure_ascii=False)),
            )
            result.nodes_loaded += 1
        except sqlite3.IntegrityError as exc:
            result.errors.append(f"Failed to insert node '{ref_id}': {exc}")

    conn.commit()

    # --- Pass 2: insert edges ---
    for edge in all_edges:
        src: str = edge.get("src", "")
        dst: str = edge.get("dst", "")
        edge_kind: str = edge.get("kind", "")

        if src not in seen_ref_ids:
            result.warnings.append(
                f"Edge src '{src}' not found in graph, skipped"
            )
            continue
        if dst not in seen_ref_ids:
            result.warnings.append(
                f"Edge dst '{dst}' not found in graph, skipped"
            )
            continue

        edge_extra: dict[str, Any] = {}
        for k, v in edge.items():
            if k not in {"src", "dst", "kind"}:
                edge_extra[k] = v

        try:
            conn.execute(
                "INSERT INTO edges (src_ref_id, dst_ref_id, kind, extra) "
                "VALUES (?, ?, ?, ?)",
                (src, dst, edge_kind, json.dumps(edge_extra, ensure_ascii=False)),
            )
            result.edges_loaded += 1
        except sqlite3.IntegrityError as exc:
            result.warnings.append(f"Failed to insert edge '{src}→{dst}': {exc}")

    conn.commit()

    return result
