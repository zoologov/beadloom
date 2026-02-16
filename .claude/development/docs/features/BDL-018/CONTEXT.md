# CONTEXT: BDL-018 — Doc-Sync Honest Detection

> **Status:** Active
> **Date:** 2026-02-16
> **Epic:** BDL-018
> **PRD:** Approved | **RFC:** Approved

---

## 1. Goal

Fix the Doc-Sync mechanism so it **honestly detects documentation staleness**. After BDL-017 added 7763 lines of new code across 4 new modules, `sync-check` reported "0 stale" — a false negative that violates Design Principle 3 ("Sync Honesty").

**Success metric:** `beadloom sync-check` on beadloom itself must detect >= 6 stale docs.

---

## 2. Key Files

### Files to modify

| File | What changes | Beads |
|------|-------------|-------|
| `src/beadloom/doc_sync/engine.py` | Fix hash computation, add `check_source_coverage()`, `check_doc_coverage()`, integrate into `check_sync()` | BEAD-01, BEAD-03, BEAD-04 |
| `src/beadloom/infrastructure/reindex.py` | `_snapshot_sync_baselines()`, pass to full reindex, fix `or None` | BEAD-01, BEAD-02 |
| `src/beadloom/infrastructure/doctor.py` | New `_check_source_coverage` check, enhanced drift output | BEAD-04 |
| `src/beadloom/services/cli.py` | Enhanced sync-check output (show missing modules/details) | BEAD-04 |

### Files for reference (DO NOT modify unless needed)

| File | Why |
|------|-----|
| `src/beadloom/infrastructure/db.py` | `sync_state` table schema |
| `src/beadloom/context_oracle/code_indexer.py` | Annotation parsing (`# beadloom:domain=X`) |
| `.beadloom/_graph/services.yml` | Graph YAML with `source:` and `docs:` fields |

---

## 3. Architecture Context

```
sync-check flow (current):
  sync_state row → compare file hashes → compare symbols_hash → ok/stale

sync-check flow (after BDL-018):
  sync_state row → compare file hashes → compare symbols_hash
                 → check source coverage (untracked files)
                 → check doc coverage (module name mentions)
                 → ok/stale
```

**Key tables:**
- `sync_state` — doc-code pairs with baseline hashes
- `nodes` — graph nodes with `source` and `ref_id`
- `code_symbols` — indexed symbols with `annotations` and `file_path`
- `docs` — indexed documentation with `ref_id` and `path`

---

## 4. Code Standards

Same as project-wide (see CLAUDE.md §0.1):

- **Language:** Python 3.10+ (type hints, `str | None` syntax)
- **Testing:** pytest, TDD (Red → Green → Refactor), >= 80% coverage
- **Linter:** ruff (lint + format)
- **Typing:** mypy --strict
- **Restrictions:** No `Any` without justification, no bare `except:`, pathlib only, parameterized SQL

---

## 5. Decisions

| # | Decision | Rationale |
|---|----------|-----------|
| D1 | Fix existing mechanism, don't rewrite | Infrastructure is sound, only baselines are broken |
| D2 | Include `file_path` in `symbols_hash` | Cheapest way to detect new files via hash change |
| D3 | Accept hash format change → initial "stale" on upgrade | Correct behavior — docs ARE stale |
| D4 | Exclude `__init__.py`, `conftest.py`, `__main__.py` from coverage | These are boilerplate, not doc-worthy modules |
| D5 | Module name check = exact string match, no AI | Covers 100% of our 8 stale cases at zero cost |
| D6 | Source coverage uses `nodes.source` from graph YAML | Already available, no new data needed |

---

## 6. Related Files

- **PRD:** `.claude/development/docs/features/BDL-018/PRD.md`
- **RFC:** `.claude/development/docs/features/BDL-018/RFC.md`
- **PLAN:** `.claude/development/docs/features/BDL-018/PLAN.md`
- **ACTIVE:** `.claude/development/docs/features/BDL-018/ACTIVE.md`
- **Strategy:** `.claude/development/STRATEGY-2.md` (Phase 8.5 — Doc Sync v2)
- **UX Issues:** `.claude/development/BDL-UX-Issues.md` (#15, #18 — related prior fixes)

---

## 7. Last Updated

2026-02-16 — Initial creation, PRD + RFC approved
