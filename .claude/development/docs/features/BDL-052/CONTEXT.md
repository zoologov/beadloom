# CONTEXT: BDL-052 (EPIC) — Usable doc-flow

> **Status:** Approved
> **Created:** 2026-06-14
> **PRD/RFC:** ./PRD.md · ./RFC.md

---

## State

- **AI tech-writer harness:** `src/beadloom/ai_agents/ai_techwriter/` (BDL-051 S2 moved it into the package). `scope.py` `discover_scope` → `beadloom sync-check --json` → grouped `DriftItem`s (no-ops on empty drift). `runner._repair_each_doc` loops stale docs **sequentially**, one Goose session each; `classify_verdict` → {ok/flagged/infra}. Invoked `python -m beadloom.ai_agents.ai_techwriter`. bd via `services/bd_seam.run_bd`.
- **CI (BDL-049/050):** `.github/workflows/ci.yml` — `gate ∥ tests(3.10-3.13) ∥ site-build` → `ai-techwriter` (`needs:` all three; self-hosted `[self-hosted, ai-techwriter]`; `fetch-depth:0`; `uv sync --extra dev --extra languages`; pushes refresh into the PR branch via `AI_TW_PAT`; loop-guard on `[skip ai-techwriter]`/bot author). Required checks (`branch_protection.DEFAULT_STATUS_CHECK_CONTEXTS`) = `gate, tests (3.10..3.13), site-build, ai-techwriter`.
- **Pre-commit hook:** `services/cli.py` `install-hooks` writes `_HOOK_TEMPLATE_WARN`/`_BLOCK` to `.git/hooks/pre-commit` (POSIX sh; `command -v` guards; ruff + mypy + sync-check; BDL-053 added the `active-sync` coherence step). **No pre-push hook today.**
- **Agentic flow scaffold:** `onboarding/agentic_flow_setup.py` vendors the live `.claude/agents/*.md` + `.claude/commands/*` byte-identical into adopter repos (drift-guard test asserts byte-equality). `config_sync.py` generates `.beadloom/AGENTS.md` (canonical, with a preserved `custom` block) + thin IDE adapter pointers (`.cursorrules` etc.). `setup-agentic-flow` / `setup-rules` / `setup-mcp` commands.
- **Cursor capability (verified June 2026):** subagents (own context/tools/model, ~10 parallel) via `.cursor/agents/*.md`; orchestrator flow w/ structured hand-off + foreground/background; MCP; worktrees (3.2) → near-parity with Claude Code for the flow.
- **`code_symbols`:** per-symbol index (powers sync-check `symbols_hash`, rules, ctx). Drift today is file-level. Coverage-lint is **error** (BDL-051) — new modules must be classified nodes + docs.
- **BDL-053 shipped:** `application/active_table.py` (`reconcile_active_tables`, the moved S4 parser) + `beadloom active-sync` + the pre-commit coherence step. The folded follow-up `beadloom-cugq` (P2) lives here as G8.

## Decisions (from PRD/RFC)

- **Hard invariant:** no code in `main` without current docs — enforced by the deterministic **Beadloom Gate** (pre-push hook + CI required check). NOT non-blocking (the first draft's post-merge model was rejected).
- **Local-primary:** the agentic flow runs on the user's own agent (Claude Code / Cursor); the tech-writer step authors docs locally — NO local Goose+Qwen.
- **CI = unchanged fallback + speed:** keep the Goose+Qwen ai-techwriter (fires only on a non-Gate-passing PR); ADD parallelism + cache only.
- **Tool-agnostic:** one canon → per-tool adapters (`.claude/agents/` + `.cursor/agents/`) + drift-guard; full parallel flow on both; inline-sequential floor elsewhere.
- **Symbol-scope:** changed-symbol ∩ doc-referenced-symbol; conservative fallback (ambiguous → include).
- **5 slices:** S1 formalize + pre-push Gate + coordinator loop · S2 tool-agnostic · S3 symbol-scope · S4 CI parallel+cache · S5 `active-sync --stage` + docs.

## Code standards (from CLAUDE.md §0.1)

- Python 3.10+, SQLite, Click, Rich, tree-sitter. pytest (≥80% changed). ruff. mypy --strict (no `Any`/`# type: ignore` w/o reason). DDD boundaries (`lint --strict`). No bare except, no `import *`, no mutable defaults. Shell `-f`. Hook templates POSIX sh + `command -v` guards.
- `ai_agents` stays a leaf consumer (forbid_import boundary, BDL-051 S2). New modules classified as nodes + docs (coverage-lint error).

## Constraints / invariants

- **Each slice = an independently-green PR on `ci.yml`**; `main` green by construction. Dogfood: from S1 on, our own pushes go through the pre-push Gate + coordinator loop.
- **CI ai-techwriter logic/verdict/trigger UNCHANGED** — S4 adds only parallelism + cache (seam-mocked tests; no network).
- **Pre-push Gate fail-safe + fast:** blocks on red with an actionable message; `--no-verify` escape documented; safe no-op outside a flow repo; incremental reindex + cache keep it quick.
- **Tool-agnostic correctness floor:** the Gate enforces the invariant on ANY tool; parallel orchestration is the per-tool optimization. Adapters stay drift-guarded against one canon.
- **Symbol-scope never under-refreshes:** conservative fallback; dropped-clean pairs still `sync-update`-baselined so `sync-check` stays honest.
- **Quality preserved:** Qwen + extended thinking settled (BDL-050); speed from scope + parallelism + rarity, not model/thinking changes.
- Anonymize third-party project names in committed artifacts.

## Definition of done

The flow is shipped as deterministic tools (no routine `[skip]`); a blocking pre-push `beadloom ci` hook + the coordinator Gate-loop enforce "no code without docs"; the full flow runs on Claude Code AND Cursor (verified end-to-end) via drift-guarded adapters from one canon; symbol-scope kills the god-file fan-out (local + CI); the CI fallback agent is parallel + cached and fires only on non-Gate-passing PRs; `active-sync --stage` stages only its paths; docs/CHANGELOG/ROADMAP + adopter guide updated; full `beadloom ci` + `ci.yml` green per slice.
