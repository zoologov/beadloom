# RFC: BDL-025-UX — TUI UX Polish (12.10.8)

> **Status:** Approved
> **Created:** 2026-02-20

---

## Overview

Four UX improvements to the Beadloom TUI discovered during v1.8.0 dogfooding. Each is an isolated widget/screen change with no cross-dependencies, enabling parallel development.

## Motivation

### Problem
The TUI shipped functional but with rough UX edges: duplicated data in Explorer, missing orientation for new users, inconsistent keyboard discoverability, and a truncated context inspector.

### Solution
Four targeted widget-level changes that improve information density, discoverability, and completeness without altering the screen architecture or data provider layer.

## Technical Context

### Constraints
- Python 3.10+, Textual framework
- Existing 7 data providers remain unchanged
- 285+ existing tests must continue passing
- `code_indexer.extract_symbols()` available for symbol data

### Affected Areas
- `tui` service — screens and widgets only
- No changes to CLI, MCP, graph, or infrastructure domains

## Proposed Solution

### BEAD-01: Explorer Node Detail — Edge Summary + Symbols (dev)

**Current:** `_render_node_detail()` in `node_detail_panel.py` renders a raw list of outgoing/incoming edges, duplicating the right panel upstream/downstream tree.

**Change:** Replace "Edges" section with two new sections:
1. **Connections** — one-line summary: `"3 outgoing (depends_on, touches_code), 2 incoming (part_of)"`
2. **Symbols** — list of top-level functions/classes from `code_indexer.extract_symbols()`, showing `kind`, `symbol_name`, `line_start`

**Data source:** `GraphDataProvider` already has `get_edges()`. For symbols, add a new method `get_symbols(ref_id)` to `GraphDataProvider` that:
1. Gets node source path via `get_node_with_source(ref_id)`
2. Calls `extract_symbols(project_root / source)` from `code_indexer`
3. Returns `list[dict]` with symbol data

**Rendering format:**
```
  Connections
  → 3 outgoing: depends_on(2), touches_code(1)
  ← 2 incoming: part_of(1), depends_on(1)

  Symbols (12)
  ƒ extract_symbols        :42
  ƒ _parse_annotations     :87
  C CodeIndexer            :15
  ƒ supported_extensions   :120
```

### BEAD-02: Screen Descriptions (dev)

**Change:** Add a 1-line description Label below each screen header:

| Screen | Description text |
|--------|-----------------|
| Dashboard | `"Architecture overview: graph structure, git activity, lint & debt health"` |
| Explorer | `"Node deep-dive: detail, dependencies, context bundle"` |
| Doc Status | `"Documentation health: coverage, freshness, staleness reasons"` |

**Implementation:** Add a `Label(id="screen-description")` with `classes="screen-desc"` in each screen's `compose()`. Style via shared CSS rule: dim color, italic, 1 line height, bottom border.

### BEAD-03: Dashboard Action Bar (dev)

**Current:** Dashboard has no action bar. Explorer has `[u]pstream [d]ownstream [c]ontext [o]pen [Esc]back`. Doc Status has `[g]enerate [p]olish [Esc]back`.

**Change:** Add action bar Label to Dashboard's `compose()`:
```
[Enter]explore  [r]eindex  [l]int  [s]ync-check  [S]napshot  [?]help
```

**Implementation:** Same pattern as Explorer/Doc Status — `Label(id="dashboard-action-bar")` docked to bottom via CSS. Uses existing global bindings already defined in `app.py`.

### BEAD-04: Context Inspector Scroll Fix (dev)

**Current:** `ContextPreviewWidget` has `overflow-y: auto` CSS but truncates content at 2000 chars in Python code before rendering.

**Change:**
1. Remove the 2000-char truncation limit in `ContextPreviewWidget.show_context()` / `render()`
2. Verify CSS `overflow-y: auto` works (already set in `explorer.tcss`)
3. Reset scroll position to top when `show_context()` is called with new ref_id via `self.scroll_home()`

### Changes Summary

| File / Module | Change |
|---------------|--------|
| `tui/widgets/node_detail_panel.py` | Replace Edges section with Connections summary + Symbols list |
| `tui/data_providers.py` | Add `GraphDataProvider.get_symbols(ref_id)` method |
| `tui/screens/dashboard.py` | Add description label + action bar |
| `tui/screens/explorer.py` | Add description label |
| `tui/screens/doc_status.py` | Add description label |
| `tui/styles/dashboard.tcss` | Style for description + action bar |
| `tui/styles/explorer.tcss` | Style for description |
| `tui/styles/doc_status.tcss` | Style for description |
| `tui/widgets/context_preview.py` | Remove 2000-char truncation, add `scroll_home()` |

### API Changes

New public method on `GraphDataProvider`:
```python
def get_symbols(self, ref_id: str) -> list[dict[str, object]]:
    """Get code symbols for a node's source file."""
```

## Alternatives Considered

### Option A: Keep Edges + add Symbols below
Keep full edge list and add symbols underneath. Rejected: makes left panel too long, duplicates right panel data.

### Option B: Replace Static with RichLog for Context Inspector
Use Textual's `RichLog` widget instead of `Static` for the context preview. Rejected: would require more refactoring for minimal gain — removing truncation + existing scroll CSS is sufficient.

## Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| `extract_symbols` slow on large files | Low | Low | Cache in provider, lazy load |
| Scroll not working on Static widget | Low | Med | Textual Static with `overflow-y: auto` is tested pattern |
| Action bar text too long for narrow terminals | Low | Low | Use abbreviated labels |

## Open Questions

| # | Question | Decision |
|---|----------|----------|
| Q1 | Should symbols show nested methods or only top-level? | Decided: top-level only (matches `extract_symbols` output) |
| Q2 | Should description be hideable via toggle? | Decided: no — always visible, 1 line is negligible overhead |
