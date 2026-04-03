# BRIEF: BDL-UX#99 — Repo-wide Doc Refresh (sync-check → honest 0)

> **Status:** Approved
> **Created:** 2026-06-01
> **Type:** chore
> **Parent bead:** `beadloom-mbb` (P2, deferred from BDL-036 Phase 0)

---

## Problem

`beadloom sync-check` reports **~37 stale doc↔code relations across 15 doc files** — **20 `symbols_changed`** (docs reference code symbols that changed) + **17 `hash_changed`** (linked source hash moved). This is genuine drift, not stale markers.

Consequences:
- The **pre-commit honesty gate is red**, so commits this session have used `--no-verify` 3× — exactly the creeping self-dishonesty Phase 0 was created to eliminate (STRATEGY-3 §3, principles 1–3).
- Going into **F2 with a red baseline gate** blunts F2's own tech-writer guardrail: a new drift can't be distinguished from the 37 pre-existing stales, so "drift closed" can't be honestly verified.
- This is leftover Phase-0 honesty debt — explicitly deferred, never closed.

## Stale inventory (by doc file)

| Doc file | rel. | F2 will re-stale? |
|----------|------|-------------------|
| `domains/graph/README.md` + `features/graph-diff/SPEC.md` | 8+1 | 🔴 yes (federation.py/loader.py) |
| `domains/infrastructure/README.md` + `doctor`/`reindex`/`watcher` SPECs | ~6 | 🔴 yes (db.py schema) |
| `services/cli.md` | 1 | 🔴 yes (export/federate) |
| `services/mcp.md` | 2 | 🟡 maybe |
| `domains/application/README.md` | 4 | 🟢 no |
| `services/tui.md` | 4 | 🟢 no |
| `domains/onboarding/README.md` | 5 | 🟢 no |
| `domains/doc-sync/README.md` + `features/docs-audit/SPEC.md` | 3 | 🟢 no |
| `domains/context-oracle/README.md` + `features/search/SPEC.md` | 2 | 🟢 no |

## Solution

Per-doc honest refresh using the **F4.1 AI-tech-writer loop** (manual dogfood):
```
1. beadloom reindex                       (incremental, current state)
2. beadloom sync-check --json             → exact stale ref_ids + reasons
3. per ref_id: beadloom docs polish --ref-id X --json   → what changed (symbols/deps)
4. update the doc text to match reality   (real content edit, not marker rubber-stamp)
5. beadloom sync-update X --check / mark_synced
6. beadloom reindex && sync-check         → verify that relation closed
```
Final gate: `beadloom reindex && beadloom sync-check` exits **0 honestly**, `beadloom lint --strict` + `doctor` stay green.

**Execution note:** pure doc work (no source), low merge-conflict risk (distinct files). Batched by domain cluster for parallelism. Given the subagent-blocked-fallback lesson (tech-writer write-denial in BDL-036), the coordinator runs tech-writer subagents but completes any blocked batch **inline**. The ~13 graph/cli/infra relations will be re-staled by F2 and re-closed by F2's tech-writer wave — expected, not a blocker.

## Beads

`beadloom-mbb` (parent, exists) + 4 tech-writer batch beads + 1 verify bead:

| Bead | Batch | Docs | Permanence |
|------|-------|------|------------|
| BEAD-01 (tech-writer) | A — graph | `graph/README` + `graph-diff/SPEC` | overlaps F2 |
| BEAD-02 (tech-writer) | B — infrastructure | `infrastructure/README` + `doctor`/`reindex`/`watcher` SPECs | overlaps F2 |
| BEAD-03 (tech-writer) | C — app + services | `application/README`, `services/cli.md`, `services/mcp.md`, `services/tui.md` | mixed |
| BEAD-04 (tech-writer) | D — independent domains | `onboarding/README`, `doc-sync/README` + `docs-audit/SPEC`, `context-oracle/README` + `search/SPEC` | permanent |
| BEAD-05 (verify) | — | full `reindex` + `sync-check`==0 + `lint --strict` + `doctor` green | — |

Dependencies: BEAD-01..04 independent (parallel-safe, distinct files) → BEAD-05 depends on all four.

## Acceptance Criteria

- [ ] `beadloom sync-check` exits **0** (honest — every relation reviewed, not marker-stamped)
- [ ] `beadloom lint --strict` = 0 violations, `beadloom doctor` clean
- [ ] Pre-commit gate passes **without `--no-verify`**
- [ ] No code changes (docs only); each doc edit reflects the real current symbols/state
- [ ] Friction notes from the F4.1-loop dogfood captured for the future `beadloom docs ai-refresh`
