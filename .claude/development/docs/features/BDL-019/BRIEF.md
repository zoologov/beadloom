# BRIEF: BDL-019 — Doc-Sync Refresh

> **Type:** task
> **Status:** Done
> **Created:** 2026-02-16

---

## Problem

After BDL-018 (Honest Detection), `beadloom sync-check` found 35 stale doc entries across 13 ref_ids. All documentation was outdated relative to actual code — `symbols_changed` detected hash mismatches everywhere.

## Solution

4 parallel tech-writer agents updated all 13 domain/service docs using the new `/tech-writer` role. Workflow per agent: `sync-check --json` -> `ctx <ref-id>` -> update doc -> `reindex` -> verify.

Also created `.claude/commands/tech-writer.md` — new role for systematic doc updates.

## Beads

| ID | Name | Priority | Status |
|----|------|----------|--------|
| BEAD-01 (`beadloom-3r1.1`) | Update context-oracle + search docs | P1 | Done |
| BEAD-02 (`beadloom-3r1.2`) | Update doc-sync + graph + graph-diff docs | P1 | Done |
| BEAD-03 (`beadloom-3r1.3`) | Update infrastructure + reindex + doctor + watcher docs | P1 | Done |
| BEAD-04 (`beadloom-3r1.4`) | Update onboarding + cli + mcp-server + tui docs | P1 | Done |

## Acceptance Criteria

- [x] All `symbols_changed` entries eliminated (35 -> 0)
- [x] 13 doc files updated to match current code
- [x] `/tech-writer` role created and integrated

## Results

- **Stale reduced:** 35 -> 12 (remaining 12 were `untracked_files` — graph structure issues, fixed in BDL-020)
- **Commit:** `310040e`
- **Files changed:** 13 docs + tech-writer.md
