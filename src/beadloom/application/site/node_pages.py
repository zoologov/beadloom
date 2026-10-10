# beadloom:domain=application
# beadloom:feature=site-generation
"""Per-node page rendering for the `docs site` generator (BDL-040 BEAD-01).

Split out of ``application/site/generate.py`` to keep each module under the domain-size
limit. Renders one Markdown page per graph node, of every kind, with summary,
source, public symbols, edges-as-links and linked hand-written docs, and mounts
the architecture viewer focused on the page's node (BDL-076 A4), in the place
the scoped Mermaid diagram had, after the text sections. The Mermaid C4 view
stays on ``architecture-diagram.md``. All output is deterministic (sorted, no
wall-clock).

A node's summary is the project's own text — ``beadloom init`` takes the root
service's from the README's first paragraph — so it goes onto the page by
:func:`beadloom.application.site.project_text.render_project_text`, the path the
About page and the published documents take: its links are rebased onto the
portal (BDL-076, ``beadloom-ujzb.11``) and it is shown as written rather than
compiled as a Vue template (``beadloom-ujzb.12``). The viewer the page mounts is
the generator's own markup and is left to Vue.
"""

# beadloom:domain=application

from __future__ import annotations

import html
from dataclasses import dataclass
from typing import TYPE_CHECKING

from beadloom.application.site.markdown_links import PortalLinks
from beadloom.application.site.project_text import render_project_text
from beadloom.infrastructure.repository import get_owned_symbols

if TYPE_CHECKING:
    import sqlite3


# Node kind -> output sub-directory (sorted, stable).
_KIND_DIR: dict[str, str] = {
    "domain": "domains",
    "service": "services",
    "feature": "features",
}

#: The section a node of a kind with no directory of its own is written under.
_OTHER_DIR = "other"

#: Every section a node page can be written under, sorted.
NODE_PAGE_SECTIONS: tuple[str, ...] = tuple(sorted({*_KIND_DIR.values(), _OTHER_DIR}))

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
    """A rendered node page: its relative output path + Markdown body, and whose it is.

    ``ref_id`` is the node's id as declared, which may hold a ``/`` and then nests
    the page: the path cannot be read back into the id, so the page carries it.
    """

    rel_path: str  # e.g. "domains/application.md"
    body: str
    ref_id: str


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
    return _KIND_DIR.get(kind, _OTHER_DIR)


def node_page_path(kind: str, ref_id: str) -> str:
    """Where a node's page is written, relative to the site root, without ``.md``.

    Every node gets a page — :func:`render_all_pages` renders all of them — and
    a kind with no directory of its own writes under ``other/``.
    """
    return f"{_kind_dir(kind)}/{ref_id}"


def node_page_urls(conn: sqlite3.Connection) -> dict[str, str]:
    """Every node's page URL (``/<dir>/<ref>``), for every kind, ``other/`` included.

    The architecture data file and both landscape views link each node to its
    page with this. The Mermaid click targets on ``landscape-diagram.md`` reach
    their page through the diagram viewer's base-path rewrite, which covers
    ``/other/`` since BDL-076 A4.
    """
    kinds = _load_kinds(conn)
    return {ref_id: f"/{node_page_path(kind, ref_id)}" for ref_id, kind in kinds.items()}


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


def _incoming_link(ref: str, kinds: dict[str, str]) -> str:
    """A link to *ref*'s page if it has one, else plain text (link-safe).

    A page exists for any node present in the graph (``kinds`` holds every
    node's ref_id). A ref with no page renders as plain text — never a dead
    link.
    """
    if ref not in kinds:
        return ref
    return f"[{ref}]({_node_link(kinds[ref], ref)})"


def _load_incoming_for(
    conn: sqlite3.Connection, ref_id: str, kinds: dict[str, str]
) -> dict[str, list[str]]:
    """Incoming relationships for a node, link-safe and deterministic.

    Returns a dict with optional keys ``"Used by"`` (deduped union of incoming
    ``uses`` + ``depends_on`` consumers) and ``"Parts"`` (incoming ``part_of``
    children). Self-edges are skipped. Each list is sorted by ref and rendered
    as a link only when the target has a page.
    """
    rows = conn.execute(
        "SELECT DISTINCT src_ref_id, kind FROM edges "
        "WHERE dst_ref_id = ? AND kind IN ('uses', 'depends_on', 'part_of')",
        (ref_id,),
    ).fetchall()
    used_by: set[str] = set()
    parts: set[str] = set()
    for row in rows:
        src = str(row["src_ref_id"])
        if src == ref_id:
            continue
        if str(row["kind"]) == "part_of":
            parts.add(src)
        else:
            used_by.add(src)
    incoming: dict[str, list[str]] = {}
    if used_by:
        incoming["Used by"] = [_incoming_link(r, kinds) for r in sorted(used_by)]
    if parts:
        incoming["Parts"] = [_incoming_link(r, kinds) for r in sorted(parts)]
    return incoming


def public_symbol_names(conn: sqlite3.Connection, ref_id: str) -> list[str]:
    """Public symbol names in the files the node OWNS, sorted + de-duped.

    Ownership (most specific source wins) is resolved in
    ``infrastructure/repository``, so a node page lists its own surface rather
    than its children's, and a package façade source still lists the package
    (BDL-UX #144/#157).
    """
    names = {
        symbol.symbol_name
        for symbol in get_owned_symbols(conn, ref_id)
        if not symbol.symbol_name.startswith("_")
    }
    return sorted(names)


def _load_docs(conn: sqlite3.Connection, ref_id: str) -> list[str]:
    """Hand-written doc paths linked to *ref_id*, sorted."""
    rows = conn.execute(
        "SELECT path FROM docs WHERE ref_id = ? ORDER BY path", (ref_id,)
    ).fetchall()
    return [str(row["path"]) for row in rows]


# Incoming relationship sections, in stable display order.
_INCOMING_LABELS: tuple[str, ...] = ("Used by", "Parts")


def _edges_section(
    grouped: dict[str, list[str]], incoming: dict[str, list[str]]
) -> list[str]:
    """Markdown lines for the relationships section (outgoing + incoming).

    Outgoing edges (``part_of`` / ``depends_on`` / ``uses``) render first in
    stable kind order, then incoming relationships (``Used by`` / ``Parts``).
    An incoming section with no entries is omitted. Only when there are no
    relationships at all is the placeholder shown.
    """
    lines: list[str] = ["## Relationships", ""]
    any_edge = False
    for edge_kind in _EDGE_KINDS:
        links = grouped.get(edge_kind)
        if not links:
            continue
        any_edge = True
        lines.append(f"- **{edge_kind}**: " + ", ".join(links))
    for label in _INCOMING_LABELS:
        links = incoming.get(label)
        if not links:
            continue
        any_edge = True
        lines.append(f"- **{label}**: " + ", ".join(links))
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


def _published_doc_link(path: str) -> str:
    """The site link to a published doc.

    Hand-written docs are published under ``site/docs/…`` (Showcase C copies the
    real ``docs/`` tree there). The ``docs`` table stores each path *relative to
    the source ``docs/`` dir* (e.g. ``domains/graph/README.md``); a path already
    carrying the ``docs/`` prefix is normalised so we never emit ``/docs/docs/…``.
    The emitted link is rooted at ``/docs/`` so it resolves to the published copy
    (a bare ``/<path>`` would be a dead link — the doc lives under ``/docs/``).
    """
    rel = path[len("docs/") :] if path.startswith("docs/") else path
    return f"/docs/{rel}"


def _docs_section(docs: list[str]) -> list[str]:
    lines: list[str] = ["## Documentation", ""]
    if docs:
        lines.extend(f"- [{path}]({_published_doc_link(path)})" for path in docs)
    else:
        lines.append("_No linked documents._")
    lines.append("")
    return lines


# The node page's viewer: one step of neighbourhood, and 60% of the window's height.
_GRAPH_DEPTH = 1
_GRAPH_HEIGHT = "60vh"


def _graph_section(ref_id: str) -> list[str]:
    """The architecture viewer, focused on *ref_id*, under ``<ClientOnly>``.

    ``ArchitectureMap`` is the architecture page's composition of the graph
    viewer and the node card; a page mounts it rather than the bare viewer,
    because a widget does not import another and the viewer alone has no card.
    """
    focus = html.escape(ref_id, quote=True)
    return [
        "## Graph",
        "",
        "<ClientOnly>",
        f'  <ArchitectureMap focus="{focus}" :depth="{_GRAPH_DEPTH}" height="{_GRAPH_HEIGHT}" />',
        "</ClientOnly>",
        "",
    ]


def render_node_page(
    conn: sqlite3.Connection,
    node: NodeRow,
    kinds: dict[str, str],
    portal: PortalLinks | None = None,
) -> NodePage:
    """Render one node's Markdown page (deterministic).

    *portal* is what the portal publishes, which a relative link in the summary
    is rebased onto. With none, every such link keeps only its text: there is no
    page the summary could be known to reach.
    """
    grouped = _load_edges_for(conn, node.ref_id, kinds)
    incoming = _load_incoming_for(conn, node.ref_id, kinds)
    symbols = public_symbol_names(conn, node.ref_id)
    docs = _load_docs(conn, node.ref_id)
    page_dir = _kind_dir(node.kind)
    # The summary sits below the page's own front matter, so a "---" in it is Markdown.
    summary = render_project_text(
        node.summary, portal or PortalLinks(), page_dir=page_dir, opens_page=False
    )

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
        summary or "_No summary._",
        "",
    ]
    if node.source:
        lines.extend([f"**Source:** `{node.source}`", ""])
    lines.extend(_symbols_section(symbols))
    lines.extend(_edges_section(grouped, incoming))
    lines.extend(_docs_section(docs))
    lines.extend(_graph_section(node.ref_id))

    rel_path = f"{node_page_path(node.kind, node.ref_id)}.md"
    return NodePage(rel_path=rel_path, body="\n".join(lines) + "\n", ref_id=node.ref_id)


def is_page_of(text: str, ref_id: str) -> bool:
    """*text* is a page :func:`render_node_page` wrote for *ref_id*, by any version.

    Node pages carry no generated marker, so the evidence is the opening every
    version since BDL-040 writes: front matter of ``title: <ref>`` and a ``kind:``
    line, then the ``# <ref>`` heading. A page written by hand rarely opens that way.
    """
    lines = text.split("\n", 6)[:6]
    return (
        len(lines) == 6
        and lines[0] == "---"
        and lines[1] == f"title: {ref_id}"
        and lines[2].startswith("kind: ")
        and lines[3] == "---"
        and lines[5] == f"# {ref_id}"
    )


def render_all_pages(
    conn: sqlite3.Connection, portal: PortalLinks | None = None
) -> list[NodePage]:
    """Render every node page, sorted by output path (deterministic)."""
    kinds = _load_kinds(conn)
    pages = [render_node_page(conn, node, kinds, portal) for node in load_nodes(conn)]
    return sorted(pages, key=lambda p: p.rel_path)
