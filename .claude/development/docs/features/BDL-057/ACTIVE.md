# ACTIVE: BDL-057 — Freshness for reference / overview documentation

> **Type:** feature
> **Branch:** features/BDL-057
> **Parent bead:** beadloom-sq4a
> **Updated:** 2026-06-15

---

## Current focus

**ALL BEADS DONE — branch ready for one PR to `main`.** Waves: `.1`+`.2` (dev, integrated `65821e3`) → `.3` (test `50a79ff`, +26 cross-cutting) → `.4` (review PASS, 3 minor) → `.6` (dev fixes `95c637d`: reference_state migration guard + interactive sync-update reference handling + `docs_audit.ignore` for false positives) → `.5` (tech-writer `51ee89c`: 11 skeleton SPECs filled, genuine facts fixed, `watches` declared on README en/ru + getting-started + architecture, feature docs). Coordinator gate check: `beadloom ci` rc 0 (docs-audit 0 stale, sync-check 151 fresh + 0 surface_drift), pytest 4316 passed, ruff/mypy clean.

**Dogfood finding (resolved):** the new `docs-audit` Gate step caught 18 stale facts in the repo's own docs — 13 genuine (reworded in `.5`) + 5 false positives (suppressed via `.beadloom/config.yml` `docs_audit.ignore` added in `.6`). The feature paid for itself on first run.

## Bead status

| Bead | Role | Status | Depends |
|------|------|--------|---------|
| beadloom-sq4a.1 | dev | open (ready) | — |
| beadloom-sq4a.2 | dev | open (ready) | — |
| beadloom-sq4a.3 | test | in progress | .1, .2 |
| beadloom-sq4a.4 | review | blocked | .3 |
| beadloom-sq4a.5 | tech-writer | in progress | .4 |

## Plan notes

- Locked decisions: Layer 1 = blocking (`stale>0`); Layer 2 = warn (`surface_drift`); declaration via `<!-- beadloom:watches=cli,graph,flow.yml -->`; `reference_state` separate table (don't touch symbol-pair logic / reason-masking).
- G4 (in .5): fill 11 skeleton SPECs (draft source: tag `archive/BDL-051-docs`, commit 1b137bf), declare `watches` on README(en/ru)/getting-started/architecture, make docs audit-clean.
- Generated `site/` is gitignored (BDL-056) — do NOT re-commit it.
- After BDL-057 merges: delete `archive/BDL-051-docs` tag; then release prep (likely 2.1.0, additive).

## Progress log

- 2026-06-15 — PRD/RFC/CONTEXT/PLAN approved; parent + 5 sub-beads created (beadloom-sq4a.1–.5) with DAG `.1∥.2 → .3 → .4 → .5`; branch `features/BDL-057` created. Starting Wave 1.
- 2026-06-15 — Wave 1 DONE: `.1`+`.2` built in parallel (worktree isolation), integrated to `features/BDL-057` (`65821e3`) via file-checkout + 3-way cli.py; worktrees removed, merge-slot released. Local `presentation` branch created for the owner's team deck (kept off main/feature; locally excluded). docs-audit dogfood finding logged above. Wave 2 (`.3` test) ready.
