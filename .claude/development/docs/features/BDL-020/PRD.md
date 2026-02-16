# PRD: BDL-020 — Source Coverage Hierarchy Fix

> **Status:** APPROVED
> **Date:** 2026-02-17

---

## Problem

`beadloom sync-check` reports 12 false-positive `untracked_files` entries across 3 ref_ids (context-oracle, infrastructure, tui). These are caused by two issues:

1. **Annotation mismatches** — 3 files annotated to child feature ref_ids instead of parent domain, 1 file missing annotation entirely
2. **No hierarchy awareness** — `check_source_coverage()` doesn't know that a file annotated to feature `doctor` (which is `part_of` `infrastructure`) is effectively tracked under `infrastructure`

## Impact

- Pre-commit hook shows 12 false stale warnings on every commit
- Developer trust in sync-check is undermined by noise
- Any new feature node with file-level `source` inside a domain directory will trigger the same problem

## Success Criteria

1. `beadloom sync-check` reports **0 stale entries** on beadloom itself
2. `check_source_coverage()` correctly handles parent-child hierarchy: a file tracked under a child feature is not flagged as untracked for the parent domain
3. All existing 1404 tests pass + new tests for hierarchy logic
4. Future feature nodes within domain directories don't cause false positives

## Scope

### Path 1: Fix annotations (immediate)
- `why.py`: `impact-analysis` → `context-oracle` (or add dual annotation)
- `doctor.py`: `domain=doctor` → `domain=infrastructure` (or dual)
- `watcher.py`: `domain=watcher` → `domain=infrastructure` (or dual)
- `tui/app.py`: Add `# beadloom:service=tui`

### Path 2: Hierarchy-aware coverage check (structural)
- `check_source_coverage()` queries child nodes (`part_of` edges) to build complete tracked-files set
- A file annotated to any descendant node is considered "tracked" for ancestor domains

## Out of Scope

- Changing `build_sync_state()` logic
- Changing the graph YAML node structure
- Multi-level hierarchy (only direct `part_of` children needed)
