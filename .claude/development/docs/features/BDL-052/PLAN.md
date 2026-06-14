# PLAN: BDL-052 (EPIC) — Usable doc-flow + role configurator

> **Status:** Approved
> **Created:** 2026-06-14
> **PRD/RFC/CONTEXT:** ./PRD.md · ./RFC.md (+ Addendum) · ./CONTEXT.md

---

## Beads (described — NOT created until this PLAN is Approved)

Parent: `BDL-052` (epic). Six slices on **ONE feature branch** (`features/BDL-052`) — **commit per slice** (dev → test → review per slice, independent dev beads **in parallel**), one tech-writer pass at the end, **ONE PR per epic** (CLAUDE.md §6). Each slice `beadloom ci`-green locally before its commit.

| Bead | Role | Title | Depends on |
|------|------|-------|------------|
| **S1 — flow mechanics (Gate hook + coordinator loop + parallelism)** | | | |
| .1 | dev | `install-hooks` gains a **pre-push** hook running `beadloom ci` (block-on-red, actionable msg; `--pre-push`/`--pre-commit`, default both; guarded no-op outside flow repo). Encode the **Gate-enforced coordinator loop** + **explicit parallelism** ("independent ready beads in a wave → launch concurrently; `merge-slot` serializes") in `.claude/commands/coordinator.md` + re-vendor (drift-guard green) | — |
| .2 | test | pre-push hook (blocks red / passes green / no-op outside flow repo, tmp git repos); selectors; coordinator-loop+parallelism encoded; re-vendor drift-guard green | .1 |
| .3 | review | S1 (Gate truly blocks; loop+parallelism tool-step-driven not memory; hook fail-safe) | .2 |
| **S2 — CORE roles (restore + modernize from 1.9.0)** | | | |
| .4 | dev | Review `git show cb4f0a6:.claude/commands/{dev,test,review,tech-writer}.md` (340/275/166/193 lines); produce **modernized, tool/stack-NEUTRAL CORE role defs** (dev/test/review/tech-writer): DDD/architecture-discovery, TDD/AAA, **annotation discipline** (`# beadloom:domain/feature/component=`), Clean Code, naming principles, validation/Gate loop, **API-CHANGE-log** (dev→review/tech-writer), review checklists, tech-writer two-sources + workflow + parallel. Best-practices-current, not verbatim paste | .1 |
| .5 | test | structural checks: each CORE role contains the required sections; annotation-discipline + API-CHANGE-log present; no stack/tool specifics leaked into CORE | .4 |
| .6 | review | S2 (rules restored + modernized; CORE genuinely neutral; nothing important still missing vs 1.9.0) | .5 |
| **S3 — role configurator (CORE + overlays + tool-adapters via `flow.yml`)** | | | |
| .7 | dev | `.beadloom/flow.yml` (`architecture: [ddd\|fsd]` + `stack` + `tools` + `quality`); **architecture overlays `ddd` + `fsd` (peers)** + **stack overlays `python, fastapi, javascript, typescript, vuejs`**; compose(CORE + arch + stack) → generate `.claude/agents/*` + `.cursor/agents/*` (+ Cursor rules / coordinator orchestrator mode); `setup-agentic-flow --tool/--stack/--architecture`; **drift-guard** (adapters ≡ composed canon, BDL-048 pattern); `config-check` covers flow.yml | .6 |
| .8 | test | compose correctness (CORE+ddd+python vs CORE+fsd+vuejs render the right adapter); `--tool/--stack/--architecture` scaffolding; drift-guard catches a hand-edit; flow.yml schema/validation | .7 |
| .9 | review | S3 (one canon→adapters; FSD at parity with DDD; Cursor adapter faithful; honest follow-up note on graph-model FSD) | .8 |
| **S4 — symbol-scope (shared local + CI)** | | | |
| .10 | dev | `ai_techwriter/scope.py` + shared `narrow_by_changed_symbols(...)` — changed-symbol ∩ doc-referenced-symbol; drop+`sync-update`-baseline clean; conservative fallback | .1 |
| .11 | test | god-file case (1 changed symbol → 1 doc); fallback (ambiguous→include); baseline keeps sync-check green; no under-refresh | .10 |
| .12 | review | S4 (no under-scope; fallback sound) | .11 |
| **S5 — CI agent boost (parallel + cache)** | | | |
| .13 | dev | `runner`: bounded parallel Goose (`max_parallel`=3) + 429/5xx back-off + rate guard (replaces sequential `_repair_each_doc`). `ci.yml` ai-techwriter job: `setup-uv` cache + hash-keyed index cache. Logic/verdict/trigger UNCHANGED | .1 |
| .14 | test | parallel result == sequential (seam-mocked); back-off; cap; cache key (stale→miss) | .13 |
| .15 | review | S5 (no behavior change vs sequential; rate/RAM safe; cache not stale) | .14 |
| **S6 — folded fix + epic docs** | | | |
| .16 | dev | `beadloom active-sync --stage` (stage only `ReconcileResult.changed_files` + jsonl); both hook templates use `--stage`. Closes `beadloom-cugq` | .1 |
| .17 | test | `--stage` stages only reconciled paths; hook uses it; no over-staging | .16 |
| .18 | review | S6 (over-staging fixed; no regression) | .17 |
| .19 | tech-writer | guides + CHANGELOG + ROADMAP + adopter guide: the flow, pre-push Gate, **role configurator (CORE+overlays, ddd/fsd, claude/cursor)**, symbol-scope/parallel/cache knobs, local-primary/CI-fallback; fill new node docs; close `beadloom-parl`/`beadloom-cugq` | .3,.6,.9,.12,.15,.18 |

## Dependencies / DAG

```
S1: .1→.2→.3 ─┬─> S2: .4→.5→.6 ─> S3: .7→.8→.9 ─┐
              ├─> S4: .10→.11→.12 ───────────────┤
              ├─> S5: .13→.14→.15 ───────────────┼─> .19 (tech-writer)
              └─> S6: .16→.17→.18 ───────────────┘
```
S1 gates all. S3 depends on S2 (configurator composes the CORE roles). S4/S5/S6 independent after S1. Within a wave, independent dev beads run **in parallel**.

## Waves (one branch; commit per slice; ONE PR at the end)

- **W1 (S1):** .1→.2→.3 → **commit**. (From here our own pushes go through the pre-push Gate + loop.)
- **W2 (S2):** .4→.5→.6 → **commit**.
- **W3 (S3):** .7→.8→.9 → **commit**.
- **W4 (S4):** .10→.11→.12 → **commit**  ┐ S4/S5/S6 are independent after S1 —
- **W5 (S5):** .13→.14→.15 → **commit**  ├ their dev beads can run as parallel waves;
- **W6 (S6):** .16→.17→.18 → **commit**  ┘ kept as ordered commits for clean trunk history.
- **W7:** .19 tech-writer → **commit** → **ONE PR `features/BDL-052` → main** → ci.yml (single run) → merge → close epic.

## Acceptance (maps to goals)

- **G1/G2/G3** ← S1. **CORE rules restored+modernized** ← S2. **G4 configurator (ddd+fsd, python/fastapi/js/ts/vue, claude/cursor)** ← S3. **G5 symbol-scope** ← S4. **G6/G7 CI parallel+cache** ← S5. **G8 `active-sync --stage`** ← S6. **G9 docs** ← .19.
