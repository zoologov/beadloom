# PRD: BDL-028 — TUI Bug Fixes: Threading, Explorer Dependencies, Screen State (Phase 12.13)

> **Status:** Done
> **Created:** 2026-02-20

---

## Problem

Three open UX issues (#58-60) remain after the BDL-025/027 TUI stabilization rounds. All affect the TUI's reliability and user trust:

1. **#58 [MEDIUM]**: Threading error on quit — `RuntimeError: cannot schedule new futures after interpreter shutdown` in the `watchfiles` background worker. Non-blocking but leaves error output in terminal after exit.
2. **#59 [HIGH]**: Explorer downstream dependents always empty — pressing `d` shows "No dependencies found" even for nodes with 9+ downstream dependents in CLI. The `analyze_node()` function returns correct data; bug is in the TUI rendering pipeline (likely race condition in `DependencyPathWidget.show_downstream()`).
3. **#60 [HIGH]**: Explorer broken after early empty visit — navigating to Explorer before selecting any node on Dashboard causes the Explorer's left panel (`NodeDetailPanel`) to never update on subsequent node selections. Root cause: `app.open_explorer()` calls `switch_screen` + `set_ref_id` synchronously, but the repaint is lost during screen transition.

## Impact

- **#59 + #60**: Two HIGH bugs render the Explorer screen partially non-functional. Users who try to explore dependencies — a core workflow — hit dead ends. This undermines the value proposition of the TUI as an architecture workstation.
- **#58**: Leaves a Python traceback in the terminal after every quit, giving the impression of a crash even though the app exited cleanly.

## Goals

- [ ] Fix threading error on quit (#58) — clean shutdown with no terminal error output
- [ ] Fix downstream dependents display (#59) — `d` key shows correct dependents matching `beadloom why` CLI output
- [ ] Fix Explorer state after early empty visit (#60) — Explorer updates correctly regardless of visit order

## Non-goals

- TUI feature additions or new screens
- Performance optimizations beyond what's needed for the fixes
- Refactoring TUI architecture

## User Stories

### US-1: Clean Quit
**As** a user, **I want** pressing `q` to exit the TUI cleanly, **so that** my terminal shows no error tracebacks after exit.

**Acceptance criteria:**
- [ ] No `RuntimeError` or `watchfiles` errors appear after quit
- [ ] File watcher thread is cancelled before event loop closes

### US-2: Working Downstream Dependents
**As** a developer, **I want** pressing `d` in Explorer to show downstream dependents, **so that** I can understand what depends on the selected node.

**Acceptance criteria:**
- [ ] Downstream dependents list matches `beadloom why <ref-id>` output
- [ ] Works for nodes with both 0 and many dependents

### US-3: Resilient Explorer Navigation
**As** a user, **I want** Explorer to work correctly regardless of whether I visit it before or after selecting a node on Dashboard, **so that** navigation order doesn't break the UI.

**Acceptance criteria:**
- [ ] Explorer left panel updates when returning from Dashboard with a selected node
- [ ] Works on first visit, repeat visits, and after screen switches
- [ ] No need to restart the app
