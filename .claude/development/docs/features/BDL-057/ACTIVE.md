# ACTIVE: BDL-057 — Freshness for reference / overview documentation

> **Type:** feature
> **Branch:** features/BDL-057
> **Parent bead:** beadloom-sq4a
> **Updated:** 2026-06-15

---

## Current focus

**Wave 2 next: `.3` test.** Wave 1 DONE + integrated (commit `65821e3`): `.1` (docs audit → Gate, block `stale>0`) + `.2` (reference `watches` surface-drift mechanism) merged via file-checkout + 3-way on `cli.py`; ruff/mypy clean, full suite green, sync-check 151 fresh. Dev agents already shipped 58 tests (7 + 51).

**Dogfood finding (wave 1):** the new `docs-audit` Gate step is active and FAILs on **18 stale facts** in Beadloom's own docs. Genuine (fix in .5): README `node_count` 20→53, `mcp_tool_count` 14→18, README.ru `cli_command_count` 14→38, SECURITY/architecture. **False positives** (need `.beadloom/config.yml` tolerances/exclusions, NOT prose — outside tech-writer's docs/-only remit): context-oracle README `language_count` 12→1, `framework_count` 12→53. → resolve before the Gate can go green; decide who owns the config tuning (coordinator/dev vs fold into .5).

## Bead status

| Bead | Role | Status | Depends |
|------|------|--------|---------|
| beadloom-sq4a.1 | dev | open (ready) | — |
| beadloom-sq4a.2 | dev | open (ready) | — |
| beadloom-sq4a.3 | test | in progress | .1, .2 |
| beadloom-sq4a.4 | review | blocked | .3 |
| beadloom-sq4a.5 | tech-writer | blocked | .4 |

## Plan notes

- Locked decisions: Layer 1 = blocking (`stale>0`); Layer 2 = warn (`surface_drift`); declaration via `<!-- beadloom:watches=cli,graph,flow.yml -->`; `reference_state` separate table (don't touch symbol-pair logic / reason-masking).
- G4 (in .5): fill 11 skeleton SPECs (draft source: tag `archive/BDL-051-docs`, commit 1b137bf), declare `watches` on README(en/ru)/getting-started/architecture, make docs audit-clean.
- Generated `site/` is gitignored (BDL-056) — do NOT re-commit it.
- After BDL-057 merges: delete `archive/BDL-051-docs` tag; then release prep (likely 2.1.0, additive).

## Progress log

- 2026-06-15 — PRD/RFC/CONTEXT/PLAN approved; parent + 5 sub-beads created (beadloom-sq4a.1–.5) with DAG `.1∥.2 → .3 → .4 → .5`; branch `features/BDL-057` created. Starting Wave 1.
- 2026-06-15 — Wave 1 DONE: `.1`+`.2` built in parallel (worktree isolation), integrated to `features/BDL-057` (`65821e3`) via file-checkout + 3-way cli.py; worktrees removed, merge-slot released. Local `presentation` branch created for the owner's team deck (kept off main/feature; locally excluded). docs-audit dogfood finding logged above. Wave 2 (`.3` test) ready.
