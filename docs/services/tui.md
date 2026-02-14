# TUI Dashboard

Beadloom TUI is built on Textual and provides an interactive terminal dashboard for browsing the architecture graph.

## Specification

### Launch

```bash
beadloom ui [--project DIR]
```

Requires optional dependency: `pip install beadloom[tui]` (installs `textual`).

### Application: BeadloomApp

Main app class in `app.py`:

- Title: "Beadloom"
- CSS: `styles/app.tcss`
- Layout: Header + Horizontal(DomainList | NodeDetail) + StatusBar + Footer
- Opens SQLite in read-only mode (`?mode=ro`)

Keybindings:

- `q` -- Quit
- `/` -- Focus search
- `r` -- Reindex (triggers `incremental_reindex`, then refreshes all panels)

### Widgets

#### DomainList

Left panel. Displays domains as an `OptionList`. Selecting a domain loads its details into the right panel.

- Events: `DomainSelected`, `NodeSelected`
- `load_domains(conn)` -- loads domains from the `nodes` table

#### NodeDetail

Right panel. Shows details for the selected node: `ref_id`, `kind`, `summary`, edges, docs, sync status.

- `show_node(conn, ref_id)` -- loads all info for a node

#### StatusBar

Bottom bar with aggregate statistics: node count, edge count, doc count, symbol count.

- `load_stats(conn)` -- loads counts from DB

### Data Flow

1. `on_mount`: `_refresh_data()` loads all panels from DB.
2. Domain selection: triggers `on_domain_list_domain_selected` -> `NodeDetail.show_node()`.
3. Node selection: triggers `on_domain_list_node_selected` -> `NodeDetail.show_node()`.
4. Reindex: `action_reindex` -> `incremental_reindex` -> `_refresh_data()`.

### Constraints

- Requires `textual` optional dependency (`beadloom[tui]`)
- Read-only database access (except reindex action)
- No network access -- fully local

## API

Module `src/beadloom/tui/app.py`:

- `BeadloomApp(db_path, project_root)` -- main Textual App

Source files in `src/beadloom/tui/`:

- `app.py` -- application class, keybindings, layout
- `widgets/domain_list.py` -- DomainList widget
- `widgets/node_detail.py` -- NodeDetail widget
- `widgets/status_bar.py` -- StatusBar widget

## Testing

TUI is tested via Textual's pilot testing framework in `tests/test_tui.py`.
