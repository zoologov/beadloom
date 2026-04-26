# PRD: BDL-040 — F4: Living Knowledge Base + Visual Landscape (VitePress)

> **Status:** Approved
> **Created:** 2026-06-02

---

## Problem

F1–F3 made Beadloom a federated, contract-aware, *enforced* architecture system — but its output lives in the terminal (`beadloom ctx`/`graph`/`federate`) and in per-repo Markdown. There is no **published, landscape-wide, URL-shareable source of truth** that humans who don't live in a terminal (PMs, new devs, other teams) and URL-reading agents can consume. STRATEGY-3 §2's "one context for everyone" is only half-delivered: the data and enforcement exist; the *shared, glanceable surface* does not. And the 🌟 differentiator — seeing the whole IT-landscape (services + contract edges + drift/health) **in one glance** — has no home.

Beadloom already generates the raw materials (`beadloom graph` → Mermaid / C4; `docs polish --json` → structured node data; `federate` → the landscape graph; `doctor`/`lint`/`debt-report` → metrics) but nothing assembles them into a navigable knowledge base or a visual map.

## Impact

F4 is the phase where Beadloom's intelligence becomes **visible and shareable** beyond the maintainer's terminal — the published "agreed state" of the architecture, versioned and rebuilt on every push. It completes "one context for everyone" (TUI = the engineer's live per-repo workstation; VitePress = the team's published landscape source of truth). It has a hard honesty dependency on Phase 0 / F2 / F3 (a KB built on a false-positive sync-check or a toothless gate is a *published lie* — worse than none), which F1–F3 have now satisfied.

**Framing — VitePress is the SHOWCASE of three Beadloom products, not a fourth doc generator.** The site is the *витрина* (storefront) that renders what Beadloom already produces. The three product-surfaces map to three site sections:

| # | Beadloom product | Site section | What it shows |
|---|------------------|--------------|----------------|
| **A** | **AaC + DocAsCode metrics** | **Dashboard** | What Beadloom *measured* — lint/debt/coverage/sync%/health + landscape rollup. |
| **B** | **Architecture-as-Code** | **Interactive architecture** | What Beadloom *knows about structure* — the intra-repo graph + C4/dependency views, AND the 🌟 cross-repo contract landscape map. Two scales of one AaC product. |
| **C** | **DocAsCode** | **Published validated documentation** | The team's & agents' *source of truth* — the REAL root `docs/` tree, published with a per-doc **validation badge** (sync-check fresh/stale + coverage) so "Beadloom keeps this honest" is visible. |

Section **C is the correction over the first PRD draft**: the existing `docs/` is the validated source of truth and must be PUBLISHED as itself (with Beadloom's freshness status surfaced), not merely transcluded into generated node pages. The generated node pages (B) and the real docs (C) are distinct surfaces.

**Scope decision (this epic):** F4 officially has three sub-deliverables — F4.1 (AI tech-writer in CI), F4.2 (VitePress KB + dashboard), F4.3 (visual landscape map). This epic delivers **F4.2 + F4.3** — the published site + the 🌟 map — built around a deterministic, testable, Beadloom-native generator. **F4.1 (AI-tech-writer-in-CI) is deferred to a dedicated follow-up epic**: it is an external-model orchestration (credentials, nondeterminism, CI), operationally the most complex and most independent piece, and it naturally comes *after* the site exists (it keeps the site's content fresh). Splitting honors the "one honest thread at a time" survival rule.

Success criterion (STRATEGY-3 §"What done looks like", adapted): **a single `beadloom` command generates a VitePress site of the architecture + landscape that builds and renders — dogfooded on Beadloom's own repo (and an anonymized federated landscape) — showing the whole system in one glance, with the data honest (no metric the gate would contradict).**

## Goals

- [ ] **G1 — Site generator + VitePress scaffold (foundation).** A new `beadloom docs site [--out DIR=site] [--federated FILE] [--project DIR]` that assembles the site tree, plus a committed `site/.vitepress/` config + pinned `package.json` (VitePress + Mermaid plugin) so `npm run build` renders it. Deterministic (sorted, byte-stable), testable in Python with no model/network; populates nav/sidebar from the node tree. **Beadloom produces; VitePress renders.**
- [ ] **G2 — Showcase A · Metrics dashboard (AaC + DocAsCode).** A generated dashboard (Markdown + a `.data.json`) surfacing the metrics Beadloom already computes: lint violations + severity + trend, debt score + worst nodes, doc coverage %, `sync-check` freshness %, stale count, `doctor` integrity summary, and a federated landscape rollup. **Honest by construction** — every number comes from the SAME code path as `lint`/`doctor`/`debt-report`/`sync-check`; the site can never show a figure the gate would contradict.
- [ ] **G3 — Showcase B · Interactive architecture (AaC, intra-repo).** Per-domain / per-service / per-feature pages (summary, `source`, public symbols, `depends_on`/`uses`/`part_of` edges as links) with embedded C4 + Mermaid diagrams (reusing `graph`/`c4`), and an architecture overview/index. This is the intra-repo AaC graph made browsable — "what Beadloom knows about the structure."
- [ ] **G4 — Showcase B · 🌟 Cross-repo landscape map (AaC, federation).** Render the F2 federated contract graph as a landscape map: services as nodes, contract edges (AMQP / GraphQL) labelled by `ContractVerdict` (CONFIRMED / BREAKING / DRIFT / EXTERNAL …), drift/health overlays, **clickable nodes** → service pages. **Thin slice:** Mermaid-rendered (native VitePress; `click`→link) from the `federate` output; rich pan/zoom (Cytoscape/D3) is an explicit follow-up.
- [ ] **G5 — Showcase C · Published validated documentation (DocAsCode).** Publish the REAL root `docs/` tree as a first-class site section (VitePress renders the actual hand-written source-of-truth docs), and inject a per-doc **validation badge** derived from the `doc_sync` engine — `fresh` / `stale (reason)` + last-synced + coverage — so "Beadloom keeps this doc honest" is *visible*. The docs are the source of truth for team + agents; the badge is the DocAsCode product made visible. (The generated node pages of G3 and the real docs of G5 are distinct surfaces; G5 does NOT rewrite doc prose.)
- [ ] **G6 — Dogfood (the success criterion).** Generate Beadloom's OWN site (6 domains / 4 services / features + the three showcases) AND a `landscape.md` from an anonymized federated landscape (reuse the committed anonymized F2/F3 fixtures); `npm ci && npm run docs:build` succeeds; spot-check the dashboard numbers match the CLI, the architecture renders, the docs show correct fresh/stale badges, and the map nodes link. Capture friction in `BDL-UX-Issues.md`.
- [ ] **G7 — Tech-writer (docs).** Document `beadloom docs site` + the VitePress workflow (build, optional gh-pages deploy) in `docs/guides/`; update the relevant domain/SPEC docs; CHANGELOG; STRATEGY-3 §F4.2/§F4.3 → delivered (and §F4.1 → noted as the follow-up).

## Non-goals (deferred / out of scope)

- **F4.1 — AI tech-writer in CI** (`beadloom docs ai-refresh`, external-model orchestration, the drift-scoped regeneration loop) → a dedicated follow-up epic. This epic does NOT call any LLM.
- **Rich interactive map** (Cytoscape/D3 pan/zoom/filter) — thin slice is Mermaid-rendered + clickable; full interactivity is a follow-up.
- **Hosted / live site** — VitePress is a *static* generator, built in CI / locally; no SaaS, no live server (Strategy-2 "no built-in LLM / no SaaS" holds). A gh-pages deploy workflow is documented/optional, not a product surface.
- **Authoring docs content with AI** — `docs site` assembles EXISTING graph data + existing Markdown; it does not write prose (that is F4.1).
- **DevOps / Infra nodes** (Terraform / k8s) in the map — F5.
- **Semantic search across the site** — F5.

## User Stories

### US-1: See the whole landscape in one glance
**As** a tech lead, **I want** a VitePress page showing all services + their contract edges with drift/health overlays, **so that** I understand the system without reading code or terminal output.

**Acceptance criteria:**
- [ ] The map renders services as nodes and AMQP/GraphQL contracts as edges, labelled by verdict.
- [ ] Nodes are clickable and link to their service pages.
- [ ] The map is generated from `federate` output (no hand-drawing).

### US-2: A published, shareable architecture KB
**As** a new dev / PM / URL-reading agent, **I want** a browsable site of domains, services, features, and diagrams, **so that** I can onboard without a terminal.

**Acceptance criteria:**
- [ ] `beadloom docs site` generates a VitePress tree that `npm run build` renders without error.
- [ ] Per-node pages carry summary, symbols, deps, and embedded C4/Mermaid diagrams.

### US-3: An honest metrics dashboard
**As** a maintainer, **I want** a dashboard of lint/debt/coverage/sync/health, **so that** the team sees the real state — never a number the gate would contradict.

**Acceptance criteria:**
- [ ] Dashboard metrics come from the same code paths as `lint`/`doctor`/`debt-report`/`sync-check`.
- [ ] A landscape rollup aggregates per-service health.

### US-4: Published docs that show they're validated (DocAsCode)
**As** a team member / agent, **I want** the real project `docs/` published with a per-doc freshness badge from Beadloom, **so that** I trust the docs as the source of truth and can see at a glance which are validated-fresh vs stale.

**Acceptance criteria:**
- [ ] The actual root `docs/` tree is published as a first-class site section (not just transcluded into node pages).
- [ ] Each doc page carries a `fresh` / `stale (reason)` badge + coverage, derived from the `doc_sync` engine (same source as `sync-check`).
- [ ] `docs site` does NOT rewrite doc prose (that is the deferred F4.1).

### US-5: Deterministic, dogfoodable generation
**As** the maintainer, **I want** `beadloom docs site` to be deterministic and self-hostable, **so that** the site is reproducible in CI and I can generate Beadloom's own site.

**Acceptance criteria:**
- [ ] Identical graph → byte-identical generated tree (sorted, stable).
- [ ] Beadloom's own site generates + builds (dogfood).
