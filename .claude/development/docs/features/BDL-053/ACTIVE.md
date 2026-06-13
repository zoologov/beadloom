# ACTIVE: BDL-053 — Tracker / ACTIVE coherence hook

> **Last updated:** 2026-06-14

---

## Current Focus

- **Phase:** COMPLETE — all 5 beads ✓ done; PR open. (was W1 BEAD-01 dev: extract `application/active_table.py` + `reconcile_active_tables()` + classify the new module.
- **Branch:** `features/BDL-053` (trunk-based; single PR via ci.yml).
- **Coordinator:** main loop (multi-agent).
- **Parent:** `beadloom-b27q`

## Beads

| Bead | Role | Status |
|------|------|--------|
| beadloom-b27q.1 | dev — extract active_table.py + reconcile + classify | ✓ done |
| beadloom-b27q.2 | dev — active-sync command + jsonl sync + hook wiring + adopter | ✓ done |
| beadloom-b27q.3 | test — reconcile matrix + no-op contract + hook e2e + adopter | ✓ done |
| beadloom-b27q.4 | review — no-op holds; ACTIVE not corrupted; extraction clean | ✓ done (PASS; 1 minor→follow-up) |
| beadloom-b27q.5 | tech-writer — guide + SPEC + CHANGELOG + flow-doc note | ✓ done |

## Waves

W1 `.1 → .2 → .3 → .4 → .5` → PR → merge. `[skip ai-techwriter]` on the PR (docs in .5).

## Key decisions (from PRD/RFC/CONTEXT)

- Reconcile-from-truth: drive off the ACTIVE table's own bead-id rows → one `bd list --json` → rewrite Status cells; preserve rich note when state agrees.
- jsonl sync = explicit `bd export -o .beads/issues.jsonl` in the hook.
- Hook step = auto-fix + `git add`, guarded **safe no-op** (no bd / no ACTIVE / untracked jsonl → exit 0).
- Extract S4 parser → `application/active_table.py` (mcp_server delegates, byte-identical).
- **Owner headline:** works out-of-the-box for every adopter of the packaged flow; zero behavior change for non-flow repos.

## Progress Log

- 2026-06-14: PRD/RFC/CONTEXT/PLAN approved; feature `beadloom-b27q` + 5 beads + linear DAG; branch `features/BDL-053`. W1 launched (.1 dev).
