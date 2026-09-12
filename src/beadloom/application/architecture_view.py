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
from dataclasses import dataclass
from typing import TYPE_CHECKING

from beadloom.application.site_pages import _KIND_DIR
from beadloom.graph.rule_engine import LayerDef, layer_of, node_tags, own_layer_of, part_of_parents
from beadloom.infrastructure.repository import count_symbols_owned_by_node

if TYPE_CHECKING:
    import sqlite3
    from collections.abc import Collection, Mapping

logger = logging.getLogger(__name__)

# Artifact schema version (additive bumps; the view tolerates missing blocks).
ARCHITECTURE_SCHEMA_VERSION = 1

# The conventional prefix a layer tag carries, removed to get the short token
# the view strata-colors by (``layer-domain`` -> ``domain``). It is NOT a layer:
# the layers are whatever the project declares, read from the indexed rule. The
# prefix is stripped because the four tokens are the front-end's contract
# (``site/.vitepress/theme/architectureTheme.js`` keys its colors and its lane
# labels by them), and a tag that does not carry the prefix is used verbatim,
# which colors grey rather than wrongly.
_LAYER_TAG_PREFIX = "layer-"

# Served extension for a published doc page. The site is built WITHOUT VitePress
# ``cleanUrls``, so a doc README is served at ``…/README.html`` — a ``.md`` link
# is a 404. (The Markdown node pages keep ``.md`` because VitePress rewrites
# in-page Markdown links; the JSON artifact is read by client JS with no such
# rewrite, so it must carry the served ``.html`` path.)
_SERVED_DOC_EXT = ".html"
_MD_EXT = ".md"

_DOC_FRESH = "fresh"
_DOC_STALE = "stale"
_DOC_NONE = "none"


# ---------------------------------------------------------------------------
# Per-node attribute reads (honest, repository-backed)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _LayerView:
    """What layer each node is in, for the declaration THIS graph carries.

    The view used to answer this itself, from a table of four tags and a table
    of four ranks, and it climbed ``part_of`` in a loop of its own. It was one
    of the three answers BDL-070 found disagreeing, so the arithmetic now lives
    in :mod:`beadloom.graph.rules.layers` and this class only says which of its
    two questions the view asks:

    - :meth:`token` reads the node's OWN tag, because the card shows what the
      node declares — a feature inside a domain declares no layer and says so.
    - :meth:`rank` INHERITS through ``part_of``, because a feature has to sit in
      its container's lane or the layout has no lane for it.

    The two differ on purpose, and the rule engine's verdict predicate is a
    third question this class does not answer.
    """

    layers: tuple[LayerDef, ...]
    parents: Mapping[str, Collection[str]]
    tags: Mapping[str, Collection[str]]

    def token(self, ref_id: str) -> str:
        """The short layer name for the node's OWN tag; ``""`` when it has none."""
        index = own_layer_of(ref_id, self.layers, self.tags)
        if index is None:
            return ""
        return self.layers[index].tag.removeprefix(_LAYER_TAG_PREFIX)

    def rank(self, ref_id: str) -> int | None:
        """The node's lane: its own layer's index, else its nearest container's.

        ``None`` when no ``part_of`` ancestor declares a layer either — honest,
        and a different fact from sitting in the bottom lane.
        """
        return layer_of(ref_id, self.layers, self.parents, self.tags)


def _declared_layers(conn: sqlite3.Connection) -> tuple[LayerDef, ...]:
    """The layer order this project DECLARES, read from the indexed rules.

    Read from the ``rules`` table — the same indexed graph every other read in
    this module goes through — rather than from ``rules.yml``, so generating the
    site needs no second path to the declaration and no project root. The JSON
    is the one ``application.reindex.rules_loader._serialize_rule`` writes; that
    is a coupling between a writer and a reader of one shape, stated here
    because it is the kind of pair that drifts silently.

    Empty when the index carries no layer rule (a graph that declares no layers,
    or one indexed before rules were loaded): the view then shows no lanes,
    which is honest, rather than putting every node in lane 0.

    A project with more than one layer rule gets the first by name. The view
    draws ONE stratification and has no way to show two.
    """
    row = conn.execute(
        "SELECT rule_json FROM rules WHERE rule_type = 'layers' ORDER BY name LIMIT 1"
    ).fetchone()
    if row is None:
        return ()
    try:
        definition = json.loads(str(row[0]))
    except json.JSONDecodeError:
        logger.warning("architecture view: the indexed layer rule is not readable JSON")
        return ()
    declared = definition.get("layers") if isinstance(definition, dict) else None
    if not isinstance(declared, list):
        return ()
    return tuple(
        LayerDef(name=str(layer.get("name", "")), tag=str(layer["tag"]))
        for layer in declared
        if isinstance(layer, dict) and layer.get("tag")
    )


def _layer_view(conn: sqlite3.Connection) -> _LayerView:
    """The layer lookup for one build, over the declaration the index holds.

    Reports the one case in which this release changes what a project sees: a
    graph whose nodes carry layer tags and whose index holds no layer rule
    rendered lanes from a table this module kept of its own and renders none
    now. The view has no way to tell which layering such a project meant — that
    is why the declaration is read rather than guessed — so it states the fact
    where it happens instead of drawing a stratification nobody declared.

    The condition counts ``layer-``-prefixed tags specifically, and that is not a
    hardcoded layer: the table this module used to keep held exactly the
    ``layer-*`` tags, so those are exactly the nodes whose lane moved. A project
    whose tags are named otherwise rendered no lanes before this release either,
    and is told nothing — the correct silence rather than a miss.
    """
    layers = _declared_layers(conn)
    tags = node_tags(conn).as_mapping()
    if not layers:
        tagged = sum(
            1 for node in tags.values() if any(tag.startswith(_LAYER_TAG_PREFIX) for tag in node)
        )
        if tagged:
            logger.info(
                "architecture view: %d node(s) carry a `%s` tag and the index holds "
                "no layer rule, so no lanes are drawn — the lanes come from the "
                "declaration, and a project that declares none gets none",
                tagged,
                _LAYER_TAG_PREFIX,
            )
    return _LayerView(
        layers=layers,
        parents=part_of_parents(conn),
        tags=tags,
    )


def _symbol_count(conn: sqlite3.Connection, ref_id: str) -> int:
    """Count the code symbols the node OWNS.

    Delegates to the single ownership rule in ``infrastructure/repository``
    (most specific source wins), so this compound view never counts a child's
    symbols against the parent that visually contains it, and a package façade
    source does not report an empty node (BDL-UX #144/#157).
    """
    return count_symbols_owned_by_node(conn, ref_id)


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
        # ``missing`` marks the node not-fresh too (BDL-UX #174).
        "SELECT 1 FROM sync_state WHERE ref_id = ? AND status IN ('stale', 'missing') LIMIT 1",
        (ref_id,),
    ).fetchone()
    return _DOC_STALE if stale is not None else _DOC_FRESH


def _doc_slug(path: str) -> str:
    """The ``docs/``-relative slug for a doc path (``.md`` stripped), normalised.

    Mirrors :func:`beadloom.application.site._published_doc_slugs` so a node's
    doc link can be gated against the SAME published-slug set (link-safe by
    construction — a doc with no published page is omitted, never a dead link).
    """
    rel = path[len("docs/") :] if path.startswith("docs/") else path
    rel = rel.replace("\\", "/")
    return rel[: -len(_MD_EXT)] if rel.endswith(_MD_EXT) else rel


def _served_doc_link(path: str) -> str:
    """The browser-resolvable site link for a doc (served ``.html``, base-less).

    The component wraps this in VitePress ``withBase()``; we emit the ``/docs/``
    rooted, ``.html``-suffixed path (no ``cleanUrls`` → a ``.md`` URL 404s).
    """
    return f"/docs/{_doc_slug(path)}{_SERVED_DOC_EXT}"


def _doc_links(
    conn: sqlite3.Connection,
    ref_id: str,
    *,
    published_doc_slugs: set[str] | None,
) -> list[str]:
    """Served ``/docs/…html`` links for the node's PUBLISHED docs, sorted.

    Honest degradation: a doc whose slug is not in *published_doc_slugs* would
    404, so it is omitted (never a dead link). When *published_doc_slugs* is
    ``None`` the gate is not applied (the caller did not supply the published
    set), and every doc row yields its served link.
    """
    rows = conn.execute(
        "SELECT path FROM docs WHERE ref_id = ? ORDER BY path", (ref_id,)
    ).fetchall()
    links: list[str] = []
    for r in rows:
        path = str(r["path"])
        if published_doc_slugs is not None and _doc_slug(path) not in published_doc_slugs:
            continue
        links.append(_served_doc_link(path))
    return links


# ---------------------------------------------------------------------------
# Edge reads (containment + dependency)
# ---------------------------------------------------------------------------


def _arch_edges(
    conn: sqlite3.Connection,
    layers: _LayerView,
) -> tuple[
    list[dict[str, object]],
    dict[str, list[str]],
    dict[str, list[str]],
    dict[str, list[str]],
    dict[str, list[str]],
]:
    """Build the architecture edges + the derived ``why`` dependency lists.

    Returns ``(edges, depends_on_by_id, depended_on_by_by_id)``:

    - ``edges``: one entry per ``part_of`` / ``depends_on`` / ``uses`` edge,
      sorted. A ``depends_on`` edge also carries a ``violation`` flag — ``True``
      when it points UP or cross-cuts the canonical layer order (``dst`` rank
      ``<=`` ``src`` rank), ``False`` when it points DOWN (healthy). ``part_of``
      is subtle containment and carries NO ``violation`` (not a flow arrow), and
      neither does ``uses``: it records a RUNTIME coupling across a process or
      file boundary (a harness shelling out to the CLI, a reader of a file
      another node writes), which cannot break a layering rule the way an import
      can. The flag is honestly omitted when either endpoint has no resolvable
      rank.
    - the four ``why`` lists, sorted + de-duplicated: what a node imports
      (``depends_on``) and who imports it, kept SEPARATE from what it ``uses``
      at runtime and who uses it. Merging them would assert an import binding
      that does not exist; dropping ``uses`` — as this builder did until the
      `ai-techwriter` node read as an island while being the hub of a whole
      workflow — hides coupling that derivation can never see, only declaration.
    """
    rows = conn.execute(
        "SELECT src_ref_id, dst_ref_id, kind FROM edges "
        "WHERE kind IN ('part_of', 'depends_on', 'uses') "
        "ORDER BY kind, src_ref_id, dst_ref_id"
    ).fetchall()
    edges: list[dict[str, object]] = []
    depends_on: dict[str, set[str]] = {}
    depended_on_by: dict[str, set[str]] = {}
    uses: dict[str, set[str]] = {}
    used_by: dict[str, set[str]] = {}
    for row in rows:
        src, dst, kind = str(row["src_ref_id"]), str(row["dst_ref_id"]), str(row["kind"])
        edge: dict[str, object] = {"src": src, "dst": dst, "kind": kind}
        if kind == "depends_on":
            depends_on.setdefault(src, set()).add(dst)
            depended_on_by.setdefault(dst, set()).add(src)
            src_rank = layers.rank(src)
            dst_rank = layers.rank(dst)
            if src_rank is not None and dst_rank is not None:
                edge["violation"] = dst_rank <= src_rank
        elif kind == "uses":
            uses.setdefault(src, set()).add(dst)
            used_by.setdefault(dst, set()).add(src)
        edges.append(edge)
    edges.sort(key=lambda e: (str(e["src"]), str(e["dst"]), str(e["kind"])))
    return (
        edges,
        {k: sorted(v) for k, v in depends_on.items()},
        {k: sorted(v) for k, v in depended_on_by.items()},
        {k: sorted(v) for k, v in uses.items()},
        {k: sorted(v) for k, v in used_by.items()},
    )


def _parent_map(conn: sqlite3.Connection) -> dict[str, str]:
    """Each node's ``part_of`` container (its ELK compound parent); ``""`` if none."""
    rows = conn.execute(
        "SELECT src_ref_id, dst_ref_id FROM edges WHERE kind = 'part_of'"
    ).fetchall()
    return {str(r["src_ref_id"]): str(r["dst_ref_id"]) for r in rows}


# ---------------------------------------------------------------------------
# Projection to the renderer-agnostic data model
# ---------------------------------------------------------------------------


def _node_dict(
    conn: sqlite3.Connection,
    ref_id: str,
    kind: str,
    summary: str,
    source: str | None,
    *,
    pages: dict[str, str],
    parent: dict[str, str],
    layers: _LayerView,
    depends_on: dict[str, list[str]],
    depended_on_by: dict[str, list[str]],
    uses: dict[str, list[str]],
    used_by: dict[str, list[str]],
    lint_violation_refs: set[str] | None,
    published_doc_slugs: set[str] | None,
) -> dict[str, object]:
    """Project one graph node to its JSON-safe architecture-view payload."""
    node: dict[str, object] = {
        "id": ref_id,
        "label": ref_id,
        "kind": kind,
        "summary": summary,
        "layer": layers.token(ref_id),
        "layer_rank": layers.rank(ref_id),
        "group": _KIND_DIR.get(kind, "other"),
        "symbols": _symbol_count(conn, ref_id),
        "doc_status": _doc_status(conn, ref_id),
        "doc_links": _doc_links(conn, ref_id, published_doc_slugs=published_doc_slugs),
        "url": pages.get(ref_id, ""),
        "parent": parent.get(ref_id, ""),
        "depends_on": depends_on.get(ref_id, []),
        "depended_on_by": depended_on_by.get(ref_id, []),
        # Declared runtime coupling, kept separate from the import lists: a
        # subprocess call or a file-format contract is real but is NOT an
        # import, and derivation cannot see it at all.
        "uses": uses.get(ref_id, []),
        "used_by": used_by.get(ref_id, []),
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
    published_doc_slugs: set[str] | None = None,
) -> dict[str, object]:
    """Build the deterministic interactive-architecture data model.

    Args:
        conn: An open read-only connection to the indexed graph DB.
        pages: Map of ``ref_id -> existing page URL`` (a node gets a non-empty
            ``url`` only when present, so a click never resolves to a dead page).
        lint_violation_refs: The set of ``ref_id``s with a lint violation, or
            ``None`` when lint was not computed. When ``None`` the per-node
            ``lint_clean`` flag is OMITTED (honest — never a fabricated "clean").
        published_doc_slugs: The set of ``docs/``-relative slugs (``.md``
            stripped) that actually got a published page. A node's doc link is
            emitted only when its slug is in this set (honest — never a 404).
            ``None`` skips the gate (every doc row yields its served link).

    Returns:
        A JSON-safe dict ``{schema_version, scope, nodes, edges}`` with every
        section sorted for byte-stable serialization. Each node carries its
        ``layer_rank`` (the partition index for the layered-lanes layout) and
        each ``depends_on`` edge a ``violation`` flag (it points up/cross-cuts).
    """
    page_map = pages or {}
    parent = _parent_map(conn)
    layers = _layer_view(conn)
    edges, depends_on, depended_on_by, uses, used_by = _arch_edges(conn, layers)
    rows = conn.execute(
        "SELECT ref_id, kind, summary, source FROM nodes ORDER BY ref_id"
    ).fetchall()
    nodes = [
        _node_dict(
            conn,
            str(r["ref_id"]),
            str(r["kind"]),
            str(r["summary"] or ""),
            r["source"],
            pages=page_map,
            parent=parent,
            layers=layers,
            depends_on=depends_on,
            depended_on_by=depended_on_by,
            uses=uses,
            used_by=used_by,
            lint_violation_refs=lint_violation_refs,
            published_doc_slugs=published_doc_slugs,
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
