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
  (the partition index for the canonical layered-lanes layout — service=0 …
  infra=3, inherited from the nearest layered container when untagged), symbol
  count, doc-status, served `.html` doc links (gated by the published-slug set
  so a link never 404s), and the `beadloom why` dependency lists; each
  `depends_on` edge carries a `violation` flag (true when it points up or
  cross-cuts the layer order). Honest degradation throughout.

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
