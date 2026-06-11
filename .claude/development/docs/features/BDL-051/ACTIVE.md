# ACTIVE: BDL-051 (EPIC) — Beadloom governs itself

> **Last updated:** 2026-06-11

---

## Current Focus

- **Phase:** S1 complete (dev/test/review ✓) → opening PR #? (ci.yml gates + ai-techwriter refreshes drift). Next: S2.
- **Branch:** `features/BDL-051` (trunk-based; each slice is its own PR via ci.yml).
- **Coordinator:** main loop (multi-agent).
- **Parent:** `beadloom-mukc`

## Beads

| Bead | Role | Status |
|------|------|--------|
| beadloom-mukc.1 | dev — S1 def + sprawl lint | ✓ done |
| beadloom-mukc.2 | test — S1 lint | ✓ done |
| beadloom-mukc.3 | review — S1 | ✓ done (PASS-WITH-FIXES; 2 minor→S3/.13) |
| beadloom-mukc.4 | dev — S2 ai_agents move + retire vendoring | blocked ← 3 |
| beadloom-mukc.5 | test — S2 | blocked ← 4 |
| beadloom-mukc.6 | review — S2 | blocked ← 5 |
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
