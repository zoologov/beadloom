# RFC: BDL-034 — UX Issues & Improvements Batch Fix

> **Status:** Approved
> **Created:** 2026-03-10

---

## Overview

Fix 3 bugs and implement 3 improvements collected during dogfooding (BDL-UX-Issues.md #65-#70). All changes are within existing Python modules — no new packages or external dependencies. Issue #66 (snapshot diffing) may already be resolved and needs verification only.

## Motivation

### Problem
Beadloom v1.8.0 has data accuracy issues in rules handling (#67, #68), a regeneration bug (#69), high false positive rate in docs audit (#65), and sync-check that masks stale docs (#70). These undermine trust in Beadloom's output for both human developers and AI agents.

### Solution
Targeted fixes in 4 existing modules: `infrastructure/reindex.py`, `onboarding/scanner.py`, `doc_sync/scanner.py`, and `doc_sync/engine.py`. Plus schema migration for two-phase sync state.

## Technical Context

### Constraints
- Python 3.10+
- SQLite (WAL mode)
- No breaking changes to CLI interface
- Backward-compatible schema migrations (additive columns only)
- All changes must pass existing test suite

### Affected Areas
| Domain | Files | Issues |
|--------|-------|--------|
| infrastructure | `reindex.py` (lines 272-337) | #67 (rules DB) |
| onboarding | `scanner.py` (lines 971-1033) | #68 (rule labels), #69 (AGENTS.md regen) |
| doc-sync | `scanner.py` (lines 83-310) | #65 (docs audit FP) |
| doc-sync | `engine.py` (lines 100-176) | #70 (sync-check baseline) |
| infrastructure | `db.py` (lines 76-87) | #70 (sync_state schema) |

## Proposed Solution

### Bug #67: `_load_rules_into_db` drops v3 rule types

**File:** `src/beadloom/infrastructure/reindex.py:272-337`

**Current:** `isinstance(rule, DenyRule)` and `isinstance(RequireRule)` branches, with `else: continue` at line 328 silently skipping 5 new types.

**Approach:** Add a generic serialization path using `rule.__class__.__name__` as type discriminator and `vars(rule)` or a `to_dict()` method for serialization. This avoids adding 5 new `isinstance` branches and is forward-compatible with future rule types.

**Changes:**
| Pattern | Before | After |
|---------|--------|-------|
| Type detection | `isinstance(rule, DenyRule)` / `isinstance(rule, RequireRule)` | Keep existing + add generic fallback for remaining types |
| Serialization | Hardcoded `{"from": {}, "to": {}}` / `{"for": {}, "has_edge_to": {}}` | Type-specific + generic `rule.to_dict()` for new types |
| Skip unknown | `else: continue` | `else:` serialize with class name as type |

**Validation:** `SELECT COUNT(*) FROM rules` returns 9 after reindex.

### Bug #68: Simplistic rule type detection in scanner.py

**File:** `src/beadloom/onboarding/scanner.py:985, 1051`

**Current:** `rule_type = "require" if "require" in rule else "deny"` — binary classification.

**Approach:** Check YAML keys against all 7 types:

```python
_RULE_TYPE_KEYS = {
    "require": "require",
    "deny": "deny",
    "forbid_cycles": "forbid_cycles",
    "layers": "layers",
    "check": "check",
    "forbid_import": "forbid_import",
    "forbid_edge": "forbid_edge",
}

def _detect_rule_type(rule: dict) -> str:
    for key, label in _RULE_TYPE_KEYS.items():
        if key in rule:
            return label
    return "unknown"
```

Apply in both `_build_rules_section()` (line 985) and `_read_rules_data()` (line 1051).

### Bug #69: AGENTS.md Custom section duplication

**File:** `src/beadloom/onboarding/scanner.py:994-1033`

**Current:** Template includes `## Custom` at end. Preservation logic captures everything after first `## Custom` marker and appends it — causing duplication when preserved content also contains the marker.

**Approach:** Replace `## Custom` with HTML comment markers:
```
<!-- beadloom:custom-start -->
<!-- beadloom:custom-end -->
```

Template includes both markers. Preservation extracts content between markers. On regeneration, only user content (not markers) is re-inserted between new markers.

**Fallback:** If old-format `## Custom` is found (no HTML markers), migrate by wrapping existing content in new markers during first regeneration.

### Improvement #65: docs audit false positive reduction

**File:** `src/beadloom/doc_sync/scanner.py:83-310`

**Current:** 8 regex masks + number <=1 skip + <10 count skip + SPEC.md exclude. Still ~60% FP on beadloom itself.

**Approach (3 layers):**

**Layer 1 — Blocklist modifiers** (highest ROI):
Skip matches where the number appears near context-killing modifiers:
```python
_FP_MODIFIERS = {">=", "<=", ">", "<", "up to", "supports", "limit",
                  "maximum", "minimum", "%", "at least", "about", "~"}
```
Check +-3 tokens around the matched number. If any modifier found, skip.

**Layer 2 — Proximity scoring:**
Weight match confidence by distance to fact-type keywords. Example: number `13` near `MCP` = likely `mcp_tool_count`; `80` near `coverage` + `%` = threshold, not `test_count`. Lower confidence = skip.

**Layer 3 — File-type heuristics:**
```python
_LOW_CONFIDENCE_PATHS = {"SPEC.md", "CONTRIBUTING.md", "examples/", "CHANGELOG.md"}
_HIGH_CONFIDENCE_PATHS = {"README.md", "AGENTS.md", "CLAUDE.md"}
```
Apply confidence multiplier based on file path.

**Target:** <15% FP rate on beadloom project.

### Improvement #66: Snapshot diffing — VERIFY FIRST

**Files:** `src/beadloom/infrastructure/snapshot.py:155-226`, `src/beadloom/services/cli.py:2498-2627`

**Finding:** Explore agent found existing implementation:
- `snapshot save [--label]` CLI command
- `snapshot list [--as-json]` CLI command
- `snapshot compare <old_id> <new_id>` CLI command
- `compare_snapshots()` with full diff logic (added/removed/changed nodes and edges)

**Action:** Verify existing implementation works correctly. If functional, close issue #66 as already resolved. If gaps exist, patch them.

### Improvement #70: Two-phase sync state

**Files:** `src/beadloom/infrastructure/db.py:76-87`, `src/beadloom/doc_sync/engine.py:100-176`, `src/beadloom/infrastructure/reindex.py:232-269`

**Current:** `sync_state` table has `code_hash_at_sync` and `doc_hash_at_sync`, both set during `_build_initial_sync_state()` at reindex time. `check_sync()` compares current file hashes against these baselines.

**Schema migration — add column:**
```sql
ALTER TABLE sync_state ADD COLUMN doc_hash_at_last_edit TEXT DEFAULT '';
```

**Logic changes:**

1. **Reindex** (`_build_initial_sync_state`): Sets `code_hash_at_sync` to current code hash. Sets `doc_hash_at_sync` to current doc hash. **Does NOT touch `doc_hash_at_last_edit`** — this is only set when the doc file actually changes outside of reindex.

2. **sync-check** (`check_sync`): New comparison logic:
   - If `doc_hash_at_last_edit` is empty (first run / legacy): fall back to current behavior
   - If `doc_hash_at_last_edit` is set: compare `code_hash_at_sync` (latest code) against the code hash that was current when the doc was last edited. If code changed since last doc edit → stale.

3. **Doc edit detection**: When sync-check runs and detects that the doc file hash changed since last check, update `doc_hash_at_last_edit` to the new doc hash and record the corresponding `code_hash_at_sync` value.

## Alternatives Considered

### Option A: Generic `rule.to_dict()` on base Rule class
For #67. Requires changing the Rule class hierarchy in `graph/` domain. Cleaner long-term but higher blast radius. **Rejected** — use class-name-based serialization in reindex.py only.

### Option B: LLM-based semantic analysis for docs audit
For #65. Would achieve ~95% precision but adds latency, API dependency, and cost. **Rejected** — pattern-based approach sufficient for CLI tool.

### Option C: Git-based doc change tracking for sync-check
For #70. Track doc changes via git log instead of DB column. **Rejected** — not all users commit docs immediately; DB-based tracking is more reliable.

## Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Schema migration breaks existing DBs | Low | High | Additive column with DEFAULT, backward-compatible |
| docs audit FP filter too aggressive (false negatives) | Medium | Medium | Tune thresholds on beadloom + external project |
| sync-check two-phase logic edge cases | Medium | Medium | Extensive test coverage for state transitions |

## Open Questions

| # | Question | Decision |
|---|----------|----------|
| Q1 | Is snapshot diffing (#66) already fully implemented? | Pending — verify in dev bead |
| Q2 | Should blocklist modifiers be configurable? | Decided: No — hardcoded list, adjust in future if needed |
| Q3 | Should `doc_hash_at_last_edit` migration be automatic? | Decided: Yes — on first DB open via `_ensure_schema()` |
