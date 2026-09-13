# Site Generation

The `docs site` VitePress content generator for the application domain.

**Source:** `src/beadloom/application/site.py` (plus the `site_*.py` cluster)

---

## Specification

### Purpose

Generate a complete VitePress content tree from the indexed graph. `docs site`
reads the graph read-only and emits the About home page, the interactive
architecture view (a canonical layered-lanes Cytoscape+ELK graph), per-node
pages, the metrics dashboard (data and page), the cross-repo landscape map, the
published `docs/` section, the nav/sidebar tree, and a generation-time Mermaid
validity guard.

### Module cluster

One feature node covers the cooperating modules below (all annotated
`# beadloom:feature=site-generation`):

- `site.py` — orchestrator / use-case entry point (`generate_site`)
- `architecture_view.py` — the interactive **architecture** data model
  (`architecture.data.json`): each node carries its `layer`, its `layer_rank`
  (the partition index for the canonical layered-lanes layout — the index of the
  node's layer in the declared order, inherited from the nearest layered
  container when the node declares none), symbol count, doc-status, served
  `.html` doc links (gated by the published-slug set so a link never 404s), and
  the `beadloom why` dependency lists; each `depends_on` edge carries a
  `violation` flag (true when the project's layer rule finds against that edge).
  Honest degradation throughout.

  **Which layers exist is read, not written down here (BDL-070 A5).** The view
  held a table of four `layer-*` tags and a table of four ranks and climbed
  `part_of` in a loop of its own — one of the three disagreeing answers to "what
  layer is this node in" that BDL-070 exists to remove. It now reads the layer
  order from the indexed `rules` table (the same graph every other read in the
  module goes through, so generating the site needs no second path to
  `rules.yml`) and resolves membership through `graph.rules.layers`, which is
  what the rule engine decides on. A graph whose index carries no layer rule
  gets no lanes rather than every node in lane 0.

  **That is the one adopter-visible change of rendered output in Release A**, and
  it is stated here because nothing else would show it: a project that carries
  `layer-*` tags and declares no layer rule rendered four lanes before and
  renders none now. This repository declares the rule, so nothing moves here —
  which is exactly why the case would go unnoticed. The view cannot tell which
  layering such a project meant, so it logs the case at INFO with the number of
  tagged nodes instead of drawing a stratification nobody declared.

  The `layer` field stays the short token — the declared tag with its
  conventional `layer-` prefix removed — because those tokens are the
  front-end's contract (`site/.vitepress/theme/architectureTheme.js` keys its
  colors and lane labels by them). A tag that does not carry the prefix is used
  verbatim and colors grey, which is the same honest degradation the rest of the
  module follows. `layer` reads the node's OWN tag while `layer_rank` inherits:
  the card states what the node declares, and the layout needs a lane for a
  feature that declares nothing.

  **The edge `violation` flag is the rule engine's verdict, asked of the rule
  (BDL-070 B4).** It was this module's own predicate — `dst_rank <= src_rank`,
  true for every edge pointing up AND every edge staying inside one layer — and
  it was the last of the three disagreeing answers this epic set out to remove.
  Measured on this repository on 2026-09-13, over a warm full rebuild of the
  index: the view drew 130 edges red that `beadloom lint` finds nothing against,
  116 of them dependencies between two parts of one domain and 14 crossings
  `rules.yml` excuses by name. The view now calls
  `graph.rules.layer_edges.flagged_layer_edges`, so an edge is red here exactly
  when the Gate reports it — direction, layer skip, the same-layer predicate
  RFC Q1 decided and the project's `exempt:` entries, none of them stated twice.

  **The rendered artifact moves for those 130 edges**, from `"violation": true`
  to `"violation": false`, which is what B4 changes about the picture. The flag
  stays OMITTED for an edge with an end in no declared layer: the rule does not
  judge such an edge, and drawing it as healthy would be the same overclaim in
  the other direction.

  The rule's `exempt:` entries reach the view through the indexed rule, so
  `reindex` carries them into `rules.rule_json`. An index written by an earlier
  release carries none, and a project that excuses crossings and regenerates its
  site without reindexing sees those crossings drawn red until it does.

  A layer rule declared over an edge kind other than `depends_on` flags nothing
  here. This picture renders the verdict on dependency arrows, so such a rule is
  reported by `beadloom lint` and drawn by nothing — a gap in what the picture
  shows rather than a disagreement about what is true.

  It also carries **declared runtime coupling** (`uses` edges) — a subprocess
  call or a file-format contract — as `uses` / `used_by`, kept SEPARATE from the
  import lists and drawn dotted, never flagged as a violation: crossing a
  process boundary to call a published interface is not a layering break the way
  an import is, and folding it into `depends_on` would assert a binding that
  does not exist. The view previously filtered these edges out entirely, so
  authored architectural intent already present in the graph — every
  `cli uses <domain>` among them — was silently absent from the picture,
  and a node coupled only that way (`ai-techwriter`, which shells out to the CLI
  and hands the dashboard a run-record file) read as an island.
- `landscape_view.py` — the interactive cross-service **landscape** data model
  (`landscape.data.json`): contract edges with their reconciled verdict +
  typed/body surface; plain (non-contract) dependencies carry no protocol.
- `site_about.py` — README → About page transform (link-rebased)
- `site_dashboard/` — metrics dashboard data + page (package, decomposed by cohesion in BDL-059 S4 into `_common`, `gate_metrics`, `ai_activity`, `recommendations`, `alerts`, `status_cards`, `assemble`; the package `__init__` re-exports the public surface)
- `site_landscape.py` — cross-repo landscape map
- `site_mermaid_guard.py` — generation-time Mermaid validity guard
- `site_metrics_history.py` — append-only metrics-history store
- `site_nav.py` — nav / sidebar tree builders
- `site_pages.py` — per-node page rendering
- `site_published.py` — published `docs/` section + per-doc badges (including
  the `reference` badge for unpaired overview docs)

The dashboard's not-fresh count and a node's stale marker read
`status IN ('stale','missing')`: a pair whose file is gone is not one less thing
to worry about (BDL-UX #174).

### Output contract

The generated `site/` tree is consumed by the VitePress site (the
`vitepress-site` node) — a real producer → consumer contract. The source `docs/`
is never written; output goes only under `--out` (default `site/`). The metrics
point recorded each run takes its timestamp from `now_ts`, injected in tests for
determinism and defaulting to the current UTC instant in production; it is the
only wall-clock read and lands only in the append-only history store, never in a
diffed dashboard field.

## Invariants

- Generation is deterministic and read-only over the graph.
- The source `docs/` is never modified; only `--out` is written.
- The Mermaid guard validates every emitted diagram at generation time, so a
  broken diagram fails the build rather than the published site.

## API

Module `src/beadloom/application/site.py`:

- `generate_site(conn, out_dir, *, project_root, federated=None, now_ts=None) -> SiteResult`
  — generate the content tree; returns the files written.
- `SiteResult` — the outcome: `out_dir` and the sorted `written` files.
- `MermaidValidationError` — raised when a generated diagram is invalid.

## Testing

Tests: `tests/test_site_generator.py`, `tests/test_site_about.py`,
`tests/test_site_dashboard.py`, `tests/test_site_landscape.py`,
`tests/test_site_mermaid_guard.py`, `tests/test_site_metrics_history.py`,
`tests/test_site_nav.py`, `tests/test_site_published_docs.py`,
`tests/test_site_coverage_edges.py`
