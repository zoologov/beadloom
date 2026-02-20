# RFC: BDL-025 — Interactive Architecture TUI

> **Status:** Approved
> **Created:** 2026-02-20

---

## Overview

Transform Beadloom's TUI from a basic read-only viewer (3 widgets, 1 screen) into an interactive architecture workstation with 3 screens, 10+ widgets, live file watching, and keyboard-driven actions. All data reads from existing infrastructure — no new storage or APIs needed.

## Motivation

### Problem
The current `beadloom ui` is a static domain list + node detail viewer. Architecture exploration requires running 5-10 separate CLI commands (`status`, `lint`, `sync-check`, `why`, `ctx`, `debt-report`). Each command produces isolated output with no persistent workspace.

### Solution
A multi-screen Textual app that integrates all existing data providers (debt report, lint engine, sync-check, git activity, why analysis, context oracle) into interactive widgets with keyboard navigation. File watcher detects source changes for live updates.

## Technical Context

### Constraints
- Python 3.10+
- Textual >= 0.80 (upgrade from current >= 0.50 — needed for Screen API improvements, CSS improvements, and Worker stability)
- watchfiles >= 0.20 (already in optional deps)
- SQLite read-only access (existing pattern)
- Optional dependency: `beadloom[tui]` — core stays lightweight
- No built-in LLM calls (agent-native principle)

### Affected Areas
- `src/beadloom/tui/` — complete rewrite of app.py, new screens, new widgets
- `src/beadloom/services/cli.py` — rename `ui` command to `tui`, add options
- `pyproject.toml` — bump textual version constraint
- `docs/services/tui.md` — documentation update
- `.beadloom/_graph/services.yml` — update TUI node summary

### Existing Data Provider APIs (no changes needed)

| Provider | Module | Key Function | Returns |
|----------|--------|-------------|---------|
| Debt report | `infrastructure/debt_report.py` | `collect_debt_data()` + `compute_debt_score()` | `DebtReport` (score, severity, categories, offenders) |
| Lint engine | `graph/rule_engine.py` | `load_rules()` + `evaluate_all()` | `list[Violation]` |
| Doc sync | `doc_sync/engine.py` | `check_sync()` | `list[dict]` (status, ref_id, doc/code paths) |
| Git activity | `infrastructure/git_activity.py` | `analyze_git_activity()` | `dict[str, GitActivity]` |
| Why analysis | `context_oracle/why.py` | `analyze_node()` | `WhyResult` (upstream/downstream trees) |
| Context oracle | `context_oracle/builder.py` | `build_context()` + `estimate_tokens()` | `dict` (bundle) + `int` (tokens) |
| Reindex | `infrastructure/reindex.py` | `incremental_reindex()` | Success/failure |

## Proposed Solution

### Approach

**Architecture: Screens + DataLayer + FileWatcher**

```
BeadloomApp (Textual Application)
│
├── Screens
│   ├── DashboardScreen (main view)
│   │   ├── DebtGaugeWidget       ← DebtDataProvider
│   │   ├── GraphTreeWidget       ← GraphDataProvider
│   │   ├── LintPanelWidget       ← LintDataProvider
│   │   ├── ActivityWidget        ← ActivityDataProvider
│   │   └── StatusBarWidget       ← all providers
│   │
│   ├── ExplorerScreen (node deep-dive)
│   │   ├── NodeDetailPanel       ← GraphDataProvider
│   │   ├── DependencyPathPanel   ← WhyDataProvider
│   │   └── ContextPreviewPanel   ← ContextDataProvider
│   │
│   └── DocStatusScreen (documentation health)
│       └── DocHealthTable        ← SyncDataProvider
│
├── DataLayer (thin wrappers over existing APIs)
│   ├── GraphDataProvider     → graph storage (SQLite nodes, edges)
│   ├── LintDataProvider      → rule_engine.evaluate_all()
│   ├── SyncDataProvider      → engine.check_sync()
│   ├── DebtDataProvider      → debt_report.compute_debt_score()
│   ├── ActivityDataProvider  → git_activity.analyze_git_activity()
│   ├── WhyDataProvider       → why.analyze_node()
│   └── ContextDataProvider   → builder.build_context()
│
├── FileWatcher (background Worker)
│   ├── watches source dirs from graph config
│   ├── debounce 500ms
│   └── posts ReindexNeeded message → StatusBar badge
│
└── Overlays
    ├── SearchOverlay         ← FTS5 search
    └── HelpOverlay           ← keybinding reference
```

**Data providers** are thin read-only wrappers that:
1. Accept a `sqlite3.Connection` and `project_root`
2. Call existing infrastructure functions
3. Return typed dataclasses (existing ones — no new types)
4. Support `refresh()` for reactive updates after reindex

**Screens** follow Textual's `Screen` pattern:
- `push_screen()` / `pop_screen()` for navigation
- CSS layout per screen via `.tcss` files
- Each widget loads data on mount and on `refresh` event

### Changes

| File / Module | Change |
|---------------|--------|
| `pyproject.toml` | Bump `textual>=0.80`, ensure `watchfiles>=0.20` |
| `src/beadloom/tui/__init__.py` | Update `launch()` entry point |
| `src/beadloom/tui/app.py` | Rewrite: multi-screen app with bindings, Workers |
| `src/beadloom/tui/screens/` (new) | `dashboard.py`, `explorer.py`, `doc_status.py` |
| `src/beadloom/tui/widgets/` | Rewrite existing + add: `debt_gauge.py`, `graph_tree.py`, `lint_panel.py`, `activity.py`, `dependency_path.py`, `context_preview.py`, `doc_health.py` |
| `src/beadloom/tui/data_providers.py` (new) | All 7 data provider classes |
| `src/beadloom/tui/file_watcher.py` (new) | FileWatcher Worker |
| `src/beadloom/tui/styles/` | New TCSS files per screen |
| `src/beadloom/services/cli.py` | Rename `ui` → `tui`, add `--no-watch` flag |
| `tests/test_tui.py` | Rewrite: test all screens, widgets, providers |

### API Changes

**CLI:**
```
beadloom tui [--project DIR] [--no-watch]
```
- `--no-watch`: disable file watcher (for CI/testing)
- Old `beadloom ui` command kept as alias for backward compatibility

**No backend API changes** — all data providers use existing public functions.

### Keyboard Bindings

| Key | Context | Action |
|-----|---------|--------|
| `1` | Global | Switch to Dashboard screen |
| `2` | Global | Switch to Explorer screen |
| `3` | Global | Switch to Doc Status screen |
| `Tab` | Global | Cycle panel focus |
| `q` | Global | Quit |
| `?` | Global | Help overlay |
| `/` | Global | Search overlay (FTS5) |
| `r` | Global | Trigger reindex (background Worker) |
| `l` | Global | Run lint check |
| `s` | Global | Run sync-check |
| `g` | Doc panel | Generate doc skeleton |
| `S` | Global | Save snapshot |
| `Enter` | Graph tree | Expand/collapse or open detail |
| `d` | Node selected | Downstream dependents |
| `u` | Node selected | Upstream dependencies |
| `c` | Node selected | Context bundle preview |
| `o` | Node selected | Open in $EDITOR |

### Screen Layouts

**Dashboard (main):**
```
┌──────────────────────────────────────────────────────┐
│  beadloom tui — ProjectName              Debt: 23 ▲  │
├───────────────────────┬──────────────────────────────┤
│  Graph Tree           │  Activity + Lint             │
│  (left, 40%)          │  (right, 60%)                │
│                       │                              │
├───────────────────────┴──────────────────────────────┤
│  Node summary bar (selected node info)               │
├──────────────────────────────────────────────────────┤
│  [1]dash [2]explore [3]docs  [r]eindex [q]uit  ● ok  │
└──────────────────────────────────────────────────────┘
```

**Explorer (detail):**
```
┌──────────────────────────────────────────────────────┐
│  Explorer: context-oracle                            │
├───────────────────────┬──────────────────────────────┤
│  Node Detail          │  Dependencies / Context      │
│  (symbols, edges,     │  (why tree or ctx preview)   │
│   routes, tests)      │                              │
├───────────────────────┴──────────────────────────────┤
│  [u]pstream [d]ownstream [c]ontext [o]pen  [Esc]back│
└──────────────────────────────────────────────────────┘
```

**Doc Status:**
```
┌──────────────────────────────────────────────────────┐
│  Documentation Health — 73% covered, 4 stale         │
├──────────────────────────────────────────────────────┤
│  Node              Status    Doc Path     Reason     │
│  context-oracle    ● fresh   README.md    —          │
│  graph             ▲ stale   README.md    symbols    │
│  search            ✖ missing —            —          │
├──────────────────────────────────────────────────────┤
│  [g]enerate [p]olish [Esc]back                       │
└──────────────────────────────────────────────────────┘
```

## Alternatives Considered

### Option A: Extend current single-screen viewer
Add panels to the existing app.py without multi-screen architecture. Rejected: becomes unmanageable with 10+ widgets, no clear navigation, poor UX on small terminals.

### Option B: Use `blessed` or `urwid` instead of Textual
Rejected: Textual is already in the stack (built on Rich), has better testing (headless pilot), CSS-like layout, and active maintenance. Switching frameworks adds risk with no benefit.

### Option C: Build each panel as a separate CLI command with `--interactive`
Rejected: defeats the purpose of a persistent workspace. Users would still switch between commands.

## Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Textual API breaking changes (0.50→0.80) | Medium | Medium | Pin to >=0.80, test all existing TUI tests first |
| Large widget count slows startup | Low | Medium | Lazy-load data providers, render shell first |
| File watcher conflicts with existing `beadloom watch` | Low | Low | TUI watcher is internal (posts messages), CLI watcher is standalone |
| Terminal compatibility (SSH, tmux) | Low | Medium | Textual handles this natively; test with `--headless` |

## Open Questions

| # | Question | Decision |
|---|----------|----------|
| Q1 | Keep `beadloom ui` as alias or deprecate? | Decided: keep as alias, primary command is `beadloom tui` |
| Q2 | Textual-plotext for sparklines or custom Rich? | Decided: custom Rich renderables — avoid extra dependency |
| Q3 | Textual CSS in separate files or inline? | Decided: separate `.tcss` files per screen (Textual best practice) |
