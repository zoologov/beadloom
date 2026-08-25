# ACTIVE: BDL-048 — Agentic-flow packaging

> **Last updated:** 2026-06-10

---

## Current Focus

- **Phase:** W1 (parallel) — BEAD-01 (setup-agentic-flow scaffold + vendor + drift-guard) ∥ BEAD-03 (MCP process-tools + bd seam).
- **Coordinator:** main loop (multi-agent).
- **Parent:** `beadloom-jxz2`
- **Blockers:** none for W1.

## Beads

| Bead | Role | Status |
|------|------|--------|
| beadloom-jxz2.1 | dev — setup-agentic-flow scaffold + vendor + drift-guard | ✓ done |
| beadloom-jxz2.2 | dev — config-check integration | ✓ done |
| beadloom-jxz2.3 | dev — MCP process-tools + bd seam | ✓ done |
| beadloom-jxz2.4 | test | ✓ done |
| beadloom-jxz2.5 | review | ✓ done |
| beadloom-jxz2.6 | dogfood | ✓ done |
| beadloom-jxz2.7 | tech-writer | ✓ done |

## Waves

W1 `.1 ∥ .3` → W2 `.2` → test `.4` → review `.5` → dogfood `.6` → tech-writer `.7`.

## Key decisions (from PRD/RFC/CONTEXT)

- Flow preserved **1:1** — vendored byte-identical from live `.claude/` + drift-guard. No rewrite.
- `setup-agentic-flow` command (setup-* family); per-project facts via `config_sync` CLAUDE.md regions.
- MCP = deterministic process-tools, NOT orchestration (G4); `complete_bead` advisory-strong, CI = true enforcement (G5).
- Tools-only v1; `bd` via mockable seam.

## Progress Log

- 2026-06-10: PRD/RFC/CONTEXT/PLAN approved; epic `beadloom-jxz2` + 7 beads + DAG created. W1 launched (.1 ∥ .3).
- 2026-06-10: BEAD-01 done — `onboarding/agentic_flow_setup.py` + vendored `templates/agentic_flow/` (4 agents + 4 commands as `*.md.txt`, byte-identical to live `.claude/` + base `CLAUDE.md.txt` with project name templated) + drift-guard test + `setup-agentic-flow` CLI. 16 tests, 100% module cov. NOTE for BEAD-02/tech-writer: `refresh_claude_md` version line uses Beadloom's `__version__` (BDL-UX #92), so a scaffolded repo's CLAUDE.md version is NOT target-derived — name/stack/packages ARE.
