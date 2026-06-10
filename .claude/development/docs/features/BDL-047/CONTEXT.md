# CONTEXT: BDL-047 (F4.1) — AI tech-writer in CI

> **Status:** Approved
> **Created:** 2026-06-04
> **PRD:** ./PRD.md · **RFC:** ./RFC.md

---

## State

- **Phase:** planning → dev
- **Roadmap:** P0 (agentic cluster), serves north-star (a) — solo multi-agent flow.
- **Builds on:** the existing doc_sync engine + `sync-check --json`, `docs polish --format json`, `ctx`/`why`, `beadloom ci`, and the F4.1 fixpoint loop-invariant (editing a domain doc re-stales all its pairs → `mark_synced_by_ref` then re-check to stable 0).

## Key decisions (from PRD/RFC)

- **Split:** Beadloom = substrate (primitives, Goose-agnostic); a **deterministic harness** (`tools/ai_techwriter/`, NOT core) orchestrates scope→loop→fixpoint→gate→PR; **Goose** does only the per-doc rewrite (tool-use), bounded by the gate.
- **Only core change:** a **non-interactive mark-synced CLI** (wraps existing `mark_synced_by_ref`; closes UX #106) + the **`beadloom setup-ai-techwriter`** scaffold (setup-* family, G8).
- **Model:** Goose → **Qwen3.7-Plus** (external OpenAI-compatible/DashScope API); key = CI secret on the VPS runner; **thinking ENABLED (quality first)**; cost bounded by scope + a generous runaway hard-ceiling, **no tiering**.
- **Honesty:** agent output is a proposal; acceptance = `sync-check`→0 **and** `beadloom ci`; **no auto-merge** (PR only); failure-in-budget → PR flagged "needs human". `sync-check` is a *freshness* gate, not a *correctness* gate — human PR review covers correctness.
- **Tool surface (Goose):** read-only code + git read + `beadloom` read commands; **write only to `docs/**`**.
- **CI — dual-platform first-class (GitHub + GitLab).** One platform-agnostic harness; per-platform thin wrapper (`.github/workflows/ai-techwriter.yml` / `.gitlab-ci.yml`) + PR/MR adapter (`gh` / `glab`\|GitLab API) + secret naming (repo secret / CI/CD variable). Self-hosted runner(s) on the VPS; dispatch/manual + schedule; harness + recipe repo-agnostic. (See team doc `BDL-AI-AGENTS-ARCHITECTURE.md`.)
- **Stack:** F4.1 runtime = Goose + Beadloom + Qwen (external). **Beads is NOT used in the F4.1 runtime** — it stays the dev-flow tracker + a future agentic-stack component.

## Standards (from CLAUDE.md §0.1)

- Python 3.10+, SQLite, Click, Rich, tree-sitter. Tests: pytest + pytest-cov (≥80% on new code). TDD.
- ruff (lint + format); mypy --strict. No `Any`/`# type: ignore` without reason; no bare `except`; no mutable default args; no `print()`/`breakpoint()`.
- Gates before commit: `uv run pytest`, `ruff check`, `mypy src/`, then `beadloom reindex && sync-check && lint --strict && doctor` (or `beadloom ci`).
- Commit format: `[BDL-047] <type>: <desc>`.
- **Scope note:** the harness lives in `tools/ai_techwriter/` (Python) — ensure ruff/mypy/pytest cover it (extend the lint/type/test scope beyond `src/` if needed). Core changes (mark-synced CLI, setup command) live in `src/beadloom/`.

## Files in play

- `src/beadloom/…` (doc_sync CLI) — non-interactive mark-synced CLI.
- `src/beadloom/…` (setup) — `beadloom setup-ai-techwriter`.
- `tools/ai_techwriter/` — **NEW**: harness (scope/packet/invoke-Goose/mark-synced/fixpoint/gate/PR) + Goose recipe + provider config.
- `.github/workflows/ai-techwriter.yml` — **NEW** workflow.
- Tests: `tests/` mirrors (mark-synced CLI, setup command, harness with Goose/model **mocked**).
- Docs: `docs/guides/ai-techwriter.md` (getting-started), CHANGELOG, ROADMAP status (tech-writer).

## Constraints

- **The live model call needs a secret** (`QWEN_API_KEY`). Dev/test mock Goose + the model (deterministic). The **real end-to-end dogfood (G6) requires the key** → run by the main loop / owner, NOT a sandboxed subagent (subagents hold no secrets). GitHub path is dogfooded on Beadloom's own repo; **the GitLab path is validated on the team's private GitLab repo** (Beadloom itself is on GitHub) — owner provides the runner(s) + key.
- Every dev step keeps Beadloom green on its own `beadloom ci` (honest ≠ complete; dogfood = acceptance).
- Docs-only writes by the agent (never `src/`).
- Anonymization: no private project names in committed artifacts (working tree + history).

## Blockers

- None for dev waves. The end-to-end dogfood (BEAD-08) is gated on the owner providing `QWEN_API_KEY` + a registered VPS runner (or running the loop locally with the key).

## UX dogfooding

- Log friction in `.claude/development/BDL-UX-Issues.md` (running total currently 131). The mark-synced CLI closes **#106**; the dogfood may close doc-debt **#130/#131** by producing a refresh PR.
