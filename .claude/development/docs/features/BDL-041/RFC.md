# RFC: BDL-041 — F4.4: Site rendering fixes + dashboard UX

> **Status:** Approved
> **Created:** 2026-06-02

---

## Summary

Fix the two generator bugs that make F4's diagrams render broken, add a **generation-time Mermaid validity guard** so broken diagrams fail pytest (not the browser), make diagrams **pan/zoom/fullscreen**, and turn the dashboard into a real **ECharts** dashboard (gauges + charts + **trends** + a prioritized **recommendations** panel) — Approach C (Beadloom emits deterministic `dashboard.data.json`; committed Vue widgets render it). Python generation stays fully pytest-testable; the Vue/ECharts frontend + `npm run docs:build` + the Mermaid guard cover render. No graph/schema-version change.

## Design principles

1. **Build green ≠ renders ok — close the gap.** A generation-time structural guard rejects unrenderable Mermaid in pytest; the dogfood additionally validates the real render. No "green build" may hide a broken page again.
2. **Beadloom produces, VitePress renders.** Python emits deterministic data + Mermaid; Vue/ECharts components render it client-side. Data stays honest-by-construction (same gate code paths).
3. **Honest trends.** Time-series come from real recorded history (sparse at first); never a fabricated point.
4. **Determinism.** `dashboard.data.json` + generated Mermaid are sorted/byte-stable; timestamps come from stored values, not `now()`.

---

## Architecture

### Module / file layout

| File | Change |
|------|--------|
| `application/site_landscape.py` | Fix `_mermaid_id`: prefix every id (e.g. `n_<sanitized>`) so it can NEVER equal a reserved keyword (`graph`/`end`/`subgraph`/`class`/`click`/…); apply to node decls + `click` + edges consistently (label stays the display text). |
| `graph/c4.py` | Fix `Rel()` emission: emit a `Rel(a,b,…)` ONLY when both endpoints are declared in the rendered diagram as `Container`/`Component`/`Person` (i.e. inside a boundary) — drop/skip Rels whose endpoint is the `System` root (or any non-declared node). The crash is `Rel(beadloom,…)` to the undeclared System root. |
| `application/site_mermaid_guard.py` (**new**) | `validate_mermaid(text) -> list[MermaidIssue]` — structural validators: (1) flowchart/graph node ids are not reserved keywords + valid charset; (2) every C4 `Rel(a,b)` endpoint is a declared `Container`/`Component`/`Person`/`System*`. Extensible. Called on EVERY diagram in `generate_site` (raise on issue) + asserted in pytest with known-bad fixtures. |
| `application/site_dashboard.py` | Add `trends` (time-series) + `recommendations` to `dashboard.data.json` (still honest — same metric code paths). |
| `application/site_metrics_history.py` (**new**) | Append/read a metrics-history store (timestamp + lint/debt/coverage/sync% + counts) so trends have real history; `docs site` records one point per run (deterministic timestamp injected in tests). Reuses `graph_snapshots` for structural counts where available. |
| `site/.vitepress/theme/index.js` (**new**) | Custom theme `extends` the VitePress default; `enhanceApp` registers the global components + ECharts; wraps/augments the Mermaid render with the diagram viewer. |
| `site/.vitepress/theme/components/*.vue` (**new**) | `DiagramViewer.vue` (svg-pan-zoom + fullscreen around a rendered Mermaid SVG); dashboard widgets: `HealthGauges.vue`, `CategoryChart.vue`, `TrendCharts.vue`, `Recommendations.vue` (ECharts via `vue-echarts`, reading `dashboard.data.json`). |
| `site/package.json` | Add pinned `echarts`, `vue-echarts`, `svg-pan-zoom` (exact versions). |
| `application/site.py` | Wire the guard (validate every emitted diagram); make `dashboard.md` mount the widget components (e.g. `<HealthGauges />`, `<TrendCharts />`, `<Recommendations />`). |

### 1. Mermaid correctness (G1)

- **Landscape ids (`site_landscape.py`):** `_mermaid_id` already strips non-`[A-Za-z0-9_]`; extend it to **prefix** the result (`n_…`) so a node named `graph` becomes `n_graph` — never colliding with a flowchart keyword. The display label (`[graph]`) is unchanged; `click n_graph "/services/graph"` keeps the real route. Apply the same id everywhere the node is referenced.
- **C4 Rels (`graph/c4.py`):** when rendering, only emit `Rel(a,b)` if both `a` and `b` are nodes declared in the diagram body (Containers/Components within boundaries). A Rel touching the `System` root (declared as the boundary, not a node) — like `Rel(beadloom, application)` — is dropped (or the System is represented appropriately). This removes the `drawRels` undefined-`x` crash. Verify both the top-level C4 and the scoped per-node C4 (node pages) are fixed.

### 2. Generation-time Mermaid guard (G2)

`site_mermaid_guard.validate_mermaid(diagram_text)` runs structural checks (no JS/node — pure Python, deterministic):
- **Reserved-id / charset:** parse `graph`/`flowchart` node decls; fail if any node id equals a reserved keyword or has an illegal char.
- **C4 Rel integrity:** collect declared `Container/Component/Person/System*` ids; fail if any `Rel(a,b,…)` references an undeclared id.
- Extensible registry of validators.

`generate_site` calls it on every diagram it emits and **raises** (fails generation) on any issue. Pytest fixtures feed known-bad diagrams (a `graph` node id; a Rel to an undeclared node) and assert the guard catches them — so the F4 bug classes can never regress without a browser. (Optional second net: a `mmdc` smoke-render in the dogfood/CI.)

### 3. Diagram pan/zoom/fullscreen (G3)

`DiagramViewer.vue` wraps the rendered Mermaid SVG with `svg-pan-zoom` (pan + wheel-zoom + reset) and a fullscreen toggle (Fullscreen API). The custom theme applies it to mermaid containers (wrap the plugin's `Mermaid` component or post-process `.mermaid` SVGs on mount). Pinned `svg-pan-zoom`. Degrades gracefully (static SVG) if JS disabled.

### 4. Dashboard widgets — ECharts (G4)

Approach C: the Python `dashboard.data.json` stays the deterministic source of truth; committed Vue widgets render ECharts (`vue-echarts` + `echarts`, pinned) from it:
- `HealthGauges.vue` — gauges for lint(0=good)/debt/coverage%/sync%.
- `CategoryChart.vue` — bar/donut: debt by category, lint by severity.
- The widgets import the generated `dashboard.data.json`; values are exactly the gate metrics (the generator already asserts equality). The dashboard renders "красиво И полезно" without inventing numbers.

### 5. Trends (G5)

- `site_metrics_history.py`: a small append-log (`.beadloom/metrics_history.json` or a `metrics_history` table) of `{ts, lint, debt, coverage, sync_pct, nodes, edges, symbols}`. `docs site` appends the current point per run (ts injected for deterministic tests). Structural counts also backfill from existing `graph_snapshots` history (real history exists from F1–F4 snapshots).
- `site_dashboard` emits the series into `dashboard.data.json.trends`; `TrendCharts.vue` renders ECharts line charts (lint/debt/coverage/sync% over time). **Honest:** only recorded points; sparse at first, grows per build. No interpolation/fabrication.

### 6. Recommendations panel (G6)

`site_dashboard` (or `site_recommendations.py`) builds a prioritized, actionable list from existing data (same code paths): worst-debt nodes (`debt_report`), stale docs to refresh (`sync_state`), contract risks (BREAKING/DRIFT from a `--federated` artifact), lint hotspots. Emitted to `dashboard.data.json.recommendations`; `Recommendations.vue` renders it (severity-ordered, each linking to the relevant page). Honest by construction.

### 7. Dogfood + render validation (G7)

Regenerate Beadloom's own site, `npm run docs:build`, and **validate the render**: the guard passes (0 issues), no `Syntax error in text` markers, the C4 + landscape diagrams render, pan/zoom/fullscreen work, the dashboard shows live gauges/charts/trends/recommendations. The coordinator runs `npm` (network-approved); friction → `BDL-UX-Issues.md`.

---

## Schema & versioning

No `EXPORT`/`FEDERATION`/DB schema-version change. A `metrics_history` store (JSON file or a small additive table) is new but additive and not part of any versioned artifact. Frontend deps are added to `site/package.json` (pinned).

## Determinism & honesty

- `dashboard.data.json` (incl. `trends`, `recommendations`) sorted + byte-stable; timestamps from stored history, not `now()` (injected in tests).
- Generated Mermaid sorted/stable; the guard is deterministic.
- Dashboard numbers + recommendations come from the exact gate code paths (no front-end-invented data); trends show only real recorded points.

## Build order (waves — detail in PLAN)

1. **P0 — Mermaid correctness + guard** (`site_landscape.py` id fix, `c4.py` Rel fix, new `site_mermaid_guard.py`, wired into `generate_site`). Unblocks an honest render.
2. **Diagram pan/zoom/fullscreen** (custom theme + `DiagramViewer.vue` + `svg-pan-zoom`).
3. **Dashboard data** — trends (`site_metrics_history.py`) + recommendations into `dashboard.data.json`.
4. **Dashboard frontend** — ECharts widgets (`HealthGauges`/`CategoryChart`/`TrendCharts`/`Recommendations`) + theme registration + `dashboard.md` mounts them (needs the data shape from wave 3).
5. **Dogfood + render validation** — regenerate + build + verify the live render.

Then test → review → tech-writer.

## Risks & mitigations

| Risk | Mitigation |
|------|------------|
| Guard re-implements a Mermaid parser (drift/incompleteness) | Scope to the SPECIFIC bug classes (reserved-id, C4 Rel integrity) as targeted structural checks, extensible; not a full parser. Optional `mmdc` smoke as a second net. |
| Frontend (Vue/ECharts) not pytest-testable → another "green build, broken render" | Python data + guard are pytest-tested; the dogfood MUST open/validate the real render (not just `build` exit 0); pin deps; keep components small. |
| C4 Rel-drop hides a real relationship | Only drop Rels whose endpoint genuinely isn't a diagram node (the System root); log/count dropped Rels; the relationship is still in the graph + landscape map. |
| Trends fabricate history | Append-only real points; sparse-start shown honestly; no interpolation; timestamps stored not `now()`. |
| ECharts bundle weight / build slowness | Pin + import only needed ECharts modules (tree-shaken); static build, one-time. |
| Determinism break (metrics history grows each run) | History append uses injected ts in tests; the committed `dashboard.data.json` regen is deterministic for a fixed history; document the history store as append-only state, not a diffed artifact. |

## Out of scope (→ follow-ups)

F4.1 AI tech-writer in CI; bespoke Cytoscape/D3 landscape engine; hosted/live dashboard; full Playwright render suite; new metric kinds.
