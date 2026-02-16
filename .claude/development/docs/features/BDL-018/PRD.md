# PRD: BDL-018 — Doc-Sync Honest Detection

> **Status:** Approved
> **Date:** 2026-02-16
> **Version:** 1.6.1

---

## 1. Problem Statement

Beadloom's Doc-Sync mechanism — described in STRATEGY-2.md as the "killer feature" — **does not actually detect documentation staleness**. During BDL-017 (3 waves, 7763 lines of new code, 4 new modules), `beadloom sync-check` reported "0 stale docs" and `beadloom doctor` reported "No symbol drift".

This contradicts Design Principle 3: **"Sync Honesty — 5 stale truth is better than 0 stale lies."**

### Evidence (dogfooding BDL-017)

| What happened | What sync-check reported |
|---------------|--------------------------|
| `route_extractor.py` (780 lines) added to context-oracle | "ok" |
| `test_mapper.py` (530 lines) added to context-oracle | "ok" |
| `git_activity.py` (259 lines) added to infrastructure | "ok" |
| `config_reader.py` (301 lines) added to onboarding | "ok" |
| 3 new MCP tools (why, diff, lint) added | "ok" |
| Rule severity system added to graph | "ok" |
| 4 new reindex pipeline steps added | "ok" |
| `_CODE_EXTENSIONS` grew from 8 to 16 | "ok" |

**8 docs are stale. 0 detected.**

---

## 2. Root Cause Analysis

Five distinct bugs discovered:

### Bug 1: Full reindex resets baseline (CRITICAL)
`reindex()` → `_drop_all_tables()` → `_build_initial_sync_state(preserved_symbols=None)` → fresh symbols_hash = current state. Baseline is always "now", drift is impossible to detect.

**Location:** `reindex.py:628`

### Bug 2: Unannotated files invisible
`build_sync_state()` only links code → doc through `# beadloom:domain=X` annotations. New files without annotation are invisible to sync tracking.

**Location:** `engine.py:69-86`

### Bug 3: symbols_hash ignores file paths
`_compute_symbols_hash()` hashes `"name:kind"` strings but NOT file paths. Adding an entirely new file with new symbols won't change the hash if the symbol name+kind combo was already present in another file.

**Location:** `engine.py:18-32`

### Bug 4: No coverage verification
The system checks "has code changed?" but never "does the doc describe the code?". A doc can exist and be "ok" while mentioning none of the actual modules.

### Bug 5: Empty dict falsy bug
`old_symbols or None` in incremental reindex — empty dict `{}` is falsy in Python, triggers fresh baseline.

**Location:** `reindex.py:1082`

---

## 3. Success Criteria

After this epic:

1. **`beadloom sync-check` on beadloom itself must detect >= 6 stale docs** (the 8 from audit minus any we explicitly update)
2. Adding a new Python module to a node's source directory and running `beadloom reindex && beadloom sync-check` → must report stale
3. `beadloom doctor` must warn about symbol drift when new symbols exist that docs don't mention
4. Existing sync-check behavior (file hash changes → stale) must not regress
5. All 1362+ existing tests must continue to pass

---

## 4. User Stories

**US-1:** As a developer, when I add a new module to an existing domain, I want sync-check to tell me the domain's README is stale, so I know to update it.

**US-2:** As an AI agent running `beadloom sync-check` before commit, I want honest "stale" reports, so I don't push undocumented code.

**US-3:** As a project maintainer, I want `beadloom doctor` to warn me about documentation coverage gaps, so I can prioritize doc updates.

---

## 5. Out of Scope

- Semantic/embedding-based coverage detection (Phase 13)
- Auto-updating stale documentation (manual or AI-assisted, separate task)
- Updating the 8 stale docs themselves (Track B, triggered by fixed sync-check)
- New CLI commands or MCP tools (improvements to existing ones only)
