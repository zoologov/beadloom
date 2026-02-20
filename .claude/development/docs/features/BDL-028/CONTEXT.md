# CONTEXT: BDL-028 — TUI Bug Fixes (Phase 12.13)

> **Status:** Done
> **Created:** 2026-02-20
> **Last updated:** 2026-02-20

---

## Phase

Phase 12.13 — TUI stabilization round 3

## Scope

Fix 3 open UX issues (#58-60) in the TUI service. No new features, no architecture changes.

## Related Files

- `src/beadloom/tui/app.py` — main TUI application, quit/shutdown, screen switching
- `src/beadloom/tui/file_watcher.py` — watchfiles background worker
- `src/beadloom/tui/screens/explorer.py` — Explorer screen with dependency display
- `src/beadloom/tui/widgets/dependency_path.py` — DependencyPathWidget
- `src/beadloom/tui/data_providers.py` — data layer for TUI screens
- `tests/test_tui.py` — main TUI test file
- `tests/tui/` — TUI test subdirectory

## Decisions

- **#58**: Use try-except + shutdown flag (not blocking join) to avoid potential hangs
- **#59**: Fix the rendering pipeline break (not the data layer — `analyze_node()` is correct)
- **#60**: Use `on_screen_resume` lifecycle hook (not await-based) for reliable screen state

## Code Standards

- Stack: Python 3.10+, Textual (TUI framework), SQLite (WAL)
- Tests: pytest + pytest-cov (>=80% coverage)
- Linter: ruff (lint + format)
- Types: mypy --strict
- TDD: write test first, then fix

## Dependencies

- No external dependencies
- TUI is a leaf service (0 downstream dependents)
- Changes are isolated to `tui/` package
