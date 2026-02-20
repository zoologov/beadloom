# TUI Dashboard

Beadloom TUI is built on Textual (>=0.80) and provides an interactive multi-screen terminal dashboard for browsing the architecture graph, monitoring debt, and checking documentation health.

## Specification

### Launch

```bash
beadloom tui [--project DIR] [--no-watch]
beadloom ui [--project DIR] [--no-watch]    # alias for backward compatibility
```

Requires optional dependency: `pip install beadloom[tui]` (installs `textual`).

- `--no-watch` -- disable file watcher (for CI/testing)

### Application: BeadloomApp

Main app class in `app.py`:

- Title: "Beadloom"
- CSS: `styles/app.tcss`
- Multi-screen architecture with 3 named screens: Dashboard, Explorer, Doc Status
- Opens SQLite in read-only mode (`?mode=ro`)
- Data providers initialized on mount
- DB connection managed via lifecycle (open on mount, close on unmount)
- File watcher started on mount when `no_watch=False`; cancelled on unmount

Global keybindings:

- `1` -- Switch to Dashboard screen
- `2` -- Switch to Explorer screen
- `3` -- Switch to Doc Status screen
- `q` -- Quit
- `?` -- Help overlay (shows all keybindings organized by context)
- `/` -- Search overlay (FTS5 search across nodes, with LIKE fallback)
- `r` -- Reindex (triggers `incremental_reindex`, refreshes providers)
- `l` -- Run lint check (shows notification with violation count)
- `s` -- Run sync-check (shows notification with stale count)
- `S` -- Save snapshot (shows "Snapshot saved" notification)
- `Tab` -- Cycle focus between panels

The app tracks the last selected node ref_id via `on_node_selected()` handler. When switching to Explorer via `2`, the screen is updated with the tracked ref_id. `open_explorer(ref_id)` provides programmatic navigation to the Explorer screen.

### Screens

#### DashboardScreen

Main overview screen with architecture health dashboard. Layout:

- Header bar: project title ("beadloom tui") + `DebtGaugeWidget` showing debt score with severity coloring
- Left panel (40%): `GraphTreeWidget` showing architecture hierarchy with doc status indicators
- Right panel (60%): `ActivityWidget` (per-domain git activity bars) + `LintPanelWidget` (violation counts and details)
- Node summary bar: shows selected node info (ref_id, kind, summary, source path) -- updated via `NodeSelected` message from GraphTreeWidget
- Status bar: `StatusBarWidget` with node/edge/doc/stale counts, watcher status, last action

Data is loaded from providers on mount via `_load_data()`. Supports `refresh_all_widgets()` for reactive updates. Handles `NodeSelected` messages from GraphTreeWidget to update the node summary bar with ref_id, kind, summary, and source path.

#### ExplorerScreen

Node deep-dive screen with detailed analysis of a selected architecture node. Layout:

- Header: "Explorer: {ref_id}" showing the current node being explored
- Left panel (50%): `NodeDetailPanel` showing ref_id, kind, summary, source path, edges, and doc status
- Right panel (50%): switchable between `DependencyPathWidget` (upstream/downstream) and `ContextPreviewWidget` (context bundle with token count)
- Action bar: keybinding hints

Keybindings:

- `d` -- show downstream dependents (default)
- `u` -- show upstream dependencies
- `c` -- show context bundle preview
- `o` -- open primary source file in `$EDITOR`
- `Esc` -- pop back to previous screen

Navigation: pressing `2` switches to Explorer with the last selected node's ref_id. `BeadloomApp.open_explorer(ref_id)` provides programmatic navigation. Node selection is tracked via `NodeSelected` messages at the app level.

Data loaded from providers on mount via `_load_data()`. Supports `refresh_all_widgets()` and `set_ref_id(ref_id)` for dynamic updates.

#### DocStatusScreen

Documentation health screen. Placeholder for BEAD-05 (doc health table).

### Dashboard Widgets

#### GraphTreeWidget (`widgets/graph_tree.py`)

Interactive tree widget showing the architecture graph hierarchy:

- Tree structure built from `part_of` edges: root -> domains -> features/services
- Each node label includes a doc status indicator and edge count badge
- Doc status indicators: fresh (green filled circle), stale (yellow triangle), missing (red X)
- Emits `NodeSelected` message when a tree node is selected
- `refresh_data(graph_provider, sync_provider)` for reactive updates
- Handles empty graph gracefully (shows "No nodes found")
- Nodes sorted by kind (service > domain > feature > other) then alphabetically

Custom message:

- `NodeSelected(ref_id: str)` -- emitted when a node is selected in the graph tree

#### DebtGaugeWidget (`widgets/debt_gauge.py`)

Displays architecture debt score with color-coded severity:

- Green (0-20): low debt
- Yellow (21-50): medium debt
- Red (51+): high debt
- Shows score number + severity label + direction arrow
- `refresh_data(score)` for reactive updates

#### LintPanelWidget (`widgets/lint_panel.py`)

Displays lint violation count and individual violations:

- Shows error/warning counts with icons
- Lists individual violations with rule name, affected node, and description
- Severity icons: error (heavy X), warning (warning sign), info (info sign)
- `refresh_data(violations)` for reactive updates

#### ActivityWidget (`widgets/activity.py`)

Displays per-domain git activity as progress bars:

- Shows domain name + activity level bar (filled/empty blocks)
- Color coding: green (>=70%), yellow (>=30%), dim (<30%)
- Activity level capped at 100% (based on commit count)
- `refresh_data(activities)` for reactive updates

#### StatusBarWidget (`widgets/status_bar.py`)

Bottom status bar showing health metrics:

- Node count, edge count, doc count, stale count
- Watcher status indicator with three states:
  - "watching" (green filled circle) -- watcher active, no pending changes
  - "changes detected (N)" (yellow filled circle) -- watcher detected N changed files
  - "watcher off" (dim empty circle) -- watcher disabled or watchfiles not installed
- Last action message (auto-dismisses on next data refresh)
- `refresh_data(node_count, edge_count, doc_count, stale_count)` for count updates
- `set_watcher_active(active)` -- sets "watching" or "watcher off" state
- `set_changes_detected(count)` -- sets "changes detected (N)" state
- `clear_changes()` -- reverts from changes-detected to "watching" state
- `set_last_action(message)` for transient action messages
- `show_notification(message, duration=3.0)` -- shows a notification that auto-dismisses after `duration` seconds using `set_timer()`
- State constants: `WATCHER_OFF`, `WATCHER_WATCHING`, `WATCHER_CHANGES`

### File Watcher (`file_watcher.py`)

Background file watcher using `watchfiles` (optional dependency) that monitors source directories discovered from the graph:

- `FileWatcherWorker` implemented as a Textual Worker (threaded)
- Monitors graph YAML dir (`.beadloom/_graph/`) and source dirs from `GraphDataProvider.get_source_paths()`
- 500ms debounce to avoid event spam
- Filters changes by watched extensions (`.py`, `.yml`, `.md`, `.ts`, etc.), skips temp/hidden files
- Posts `ReindexNeeded(changed_paths)` custom message to the app when relevant changes detected
- Graceful fallback when `watchfiles` is not installed (logs warning, watcher disabled)
- Started on `on_mount()` when `no_watch=False` (default)
- Clean shutdown via Worker cancellation on app unmount
- App handles `ReindexNeeded`: updates StatusBar to "changes detected (N)" badge
- Pressing `r` triggers reindex, refreshes all providers, clears the changes badge

Key functions:

- `start_file_watcher(app, project_root, source_paths)` -- returns `Worker` or `None`
- `_has_watchfiles()` -- checks if watchfiles is available via `importlib.util.find_spec`
- `_collect_watch_dirs(project_root, source_paths)` -- builds de-duplicated watch dir list
- `_filter_paths(raw_changes, project_root)` -- filters by extension, skips hidden/temp

Custom message:

- `ReindexNeeded(changed_paths: list[str])` -- posted when source files change

### Data Providers

Seven thin read-only wrappers over existing infrastructure APIs in `data_providers.py`:

- `GraphDataProvider` -- SQLite queries for nodes/edges: `get_nodes()`, `get_edges()`, `get_node(ref_id)`, `get_node_with_source(ref_id)`, `get_hierarchy()`, `get_edge_counts()`, `get_doc_ref_ids()`, `get_source_paths()`
- `LintDataProvider` -- wraps `rule_engine.load_rules()` + `evaluate_all()`: `get_violations()`, `get_violation_count()`
- `SyncDataProvider` -- wraps `engine.check_sync()`: `get_sync_results()`, `get_stale_count()`, `get_coverage()`
- `DebtDataProvider` -- wraps `debt_report.collect_debt_data()` + `compute_debt_score()`: `get_debt_report()`, `get_score()`
- `ActivityDataProvider` -- wraps `git_activity.analyze_git_activity()`: `get_activity()`
- `WhyDataProvider` -- wraps `why.analyze_node()`: `analyze(ref_id, reverse=False)`
- `ContextDataProvider` -- wraps `builder.build_context()` + `estimate_tokens()`: `get_context(ref_id)`, `estimate_tokens(text)`

Each provider takes `sqlite3.Connection` + `Path` (project_root) and supports `refresh()`.

### Explorer Widgets

#### NodeDetailPanel (`widgets/node_detail_panel.py`)

Scrollable panel showing detailed information about a selected node:

- ref_id, kind, summary
- Source path (or "no source path" if absent)
- Edges: outgoing and incoming edges with edge kinds
- Documentation status: documented (green) or missing (red)
- Uses `GraphDataProvider` for all data
- `set_node(ref_id)` for updating displayed node
- `set_provider(graph_provider)` for setting data source

#### DependencyPathWidget (`widgets/dependency_path.py`)

Widget showing upstream/downstream dependency trees using WhyDataProvider:

- Renders tree structure with connectors: node -> dependents/dependencies with edge types
- Shows impact summary: direct/transitive counts, stale doc count
- `show_upstream(ref_id)` -- show upstream dependencies
- `show_downstream(ref_id)` -- show downstream dependents
- `set_provider(why_provider)` for setting data source
- Shows "No dependencies found" when empty
- Handles missing nodes gracefully

#### ContextPreviewWidget (`widgets/context_preview.py`)

Widget showing context bundle preview with token estimation:

- Shows ref_id, estimated token count, character length
- Lists bundle keys
- Truncated preview of serialized context bundle (max 2000 chars)
- Uses `ContextDataProvider` for context bundle building and token estimation
- `show_context(ref_id)` for updating displayed context
- `set_provider(context_provider)` for setting data source

### Overlay Widgets

#### HelpOverlay (`widgets/help_overlay.py`)

Modal screen showing all keybindings organized by context:

- Sections: Global, Dashboard, Explorer, Doc Status
- Each section lists key + description in formatted table
- Activated by `?` key globally
- Dismissed by `Esc` key
- Uses `ModalScreen` for overlay behavior
- `build_help_text()` generates the formatted help text

#### SearchOverlay (`widgets/search_overlay.py`)

Modal screen for FTS5 search across architecture nodes:

- Text input field for search query
- Uses FTS5 full-text search when `search_index` table is populated; falls back to SQL LIKE on nodes table
- Shows results as numbered list with kind, ref_id, and snippet
- Enter on query: executes search; Enter again: navigates to first result
- Esc: dismisses overlay without navigation
- Activated by `/` key globally
- On result selection, calls `BeadloomApp.open_explorer(ref_id)` to navigate

Key functions:

- `_search_nodes(conn, query, limit=20)` -- search with FTS5 / LIKE fallback
- `_format_results(results)` -- format search results for display

### Legacy Widgets

The following widgets from the previous single-screen architecture still exist but are no longer imported by the app:

- `widgets/domain_list.py` -- DomainList widget (extends OptionList)
- `widgets/node_detail.py` -- NodeDetail widget (extends Static)

These will be replaced by new screen-specific widgets in later beads.

### Data Flow

1. `on_mount`: Opens DB, initializes 7 data providers, installs 3 screens, pushes DashboardScreen, starts file watcher (if enabled).
2. DashboardScreen `on_mount`: Loads debt score, activity, lint violations, and status bar counts from providers.
3. Screen switching: keys 1/2/3 call `action_switch_screen(name)` -> `switch_screen()`. Explorer screen receives tracked ref_id.
4. File watcher: background Worker posts `ReindexNeeded` -> status bar shows "changes detected (N)" badge.
5. Reindex: `action_reindex()` -> `incremental_reindex()` -> refresh all providers -> clear changes badge -> refresh screen widgets.
6. Lint: `action_lint()` -> `lint_provider.refresh()` -> notify count + status bar notification (auto-dismiss 3s).
7. Sync: `action_sync_check()` -> `sync_provider.refresh()` -> notify stale count + status bar notification (auto-dismiss 3s).
8. Snapshot: `action_save_snapshot()` -> "Snapshot saved" notification (placeholder) + status bar notification.
9. Help: `action_help()` -> push `HelpOverlay` modal screen.
10. Search: `action_search()` -> push `SearchOverlay` modal screen -> on result, navigate to Explorer.

### Constraints

- Requires `textual>=0.80` optional dependency (`beadloom[tui]`)
- Read-only database access (except reindex action)
- No network access -- fully local
- Data providers are read-only wrappers -- no new DB tables

## API

Module `src/beadloom/tui/__init__.py`:

- `launch(db_path, project_root, *, no_watch=False)` -- entry point

Module `src/beadloom/tui/app.py`:

- `BeadloomApp(db_path, project_root, *, no_watch=False)` -- main Textual App

Module `src/beadloom/tui/data_providers.py`:

- `GraphDataProvider`, `LintDataProvider`, `SyncDataProvider`, `DebtDataProvider`, `ActivityDataProvider`, `WhyDataProvider`, `ContextDataProvider`

Module `src/beadloom/tui/widgets/`:

- `GraphTreeWidget` -- interactive architecture hierarchy tree with doc status indicators
- `NodeSelected` -- custom message emitted on tree node selection
- `DebtGaugeWidget` -- debt score with severity coloring
- `LintPanelWidget` -- lint violation counts and details
- `ActivityWidget` -- per-domain git activity bars
- `StatusBarWidget` -- health metrics, watcher status, last action
- `NodeDetailPanel` -- node detail with ref_id, kind, summary, source, edges, doc status
- `DependencyPathWidget` -- upstream/downstream dependency tree visualization
- `ContextPreviewWidget` -- context bundle preview with token count
- `DocHealthTable` -- documentation health table with per-node status
- `HelpOverlay` -- modal help screen with all keybindings
- `SearchOverlay` -- modal search screen with FTS5/LIKE search

Source files in `src/beadloom/tui/`:

- `app.py` -- application class, keybindings, screen management, file watcher integration
- `data_providers.py` -- 7 data provider classes
- `file_watcher.py` -- FileWatcher Worker, ReindexNeeded message, watch helpers
- `screens/dashboard.py` -- DashboardScreen with all dashboard widgets
- `screens/explorer.py` -- ExplorerScreen with node detail, dependency path, context preview
- `screens/doc_status.py` -- DocStatusScreen (stub)
- `styles/app.tcss` -- app-level styles
- `styles/dashboard.tcss` -- dashboard screen styles (header, left/right panels, summary, status bar)
- `styles/explorer.tcss` -- explorer screen styles
- `styles/doc_status.tcss` -- doc status screen styles
- `widgets/activity.py` -- ActivityWidget (per-domain git activity)
- `widgets/debt_gauge.py` -- DebtGaugeWidget (debt score severity)
- `widgets/graph_tree.py` -- GraphTreeWidget (architecture hierarchy tree) + NodeSelected message
- `widgets/lint_panel.py` -- LintPanelWidget (violations display)
- `widgets/status_bar.py` -- StatusBarWidget (health metrics bar)
- `widgets/node_detail_panel.py` -- NodeDetailPanel (node detail display for explorer)
- `widgets/dependency_path.py` -- DependencyPathWidget (upstream/downstream tree)
- `widgets/context_preview.py` -- ContextPreviewWidget (context bundle preview)
- `widgets/doc_health.py` -- DocHealthTable (documentation health table)
- `widgets/help_overlay.py` -- HelpOverlay (modal keybinding reference)
- `widgets/search_overlay.py` -- SearchOverlay (modal FTS5/LIKE search)
- `widgets/domain_list.py` -- legacy DomainList widget
- `widgets/node_detail.py` -- legacy NodeDetail widget

## Testing

TUI is tested via Textual's pilot testing framework in `tests/test_tui.py`. Tests cover: all 7 data providers (including extended GraphDataProvider methods with `get_source_paths()`), app shell instantiation, screen switching (keys 1/2/3), CLI commands (`tui` and `ui`), launch function signature, all 5 dashboard widgets (GraphTreeWidget, DebtGaugeWidget, LintPanelWidget, ActivityWidget, StatusBarWidget), GraphTreeWidget hierarchy building, doc status indicators, NodeSelected message emission, empty graph handling, tree refresh, DashboardScreen composition and data loading, DocStatusScreen composition and data loading, file watcher (ReindexNeeded message, helper functions, start_file_watcher, watcher status states, app integration with no_watch flag, reindex clearing changes badge), ExplorerScreen (composition, header, action bar, keybindings d/u/c switching right panel, Esc pop, set_ref_id, empty ref_id, empty DB, open source action), NodeDetailPanel (render with/without ref_id, missing node, edges, doc status, set_node, set_provider), DependencyPathWidget (upstream/downstream rendering, missing node, no provider, show methods), ContextPreviewWidget (render with/without ref_id, token count, bundle keys, missing node, no provider), app-level NodeSelected tracking and open_explorer navigation, HelpOverlay (build_help_text sections/bindings, open/dismiss via ?/Esc, content widgets), SearchOverlay (_search_nodes with LIKE fallback, _format_results, open/dismiss via //Esc, input widget), StatusBarWidget notification (show_notification, _clear_notification, auto-dismiss via set_timer), keyboard actions (lint/sync/snapshot key notifications, all global bindings, explorer bindings, doc status bindings, save snapshot binding). Total: 207 tests.
