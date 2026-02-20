# TUI — Interactive Architecture Dashboard

Beadloom TUI is a multi-screen terminal application built on Textual (>=0.80) for browsing the architecture graph, monitoring debt, running lint checks, and tracking documentation health -- all from a single keyboard-driven interface.

## Prerequisites

The TUI requires the optional `tui` dependency group:

```bash
pip install beadloom[tui]
# or
uv tool install beadloom[tui]
```

This installs `textual>=0.80` and `watchfiles>=0.20`.

## Launch

```bash
beadloom tui [--project DIR] [--no-watch]
beadloom ui  [--project DIR] [--no-watch]    # backward-compatible alias
```

| Flag | Description |
|------|-------------|
| `--project DIR` | Project root directory (default: current directory) |
| `--no-watch` | Disable the file watcher (useful for CI or testing) |

The TUI opens the SQLite database in read-only mode and initializes 7 data providers before displaying the Dashboard screen.

## Screens

The TUI has three screens, accessible via the `1`, `2`, and `3` keys. Each screen includes a description label below its header explaining the screen's purpose, and an action bar at the bottom with keybinding hints for available actions.

### Dashboard (key: 1)

Main overview showing architecture health at a glance.

```
+------------------------------------------------------+
|  beadloom tui -- ProjectName              Debt: 23 ^  |
+------------------------------------------------------+
|  Architecture overview: graph structure, git ...      |
+------------------------+-----------------------------+
|  Graph Tree            |  Activity + Lint            |
|  (left, 40%)           |  (right, 60%)               |
|                        |                             |
+------------------------+-----------------------------+
|  Node summary bar (selected node info)                |
+------------------------------------------------------+
|  [1]dash [2]explore [3]docs  [r]eindex [q]uit  * ok   |
+------------------------------------------------------+
|  [Enter]explore [r]eindex [l]int [s]ync-check ...     |
+------------------------------------------------------+
```

**Widgets:**

- **DebtGaugeWidget** -- Debt score with severity coloring (green 0-20, yellow 21-50, red 51+) and direction arrow.
- **Screen description** -- A label describing the screen purpose ("Architecture overview: graph structure, git activity, lint & debt health").
- **GraphTreeWidget** -- Interactive tree built from `part_of` edges showing the architecture hierarchy. Each node label includes a doc status indicator (green circle = fresh, yellow triangle = stale, red X = missing) and an edge count badge. Nodes are sorted by kind (service > domain > feature) then alphabetically. Selecting a node emits a `NodeSelected` message that updates the summary bar.
- **ActivityWidget** -- Per-domain git activity displayed as colored progress bars (green >=70%, yellow >=30%, dim <30%).
- **LintPanelWidget** -- Violation counts with severity icons (error, warning, info) and individual violation details (rule name, affected node, description).
- **StatusBarWidget** -- Node count, edge count, doc count, stale count, watcher status indicator, and last action message. Supports auto-dismissing notifications.
- **Action bar** -- Keybinding hints at the bottom of the screen showing available actions: `[Enter]explore`, `[r]eindex`, `[l]int`, `[s]ync-check`, `[S]napshot`, `[?]help`.

### Explorer (key: 2)

Deep-dive into a selected architecture node.

```
+------------------------------------------------------+
|  Explorer: context-oracle                             |
+------------------------------------------------------+
|  Node deep-dive: detail, dependencies, context bundle |
+------------------------+-----------------------------+
|  Node Detail           |  Dependencies / Context     |
|  (connections, symbols)|  (why tree or ctx preview)  |
|                        |                             |
+------------------------+-----------------------------+
|  [u]pstream [d]ownstream [c]ontext [o]pen  [Esc]back  |
+------------------------------------------------------+
```

The Explorer screen loads the node selected on the Dashboard (tracked via `NodeSelected` messages at the app level). You can also navigate directly via `BeadloomApp.open_explorer(ref_id)`.

**Widgets:**

- **Screen description** -- A label describing the screen purpose ("Node deep-dive: detail, dependencies, context bundle").
- **NodeDetailPanel** -- Shows ref_id, kind, summary, source path, a Connections summary (outgoing/incoming edge counts grouped by edge kind), a Symbols list (top-level functions and classes from the code indexer with kind glyphs and line numbers), and documentation status (documented or missing).
- **DependencyPathWidget** -- Renders upstream or downstream dependency trees with connectors, edge types, and an impact summary (direct/transitive counts, stale doc count). Toggle between `u`pstream and `d`ownstream views.
- **ContextPreviewWidget** -- Shows the context bundle for a node with estimated token count, character length, bundle keys, and the full bundle content. The widget supports vertical scrolling via `overflow-y: auto` for large context bundles.

### Doc Status (key: 3)

Documentation health overview with per-node status tracking.

```
+------------------------------------------------------+
|  Documentation Health -- 73% covered, 4 stale         |
+------------------------------------------------------+
|  Documentation health: coverage, freshness, ...       |
+------------------------------------------------------+
|  Node              Status    Doc Path     Reason      |
|  context-oracle    * fresh   README.md    --          |
|  graph             ^ stale   README.md    symbols     |
|  search            x missing --           --          |
+------------------------------------------------------+
|  [g]enerate  [p]olish  [Esc]back                      |
+------------------------------------------------------+
```

**Widgets:**

- **Screen description** -- A label describing the screen purpose ("Documentation health: coverage, freshness, staleness reasons").
- **DocHealthTable** -- DataTable with columns: Node, Status (indicator + label), Doc Path, Reason. Rows are sorted: stale first, then missing, then fresh. Color-coded by status. Supports row selection for generate/polish actions.
- **Action bar** -- Keybinding hints at the bottom showing available actions: `[g]enerate`, `[p]olish`, `[Esc]back`.

## Keyboard Bindings

### Global (available on all screens)

| Key | Action |
|-----|--------|
| `1` | Switch to Dashboard |
| `2` | Switch to Explorer |
| `3` | Switch to Doc Status |
| `Tab` | Cycle panel focus |
| `q` | Quit |
| `?` | Help overlay (keybinding reference) |
| `/` | Search overlay (FTS5 search) |
| `r` | Trigger reindex (runs `incremental_reindex`, refreshes all providers) |
| `l` | Run lint check (shows violation count notification) |
| `s` | Run sync-check (shows stale count notification) |
| `S` | Save snapshot (placeholder) |

### Dashboard

| Key | Action |
|-----|--------|
| `Enter` | Expand/collapse tree node or open detail |

### Explorer

| Key | Action |
|-----|--------|
| `d` | Show downstream dependents |
| `u` | Show upstream dependencies |
| `c` | Show context bundle preview |
| `o` | Open primary source file in `$EDITOR` |
| `Esc` | Return to previous screen |

### Doc Status

| Key | Action |
|-----|--------|
| `g` | Generate doc skeleton for selected node |
| `p` | View polish data for selected node |
| `Esc` | Return to previous screen |

## Overlays

### Search Overlay (`/`)

Modal screen for FTS5 full-text search across architecture nodes. When the `search_index` table is populated, search uses FTS5; otherwise it falls back to SQL LIKE matching on the `nodes` table. Results are displayed as a numbered list with kind, ref_id, and snippet. Press Enter to search, Enter again to navigate to the first result, or Esc to dismiss.

### Help Overlay (`?`)

Modal screen showing all keybindings organized by context (Global, Dashboard, Explorer, Doc Status). Dismissed with Esc.

## File Watcher

The TUI includes a background file watcher powered by `watchfiles` (optional dependency). It monitors:

- The graph YAML directory (`.beadloom/_graph/`)
- All source directories discovered from `GraphDataProvider.get_source_paths()`

**Behavior:**

- 500ms debounce window to avoid event spam
- Filters by watched extensions: `.py`, `.yml`, `.yaml`, `.md`, `.ts`, `.tsx`, `.js`, `.jsx`, `.go`, `.rs`
- Skips temporary files (`~` prefix, `.tmp` suffix) and hidden directories (except `.beadloom`)
- Posts `ReindexNeeded` message with changed paths to the app
- Status bar shows "changes detected (N)" badge when files change
- Pressing `r` triggers reindex, refreshes all providers, and clears the badge

**Disable:** Use `--no-watch` to run without the file watcher. If `watchfiles` is not installed, the watcher is disabled gracefully with a log warning.

## Architecture

### Data Flow

```
BeadloomApp
  |-- on_mount: open DB -> init providers -> install screens -> push Dashboard -> start watcher
  |
  Screens
  |-- DashboardScreen.on_mount -> load debt, activity, lint, graph, status bar
  |-- ExplorerScreen.set_ref_id -> load node detail, dependencies, context
  |-- DocStatusScreen.on_mount -> compute doc rows, coverage stats
  |
  Data Providers (thin read-only wrappers)
  |-- GraphDataProvider    -> SQLite: nodes, edges, hierarchy, doc_ref_ids, source_paths
  |-- LintDataProvider     -> rule_engine.load_rules() + evaluate_all()
  |-- SyncDataProvider     -> engine.check_sync()
  |-- DebtDataProvider     -> debt_report.collect_debt_data() + compute_debt_score()
  |-- ActivityDataProvider -> git_activity.analyze_git_activity()
  |-- WhyDataProvider      -> why.analyze_node() (on-demand per ref_id)
  |-- ContextDataProvider  -> builder.build_context() + estimate_tokens() (on-demand)
  |
  FileWatcherWorker (threaded Textual Worker)
  |-- watches source dirs from graph
  |-- debounce 500ms
  |-- posts ReindexNeeded -> StatusBar badge
```

### Module Structure

Each provider accepts `sqlite3.Connection` and `Path` (project_root), supports `refresh()` for reactive updates. Screens follow Textual's `Screen` pattern with `push_screen()`/`pop_screen()` navigation. CSS layout is defined in separate `.tcss` files per screen.

```
src/beadloom/tui/
  __init__.py             -- launch() entry point
  app.py                  -- BeadloomApp: screens, bindings, providers, watcher
  data_providers.py       -- 7 data provider classes
  file_watcher.py         -- FileWatcherWorker, ReindexNeeded message
  screens/
    dashboard.py          -- DashboardScreen
    explorer.py           -- ExplorerScreen
    doc_status.py         -- DocStatusScreen
  widgets/
    graph_tree.py          -- GraphTreeWidget + NodeSelected message
    debt_gauge.py          -- DebtGaugeWidget
    lint_panel.py          -- LintPanelWidget
    activity.py            -- ActivityWidget
    status_bar.py          -- StatusBarWidget
    node_detail_panel.py   -- NodeDetailPanel
    dependency_path.py     -- DependencyPathWidget
    context_preview.py     -- ContextPreviewWidget
    doc_health.py          -- DocHealthTable + compute helpers
    help_overlay.py        -- HelpOverlay (ModalScreen)
    search_overlay.py      -- SearchOverlay (ModalScreen)
  styles/
    app.tcss               -- app-level styles
    dashboard.tcss         -- dashboard layout
    explorer.tcss          -- explorer layout
    doc_status.tcss        -- doc status layout
```

## Constraints

- Requires `textual>=0.80` optional dependency (`beadloom[tui]`)
- Read-only database access (except reindex action which writes)
- No network access -- fully local
- Data providers are read-only wrappers -- no new DB tables
- No built-in LLM calls (agent-native principle)

## API

Module `src/beadloom/tui/__init__.py`:

- `launch(db_path, project_root, *, no_watch=False)` -- entry point

Module `src/beadloom/tui/app.py`:

- `BeadloomApp(db_path, project_root, *, no_watch=False)` -- main Textual App

Module `src/beadloom/tui/data_providers.py`:

- `GraphDataProvider` -- `get_nodes()`, `get_edges()`, `get_node(ref_id)`, `get_node_with_source(ref_id)`, `get_hierarchy()`, `get_edge_counts()`, `get_doc_ref_ids()`, `get_source_paths()`, `get_symbols(ref_id)`
- `LintDataProvider` -- `get_violations()`, `get_violation_count()`
- `SyncDataProvider` -- `get_sync_results()`, `get_stale_count()`, `get_coverage()`
- `DebtDataProvider` -- `get_debt_report()`, `get_score()`
- `ActivityDataProvider` -- `get_activity()`
- `WhyDataProvider` -- `analyze(ref_id, reverse=False)`
- `ContextDataProvider` -- `get_context(ref_id)`, `estimate_tokens(text)`

Module `src/beadloom/tui/file_watcher.py`:

- `start_file_watcher(app, project_root, source_paths, *, debounce_ms=500)` -- returns `Worker` or `None`
- `ReindexNeeded(changed_paths)` -- custom Textual message

## Testing

TUI tests use Textual's headless pilot framework (`app.run_test()`).

```bash
uv run pytest tests/test_tui.py -v
```

Tests cover all 7 data providers, app shell instantiation, screen switching, CLI commands (`tui` and `ui`), all dashboard and explorer widgets, file watcher integration, overlays, keyboard actions, and status bar notifications. Total: 285 tests.
