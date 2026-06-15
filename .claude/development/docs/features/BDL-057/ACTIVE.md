# ACTIVE: BDL-057 — Freshness for reference / overview documentation

> **Type:** feature
> **Branch:** features/BDL-057
> **Parent bead:** beadloom-sq4a
> **Updated:** 2026-06-15

---

## Current focus

**Wave 1 (parallel dev):** `.1` (Layer 1 — docs audit → Gate, block `stale>0`) ∥ `.2` (Layer 2 — reference `watches` mechanism). Worktree isolation; light `cli.py` overlap → serialize the merge.

## Bead status

| Bead | Role | Status | Depends |
|------|------|--------|---------|
| beadloom-sq4a.1 | dev | open (ready) | — |
| beadloom-sq4a.2 | dev | open (ready) | — |
| beadloom-sq4a.3 | test | ready | .1, .2 |
| beadloom-sq4a.4 | review | blocked | .3 |
| beadloom-sq4a.5 | tech-writer | blocked | .4 |

## Plan notes

- Locked decisions: Layer 1 = blocking (`stale>0`); Layer 2 = warn (`surface_drift`); declaration via `<!-- beadloom:watches=cli,graph,flow.yml -->`; `reference_state` separate table (don't touch symbol-pair logic / reason-masking).
- G4 (in .5): fill 11 skeleton SPECs (draft source: tag `archive/BDL-051-docs`, commit 1b137bf), declare `watches` on README(en/ru)/getting-started/architecture, make docs audit-clean.
- Generated `site/` is gitignored (BDL-056) — do NOT re-commit it.
- After BDL-057 merges: delete `archive/BDL-051-docs` tag; then release prep (likely 2.1.0, additive).

## Progress log

- 2026-06-15 — PRD/RFC/CONTEXT/PLAN approved; parent + 5 sub-beads created (beadloom-sq4a.1–.5) with DAG `.1∥.2 → .3 → .4 → .5`; branch `features/BDL-057` created. Starting Wave 1.
