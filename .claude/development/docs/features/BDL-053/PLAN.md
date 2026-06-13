# PLAN: BDL-053 — Tracker / ACTIVE coherence hook

> **Status:** Approved
> **Created:** 2026-06-14
> **PRD/RFC/CONTEXT:** ./PRD.md · ./RFC.md · ./CONTEXT.md

---

## Beads (described — NOT created until this PLAN is Approved)

Parent: `BDL-053` (feature). Single trunk-based PR (dev → test → review → tech-writer).

| Bead | Role | Title | Depends on |
|------|------|-------|------------|
| .1 | dev | **Extract `application/active_table.py`** (move `_split_table_row`/`_is_separator_cells`/`_set_active_table_status` from `mcp_server`; `mcp_server` delegates — S4 behavior byte-identical) + **`reconcile_active_tables(project_root, bd_statuses, epic=None)`** (drive off the table's bead-id rows; status→cell map closed/in_progress/blocked/ready; preserve rich note when state agrees; epic discovery scanning `.claude/development/docs/features/*/ACTIVE.md`) + classify the new module as a graph node + SPEC | — |
| .2 | dev | **`beadloom active-sync` command** (`--check` nonzero-on-drift / `--epic` / `--json` / default fix) reading bd via `bd_seam.run_bd` (`bd list --json`); `BdUnavailableError`→no-op exit 0. **jsonl sync** (`bd export -o .beads/issues.jsonl` when tracked). **Hook wiring:** extend `_HOOK_TEMPLATE_WARN`+`_BLOCK` with the guarded coherence step (`command -v bd` → `beadloom active-sync` + export + `git add`); update agentic-flow `CLAUDE.md.txt` note + re-vendor (BDL-048 drift-guard) | .1 |
| .3 | test | reconcile matrix (3/4-col tables, status map, rich-note preserved, drift fixed); `--check` exit codes; **no-op contract** (bd-less / no-ACTIVE / untracked-jsonl → exit 0, zero writes); hook end-to-end in a temp git repo; **adopter-without-bd** case; S4 parser still green after extraction | .2 |
| .4 | review | correctness/honesty (no-op contract holds; reconcile never corrupts ACTIVE; auto-fix+restage safe; shared-module extraction clean; coverage-lint clean) | .3 |
| .5 | tech-writer | guide for `active-sync` + the hook coherence step + the no-op contract; fill the new module SPEC; CHANGELOG (BDL-053); note in flow docs that ACTIVE is reconciled by the hook, not by hand | .4 |

## Dependencies / DAG

```
.1 (extract + reconcile core) → .2 (command + jsonl + hook + adopter) → .3 (test) → .4 (review) → .5 (tech-writer)
```

Linear (single feature; .2 builds on .1's shared module). One PR.

## Waves

- **W1:** .1 dev → .2 dev → .3 test → .4 review → .5 tech-writer → PR → merge.

Green on `ci.yml` before merge; `[skip ai-techwriter]` per the BDL-051 slice policy (docs in .5). After merge: `beadloom install-hooks` to refresh the local hook.

## Acceptance (maps to goals)

- **G1** ← .1 (reconcile-from-bd, tolerant). **G2** ← .2 (`bd export` jsonl sync).
- **G3** ← .2 (`active-sync` command, `--check`/fix). **G4** ← .2 (hook wiring, guarded no-op) + .3 (adopter no-op test).
- **G5** ← .5 (docs/CHANGELOG/flow note). Plus: new module graph-classified (.1), full `ci.yml` green.
