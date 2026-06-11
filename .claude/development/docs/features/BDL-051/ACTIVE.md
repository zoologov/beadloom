# ACTIVE: BDL-051 (EPIC) — Beadloom governs itself

> **Last updated:** 2026-06-11

---

## Current Focus

- **Phase:** S1 MERGED (PR #7, main 35769d7). Next: S2 (ai_agents move). POLICY: [skip ai-techwriter] on slice-PRs (per-slice agent ~15min — untenable); all docs in tech-writer .13. Reinforces BDL-052 (non-blocking).
- **Branch:** `features/BDL-051` (trunk-based; each slice is its own PR via ci.yml).
- **Coordinator:** main loop (multi-agent).
- **Parent:** `beadloom-mukc`

## Beads

| Bead | Role | Status |
|------|------|--------|
| beadloom-mukc.1 | dev — S1 def + sprawl lint | ✓ done |
| beadloom-mukc.2 | test — S1 lint | ✓ done |
| beadloom-mukc.3 | review — S1 | ✓ done (PASS-WITH-FIXES; 2 minor→S3/.13) |
| beadloom-mukc.4 | dev — S2 ai_agents move + retire vendoring | in progress (impl complete; full ci rc0) |
| beadloom-mukc.5 | test — S2 | ✓ done (found+fixed tools/ CI bug) |
| beadloom-mukc.6 | review — S2 | ✓ done (PASS-WITH-FIXES; crit+major fixed) |
| beadloom-mukc.7 | dev — S3 onboarding re-model + audit | blocked ← 3 |
| beadloom-mukc.8 | test — S3 | blocked ← 7 |
| beadloom-mukc.9 | review — S3 | blocked ← 8 |
| beadloom-mukc.10 | dev — S4 ACTIVE-table fix + adopt | blocked ← 3 |
| beadloom-mukc.11 | test — S4 | blocked ← 10 |
| beadloom-mukc.12 | review — S4 | blocked ← 11 |
| beadloom-mukc.13 | tech-writer (epic close) | blocked ← 6,9,12 |

## Waves (trunk-based: one slice-PR at a time)

W1 (S1) `.1→.2→.3` → W2 (S2) `.4→.5→.6` → W3 (S3) `.7→.8→.9` → W4 (S4) `.10→.11→.12` → W5 `.13` → close.

## Key decisions (from PRD/RFC/CONTEXT)

- 4 trunk-based slices; S1 def+sprawl-lint gates all.
- Sprawl-lint `unregistered-feature-candidate` (warn): per-domain files with `domain=`/no-`feature=`/≥N symbols (N=5).
- ai_agents: move `tools/ai_techwriter → src/beadloom/ai_agents/ai_techwriter/`; **retire vendoring** (ships in package; `python -m beadloom.ai_agents.ai_techwriter`); recipe/provisioner → package-data; boundary rule.
- onboarding features: config-check, branch-protection, agentic-flow-setup, ai-techwriter-setup.
- ACTIVE-table maintenance in MCP checkpoint/complete_bead + coordinator adoption. Orchestration stays main-loop (G4).

## Progress Log

- 2026-06-11: PRD/RFC/CONTEXT/PLAN approved; epic `beadloom-mukc` + 13 beads + DAG; branch `features/BDL-051`. W1 (S1) launched (.1 dev).

- 2026-06-11: **S1 MERGED** (#7). Gate caught a config-drift (AGENTS.md stale after new rule) my local sync/lint missed → fixed via config-check --fix (lesson: run full `beadloom ci` pre-push). ai-techwriter on the slice ran ~16min (wide domain-doc drift) → established [skip-on-slices] policy, docs → .13.

- 2026-06-11: **S2 / BEAD-04 dev impl complete (NOT committed).** `git mv tools/ai_techwriter → src/beadloom/ai_agents/ai_techwriter/` (history preserved) + `ai_agents/__init__.py`; recipe.yaml + provision-runner.sh now ride as package data (importlib.resources; `provider.default_recipe_path` rewritten; pyproject `force-include` + verified in built wheel). All imports/CI/templates → `beadloom.ai_agents.ai_techwriter`; console script `beadloom-ai-techwriter`. **Vendoring RETIRED**: removed HARNESS_MODULES/vendor_harness/sync_vendored_harness + `templates/ai_techwriter/harness/*.py.txt`; setup-ai-techwriter now emits workflow+guide+operator recipe/provisioner (no Python vendored); tests updated to no-vendoring reality. Graph: `ai_agents` domain + `ai-techwriter` feature nodes+edges+README+SPEC; per-module `domain=`/`feature=` annotations. Boundary: `core-no-import-ai-agents` + `application-no-import-ai-agents` forbid_import rules (error severity; fnmatch `[!a]*` / `a[!i]*` exclude ai_agents self-imports). Full `beadloom ci` rc0 (only pre-existing S3-deferred warn-level sprawl/size warnings), doctor rc0, lint --strict rc0, sync-check rc0 (fixpoint), config-check --fix regenerated CLAUDE.md/AGENTS.md packages list. 3696 pytest pass, ruff+mypy clean. Handoff → .5 (test).
