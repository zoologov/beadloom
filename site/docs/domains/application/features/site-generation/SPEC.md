<!-- beadloom:badge-start -->
> ✅ **fresh**
> 
> last synced 2026-06-11T14:19:08.709748+00:00 · coverage 100% (`site-generation`)
> 
> _Validation by Beadloom `doc_sync` — same source as `sync-check`._
<!-- beadloom:badge-end -->

# Site Generation

The `docs site` VitePress content generator for the application domain.

**Source:** `src/beadloom/application/site.py` (plus the `site_*.py` cluster)

---

## Specification

### Purpose

Generate a complete VitePress content tree from the indexed graph. `docs site`
reads the graph read-only and emits the About home, the architecture overview,
per-node pages, the metrics dashboard (data + page), the cross-repo landscape
map, the published `docs/` section, the nav/sidebar tree, and a generation-time
Mermaid validity guard.

### Module cluster

One feature node covers nine cooperating modules (all annotated
`# beadloom:feature=site-generation`):

- `site.py` — orchestrator / use-case entry point
- `site_about.py` — README → About page transform
- `site_dashboard.py` — metrics dashboard data + page
- `site_landscape.py` — cross-repo landscape map
- `site_mermaid_guard.py` — generation-time Mermaid validity guard
- `site_metrics_history.py` — metrics-history append store
- `site_nav.py` — nav / sidebar tree builders
- `site_pages.py` — per-node page rendering
- `site_published.py` — published `docs/` section + per-doc badges

### Contract

- **Input:** the indexed graph + project `docs/` / `README.md`.
- **Output:** a `site/` content tree consumed by the VitePress site
  (`vitepress-site` node) — the real producer→consumer contract.
- **Invariants:** generation is deterministic and read-only over the graph.

> Skeleton (BDL-051 S3b / BEAD-14). The tech-writer pass (BEAD-13) fills prose.
