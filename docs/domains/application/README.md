# Application

Use-case orchestration layer. Sits between the interface layer (`services`/`tui`)
and the domain layer (`context_oracle`, `doc_sync`, `graph`, `onboarding`). Its
modules coordinate multiple domains plus infrastructure to fulfil a use case and
hold no business rules of their own.

Layer order: `services → application → domains → infrastructure`. The application
layer may depend on domains and infrastructure (legal top-down); it is never
depended upon by a lower layer. Extracting these orchestrators out of
`infrastructure` is what lets `infrastructure` stay domain-agnostic and restores
the DDD Dependency Rule.

## Specification

### Modules

- **reindex.py** — `reindex(root)` performs full reindex: snapshot sync baselines → drop tables → create schema → load graph YAML → store deep config → index docs → index code → resolve imports → load rules → map tests → analyze git activity → extract API routes → build sync state (with preserved symbol hashes) → populate FTS5 → clear bundle cache → take health snapshot → populate file index → store parser fingerprint. `incremental_reindex(root)` updates only changed files; detects parser availability changes via fingerprint comparison and graph YAML changes via `_graph_yaml_changed()`, triggering full reindex when needed.
- **doctor.py** — `run_checks(conn, *, project_root=None)` validates graph health with DB checks (empty summaries, unlinked docs, nodes without docs, isolated nodes, symbol drift, stale sync entries, source coverage gaps) plus an optional "Agent Instructions" check when `project_root` is provided, comparing CLAUDE.md/AGENTS.md factual claims (version, packages, CLI commands, MCP tool count) against runtime truth.
- **debt_report.py** — `collect_debt_data()` aggregates architecture health signals from lint, sync-check, doctor, git activity, and test mapper. `compute_debt_score()` applies a weighted formula producing a 0-100 debt score with category breakdown, severity classification, and per-node top offenders. `format_debt_report()`/`format_debt_json()` render the report. `compute_debt_trend()` compares against the last graph snapshot.
- **watcher.py** — `watch()` monitors project files (graph YAML, docs, source) and auto-triggers reindex on changes using `watchfiles`. Graph changes trigger full reindex; other changes trigger incremental. `WatchEvent` frozen dataclass captures per-event metadata. `DEFAULT_DEBOUNCE_MS` constant (500ms).
- **site.py** — `generate_site(conn, out_dir, *, project_root, federated=None)` is the `docs site` use-case: it reads the indexed graph read-only and writes a VitePress content tree under `out_dir` (default `site/`) — an `index.md` architecture overview (counts + top-level C4/Mermaid + a read-only health summary), one page per node (delegated to `site_pages.py`), the metrics dashboard (`dashboard.md` + `dashboard.data.json`, delegated to `site_dashboard.py`), the 🌟 landscape map (`landscape.md`, delegated to `site_landscape.py`), and `.vitepress/config.generated.mjs` (nav/sidebar). Beadloom produces, VitePress renders. Output is deterministic (sorted, stable frontmatter, no wall-clock) and never writes into the source `docs/`. Returns a frozen `SiteResult` listing every written path. Reuses `graph/c4.py` (`map_to_c4`/`filter_c4_nodes`/`render_c4_mermaid`) for diagrams; reimplements no graph logic.
- **site_pages.py** — per-node page rendering for `site.py` (split out to stay under the domain-size limit). `render_all_pages(conn)` returns sorted `NodePage`s; each page has summary, source, public symbols, `part_of`/`depends_on`/`uses` edges as Markdown links to other node pages, linked hand-written docs, and an embedded scoped C4/Mermaid diagram.
- **site_dashboard.py** — Showcase A, the AaC/DocAsCode metrics dashboard. `build_dashboard_data(conn, *, project_root, federated=None)` returns a deterministic, JSON-safe dict and `render_dashboard_md(data)` renders the human page from that same dict (the front-end never invents a figure). Honest by construction: every number comes from the SAME code path as its gate — `lint` (count + severity breakdown via `graph/linter.lint`), `debt` (`debt_report.compute_debt_score` + `compute_debt_trend`, serialized via `format_debt_json`), `docs` (coverage % + `sync_state` freshness % + stale count, read-only), `doctor` (`doctor.run_checks` pass/fail summary), and an optional `federated` rollup (per-service edge-verdict health + contract-verdict counts) reusing the `federate` output verbatim.
- **site_landscape.py** — Showcase B, the 🌟 cross-repo landscape map. `build_landscape_data(conn=None, *, federated=None)` returns a deterministic, JSON-safe dict (`scope`/`nodes`/`edges`) and `render_landscape_md(data)` renders a **Mermaid** diagram from it (never hand-drawn). With a `federated.json` (the F2 `federate` hub output) nodes are the satellites and edges are the cross-repo links carrying the hub's `ContractVerdict`-style verdict verbatim; without it the map degenerates to one landscape from the local graph (`uses`/`depends_on` edges, all `confirmed`). Edges are labelled by their verdict; a Mermaid `classDef` health overlay colours nodes (green = healthy, red = broken, grey = external/expected) and broken edges get a red `linkStyle`; each node is clickable (`click <id> "/services/<ref>"`) to its intra-repo page. Thin slice = Mermaid only (no JS graph library).
- **gate.py** — `run_ci_gate(project_root, *, fail_on, hub_exports, no_reindex)` is the unified CI enforcement gate (the `beadloom ci` orchestrator). It composes the existing checkers IN ORDER — reindex (unless `no_reindex`) → `lint --strict` → `sync-check` → `config-check` (AgentConfigAsCode) → `doctor` (graph/data integrity; only `ERROR`-severity checks fail the gate, so advisory WARNING/INFO checks never block — no false gate) → (when `hub_exports` given) `federate --fail-on` — into one `GateResult` whose `.ok` is True only when every step passed. It ORCHESTRATES existing domain code; it reimplements no checker (the doctor step reuses `doctor.run_checks`). Honesty invariants: no short-circuit (every step runs and ALL findings are collected even after an earlier failure) and no silent skip (each `GateStep` records `PASS`/`FAIL`/`SKIP`). Findings are projected to the shared agent-actionable shape `{kind, rule, severity, locations, why, remediation}` (reused from `graph/linter.py`) uniformly across all steps, so `--format json`/`github` are identical regardless of which step produced a finding.

## API

Module `src/beadloom/application/reindex.py`:
- `ReindexResult` — dataclass with counts, `nothing_changed` flag, `errors`, and `warnings`
- `reindex(project_root, *, docs_dir=None)` -> `ReindexResult` — full reindex with sync baseline preservation
- `incremental_reindex(project_root, *, docs_dir=None)` -> `ReindexResult` — incremental reindex with parser fingerprint and graph YAML change detection
- `resolve_scan_paths(project_root)` -> `list[str]` — resolves source scan directories from config

Module `src/beadloom/application/doctor.py`:
- `Severity` — enum: `OK`, `INFO`, `WARNING`, `ERROR`
- `Check` — dataclass: `name`, `severity`, `description`
- `run_checks(conn, *, project_root=None)` -> `list[Check]` — runs DB validation checks plus optional agent instructions freshness check when `project_root` is provided

Module `src/beadloom/application/debt_report.py`:
- `DebtReport` — frozen dataclass: `debt_score` (0-100), `severity`, `categories`, `top_offenders`, `trend`
- `load_debt_weights(project_root)` -> `DebtWeights`
- `collect_debt_data(conn, project_root, weights=None)` -> `DebtData`
- `compute_debt_score(data, weights=None)` -> `DebtReport`
- `compute_debt_trend(conn, current_report, project_root, weights=None)` -> `DebtTrend | None`
- `format_debt_report(report)` -> `str`
- `format_debt_json(report, category=None)` -> `dict[str, Any]`

Module `src/beadloom/application/watcher.py`:
- `DEFAULT_DEBOUNCE_MS` — debounce constant (500ms)
- `WatchEvent` — frozen dataclass: `files_changed`, `is_graph_change`, `reindex_type`
- `watch(project_root, debounce_ms=DEFAULT_DEBOUNCE_MS, callback=None)` — monitors project files via `watchfiles`

Module `src/beadloom/application/site.py`:
- `SiteResult` — frozen dataclass: `out_dir`, `written` (sorted tuple of every written path)
- `generate_site(conn, out_dir, *, project_root, federated=None)` -> `SiteResult` — deterministic VitePress tree generator; never writes into the source `docs/`

Module `src/beadloom/application/site_dashboard.py`:

- `build_dashboard_data(conn, *, project_root, federated=None)` -> `dict` — deterministic dashboard data (lint/debt/docs/doctor + optional federated rollup); honest by construction (reuses each gate's code path)
- `render_dashboard_md(data)` -> `str` — render `dashboard.md` from the data dict
- `serialize_dashboard_data(data)` -> `str` — deterministic JSON (sorted keys) for `dashboard.data.json`

Module `src/beadloom/application/site_landscape.py`:
- `build_landscape_data(conn=None, *, federated=None)` -> `dict` — deterministic landscape-map data (`scope`/`nodes`/`edges`); federated when a `federate` artifact is given, else a single-repo map from the local graph
- `render_landscape_md(data)` -> `str` — render `landscape.md` as a Mermaid diagram (verdict-labelled edges, `classDef` health overlay, clickable nodes); never hand-drawn

Module `src/beadloom/application/site_pages.py`:
- `NodeRow` / `NodePage` — frozen dataclasses for a graph node and its rendered page
- `load_nodes(conn)` -> `list[NodeRow]`; `render_all_pages(conn)` -> sorted `list[NodePage]`

Module `src/beadloom/application/gate.py`:
- `GateStep` — dataclass: `name`, `passed`, `skipped`, `findings`, `summary`; `.status` -> `PASS`/`FAIL`/`SKIP`
- `GateResult` — dataclass: `steps`; `.ok` (all steps passed), `.findings` (all findings across steps)
- `run_ci_gate(project_root, *, fail_on, hub_exports, no_reindex)` -> `GateResult` — composes reindex → lint → sync-check → config-check → doctor → (optional) federate; never short-circuits

## Testing

Tests: `tests/test_reindex.py`, `tests/test_reindex_config.py`, `tests/test_reindex_tests.py`, `tests/test_reindex_activity.py`, `tests/test_reindex_routes.py`, `tests/test_doctor.py`, `tests/test_doctor_drift.py`, `tests/test_doctor_instructions.py`, `tests/test_watcher.py`, `tests/test_debt_report.py`, `tests/test_debt_integration.py`, `tests/test_gate.py`, `tests/test_site_generator.py`, `tests/test_site_dashboard.py`, `tests/test_site_landscape.py`
