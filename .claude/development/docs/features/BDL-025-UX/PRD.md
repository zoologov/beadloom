# PRD: BDL-025-UX — TUI UX Polish (12.10.8)

> **Status:** Approved
> **Created:** 2026-02-20

---

## Problem

After releasing the TUI (v1.8.0, BDL-025), dogfooding revealed several UX issues that reduce usability for both new and experienced users:

1. **Explorer Edges duplication** — The left panel "Edges" section shows raw edge list (outgoing/incoming) that largely duplicates the right panel "Upstream/Downstream" dependency tree. Two panels showing overlapping data wastes 50% of screen space.
2. **No screen descriptions** — New users don't understand what each screen does. Dashboard shows "Activity" bars but doesn't explain they represent git commit frequency. Doc Status shows "fresh/stale/missing" without explaining what triggers staleness.
3. **Inconsistent keybinding hints** — Explorer and Doc Status have action bars, but Dashboard has none. Users must guess that `1/2/3` switch screens, `r` triggers reindex, etc.
4. **Context Inspector no scroll** — The `ContextPreviewWidget` truncates at 2000 chars with no scroll, making long context bundles unreadable.

## Impact

- **New users** abandon the TUI because screens are confusing without descriptions
- **All users** miss available keyboard shortcuts on Dashboard
- **Developers** can't inspect full context bundles (the primary debugging use case)
- **Explorer users** see redundant data instead of richer code-level information

## Goals

- [ ] Replace Explorer Edges with grouped edge summary + code symbols from `code_indexer`
- [ ] Add brief purpose descriptions to all 3 screens (Dashboard, Explorer, Doc Status)
- [ ] Add contextual keybinding hints to Dashboard (matching Explorer/Doc Status pattern)
- [ ] Fix Context Inspector scroll to show full context bundle content

## Non-goals

- Redesigning screen layouts or navigation flow
- Adding new screens or widgets
- Changing the data provider layer or CLI commands
- Performance optimization of data loading

## User Stories

### US-1: Rich Explorer Detail
**As** a developer exploring a node, **I want** to see a concise edge summary and the node's code symbols, **so that** I get useful information instead of duplicated dependency data.

**Acceptance criteria:**
- [ ] Edges section replaced with "Connections" summary (e.g., "3 outgoing, 2 incoming" one-liner)
- [ ] New "Symbols" section shows top-level functions/classes from `code_indexer` with line numbers
- [ ] No duplication with right panel upstream/downstream view

### US-2: Screen Descriptions
**As** a new user, **I want** to see a brief explanation of what each screen shows, **so that** I can orient myself without reading docs.

**Acceptance criteria:**
- [ ] Dashboard: description explains graph tree, activity bars, lint/debt gauges
- [ ] Explorer: description explains node deep-dive with deps and context
- [ ] Doc Status: description explains doc coverage and freshness tracking

### US-3: Dashboard Keybinding Hints
**As** a user on the Dashboard, **I want** to see available keyboard shortcuts, **so that** I know what actions I can perform.

**Acceptance criteria:**
- [ ] Dashboard has action bar/footer matching Explorer/Doc Status pattern
- [ ] Shows screen-specific keys: `[Enter]explore  [1]dashboard  [2]explorer  [3]doc status  [r]eindex  [l]int`

### US-4: Scrollable Context Inspector
**As** a developer inspecting a context bundle, **I want** to scroll through the full content, **so that** I can see all sections of large bundles.

**Acceptance criteria:**
- [ ] Context Inspector widget has vertical scroll enabled
- [ ] Full context bundle displayed (no 2000-char truncation)
- [ ] Scroll position resets when switching nodes

## Acceptance Criteria (overall)

- [ ] All 4 sub-features implemented with tests
- [ ] Existing TUI tests pass (285+ tests)
- [ ] New tests cover: symbol rendering, screen descriptions, action bar content, scroll behavior
- [ ] `mypy --strict` and `ruff check` clean
- [ ] `beadloom lint --strict` — 0 violations
- [ ] Manual dogfooding confirms improved UX
