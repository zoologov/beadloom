# PRD: BDL-034 — UX Issues & Improvements Batch Fix

> **Status:** Approved
> **Created:** 2026-03-10

---

## Problem

Beadloom v1.8.0 has 3 open bugs and 3 improvement proposals collected during dogfooding (issues #65-#70 in BDL-UX-Issues.md). These affect data accuracy, developer experience, and agent reliability:

1. **Rules DB incomplete** — `_load_rules_into_db()` silently drops 5 of 9 v3 rule types. The `rules` table shows 4 rows instead of 9. Any MCP tool or TUI widget querying rules gets stale data. `docs audit` reports wrong `rule_type_count`.
2. **Rule type labels wrong** — `_build_rules_section()` and `_read_rules_data()` classify all non-`require` rules as `deny`, producing incorrect labels for `forbid_cycles`, `layers`, `check`, `forbid_import`, `forbid_edge` rules in AGENTS.md and `beadloom prime`.
3. **AGENTS.md regeneration corrupts file** — Custom section preservation logic duplicates content when prior content already contains a `## Custom` marker.
4. **docs audit ~60% false positives** — Stale mention detection lacks context awareness: threshold numbers, capability descriptions, example values, and years trigger false matches.
5. **No snapshot diffing** — `graph_snapshots` stores point-in-time captures but provides no CLI to compare two snapshots.
6. **sync-check masks stale docs after reindex** — Running `beadloom reindex` resets the sync baseline, so subsequent `sync-check` reports `[ok]` even when doc content was never updated.

## Impact

- **Agents** get inaccurate architecture data from rules DB and AGENTS.md (issues #67, #68)
- **CI/CD** cannot reliably detect stale documentation (issue #70)
- **Developers** see garbled AGENTS.md after regeneration (issue #69)
- **docs audit** is unusable at ~60% false positive rate — developers ignore its output (issue #65)
- **Architecture tracking** has no diff capability between versions (issue #66)

## Goals

- [ ] All 9 v3 rule types stored correctly in rules DB table
- [ ] Rule type labels in AGENTS.md and `beadloom prime` match actual YAML key for all 7 rule types
- [ ] AGENTS.md regeneration produces clean output without duplication
- [ ] `docs audit` false positive rate reduced from ~60% to <15% on beadloom itself
- [ ] `beadloom snapshots diff` CLI command compares two graph snapshots
- [ ] `sync-check` distinguishes between "reindex ran" and "doc content updated"

## Non-goals

- LLM-based semantic analysis for docs audit (overkill for CLI tool)
- Full version control for graph (Dolt, git-based diffing)
- Breaking changes to existing CLI interface
- Rewriting the sync-check architecture from scratch

## User Stories

### US-1: Accurate Rules in DB
**As** an AI agent querying rules via MCP, **I want** all 9 architecture rules stored in the DB, **so that** my context includes the complete rule set.

**Acceptance criteria:**
- [ ] `rules` table contains 9 rows after reindex with v3 rules.yml
- [ ] `docs audit` reports `rule_type_count: 9`

### US-2: Correct Rule Type Labels
**As** a developer reading AGENTS.md, **I want** each rule labeled with its actual type (require/deny/forbid_cycles/layers/check/forbid_import/forbid_edge), **so that** I understand what each rule does.

**Acceptance criteria:**
- [ ] AGENTS.md shows correct type for all 9 rules
- [ ] `beadloom prime` output shows correct type labels

### US-3: Clean AGENTS.md Regeneration
**As** a developer running `beadloom setup-rules --refresh`, **I want** AGENTS.md regenerated without content duplication, **so that** the file is always valid.

**Acceptance criteria:**
- [ ] Regeneration with existing `## Custom` content produces clean output
- [ ] Idempotent: running twice produces identical output

### US-4: Reliable Docs Audit
**As** a tech writer, **I want** `docs audit` to report only genuinely stale mentions, **so that** I can trust and act on its output.

**Acceptance criteria:**
- [ ] False positive rate <15% on beadloom project
- [ ] Threshold numbers (>=, %, up to) are not flagged
- [ ] Year values (2026, etc.) are not flagged
- [ ] File-type heuristics lower confidence for SPEC.md, examples/

### US-5: Snapshot Diffing
**As** a developer tracking architecture evolution, **I want** to compare two graph snapshots, **so that** I can see what changed between versions.

**Acceptance criteria:**
- [ ] `beadloom snapshots list` shows saved snapshots
- [ ] `beadloom snapshots diff <a> <b>` shows added/removed/changed nodes and edges
- [ ] `--json` flag for automation

### US-6: Honest Sync-Check
**As** a tech writer agent, **I want** `sync-check` to detect stale docs even after `reindex`, **so that** code changes always surface as doc update tasks.

**Acceptance criteria:**
- [ ] Two-phase sync state: separate code hash (reindex) from doc hash (last edit)
- [ ] sync-check reports stale when code changed since last doc edit
- [ ] Backward-compatible schema migration

## Acceptance Criteria (overall)

- [ ] All 6 issues resolved and verified with tests
- [ ] Zero regression in existing test suite
- [ ] `beadloom lint --strict` passes (excluding pre-existing architecture violations)
- [ ] `beadloom sync-check` reports no stale docs
- [ ] Issues #65-#70 moved to "Closed" section in BDL-UX-Issues.md
