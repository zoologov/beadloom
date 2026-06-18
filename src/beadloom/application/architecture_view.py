# beadloom:domain=application
# beadloom:feature=site-generation
"""Interactive architecture data (BDL-060 S4 ext) — the LOCAL graph artifact.

Builds ``architecture.data.json``: a deterministic, JSON-safe model of the
project's OWN architecture graph (domains / services / features / components)
that the Cytoscape+ELK view (``site/.vitepress/theme``) renders client-side as a
compound, layered map — replacing the unreadable Mermaid "Top-level diagram" as
the primary architecture page.

It is GENERATED from the SAME indexed graph the gate/report read (the ``nodes`` /
``edges`` / ``docs`` / ``sync_state`` / ``code_symbols`` tables via the
repository seam) — never a re-implemented surface. Each node carries its
``kind``, ``summary``, ``layer`` (the ``layer-*`` tag), symbol count, doc-status
(fresh / stale / none), page url + published doc link(s), its compound ``parent``
(the ``part_of`` container), and the ``beadloom why`` dependency lists
(``depends_on`` / ``depended_on_by``). Edges carry ``depends_on`` (solid) +
``part_of`` (containment).

Honest degradation (DATA-STRICTNESS): a node with no doc gets an EMPTY
``doc_links`` (the view shows none, never a fabricated link); a node with no
``layer-*`` tag gets an empty ``layer``; the lint-clean flag is OMITTED entirely
when lint was not computed (``lint_violation_refs is None``) rather than faking a
"clean" verdict. Determinism: nodes/edges are sorted and the payload serializes
with ``sort_keys`` so regeneration is byte-stable.
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

from beadloom.application.site_pages import _KIND_DIR, _published_doc_link

if TYPE_CHECKING:
    import sqlite3

logger = logging.getLogger(__name__)

# Artifact schema version (additive bumps; the view tolerates missing blocks).
ARCHITECTURE_SCHEMA_VERSION = 1

# layer-* tag -> the short layer name the view strata-colors by.
_LAYER_TAGS = {
    "layer-service": "service",
    "layer-application": "application",
    "layer-domain": "domain",
    "layer-infra": "infra",
}

_DOC_FRESH = "fresh"
_DOC_STALE = "stale"
_DOC_NONE = "none"


# ---------------------------------------------------------------------------
# Per-node attribute reads (honest, repository-backed)
# ---------------------------------------------------------------------------


def _layer_of(extra_raw: str) -> str:
    """The node's layer (``service`` / ``application`` / ``domain`` / ``infra``).

    Read from the ``layer-*`` tag in the node ``extra`` JSON. Honest empty string
    when no layer tag is present (a feature/component carries no layer tag).
    """
    if not extra_raw:
        return ""
    try:
        extra = json.loads(extra_raw)
    except json.JSONDecodeError:
        return ""
    if not isinstance(extra, dict):
        return ""
    tags = extra.get("tags")
    if not isinstance(tags, list):
        return ""
    for tag in tags:
        layer = _LAYER_TAGS.get(str(tag))
        if layer is not None:
            return layer
    return ""


def _symbol_count(conn: sqlite3.Connection, source: str | None) -> int:
    """Count code symbols whose file lives under the node *source*.

    A directory source (``src/dom/``) matches every file beneath it via a LIKE
    prefix; a file source matches exactly. Mirrors the repository symbol read so
    the count agrees with the per-node page. ``0`` when the node has no source.
    """
    if not source:
        return 0
    pattern = source + "%" if source.endswith("/") else source
    row = conn.execute(
        "SELECT count(*) FROM code_symbols WHERE file_path LIKE ?", (pattern,)
    ).fetchone()
    return int(row[0])


def _doc_status(conn: sqlite3.Connection, ref_id: str) -> str:
    """The node's doc freshness: ``fresh`` / ``stale`` / ``none`` (honest).

    ``none`` when the node has no associated doc (never reported as fresh);
    ``stale`` when any sync pair for the node is marked stale; else ``fresh``.
    """
    has_doc = conn.execute(
        "SELECT 1 FROM docs WHERE ref_id = ? LIMIT 1", (ref_id,)
    ).fetchone()
    if has_doc is None:
        return _DOC_NONE
    stale = conn.execute(
        "SELECT 1 FROM sync_state WHERE ref_id = ? AND status = 'stale' LIMIT 1",
        (ref_id,),
    ).fetchone()
    return _DOC_STALE if stale is not None else _DOC_FRESH


def _doc_links(conn: sqlite3.Connection, ref_id: str) -> list[str]:
    """Published ``/docs/`` links for the node's docs, sorted (empty when none)."""
    rows = conn.execute(
        "SELECT path FROM docs WHERE ref_id = ? ORDER BY path", (ref_id,)
    ).fetchall()
    return [_published_doc_link(str(r["path"])) for r in rows]


# ---------------------------------------------------------------------------
# Edge reads (containment + dependency)
# ---------------------------------------------------------------------------


def _arch_edges(
    conn: sqlite3.Connection,
) -> tuple[list[dict[str, str]], dict[str, str], dict[str, list[str]], dict[str, list[str]]]:
    """Build the architecture edges + the derived per-node relationships.

    Returns ``(edges, parent_by_id, depends_on_by_id, depended_on_by_by_id)``:

    - ``edges``: one ``{src, dst, kind}`` per ``part_of`` / ``depends_on`` edge,
      sorted (so the view's compound containment + dependency arrows are stable).
    - ``parent_by_id``: each node's ``part_of`` container (its ELK compound
      parent); a node with no container maps to ``""``.
    - ``depends_on_by_id`` / ``depended_on_by_by_id``: the ``beadloom why`` lists
      (what a node depends on / who depends on it), sorted + de-duplicated.
    """
    rows = conn.execute(
        "SELECT src_ref_id, dst_ref_id, kind FROM edges "
        "WHERE kind IN ('part_of', 'depends_on') "
        "ORDER BY kind, src_ref_id, dst_ref_id"
    ).fetchall()
    edges: list[dict[str, str]] = []
    parent: dict[str, str] = {}
    depends_on: dict[str, set[str]] = {}
    depended_on_by: dict[str, set[str]] = {}
    for row in rows:
        src, dst, kind = str(row["src_ref_id"]), str(row["dst_ref_id"]), str(row["kind"])
        edges.append({"src": src, "dst": dst, "kind": kind})
        if kind == "part_of":
            parent[src] = dst
        else:  # depends_on
            depends_on.setdefault(src, set()).add(dst)
            depended_on_by.setdefault(dst, set()).add(src)
    edges.sort(key=lambda e: (e["src"], e["dst"], e["kind"]))
    return (
        edges,
        parent,
        {k: sorted(v) for k, v in depends_on.items()},
        {k: sorted(v) for k, v in depended_on_by.items()},
    )


# ---------------------------------------------------------------------------
# Projection to the renderer-agnostic data model
# ---------------------------------------------------------------------------


def _node_dict(
    conn: sqlite3.Connection,
    ref_id: str,
    kind: str,
    summary: str,
    source: str | None,
    extra_raw: str,
    *,
    pages: dict[str, str],
    parent: dict[str, str],
    depends_on: dict[str, list[str]],
    depended_on_by: dict[str, list[str]],
    lint_violation_refs: set[str] | None,
) -> dict[str, object]:
    """Project one graph node to its JSON-safe architecture-view payload."""
    node: dict[str, object] = {
        "id": ref_id,
        "label": ref_id,
        "kind": kind,
        "summary": summary,
        "layer": _layer_of(extra_raw),
        "group": _KIND_DIR.get(kind, "other"),
        "symbols": _symbol_count(conn, source),
        "doc_status": _doc_status(conn, ref_id),
        "doc_links": _doc_links(conn, ref_id),
        "url": pages.get(ref_id, ""),
        "parent": parent.get(ref_id, ""),
        "depends_on": depends_on.get(ref_id, []),
        "depended_on_by": depended_on_by.get(ref_id, []),
    }
    # Honest degradation: only carry the lint-clean flag when lint was computed.
    if lint_violation_refs is not None:
        node["lint_clean"] = ref_id not in lint_violation_refs
    return node


def build_architecture_view_data(
    conn: sqlite3.Connection,
    *,
    pages: dict[str, str] | None = None,
    lint_violation_refs: set[str] | None = None,
) -> dict[str, object]:
    """Build the deterministic interactive-architecture data model.

    Args:
        conn: An open read-only connection to the indexed graph DB.
        pages: Map of ``ref_id -> existing page URL`` (a node gets a non-empty
            ``url`` only when present, so a click never resolves to a dead page).
        lint_violation_refs: The set of ``ref_id``s with a lint violation, or
            ``None`` when lint was not computed. When ``None`` the per-node
            ``lint_clean`` flag is OMITTED (honest — never a fabricated "clean").

    Returns:
        A JSON-safe dict ``{schema_version, scope, nodes, edges}`` with every
        section sorted for byte-stable serialization.
    """
    page_map = pages or {}
    edges, parent, depends_on, depended_on_by = _arch_edges(conn)
    rows = conn.execute(
        "SELECT ref_id, kind, summary, source, extra FROM nodes ORDER BY ref_id"
    ).fetchall()
    nodes = [
        _node_dict(
            conn,
            str(r["ref_id"]),
            str(r["kind"]),
            str(r["summary"] or ""),
            r["source"],
            str(r["extra"] or ""),
            pages=page_map,
            parent=parent,
            depends_on=depends_on,
            depended_on_by=depended_on_by,
            lint_violation_refs=lint_violation_refs,
        )
        for r in rows
    ]
    return {
        "schema_version": ARCHITECTURE_SCHEMA_VERSION,
        "scope": "architecture",
        "nodes": nodes,
        "edges": edges,
    }


def serialize_architecture_view(data: dict[str, object]) -> str:
    """Serialize the architecture data to deterministic JSON (sorted, 2-space)."""
    return json.dumps(data, sort_keys=True, indent=2, ensure_ascii=False) + "\n"


def _as_list(value: object) -> list[object]:
    return value if isinstance(value, list) else []


def render_architecture_view_md(data: dict[str, object]) -> str:
    """Render the interactive architecture page (``architecture.md``) from *data*.

    Mounts the client-side ``<ArchitectureMap>`` (Cytoscape + ELK compound
    layout, reads ``architecture.data.json``) inside ``<ClientOnly>`` so the
    build stays SSR-safe, plus a static honest fallback (node/edge counts + a
    link to the demoted Mermaid diagram) for when JS is disabled. Deterministic:
    a pure function of *data*.
    """
    nodes = _as_list(data.get("nodes"))
    edges = _as_list(data.get("edges"))
    deps = sum(1 for e in edges if isinstance(e, dict) and e.get("kind") == "depends_on")
    lines: list[str] = [
        "---",
        "title: Architecture",
        "---",
        "",
        "# Architecture",
        "",
        "Generated by `beadloom docs site` from the indexed graph — never "
        "hand-drawn. Domains are compound boxes containing their features and "
        "components; edges are `depends_on` (solid arrows) over the layered "
        "stratification (service → application → domain → infra). "
        "Click a node for its card (kind, summary, layer, symbol count, "
        "doc-status, dependency lists like `beadloom why`, and a base-path-correct "
        "link to its page); click to highlight its blast radius. Filter by kind / "
        "domain / layer, or show only nodes with stale docs or lint violations.",
        "",
        "<ClientOnly>",
        "  <ArchitectureMap />",
        "</ClientOnly>",
        "",
        f"_Static summary (JS-off fallback): {len(nodes)} nodes, {deps} "
        "dependency edge(s)._ See the [secondary diagram](/architecture-diagram) "
        "for a static Mermaid fallback.",
        "",
    ]
    return "\n".join(lines) + "\n"
