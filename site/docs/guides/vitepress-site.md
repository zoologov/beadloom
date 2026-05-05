# VitePress Site Guide

`beadloom docs site` turns the indexed architecture graph into a **VitePress
knowledge base** — a published, versioned, URL-shareable source of truth for
humans *and* agents. It is the F4 "Living Knowledge Base + Visual Landscape"
deliverable of Strategy 3.

> **Beadloom produces, VitePress renders.** Beadloom emits a deterministic
> Markdown/config content tree; VitePress (a static site generator) renders it.
> There is no live server, no SaaS, and no LLM in this path — freshness comes
> from rebuilding on push, the same way `beadloom ci` keeps the graph honest.

## What it generates

```bash
beadloom docs site [--out DIR] [--federated FILE] [--project DIR]
```

Reading the graph **read-only**, the command writes the following under `--out`
(default `site/`). It NEVER writes into the source `docs/` tree.

| Output | Showcase | What it is |
|--------|----------|------------|
| `index.md` | — | Architecture overview: node counts, the top-level C4/Mermaid diagram, a health summary line. |
| `domains/<ref>.md`, `services/<ref>.md`, `features/<ref>.md` | Architecture | One page per node: summary, source, public symbols, `part_of`/`depends_on`/`uses` edges as links, linked docs, an embedded scoped C4/Mermaid diagram. |
| `dashboard.md` + `dashboard.data.json` | **A — metrics dashboard** | AaC/DocAsCode metrics. |
| `landscape.md` | **B — 🌟 landscape map** | The federated contract graph as an interactive Mermaid diagram. |
| `docs/**` + `docs/index.md` | **C — published validated docs** | The real `docs/` tree, copied verbatim, with per-doc freshness badges. |
| `.vitepress/config.generated.mjs` | — | Nav/sidebar config imported by the committed scaffold; sections Dashboard / Architecture / Landscape / Documentation. |

### Showcase A — AaC/DocAsCode metrics dashboard

`dashboard.md` (human page) + `dashboard.data.json` (machine data) surface lint
violations and severity breakdown, the debt score and its trend, doc coverage,
`sync-check` freshness % and stale count, the `doctor` pass/fail summary, and —
when `--federated` is given — a per-service edge-verdict + contract-verdict
rollup.

**Honest by construction.** Every figure comes from the *same code path* as the
gate that owns it: `lint` (`graph/linter.lint`), debt (`debt_report`), docs
(`doc_sync` `sync_state`), `doctor` (`doctor.run_checks`), and the federated
rollup (the `federate` output, verbatim). The dashboard cannot show a number the
gate disagrees with — it is the gate, rendered. The page never invents a figure
the data dict does not contain.

### Showcase B — 🌟 the cross-repo landscape map

`landscape.md` renders the federated contract graph (F2) as a **Mermaid**
diagram:

- **With `--federated federated.json`** (a `beadloom federate` hub artifact):
  nodes are the satellite services and edges are the cross-repo contract links,
  each carrying the hub's verdict (`CONFIRMED` / `BREAKING` / `ORPHANED_CONSUMER`
  / `UNDECLARED_PRODUCER` / `EXTERNAL` / `DRIFT` / …) verbatim.
- **Without it:** the map degenerates to a single landscape built from the local
  graph (`uses` / `depends_on` edges, all `confirmed`).

Edges are labelled by their verdict; a Mermaid `classDef` health overlay colours
nodes (green = healthy, red = broken, grey = external/expected) and broken edges
get a red `linkStyle`. Each node is clickable, linking to its intra-repo page.

This is the *thin slice*: Mermaid only (clickable). A richer JS graph library
(Cytoscape / D3) is a follow-up — no schema bump was needed for the Mermaid map.

### Showcase C — published validated documentation

`publish_docs` copies the **real** `docs/**` tree into `site/docs/…`, preserving
structure, and injects a per-doc validation badge into the **copy only**:

- The badge status comes from the `doc_sync` engine via `check_sync` — the SAME
  code path `beadloom sync-check` runs — so a doc the gate calls stale shows
  `stale — <reason>` on the site (`fresh` / `stale` / `untracked`). The badge
  also shows the stored `last synced` time (deterministic, not wall-clock) and
  the owning node's source-coverage %.
- The badge is wrapped between stable `<!-- beadloom:badge-start -->
> ⚪ **untracked** — not tracked by any doc-code pair
> 
> _Validation by Beadloom `doc_sync` — same source as `sync-check`._
<!-- beadloom:badge-end -->

` markers, so regeneration overwrites ONLY the
  badge region and leaves the authored prose byte-for-byte intact.

**The published `docs/` is the source of truth.** The source tree is never
mutated; there is no AI prose-rewriting (that is the deferred F4.1 follow-up).
Badges come from `doc_sync`, not from a model.

## Building and previewing

The committed VitePress **scaffold** (`site/package.json`, `site/.vitepress/config.mjs`)
renders the generated content tree. The build output (`site/.vitepress/dist/`),
the VitePress cache, and `site/node_modules/` are gitignored — only the scaffold
and the generated, deterministic Markdown/config are committed.

```bash
# 1. Generate the content tree from the indexed graph (run `beadloom reindex` first).
beadloom docs site --out site

# 2. Build the static site.
cd site && npm install && npm run docs:build

# 3. Preview the built site locally.
npm run docs:preview          # or `npm run docs:dev` for a live-reload dev server
```

For the landscape map (Showcase B), feed a federation artifact:

```bash
beadloom federate service-a.json service-b.json   # writes .beadloom/federated.json
beadloom docs site --out site --federated .beadloom/federated.json
```

### Optional — deploy to GitHub Pages

A minimal workflow that rebuilds the site on every push to the default branch:

```yaml
# .github/workflows/docs-site.yml
name: Docs Site
on:
  push:
    branches: [main]
permissions:
  contents: read
  pages: write
  id-token: write
jobs:
  build-deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - run: pip install beadloom
      - run: beadloom reindex && beadloom docs site --out site
      - uses: actions/setup-node@v4
        with: { node-version: "20" }
      - run: cd site && npm ci && npm run docs:build
      - uses: actions/upload-pages-artifact@v3
        with: { path: site/.vitepress/dist }
      - uses: actions/deploy-pages@v4
```

> Set VitePress's `base` option in `site/.vitepress/config.mjs` to your repo name
> (e.g. `base: "/beadloom/"`) when deploying to a project Pages URL.

## Determinism

Identical graph → byte-identical tree: pages are sorted, frontmatter is stable,
and no wall-clock value lands in the diffed output (the published-doc badge uses
the stored `sync_state.synced_at`, not "now"). This makes the generated tree safe
to commit and to diff in review, and makes a rebuilt site reproducible.

## Where this fits — TUI vs VitePress

- **TUI** (`beadloom tui`) is the engineer's *live, per-repo workstation* — "what
  is happening now," real-time, over SSH.
- **VitePress** is the team's *published, landscape-wide source of truth* —
  versioned, URL-addressable, readable by humans and agents alike. It is the
  channel for PMs, new devs, other teams, and URL-reading agents.

## Scope and follow-ups

- **Delivered (F4.2 / F4.3):** the `docs site` generator, all three showcases,
  and the committed VitePress scaffold — dogfooded by building Beadloom's own
  site (`vitepress build` exit 0).
- **Deferred (F4.1):** the AI tech-writer in CI — orchestrating an *external*
  model to refresh drifted docs, scoped by `sync-check` / `docs polish --json`,
  with team review on a PR. The published-docs showcase intentionally does NOT
  rewrite prose today; badges are computed, not generated.
- **Deferred:** a richer JS graph library for the landscape map (Cytoscape / D3)
  beyond the current clickable Mermaid thin slice; REST/OpenAPI + gRPC contracts
  in the federated map.

See the [`beadloom docs site` CLI reference](../services/cli.md#beadloom-docs-site),
the [application domain README](../domains/application/README.md) for the
generator modules, and the [federation SPEC](../domains/graph/features/federation/SPEC.md)
for the contract graph the landscape map renders.
