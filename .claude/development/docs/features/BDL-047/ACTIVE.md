# ACTIVE: BDL-047 (F4.1) — AI tech-writer in CI

> **Last updated:** 2026-06-04

---

## Current Focus

- **Phase:** Wave 3 (dev, parallel) — BEAD-03 (Goose recipe+Qwen) ∥ BEAD-06 (dashboard widget). W1+W2 done+committed.
- **Coordinator:** main loop (multi-agent)
- **Parent:** `beadloom-zqlr`
- **Blockers:** none for dev. BEAD-09 (dogfood) gated on owner-provided `QWEN_API_KEY` + runner(s).

## Beads

| Bead | Role | Status |
|------|------|--------|
| beadloom-zqlr.1 | dev — mark-synced CLI | ✓ done (W1) |
| beadloom-zqlr.2 | dev — harness + adapter + run-record | ✓ done (W2) |
| beadloom-zqlr.3 | dev — Goose recipe + Qwen | in progress (W3) |
| beadloom-zqlr.4 | dev — both CI wrappers (GH+GL) | blocked ← 2,3 |
| beadloom-zqlr.5 | dev — setup-ai-techwriter | blocked ← 3,4 |
| beadloom-zqlr.6 | dev — dashboard widget (G9) | in progress (W3 ∥) |
| beadloom-zqlr.7 | test | blocked ← 1-6 |
| beadloom-zqlr.8 | review | blocked ← 7 |
| beadloom-zqlr.9 | dogfood (needs key) | blocked ← 8 |
| beadloom-zqlr.10 | tech-writer | blocked ← 9 |

## Waves

W1 `01` → W2 `02` → W3 `03` → W4 `04` → W5 `05` → W6 `06`(∥ from 02) → test `07` → review `08` → dogfood `09` → docs `10`.

## Key decisions (from PRD/RFC/CONTEXT)

- Split: Beadloom substrate (Goose-agnostic) + deterministic harness + Goose (per-doc rewrite only), bounded by gate.
- **Dual-platform GitHub + GitLab first-class** (platform-agnostic harness + per-platform wrapper + PR/MR adapter). GitLab validated on team's private repo.
- Goose + Qwen3.7-Plus (external), thinking ENABLED (quality first), no tiering, **no Beads in runtime**.
- Honesty by gate: proposal → `sync-check`0 + `beadloom ci` → PR/MR; no auto-merge; sync-check = freshness not correctness.
- **G9 (variant A):** harness emits honest run-record (tokens = fact from API; $ = labeled estimate); dashboard widget shows activity + token spend.
- Only core changes: mark-synced CLI (closes UX#106) + `setup-ai-techwriter`.

## Progress Log

- 2026-06-04: docs approved (PRD/RFC/CONTEXT/PLAN), 10 beads + DAG created. Dual-platform + G9 token-widget folded in (aligned with team doc `BDL-AI-AGENTS-ARCHITECTURE.md`). W1 pending start.
- 2026-06-10: BEAD-03 done (W3). Real Goose integration: `tools/ai_techwriter/recipe.yaml` (per-doc tech-writer recipe, constrained allow/deny tool list, thinking enabled), `tools/ai_techwriter/provider.py` (`ProviderConfig`/`qwen_provider` — Qwen3.7-Plus via DashScope OpenAI-compatible endpoint, key from env `QWEN_API_KEY`, generous runaway caps). `GooseAgentRunner` now builds the real `goose run` command (recipe + packet param + caps) + provider env, parses usage→`AgentResult`, returns empty result on failure (graceful → still-stale/retry). `run_command` gained optional `env` overlay. 12 new tests (provider) + 1 new + 4 updated (seams); coverage 95% on changed code; full suite 3281 green. No graph/src changes (stale `application` doc is BEAD-06's, untouched).
