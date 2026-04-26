# RFC: BDL-040 — F4: Living Knowledge Base + Visual Landscape (VitePress)

> **Status:** Approved
> **Created:** 2026-06-02

---

## Summary

A new `beadloom docs site [--out DIR=site] [--federated FILE]` generator (in `application/site.py`) that turns the VitePress site into the **showcase (витрина) of three Beadloom products**:

- **Showcase A — Metrics dashboard** (AaC + DocAsCode): the metrics Beadloom already computes (`lint`/`doctor`/`debt-report`/`sync-check`), honest by construction.
- **Showcase B — Interactive architecture** (AaC), at two scales: intra-repo per-node pages + C4/Mermaid, AND the 🌟 cross-repo contract landscape map (Mermaid, clickable).
- **Showcase C — Published validated documentation** (DocAsCode): the REAL root `docs/` tree, published as itself, with a per-doc **validation badge** (`fresh`/`stale (reason)` + coverage) injected from the `doc_sync` engine — making "Beadloom keeps this honest" visible.

Plus a committed VitePress scaffold (`site/.vitepress/` config + pinned `package.json`) so the tree builds. **Beadloom produces; VitePress renders** — no LLM (that is the deferred F4.1), no SaaS, no hand-drawing, no prose-rewriting. Purely additive: no graph-format / schema-version change; reads the existing DB + `docs/` + `federate` output.

## Design principles (from STRATEGY-3)

1. **Beadloom produces, VitePress renders** — the generator emits Markdown/JSON/Vue-config; rendering polish must not become a scope sink (§F4.2).
2. **Honest by construction** — every dashboard number comes from the SAME code path as `lint`/`doctor`/`debt-report`/`sync-check`; never a metric the gate would contradict (the Phase-0 hard dependency).
3. **Deterministic** — identical graph → byte-identical generated tree (sorted nodes/edges/pages, stable frontmatter, injected/no timestamps) — reproducible in CI, reviewable as a diff.
4. **TUI vs VitePress division** — TUI = live per-repo workstation; VitePress = published, landscape-wide, versioned source of truth for humans + URL-reading agents. Do not duplicate; the site is the *published* surface.
5. **Thin slice on the map** — Mermaid (native VitePress, supports `click`→link) first; rich Cytoscape/D3 interactivity is an explicit follow-up.

---

## Architecture

### Module layout

| Module | Change |
|--------|--------|
| `application/site.py` (**new**) | The `docs site` use-case: load graph → render pages + dashboard + map + nav config → write the tree. Pure-ish (DB in, files out), deterministic. Orchestrates existing renderers; no new graph logic. |
| `application/site_pages.py` (**new, optional split**) | Per-node page rendering (overview / domain / service / feature) — split out if `site.py` nears the domain-size limit. |
| `services/cli.py` | New `beadloom docs site` subcommand (under the existing `docs` group). |
| `graph/c4.py`, `graph` Mermaid | **Reused** (already render Mermaid / C4) — the generator calls them, does not reimplement. |
| `application/debt_report.py`, `doctor.py`, `graph/linter.py`, `doc_sync` | **Reused** for dashboard metrics (same code paths → honest numbers). |
| `doc_sync` engine (`sync_state`) | **Reused** for Showcase C — per-doc `status` / reason / `synced_at` + coverage drive the validation badges (same source as `sync-check`). |
| `graph/federation.py` | **Reused** — read a `federated.json` (or the local graph) for the landscape map. |
| `site/.vitepress/config.mjs` + `site/package.json` (**new, committed scaffold**) | Pinned VitePress + Mermaid plugin; the generator populates nav/sidebar; VitePress renders. |

The generated content tree lives under a **separate `--out` dir (default `site/`)**, NOT the existing source `docs/` — so generation never clobbers the hand-written domain docs. Build output (`site/.vitepress/dist`, `node_modules`) is gitignored; the generated Markdown + config are reproducible (regenerated, not hand-edited).

### 1. Site generator — `beadloom docs site` (G1)

```
beadloom docs site [--out DIR=site] [--federated FILE] [--project DIR]
```

Pipeline (deterministic, sorted at every step):
1. Load the indexed graph (read-only).
2. Emit `index.md` (architecture overview: domains/services/features counts, the top-level C4/Mermaid diagram, health summary).
3. Emit one page per node — `domains/<ref>.md`, `services/<ref>.md`, `features/<ref>.md` — each with: summary, `source`, public symbols, `depends_on`/`uses`/`part_of` edges (as links), linked hand-written docs (transcluded or linked), and an embedded scoped C4/Mermaid diagram for that node.
4. Emit the three showcases: the dashboard (§2), the architecture pages + landscape map (§3a/§3b), and the published validated `docs/` with badges (§3c).
5. Emit the VitePress nav/sidebar config (populate the scaffold's `config.mjs` `themeConfig.sidebar`/`nav`: Dashboard · Architecture · Landscape · Documentation).

Node page data reuses `docs polish --json` / the graph DB (symbols, deps) — no reimplementation. Output is byte-stable for identical input (a determinism test asserts it).

### 2. AaC/DocAsCode dashboard (G2)

`dashboard.md` + `dashboard.data.json`, generated from the EXISTING metric code paths:
- lint: violation count + severity breakdown + (if a snapshot exists) trend.
- debt: `debt_report` score + per-category + worst nodes.
- docs: coverage %, `sync-check` freshness % + stale count.
- doctor: integrity check pass/fail summary.
- federated rollup (when `--federated` given): per-service health + contract-verdict counts.

The `.data.json` is consumed by a small VitePress Vue widget (filterable table / counts) — but the **numbers are computed in Python**, so the dashboard cannot show a figure the gate would contradict (honest by construction). No metric is invented in the front-end.

### 3a. Showcase B — interactive architecture, intra-repo (G3)

The intra-repo AaC graph made browsable. One page per node — `domains/<ref>.md`, `services/<ref>.md`, `features/<ref>.md` — each with summary, `source`, public symbols, `depends_on`/`uses`/`part_of` edges rendered as **links to the other node pages**, the node's linked hand-written docs (linked into Showcase C), and an embedded **scoped C4/Mermaid** diagram (reusing `graph`/`c4`). Plus an architecture `index.md` (counts + the top-level C4 diagram + health summary). Node data comes from the graph DB / `docs polish --json` — no reimplementation.

### 3b. Showcase B — 🌟 cross-repo landscape map (G4)

`landscape.md` — the federated contract graph as a **Mermaid** diagram:
- Nodes = services/repos; edges = contracts (AMQP / GraphQL) **labelled by `ContractVerdict`** (CONFIRMED / BREAKING / DRIFT / ORPHANED_CONSUMER / UNDECLARED_PRODUCER / EXTERNAL).
- **Health overlay** via Mermaid `classDef` (red = BREAKING/DRIFT, green = CONFIRMED, grey = EXTERNAL/EXPECTED).
- **Clickable** nodes via Mermaid `click <id> "<url>"` → the node's service page (Showcase B intra-repo).
- Source: a `--federated <federated.json>` (F2 output) when given; otherwise the single-repo graph (a degenerate one-node landscape). The Mermaid is generated from the data — never hand-drawn.

**Thin-slice boundary:** Mermaid only (VitePress renders it natively + supports click). A rich pan/zoom/filter Cytoscape/D3 component is a documented follow-up; this epic does not add a JS graph library.

### 3c. Showcase C — published validated documentation (G5)

The REAL root `docs/` is published as a first-class site section (the team's & agents' source of truth), with Beadloom's validation status made visible:
- The generator copies the `docs/` tree into the site (`site/docs/…`) — or configures VitePress to include it — preserving its structure (it is the source of truth, rendered as-is; **prose is never rewritten**).
- For each published doc, the generator injects a **validation badge** at the top, derived from the `doc_sync` engine's `sync_state`: `✅ fresh` or `⚠️ stale — <reason>` (`hash_changed` / `symbols_changed` / `untracked_files`), plus `last synced <ts>` and the node's doc-coverage %. A doc not tracked by any pair is badged `untracked` honestly.
- The badge is **generated from the same data as `sync-check`** — so a doc the gate calls stale shows stale on the site. This is the DocAsCode product made visible: the site doesn't just host docs, it shows they're *kept honest*.
- Injection is deterministic (badge block is a stable, sorted, marker-delimited prefix); regenerating overwrites only the badge region, never the authored prose.

### 4. VitePress scaffold + buildable site (G4)

- Committed `site/package.json` (pinned `vitepress` + a Mermaid plugin, e.g. `vitepress-plugin-mermaid` + `mermaid`, exact versions) and `site/.vitepress/config.mjs` (theme, Mermaid enable; nav/sidebar populated by the generator).
- `npm ci && npm run docs:build` renders the generated tree. C4 + Mermaid render natively.
- The Python generator is fully unit-testable WITHOUT node (it emits files); the actual `npm run build` is validated in the dogfood (BEAD-05) + an optional CI job, not in pytest.

### 5. Dogfood + CI build (G5)

- Generate Beadloom's OWN site (`beadloom docs site --out site`) — its 6 domains / 4 services / features + dashboard; AND a `landscape.md` from an anonymized federated landscape (reuse the F2/F3 anonymized fixtures — NOT the gitignored scratch; the committed `tests/fixtures/` exports).
- `npm ci && npm run docs:build` must succeed; spot-check the map renders + nodes link. Capture friction in `BDL-UX-Issues.md`.
- Optional: a `.github/workflows/` job that builds the site on push (documented; a gh-pages deploy is documented/optional, not required to ship).

---

## Schema & versioning

No `EXPORT` / `FEDERATION` / DB schema-version change. `docs site` is a read-only generator over the existing graph + `federate` output. The VitePress scaffold is committed config, not a schema.

## Determinism & honesty

- Generated Markdown/JSON/config are **sorted + byte-stable** for identical input (no wall-clock in committed output; inject a fixed "generated_at" only into a non-diffed footer or omit). A determinism test re-generates and diffs.
- Dashboard metrics share code paths with `lint`/`doctor`/`debt-report`/`sync-check` — the site cannot publish a number the gate would contradict (honesty hard-dependency satisfied by F1–F3).
- The map is generated from `federate`/graph data — never hand-authored.

## Build order (waves — detail in PLAN)

1. **Generator core + scaffold** — `application/site.py` + `docs site` + committed `site/.vitepress/` config + pinned `package.json`: graph → per-node pages + overview + nav, buildable empty-ish tree (foundation; embed C4/Mermaid here too).
2. **Showcase A — dashboard** — metrics page + `.data.json` (reuse debt/doctor/lint/sync).
3. **Showcase B — 🌟 landscape map** — Mermaid from `federated.json`/graph, clickable + verdict/health overlays.
4. **Showcase C — published validated docs** — copy/include `docs/` + inject per-doc validation badges from `doc_sync`.
5. **Dogfood** — Beadloom's own site (3 showcases) + anonymized landscape; `npm run docs:build` succeeds; spot-check.

(Showcase B intra-repo node pages + diagrams are folded into the generator core, wave 1.) Then test → review → tech-writer (guide, SPEC, CHANGELOG, STRATEGY §F4.2/§F4.3 → delivered, §F4.1 → follow-up).

## Risks & mitigations

| Risk | Mitigation |
|------|------------|
| Rendering polish becomes a scope sink | Beadloom emits content; VitePress renders. Mermaid-first map (no JS graph lib). Pin the scaffold. Thin-slice the interactivity. |
| JS/node toolchain in a Python repo | The Python generator is fully pytest-testable without node; `npm run build` is dogfood/CI-validated, not unit-tested. `package.json` pins exact versions. |
| Generated `site/` collides with source `docs/` | Generate into a separate `--out` dir (default `site/`); never write into `docs/`. |
| Non-determinism (timestamps, dict order) | Sort everything; no wall-clock in diffed output; determinism test. |
| Dashboard drifts from real metrics | Reuse the exact `lint`/`doctor`/`debt-report`/`sync-check` code paths — no parallel metric computation. |
| Map over-promises interactivity | README/PRD state Mermaid-clickable thin slice; Cytoscape/D3 is an explicit follow-up. |
| Badge injection mutates the source-of-truth `docs/` | Badges are injected into the COPY under `site/docs/…`, never the source `docs/`; the real docs stay authored-only. Badge region is marker-delimited + deterministic (regeneration overwrites only it). |
| Scope creep (F4.1 LLM, hosting) | Hard non-goals: no LLM call in this epic; static site only; gh-pages documented not built. |

## Out of scope (→ follow-ups / F5)

F4.1 AI tech-writer in CI (`docs ai-refresh` + external model); rich Cytoscape/D3 interactive map; hosted/live site; AI-authored prose; DevOps/Infra nodes; semantic search.
