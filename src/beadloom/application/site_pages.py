"""Per-node page rendering for the `docs site` generator (BDL-040 BEAD-01).

Split out of ``application/site.py`` to keep each module under the domain-size
limit. Renders one Markdown page per graph node (domain / service / feature)
with summary, source, public symbols, edges-as-links, linked hand-written docs,
and an embedded scoped C4/Mermaid diagram. All output is deterministic
(sorted, no wall-clock).
"""

# beadloom:domain=application

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from beadloom.graph.c4 import filter_c4_nodes, map_to_c4, render_c4_mermaid

if TYPE_CHECKING:
    import sqlite3


# Node kind -> output sub-directory (sorted, stable).
_KIND_DIR: dict[str, str] = {
    "domain": "domains",
    "service": "services",
    "feature": "features",
}

# Edge kinds rendered on a node page, in stable display order.
_EDGE_KINDS: tuple[str, ...] = ("part_of", "depends_on", "uses")


@dataclass(frozen=True)
class NodeRow:
    """A single graph node as read from the DB (read-only)."""

    ref_id: str
    kind: str
    summary: str
    source: str | None


@dataclass(frozen=True)
class NodePage:
    """A rendered node page: its relative output path + Markdown body."""

    rel_path: str  # e.g. "domains/application.md"
    body: str


def load_nodes(conn: sqlite3.Connection) -> list[NodeRow]:
    """Read all graph nodes, sorted by ref_id (deterministic)."""
    rows = conn.execute(
        "SELECT ref_id, kind, summary, source FROM nodes ORDER BY ref_id"
    ).fetchall()
    return [
        NodeRow(
            ref_id=row["ref_id"],
            kind=str(row["kind"]),
            summary=row["summary"] or "",
            source=row["source"],
        )
        for row in rows
    ]


def _kind_dir(kind: str) -> str:
    """Map a node kind to its output sub-directory (default: 'other')."""
    return _KIND_DIR.get(kind, "other")


def _node_link(target_kind: str, target_ref: str) -> str:
    """A relative Markdown link from one node page to another's page.

    Both pages live one level under ``out`` (``<dir>/<ref>.md``), so a sibling
    link is ``../<dir>/<ref>.md``.
    """
    return f"../{_kind_dir(target_kind)}/{target_ref}.md"


def _load_kinds(conn: sqlite3.Connection) -> dict[str, str]:
    """ref_id -> kind for every node (used to resolve edge link targets)."""
    rows = conn.execute("SELECT ref_id, kind FROM nodes").fetchall()
    return {row["ref_id"]: str(row["kind"]) for row in rows}


def _load_edges_for(
    conn: sqlite3.Connection, ref_id: str, kinds: dict[str, str]
) -> dict[str, list[str]]:
    """Outgoing edges grouped by edge-kind, each as a sorted Markdown link list."""
    rows = conn.execute(
        "SELECT dst_ref_id, kind FROM edges "
        "WHERE src_ref_id = ? AND kind IN ('part_of', 'depends_on', 'uses') "
        "ORDER BY kind, dst_ref_id",
        (ref_id,),
    ).fetchall()
    grouped: dict[str, list[str]] = {}
    for row in rows:
        dst = str(row["dst_ref_id"])
        if dst == ref_id:
            continue
        edge_kind = str(row["kind"])
        target_kind = kinds.get(dst, "other")
        link = f"[{dst}]({_node_link(target_kind, dst)})"
        grouped.setdefault(edge_kind, []).append(link)
    return grouped


def _load_symbols(conn: sqlite3.Connection, source: str | None) -> list[str]:
    """Public symbol names whose file lives under *source*, sorted + de-duped."""
    if not source:
        return []
    rows = conn.execute(
        "SELECT DISTINCT symbol_name FROM code_symbols "
        "WHERE file_path = ? OR file_path LIKE ? "
        "ORDER BY symbol_name",
        (source, f"{source.rstrip('/')}/%"),
    ).fetchall()
    return [
        str(row["symbol_name"])
        for row in rows
        if not str(row["symbol_name"]).startswith("_")
    ]


def _load_docs(conn: sqlite3.Connection, ref_id: str) -> list[str]:
    """Hand-written doc paths linked to *ref_id*, sorted."""
    rows = conn.execute(
        "SELECT path FROM docs WHERE ref_id = ? ORDER BY path", (ref_id,)
    ).fetchall()
    return [str(row["path"]) for row in rows]


def _scoped_diagram(conn: sqlite3.Connection, ref_id: str) -> str:
    """A scoped C4/Mermaid diagram for one node (its component view).

    Falls back to the container view when the node has no children.
    """
    nodes, rels = map_to_c4(conn)
    try:
        scoped_nodes, scoped_rels = filter_c4_nodes(
            nodes, rels, level="component", scope=ref_id
        )
    except ValueError:
        scoped_nodes, scoped_rels = filter_c4_nodes(nodes, rels, level="container")
    if not scoped_nodes:
        scoped_nodes, scoped_rels = filter_c4_nodes(nodes, rels, level="container")
    return render_c4_mermaid(scoped_nodes, scoped_rels)


def _edges_section(grouped: dict[str, list[str]]) -> list[str]:
    """Markdown lines for the edges section (stable kind order)."""
    lines: list[str] = ["## Relationships", ""]
    any_edge = False
    for edge_kind in _EDGE_KINDS:
        links = grouped.get(edge_kind)
        if not links:
            continue
        any_edge = True
        lines.append(f"- **{edge_kind}**: " + ", ".join(links))
    if not any_edge:
        lines.append("_No relationships._")
    lines.append("")
    return lines


def _symbols_section(symbols: list[str]) -> list[str]:
    lines: list[str] = ["## Public symbols", ""]
    if symbols:
        lines.extend(f"- `{name}`" for name in symbols)
    else:
        lines.append("_None indexed._")
    lines.append("")
    return lines


def _docs_section(docs: list[str]) -> list[str]:
    lines: list[str] = ["## Documentation", ""]
    if docs:
        lines.extend(f"- [{path}](/{path})" for path in docs)
    else:
        lines.append("_No linked documents._")
    lines.append("")
    return lines


def _diagram_section(diagram: str) -> list[str]:
    return ["## Diagram", "", "```mermaid", diagram.rstrip("\n"), "```", ""]


def render_node_page(conn: sqlite3.Connection, node: NodeRow, kinds: dict[str, str]) -> NodePage:
    """Render one node's Markdown page (deterministic)."""
    grouped = _load_edges_for(conn, node.ref_id, kinds)
    symbols = _load_symbols(conn, node.source)
    docs = _load_docs(conn, node.ref_id)
    diagram = _scoped_diagram(conn, node.ref_id)

    lines: list[str] = [
        "---",
        f"title: {node.ref_id}",
        f"kind: {node.kind}",
        "---",
        "",
        f"# {node.ref_id}",
        "",
        f"**Kind:** {node.kind}",
        "",
        node.summary or "_No summary._",
        "",
    ]
    if node.source:
        lines.extend([f"**Source:** `{node.source}`", ""])
    lines.extend(_symbols_section(symbols))
    lines.extend(_edges_section(grouped))
    lines.extend(_docs_section(docs))
    lines.extend(_diagram_section(diagram))

    rel_path = f"{_kind_dir(node.kind)}/{node.ref_id}.md"
    return NodePage(rel_path=rel_path, body="\n".join(lines) + "\n")


def render_all_pages(conn: sqlite3.Connection) -> list[NodePage]:
    """Render every node page, sorted by output path (deterministic)."""
    kinds = _load_kinds(conn)
    pages = [render_node_page(conn, node, kinds) for node in load_nodes(conn)]
    return sorted(pages, key=lambda p: p.rel_path)
