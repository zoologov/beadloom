# CONTEXT: BDL-020 — Source Coverage Hierarchy Fix

> **Last updated:** 2026-02-17
> **Phase:** PLANNING

---

## Goal

Eliminate 12 false-positive `untracked_files` stale entries by fixing annotation mismatches and making `check_source_coverage()` hierarchy-aware.

## Constraints

- Only direct `part_of` children (1 level), no recursive traversal
- Annotation changes must not break existing sync pairs
- Logic change is additive — no modification of existing queries
- All 1404 existing tests must pass

## Code Standards

Established in BDL-018. Python 3.10+, uv, pytest, ruff, mypy --strict. TDD workflow.

## Key Files

| File | Role |
|------|------|
| `src/beadloom/doc_sync/engine.py:332` | `check_source_coverage()` — add hierarchy logic |
| `src/beadloom/context_oracle/why.py:3` | Fix annotation `impact-analysis` → `context-oracle` |
| `src/beadloom/infrastructure/doctor.py:3` | Fix annotation `doctor` → `infrastructure` |
| `src/beadloom/infrastructure/watcher.py:3` | Fix annotation `watcher` → `infrastructure` |
| `src/beadloom/tui/app.py:1` | Add `# beadloom:service=tui` |
| `tests/test_source_coverage.py` | Add hierarchy tests |

## Decisions

| # | Decision | Reason |
|---|----------|--------|
| 1 | Fix annotations AND logic (both paths) | Annotations fix immediate issue; logic prevents recurrence |
| 2 | Query `edges` table for `part_of` children | Simple, indexed, no schema changes needed |
| 3 | 1-level hierarchy only | Beadloom graph has feature→domain, no deeper nesting |
| 4 | Annotation: use parent domain ref_id | Feature tracking via graph `source` field, not annotation |

## Related

- BDL-018: Created `check_source_coverage()` (the function being fixed)
- BDL-019: Updated all docs (cleared `symbols_changed`, exposed `untracked_files`)
