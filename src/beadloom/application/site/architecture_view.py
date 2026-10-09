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
(``depends_on`` / ``depended_on_by``). Edges carry ``depends_on`` (solid),
``part_of`` (containment), ``uses`` (declared runtime coupling) and the contract
kinds ``consumes`` / ``produces``.

Schema version 2 (BDL-076 A1) keeps every version-1 key and adds the node card
(:mod:`beadloom.application.site.architecture_card`) and, at the top level, the
run's provenance (``generated_at``, ``beadloom_version``) and the declared
``layers`` with their ``layer_order``, from which the viewer builds its palette
instead of a vocabulary of its own, and lint's reach over the whole project
(``lint``, BDL-080 S4a) that a card's findings are read against. ``touches_code`` stays out: it
points at files, not at nodes. Nothing derived from the git remote is published
at the top level: the card needs it only as each node's finished ``source_url``,
and a remote can carry a credential (BDL-076 re-review finding m3).

Honest degradation (DATA-STRICTNESS): a node with no doc gets an EMPTY
``doc_links`` (the view shows none, never a fabricated link); a node with no
``layer-*`` tag gets an empty ``layer``; the lint-clean flag is OMITTED entirely
when lint was not computed (no findings supplied) rather than faking a
"clean" verdict. Determinism: nodes/edges are sorted and the payload serializes
with ``sort_keys``, so regeneration is byte-stable for a fixed ``generated_at``.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from beadloom import __version__
from beadloom.application.site.architecture_card import (
    CardSources,
    NodeVerdicts,
    card_fields,
    card_sources,
)
from beadloom.application.site.layer_rules_view import (
    FLAGGED_EDGE_KIND,
    LayerRulesView,
    declared_layer_rules,
    layer_rules_view,
)
from beadloom.application.site.node_pages import _KIND_DIR
from beadloom.graph.rule_engine import (
    LayerDef,
    LayerRule,
    layer_of,
    node_tags,
    own_layer_of,
    part_of_parents,
)
from beadloom.infrastructure.repository import count_symbols_owned_by_node

if TYPE_CHECKING:
    import sqlite3
    from collections.abc import Collection, Mapping

    from beadloom.application.site.lint_reach import LintReach
    from beadloom.application.site.repository_link import RepositoryLink

logger = logging.getLogger(__name__)

# Artifact schema version. Version 2 (BDL-076 A1) is additive: every key of
# version 1 is kept with its meaning, and the viewer refuses a version it does
# not know with a visible message.
ARCHITECTURE_SCHEMA_VERSION = 2

# The conventional prefix a layer tag carries, removed to get the short token
# the view strata-colors by (``layer-domain`` -> ``domain``). It is NOT a layer:
# the layers are whatever the project declares, read from the indexed rule. The
# prefix is stripped because the four tokens are the front-end's contract
# (``site/.vitepress/theme/architectureTheme.js`` keys its colors and its lane
# labels by them), and a tag that does not carry the prefix is used verbatim,
# which colors grey rather than wrongly. Since schema version 2 the file also
# names the declared layers with their tokens, so a viewer can color by those.
_LAYER_TAG_PREFIX = "layer-"

# Served extension for a published doc page. The site is built WITHOUT VitePress
# ``cleanUrls``, so a doc README is served at ``…/README.html`` — a ``.md`` link
# is a 404. (The Markdown node pages keep ``.md`` because VitePress rewrites
# in-page Markdown links; the JSON artifact is read by client JS with no such
# rewrite, so it must carry the served ``.html`` path.)
_SERVED_DOC_EXT = ".html"
_MD_EXT = ".md"

# The edge kind the view renders a layering verdict on, and the one whose
# `why` lists are built. Owned by `layer_rules_view`, where the verdict is read.
_FLAGGED_EDGE_KIND = FLAGGED_EDGE_KIND

# The kinds that name a contract, carried on the edge so two contracts between
# one pair of nodes stay two edges.
_CONTRACT_EDGE_KINDS = frozenset({"consumes", "produces"})

_DOC_FRESH = "fresh"
_DOC_STALE = "stale"
_DOC_NONE = "none"


# ---------------------------------------------------------------------------
# Per-node attribute reads (honest, repository-backed)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _LayerView:
    """What layer each node is in under the FIRST layer rule by name.

    The data file's original layer keys — ``layers``, ``layer_order``, a node's
    ``layer`` and ``layer_rank`` — describe one rule, the first by name, and keep
    doing so since BDL-080 S1b added every rule beside them
    (:mod:`beadloom.application.site.layer_rules_view`): changing what an
    existing key means is a major change by the declared public API.

    ``tags`` are the ones inside the first rule's ``scope:``, the map the linter
    judges it by, so a node outside the scope has no ``layer`` and no
    ``layer_rank`` even where it carries one of the rule's tags (BDL-080 S1f).

    The view used to answer this itself, from a table of four tags and a table
    of four ranks, and it climbed ``part_of`` in a loop of its own. It was one of
    the three answers BDL-070 found disagreeing, so the arithmetic lives in
    :mod:`beadloom.graph.rules.layers`. This class only says which question the
    view asks:

    - :meth:`token` reads the node's OWN tag, because the card shows what the
      node declares — a feature inside a domain declares no layer and says so.
    - :meth:`rank` INHERITS through ``part_of``, because a feature has to sit in
      its container's lane or the layout has no lane for it.

    Which edges are found against is the rules' verdict, asked of every rule
    (:meth:`~beadloom.application.site.layer_rules_view.LayerRulesView.flagged`).
    """

    rule: LayerRule | None
    parents: Mapping[str, Collection[str]]
    tags: Mapping[str, Collection[str]]

    @property
    def layers(self) -> tuple[LayerDef, ...]:
        """The declared layers, top to bottom; empty when none are declared."""
        return () if self.rule is None else self.rule.layers

    @property
    def order(self) -> str:
        """The direction the declared rule enforces; ``""`` when none is declared."""
        return "" if self.rule is None else self.rule.enforce

    def declared(self) -> list[dict[str, object]]:
        """The declared layers as the data file carries them, top to bottom.

        ``token`` is what a node in that layer carries as its ``layer``, so the
        viewer can match the two without knowing any project's vocabulary.
        """
        return [
            {"name": layer.name, "rank": rank, "tag": layer.tag, "token": _token(layer)}
            for rank, layer in enumerate(self.layers)
        ]

    def token(self, ref_id: str) -> str:
        """The short layer name for the node's OWN tag; ``""`` when it has none."""
        index = own_layer_of(ref_id, self.layers, self.tags)
        if index is None:
            return ""
        return _token(self.layers[index])

    def rank(self, ref_id: str) -> int | None:
        """The node's lane: its own layer's index, else its nearest container's.

        ``None`` when no ``part_of`` ancestor declares a layer either — honest,
        and a different fact from sitting in the bottom lane.
        """
        return layer_of(ref_id, self.layers, self.parents, self.tags)


def _token(layer: LayerDef) -> str:
    return layer.tag.removeprefix(_LAYER_TAG_PREFIX)


@dataclass(frozen=True)
class _Strata:
    """The two layer readings one build takes, and the tags they are read from.

    ``tags`` is every node's tags, unnarrowed: what a node declares, which its
    card shows. ``first`` reads the first rule's scope only and ``every`` each
    rule's own, so a rule's scope decides what it judges and never what a node
    is shown to declare.
    """

    first: _LayerView
    every: LayerRulesView
    tags: Mapping[str, Collection[str]]


def _strata(conn: sqlite3.Connection) -> _Strata:
    """The layer lookups for one build, over the declarations the index holds.

    Reports the one case in which a release changed what a project sees: a
    graph whose nodes carry layer tags and whose index holds no layer rule
    rendered lanes from a table this module kept of its own and renders none
    now. The view has no way to tell which layering such a project meant — that
    is why the declaration is read rather than guessed — so it states the fact
    where it happens instead of drawing a stratification nobody declared.

    The condition counts ``layer-``-prefixed tags specifically, and that is not a
    hardcoded layer: the table this module used to keep held exactly the
    ``layer-*`` tags, so those are exactly the nodes whose lane moved. A project
    whose tags are named otherwise rendered no lanes before that release either,
    and is told nothing — the correct silence rather than a miss.
    """
    rules = declared_layer_rules(conn)
    tags = node_tags(conn).as_mapping()
    parents = part_of_parents(conn)
    if not rules:
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
    every = layer_rules_view(rules, parents, tags)
    # The first rule's view reads the tags inside its scope, as the linter does:
    # a node outside it is in none of the rule's layers, and an edge between two
    # such nodes is judged by no rule (review `beadloom-m7xq` finding 1). With no
    # `scope:` the narrowing hands the same map on, so the keys are what they were.
    return _Strata(
        first=_LayerView(
            rule=rules[0] if rules else None,
            parents=parents,
            tags=every.scoped_tags[0] if rules else tags,
        ),
        every=every,
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

    Mirrors :func:`beadloom.application.site.generate._published_doc_slugs` so a node's
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
    strata: _Strata,
) -> tuple[
    list[dict[str, object]],
    dict[str, list[str]],
    dict[str, list[str]],
    dict[str, list[str]],
    dict[str, list[str]],
]:
    """Build the architecture edges + the derived ``why`` dependency lists.

    Returns ``(edges, depends_on_by_id, depended_on_by_by_id)``:

    - ``edges``: one entry per ``part_of`` / ``depends_on`` / ``uses`` /
      ``consumes`` / ``produces`` edge, sorted; a contract edge carries its
      ``contract`` key. A ``depends_on`` edge also carries a ``violation`` flag — ``True``
      when any of the project's layer rules finds against that edge (BDL-080
      S1b: the union over rules), ``False`` when none does. **The verdict is the
      rules'** (BDL-070 B4): the view asks
      :func:`~beadloom.graph.rules.layer_edges.flagged_layer_edges` rather than
      deciding, so an edge is red here exactly when ``beadloom lint`` reports
      it. Until B4 this module flagged every edge at ``dst_rank <= src_rank``,
      which drew a dependency between two parts of one domain as a layering
      violation — 130 such edges on this repository against the rule's nought.
      ``part_of`` is subtle containment and carries NO ``violation`` (not a flow
      arrow), and neither does ``uses``: it records a RUNTIME coupling across a
      process or file boundary (a harness shelling out to the CLI, a reader of a
      file another node writes), which cannot break a layering rule the way an
      import can. The flag is honestly omitted when no rule places a layer at
      both ends — an edge no rule judged must not be drawn as healthy. The
      first rule's ranks are asked as well, which keeps the flag on every edge
      that carried one before every rule was read; they are its ranks inside its
      ``scope:``, so an edge outside the scope is not called judged by it.
    - the four ``why`` lists, sorted + de-duplicated: what a node imports
      (``depends_on``) and who imports it, kept SEPARATE from what it ``uses``
      at runtime and who uses it. Merging them would assert an import binding
      that does not exist; dropping ``uses`` — as this builder did until the
      `ai-techwriter` node read as an island while being the hub of a whole
      workflow — hides coupling that derivation can never see, only declaration.
    """
    # ``touches_code`` is not read: it points at a file, and the viewer draws nodes.
    rows = conn.execute(
        "SELECT src_ref_id, dst_ref_id, kind, contract_key FROM edges "
        "WHERE kind IN ('part_of', 'depends_on', 'uses', 'consumes', 'produces') "
        "ORDER BY kind, src_ref_id, dst_ref_id, contract_key"
    ).fetchall()
    flagged = strata.every.flagged(conn)
    first = strata.first
    edges: list[dict[str, object]] = []
    depends_on: dict[str, set[str]] = {}
    depended_on_by: dict[str, set[str]] = {}
    uses: dict[str, set[str]] = {}
    used_by: dict[str, set[str]] = {}
    for row in rows:
        src, dst, kind = str(row["src_ref_id"]), str(row["dst_ref_id"]), str(row["kind"])
        edge: dict[str, object] = {"src": src, "dst": dst, "kind": kind}
        if kind in _CONTRACT_EDGE_KINDS:
            edge["contract"] = str(row["contract_key"] or "")
        if kind == _FLAGGED_EDGE_KIND:
            depends_on.setdefault(src, set()).add(dst)
            depended_on_by.setdefault(dst, set()).add(src)
            judged_by_first = first.rank(src) is not None and first.rank(dst) is not None
            if judged_by_first or strata.every.judges(src, dst):
                edge["violation"] = (src, dst) in flagged
        elif kind == "uses":
            uses.setdefault(src, set()).add(dst)
            used_by.setdefault(dst, set()).add(src)
        edges.append(edge)
    edges.sort(
        key=lambda e: (str(e["src"]), str(e["dst"]), str(e["kind"]), str(e.get("contract", "")))
    )
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


@dataclass(frozen=True)
class _Relations:
    """The ``why`` lists of every node, derived once from the edges."""

    depends_on: dict[str, list[str]]
    depended_on_by: dict[str, list[str]]
    uses: dict[str, list[str]]
    used_by: dict[str, list[str]]


@dataclass(frozen=True)
class _BuildInputs:
    """Everything one build reads for every node, taken once."""

    pages: Mapping[str, str]
    parent: Mapping[str, str]
    strata: _Strata
    relations: _Relations
    card: CardSources
    published_doc_slugs: set[str] | None


def _node_dict(
    conn: sqlite3.Connection, row: sqlite3.Row, inputs: _BuildInputs
) -> dict[str, object]:
    """Project one graph node to its JSON-safe architecture-view payload."""
    ref_id, kind = str(row["ref_id"]), str(row["kind"])
    relations = inputs.relations
    placement = inputs.strata.every.placement(ref_id)
    node: dict[str, object] = {
        "id": ref_id,
        "label": ref_id,
        "kind": kind,
        "summary": str(row["summary"] or ""),
        "layer": inputs.strata.first.token(ref_id),
        "layer_rank": inputs.strata.first.rank(ref_id),
        # The rule that places the node, among every declared layer rule, and
        # its rank there (BDL-080 S1b); `layer`/`layer_rank` stay the first's.
        "layer_rule": "" if placement is None else placement.rule,
        "layer_rule_rank": None if placement is None else placement.rank,
        "group": _KIND_DIR.get(kind, "other"),
        "symbols": _symbol_count(conn, ref_id),
        "doc_status": _doc_status(conn, ref_id),
        "doc_links": _doc_links(conn, ref_id, published_doc_slugs=inputs.published_doc_slugs),
        "url": inputs.pages.get(ref_id, ""),
        "parent": inputs.parent.get(ref_id, ""),
        "depends_on": relations.depends_on.get(ref_id, []),
        "depended_on_by": relations.depended_on_by.get(ref_id, []),
        # Declared runtime coupling, kept separate from the import lists: a
        # subprocess call or a file-format contract is real but is NOT an
        # import, and derivation cannot see it at all.
        "uses": relations.uses.get(ref_id, []),
        "used_by": relations.used_by.get(ref_id, []),
    }
    node.update(
        card_fields(
            conn,
            ref_id,
            source=row["source"],
            lifecycle=str(row["lifecycle"]),
            raw_extra=row["extra"],
            sources=inputs.card,
        )
    )
    # Honest degradation: only carry the lint-clean flag when lint was computed.
    # It is the version-1 reading of the findings the card now lists in full.
    if "findings" in node:
        node["lint_clean"] = not node["findings"]
    return node


def build_architecture_view_data(
    conn: sqlite3.Connection,
    *,
    pages: dict[str, str] | None = None,
    published_doc_slugs: set[str] | None = None,
    verdicts: NodeVerdicts | None = None,
    generated_at: str = "",
    repository: RepositoryLink | None = None,
    lint: LintReach | None = None,
) -> dict[str, object]:
    """Build the deterministic interactive-architecture data model.

    Args:
        conn: An open read-only connection to the indexed graph DB.
        pages: Map of ``ref_id -> existing page URL`` (a node gets a non-empty
            ``url`` only when present, so a click never resolves to a dead page).
            ``docs site`` passes :func:`~beadloom.application.site.node_pages.node_page_urls`,
            which covers every kind.
        published_doc_slugs: The set of ``docs/``-relative slugs (``.md``
            stripped) that actually got a published page. A node's doc link is
            emitted only when its slug is in this set (honest — never a 404).
            ``None`` skips the gate (every doc row yields its served link).
        verdicts: The lint findings and the debt report the site run computed.
            A field left ``None`` is OMITTED from every node — ``findings`` with
            ``lint_clean``, and ``debt`` — rather than reported clean.
        generated_at: The instant the site run states for this file. The
            caller supplies it, so a fixed value regenerates byte-identically.
        repository: The repository the card links a node's source to, as the
            caller resolves it; ``None`` gives every node an empty link rather
            than one nobody stated. It reaches the file only as each node's
            ``source_url``.
        lint: Lint's totals and node-less findings for the whole project
            (BDL-080 S4a). Carried as the top-level ``lint`` when given, and
            omitted rather than reported clean when lint did not run.

    Returns:
        A JSON-safe dict with ``schema_version`` 2, ``scope``, ``nodes``,
        ``edges``, ``generated_at``, ``beadloom_version``, ``layers`` and
        ``layer_order`` (the first layer rule by name), ``layer_rules`` (every
        layer rule with its scope, BDL-080 S1b), ``lint`` when *lint* is given,
        every section sorted for
        byte-stable serialization. Each node carries its ``layer_rank`` (the
        partition index for the layered-lanes layout), its ``layer_rule`` and
        ``layer_rule_rank``, and each ``depends_on`` edge a ``violation`` flag
        when a rule judged both ends.
    """
    strata = _strata(conn)
    edges, depends_on, depended_on_by, uses, used_by = _arch_edges(conn, strata)
    parent = _parent_map(conn)
    inputs = _BuildInputs(
        pages=pages or {},
        parent=parent,
        strata=strata,
        relations=_Relations(depends_on, depended_on_by, uses, used_by),
        card=card_sources(
            conn, tags=strata.tags, verdicts=verdicts, repository=repository, parent=parent
        ),
        published_doc_slugs=published_doc_slugs,
    )
    rows = conn.execute(
        "SELECT ref_id, kind, summary, source, lifecycle, extra FROM nodes ORDER BY ref_id"
    ).fetchall()
    data: dict[str, object] = {
        "schema_version": ARCHITECTURE_SCHEMA_VERSION,
        "scope": "architecture",
        "generated_at": generated_at,
        "beadloom_version": __version__,
        "layers": strata.first.declared(),
        "layer_order": strata.first.order,
        "layer_rules": strata.every.declared(str(row["ref_id"]) for row in rows),
        "nodes": [_node_dict(conn, row, inputs) for row in rows],
        "edges": edges,
    }
    if lint is not None:
        data["lint"] = lint.as_dict()
    return data


def serialize_architecture_view(data: dict[str, object]) -> str:
    """Serialize the architecture data to deterministic JSON (sorted, 2-space)."""
    return json.dumps(data, sort_keys=True, indent=2, ensure_ascii=False) + "\n"


def _as_list(value: object) -> list[object]:
    return value if isinstance(value, list) else []


def _stratification(data: dict[str, object]) -> str:
    """The sentence naming the declared layers, top to bottom, from *data*.

    The names come from the project's declaration. A page that wrote a fixed
    list would describe this repository's layers on every adopter's site.
    """
    names = [
        str(layer["name"])
        for layer in _as_list(data.get("layers"))
        if isinstance(layer, dict) and layer.get("name")
    ]
    if not names:
        return "The project declares no layers, so the map draws no lanes."
    return f"The lanes are the declared layers, top to bottom: {' → '.join(names)}."


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
        "hand-drawn. Domains and services are boxes around their features and "
        "components. Each edge kind — `depends_on`, `uses`, `consumes` and "
        "`produces` — has its own line, with its arrow at the edge's target, "
        "and the legend lists the kinds drawn. "
        f"{_stratification(data)} "
        "Select a node to open its card and mark its neighbourhood; the toolbar "
        "sets how deep and in which direction it reaches, and **Impact** shows "
        "everything that depends on the node, ring by ring, with the risky nodes "
        "marked. Filter by kind, domain, layer or name, or show only the flagged "
        "nodes. The view's state is in the URL, so a view can be linked.",
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
