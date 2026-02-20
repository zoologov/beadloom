# BRIEF: BDL-029 — TUI UX Improvements Phase 12.14

> **Type:** task
> **Status:** Approved
> **Created:** 2026-02-21

---

## Problem

Four UX issues discovered during TUI dogfooding session (BDL-028 diagnosis). Additionally, BDL-UX-Issues.md contains stale descriptions for bugs #58-60 that reference dead code from the original commit before amend.

Issues:
1. Domain nodes in graph tree cannot be opened directly in Explorer — Enter expands the tree, no shortcut to navigate
2. "tui" node shows expandable triangle icon but has no children at cold start (fixes after reindex)
3. `[N]` edge count numbers next to tree nodes have no legend or tooltip — users don't understand what they mean
4. Esc (Back) from Explorer leads to dead empty screen; pressing hotkeys 2/3 from there crashes with `ScreenStackError: Can't pop screen`

## Solution

### BEAD-01: Explorer direct navigation key (feature)
Add `e` key binding to open any highlighted node in Explorer, regardless of whether it has children. This bypasses the Enter-expands-tree behavior for domain nodes.

### BEAD-02: Fix triangle icon for childless nodes (bug)
Investigate why "tui" node shows as expandable at cold start despite having no children in the hierarchy. Fix the tree building logic to correctly determine expandability.

### BEAD-03: Edge count legend in tree (feature)
Add a tooltip or legend explaining what `[N]` means next to tree nodes. Options: rename to `[N edges]`, add help text, or show on hover.

### BEAD-04: Fix Esc back navigation crash (bug)
`action_go_back()` in ExplorerScreen calls `pop_screen()` which fails when there's only one screen on the stack (after `switch_screen` navigation). Fix: use `switch_screen` to Dashboard instead of `pop_screen`, or guard against empty stack.

### BEAD-05: Update BDL-UX-Issues.md (tech-writer)
Update descriptions for bugs #58-60 to reflect actual fixes (after amend). Add new issues #61-64 for the four items above.

## Beads

| ID | Name | Type | Priority | Depends On | Agent | Status |
|----|------|------|----------|------------|-------|--------|
| BEAD-01 | Explorer direct navigation key | feature | P2 | - | /dev, /test | Pending |
| BEAD-02 | Fix triangle icon for childless nodes | bug | P2 | - | /dev, /test | Pending |
| BEAD-03 | Edge count legend in tree | feature | P2 | - | /dev, /test | Pending |
| BEAD-04 | Fix Esc back navigation crash | bug | P1 | - | /dev, /test | Pending |
| BEAD-05 | Update BDL-UX-Issues.md | task | P2 | 01,02,03,04 | /tech-writer | Pending |
| BEAD-06 | Test verification | task | P2 | 01,02,03,04 | /test | Pending |
| BEAD-07 | Code review | task | P2 | 06 | /review | Pending |

## Acceptance Criteria

- [ ] `e` key opens Explorer for any highlighted node (including domain nodes with children)
- [ ] "tui" node does not show expandable triangle when it has no children
- [ ] Edge counts have visible explanation in UI (legend, label, or help text)
- [ ] Esc from Explorer returns to Dashboard without crash
- [ ] Pressing hotkeys after Esc does not cause ScreenStackError
- [ ] BDL-UX-Issues.md bugs #58-60 have accurate descriptions matching amend commit
- [ ] BDL-UX-Issues.md has new issues #61-64 for the four UX items
- [ ] All existing 2487 tests pass + new regression tests added
- [ ] `beadloom lint --strict` clean
- [ ] `beadloom sync-check` clean
