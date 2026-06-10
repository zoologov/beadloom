# ACTIVE: BDL-047 (F4.1) — AI tech-writer in CI

> **Last updated:** 2026-06-04

---

## Current Focus

- **Phase:** Wave 1 (dev) — BEAD-01 (non-interactive mark-synced CLI)
- **Coordinator:** main loop (multi-agent)
- **Parent:** `beadloom-zqlr`
- **Blockers:** none for dev. BEAD-09 (dogfood) gated on owner-provided `QWEN_API_KEY` + runner(s).

## Beads

| Bead | Role | Status |
|------|------|--------|
| beadloom-zqlr.1 | dev — mark-synced CLI | ready |
| beadloom-zqlr.2 | dev — harness + adapter + run-record | blocked ← 1 |
| beadloom-zqlr.3 | dev — Goose recipe + Qwen | blocked ← 2 |
| beadloom-zqlr.4 | dev — both CI wrappers (GH+GL) | blocked ← 2,3 |
| beadloom-zqlr.5 | dev — setup-ai-techwriter | blocked ← 3,4 |
| beadloom-zqlr.6 | dev — dashboard widget (G9) | blocked ← 2 |
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
