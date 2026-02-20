# RFC: BDL-028 — TUI Bug Fixes: Threading, Explorer Dependencies, Screen State

> **Status:** Approved
> **Created:** 2026-02-20

---

## Summary

Fix 3 open TUI bugs (#58-60) affecting quit stability, Explorer dependency display, and Explorer screen state management. All bugs are in the `tui/` service with no downstream dependents — changes are safe and isolated.

## Technical Analysis

### Bug #58: Threading Error on Quit

**Root cause:** File watcher worker thread (`file_watcher.py:162`) calls `app.post_message(ReindexNeeded(...))` during shutdown. `on_unmount()` in `app.py:190` calls `worker.cancel()` but doesn't wait for the thread to exit. The watcher thread may still have buffered file changes from `watch()` that get processed after the event loop is closing.

**Fix approach:** Wrap `post_message()` in the file watcher's event callback with a try-except that silently catches `RuntimeError` during interpreter shutdown. Additionally, add a `_shutting_down` flag checked in the watch loop before calling `post_message()`.

**Files:** `src/beadloom/tui/file_watcher.py`, `src/beadloom/tui/app.py`

### Bug #59: Explorer Downstream Dependents Always Empty

**Root cause:** In the `DependencyPathWidget.show_downstream()` method, the downstream dependents data flow from `why.py` through the TUI rendering pipeline has a disconnect. The `analyze_node()` function in `why.py` returns correct data when called directly via CLI, but the TUI widget's rendering doesn't properly display the results. The issue is in how the widget processes and renders the downstream tree data — likely the tree is built but the widget content is not updated or is overwritten by a subsequent refresh.

**Fix approach:** Trace the exact data flow in `DependencyPathWidget.show_downstream()` — verify the query returns data, verify the widget receives it, verify the render method displays it. Fix the specific break in the pipeline (likely a missing `refresh()` call or incorrect widget content assignment).

**Files:** `src/beadloom/tui/widgets/dependency_path.py`, `src/beadloom/tui/screens/explorer.py`

### Bug #60: Explorer Broken After Early Empty Visit

**Root cause:** `app.open_explorer()` calls `_safe_switch_screen(SCREEN_EXPLORER)` then `explorer.set_ref_id(ref_id)` sequentially. But `_safe_switch_screen()` is not awaited — `set_ref_id()` fires `_load_data()` which calls `query_one()` on widgets that aren't fully composed yet. Exception handlers silently swallow the errors. On subsequent visits, the Explorer never recovers because it cached the empty initial state.

**Fix approach:** Use Textual's `on_screen_resume()` lifecycle hook on `ExplorerScreen` to reload data when the screen becomes active. This way `set_ref_id()` stores the ref_id, and the actual data load happens when the screen is ready. Remove the race between screen transition and data loading.

**Files:** `src/beadloom/tui/screens/explorer.py`, `src/beadloom/tui/app.py`

## Architecture

No new modules. All changes are within existing TUI files:

```
src/beadloom/tui/
├── app.py                          # #58: shutdown flag, #60: open_explorer timing
├── file_watcher.py                 # #58: graceful post_message
├── screens/
│   └── explorer.py                 # #59: dependency rendering, #60: on_screen_resume
└── widgets/
    └── dependency_path.py          # #59: show_downstream fix
```

## Testing Strategy

- Each bug fix gets dedicated regression tests
- Test #58: verify clean shutdown (mock file watcher)
- Test #59: verify downstream dependents display with known graph data
- Test #60: verify Explorer works when visited before/after node selection

## Risks

- **Low risk**: TUI is a leaf service with 0 downstream dependents
- **Regression risk**: Existing 234 TUI tests provide safety net
- **Threading (#58)**: Silent catch may hide real errors — mitigate with logging at DEBUG level

## Alternatives Considered

- **#58**: Blocking join after cancel — rejected, may hang if watcher thread is stuck in `watch()` poll
- **#60**: Awaiting `_safe_switch_screen` — rejected, Textual's `switch_screen` is synchronous; the issue is widget composition timing, not screen switching
