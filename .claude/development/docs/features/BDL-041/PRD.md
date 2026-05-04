# PRD: BDL-041 — F4.4: Site rendering fixes + dashboard UX

> **Status:** Approved
> **Created:** 2026-06-02

---

## Problem

F4 (BDL-040) shipped the VitePress showcase and `vitepress build` exits 0 — but **the live site renders broken**, which `build` did not catch (build-green was necessary but insufficient; the real test is opening the rendered pages). Dogfooding the running site surfaced:

- **🔴 Two real generator bugs producing broken Mermaid (console-confirmed):**
  - **Landscape flowchart parse error** (`got 'GRAPH'`): a node uses the raw `ref_id` `graph` as its Mermaid id, colliding with the reserved `graph` keyword of `graph LR`. The generator emits raw `ref_id`s as Mermaid identifiers without sanitization → any node named `graph`/`end`/`subgraph`/etc. breaks the diagram.
  - **C4 diagram crash** (`Cannot read properties of undefined (reading 'x')` in `drawRels`): the C4 emits `Rel(beadloom, …)` where `beadloom` (the root) is NOT declared as a `Container(…)` in the boundary → mermaid-C4 cannot resolve the node and crashes. The generator emits `Rel()` edges to/from nodes that are not container-level.
  - Both surface as `Syntax error in text` SVG fallbacks on the page.
- **🟡 Diagrams are unreadable** — no pan / zoom / fullscreen, so large C4/landscape graphs can't be inspected.
- **🟡 The dashboard is not a dashboard** — it is dry Markdown. The honest `dashboard.data.json` exists, but there is no visual layer: no widgets, charts, trends, or recommendations.

A published site with broken diagrams is a *published lie* (the very thing F4's honesty principle forbids) — so F4 must not ship until the render is fixed.

## Impact

F4.4 makes the F4 showcase actually usable and trustworthy in the browser: correct diagrams (caught at generation, not in production), readable/interactive diagrams, and a genuine dashboard (widgets + live charts + trends + actionable recommendations) — "красиво И полезно". It also closes the process gap that let broken render ship under a green build: a **generation-time Mermaid validity guard** so broken diagrams fail pytest, not the user's browser. F4 + F4.4 ship (and push) together.

Success criterion: **Beadloom's own site renders with zero diagram/console errors, diagrams are pan/zoom/fullscreen-able, and the dashboard shows live ECharts widgets + trends + a prioritized recommendations panel — all data honest-by-construction.**

## Goals

- [ ] **G1 — Fix the two Mermaid bugs (P0).** (a) **Node-id sanitization:** map every `ref_id` to a safe Mermaid identifier that can never collide with a reserved keyword (`graph`/`end`/`subgraph`/`class`/`click`/…) or contain illegal chars — across the landscape map AND node pages; keep the human label as the display text. (b) **C4 `Rel()` integrity:** emit `Rel(a, b, …)` ONLY when both `a` and `b` are declared `Container(…)` in the diagram (filter edges whose endpoints aren't container-level, or declare the missing nodes) — no Rel to the root/feature nodes that aren't containers.
- [ ] **G2 — Generation-time Mermaid validity guard (P0).** Structural validators run at generation (and in pytest, no browser/node needed) that reject the bug classes above: no node id equal to a reserved keyword / illegal charset; every C4 `Rel` endpoint is a declared `Container`; (extensible to future classes). A generated diagram that would not parse fails the generator/test — closing the "build green ≠ renders ok" gap. Optionally a node `mmdc` smoke-check in the dogfood/CI as a second net.
- [ ] **G3 — Diagram pan / zoom / fullscreen (P1).** A committed Vue wrapper component (e.g. `svg-pan-zoom` + a fullscreen toggle) around every rendered Mermaid diagram, so large C4/landscape graphs are inspectable. Pinned deps.
- [ ] **G4 — Real dashboard widgets (ECharts, P1).** Committed Vue widgets rendering **ECharts** (via `vue-echarts`, pinned) from the deterministic `dashboard.data.json` (Approach C — data honest+deterministic, render interactive): health gauges (lint/debt/coverage/sync%), category bar/donut (debt by category, lint by severity), responsive + themed. Beautiful AND useful.
- [ ] **G5 — Trends (P1).** Emit time-series into `dashboard.data.json` from the snapshot history (`graph_snapshots`) + `debt_report.DebtTrend`, rendered as ECharts line charts (lint / debt / coverage / sync% over time). Honest: show only the history that exists (sparse at first); each `docs site` run appends a metrics snapshot so the series grows. No fabricated points.
- [ ] **G6 — Recommendations panel (P1).** An actionable "fix first" panel derived from existing data (same code paths): worst-debt nodes, stale docs to refresh (`sync-check`), contract risks (BREAKING / DRIFT from `federate`), lint hotspots — prioritized. Honest by construction.
- [ ] **G7 — Dogfood + render validation (the success criterion).** Regenerate + `npm run docs:build` Beadloom's own site AND validate the RENDER: the Mermaid guard passes, no `Syntax error in text` / console errors, diagrams pan/zoom/fullscreen, the dashboard shows live charts + trends + recommendations. Capture friction in `BDL-UX-Issues.md`.
- [ ] **G8 — Tech-writer (docs).** Update the VitePress guide (dashboard widgets, diagram interactivity, the Mermaid guard), domain/SPEC docs, CHANGELOG, STRATEGY-3 note.

## Non-goals (deferred / out of scope)

- **F4.1 — AI tech-writer in CI** — still the separate follow-up epic.
- **Cytoscape/D3 fully-custom interactive landscape graph** — pan/zoom/fullscreen on the Mermaid render is the chosen thin slice; a bespoke graph engine is a later option.
- **Live/hosted dashboard / server-side data** — static site, data baked at generation (rebuild on push); no SaaS.
- **Headless browser render testing in pytest** — the Python validators + the `npm run docs:build` + (optional) `mmdc` smoke + the manual dogfood cover render; a full Playwright suite is out of scope.
- **New metric *kinds*** beyond what Beadloom already computes — F4.4 visualizes existing honest data, it does not invent metrics.

## User Stories

### US-1: Diagrams that actually render
**As** a site visitor, **I want** the C4 and landscape diagrams to render correctly (no "Syntax error in text"), **so that** I can read the architecture.

**Acceptance criteria:**
- [ ] A node named `graph` (or any reserved word) renders fine (sanitized id).
- [ ] The C4 diagram renders with no `drawRels` crash (Rel only between declared Containers).
- [ ] A generation-time validator fails the build/test if a generated diagram would not parse.

### US-2: Readable large diagrams
**As** a visitor, **I want** to pan / zoom / fullscreen a diagram, **so that** a big landscape/C4 graph is inspectable.

**Acceptance criteria:**
- [ ] Each rendered diagram supports pan + zoom + a fullscreen toggle.

### US-3: A real dashboard
**As** a tech lead, **I want** the dashboard to show live gauges, charts, trends, and a prioritized "fix first" panel, **so that** I see the system's health and what to act on — at a glance.

**Acceptance criteria:**
- [ ] ECharts gauges/bars/donut render from `dashboard.data.json` (values still == the gate code paths).
- [ ] Line-chart trends render from real snapshot history (sparse at first, no fabricated points).
- [ ] A recommendations panel lists worst debt / stale docs / contract risks / lint hotspots, prioritized.

### US-4: Broken render can't ship again
**As** the maintainer, **I want** a generated diagram that wouldn't render to fail pytest, **so that** "build green" can never again hide a broken page.

**Acceptance criteria:**
- [ ] The Mermaid validity guard runs in pytest (no browser/node) and catches the reserved-id + C4-Rel classes.
