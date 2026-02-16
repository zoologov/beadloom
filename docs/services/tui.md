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
- `/` -- Focus search (focuses domain list for keyboard navigation)
- `r` -- Reindex (triggers `incremental_reindex`, then refreshes all panels)

### Widgets

#### DomainList

Left panel. Extends `OptionList`. Displays domains with doc coverage indicators (filled/open circle) and edge counts. Selecting or highlighting a domain loads its details into the right panel.

- Events: `DomainSelected(ref_id)`, `NodeSelected(ref_id)`
- `load_domains(conn)` -- loads domains from the `nodes` table, counts edges, checks doc coverage
- Responds to both `on_option_list_option_selected` (click/Enter) and `on_option_list_option_highlighted` (arrow keys)

#### NodeDetail

Right panel. Extends `Static`. Shows details for the selected node: `ref_id`, `kind`, `summary`, outgoing edges, incoming edges, docs (count + paths), sync status (stale docs).

- `show_node(conn, ref_id)` -- loads full info: node metadata, outgoing/incoming edges, docs, stale sync pairs
- `show_domain(conn, ref_id)` -- shows domain overview with child nodes (via `part_of` edges)

#### StatusBar

Bottom bar. Extends `Static`. Shows aggregate statistics: node count, edge count, doc count, documentation coverage percentage, and stale doc count.

- `load_stats(conn)` -- loads counts from DB and computes coverage percentage

### Data Flow

1. `on_mount`: `_refresh_data()` loads all panels from DB; auto-selects first domain to populate detail panel.
2. Domain selection: triggers `on_domain_list_domain_selected` -> `NodeDetail.show_node()`.
3. Domain highlight: also triggers `on_domain_list_domain_selected` -> `NodeDetail.show_node()`.
4. Node selection: triggers `on_domain_list_node_selected` -> `NodeDetail.show_node()`.
5. Reindex: `action_reindex` -> `incremental_reindex` -> `_refresh_data()`.
6. Search: `action_focus_search` -> focuses `DomainList` widget for keyboard navigation.

### Constraints

- Requires `textual` optional dependency (`beadloom[tui]`)
- Read-only database access (except reindex action)
- No network access -- fully local

## API

Module `src/beadloom/tui/app.py`:

- `BeadloomApp(db_path, project_root)` -- main Textual App

Source files in `src/beadloom/tui/`:

- `app.py` -- application class, keybindings, layout
- `widgets/domain_list.py` -- DomainList widget (extends OptionList)
- `widgets/node_detail.py` -- NodeDetail widget (extends Static)
- `widgets/status_bar.py` -- StatusBar widget (extends Static)

## Testing

TUI is tested via Textual's pilot testing framework in `tests/test_tui.py`.
