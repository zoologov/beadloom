# RFC: BDL-052 (EPIC) — Usable doc-flow: tool-agnostic local authoring + Gate enforcement + CI fallback boost

> **Status:** Approved
> **Created:** 2026-06-14
> **PRD:** ./PRD.md
> **Note:** replaces the earlier non-blocking/post-merge draft (rejected — the doc-freshness invariant is hard, Gate-enforced).

---

## Summary

Make the doc-flow usable + reproducible without weakening "no code in `main` without current docs". Two execution layers, one hard invariant enforced by a deterministic tool:

- **Local (primary):** the Beadloom agentic flow runs on the **user's own coding agent** (Claude Code, Cursor, …). The tech-writer step authors docs there — no local Goose+Qwen. A **blocking pre-push `beadloom ci` Gate** is the enforcement: red Gate ⇒ push blocked ⇒ coordinator runs tech-writer ⇒ re-Gate ⇒ green ⇒ PR.
- **CI (fallback, UNCHANGED logic + boosted):** the BDL-049/050 Goose+Qwen ai-techwriter stays; it fires only when a PR arrives not passing the Gate. We only ADD speed (parallel sessions, cached setup).
- **Shared:** symbol-level scope so a god-file edit refreshes only the docs that depend on what changed — for both the local agent and the CI agent.

Five slices: **S1** formalize the flow + pre-push Gate hook + coordinator loop · **S2** tool-agnostic (Claude Code + Cursor) · **S3** symbol-scope · **S4** CI agent parallel + cache · **S5** folded `--stage` fix + docs.

## Decisions on the open questions

1. **Tool-agnostic mechanism → one canonical flow, per-tool adapters generated from it; FULL orchestration on tools that have subagents (Claude Code AND Cursor).** Verified (June 2026): Cursor 2.4+/3.x has first-class **subagents** (own context/tools/model, up to ~10 parallel) declared in **`.cursor/agents/*.md`**, an **orchestrator flow** with structured hand-off + **foreground/background** modes, MCP support, and **worktrees** (3.2) — i.e. near-parity with Claude Code's `Agent`-spawn for our flow. So the earlier "Cursor degrades to sequential" assumption is wrong.
   - **Decision:** keep ONE **canonical source** for the roles + coordinator loop (the role protocols in `.beadloom/AGENTS.md` + the live `.claude/` set), and **generate per-tool adapters** from it: `.claude/agents/*.md` + `.claude/commands/*` (Claude Code) and **`.cursor/agents/*.md` + Cursor rules** (Cursor), with a **drift-guard** asserting the adapters stay byte-consistent with the canon (same pattern as the BDL-048 vendoring guard). Both tools run the **full parallel flow** (coordinator → dev/test/review/tech-writer as subagents). The portable substrate (MCP process-tools, `beadloom` Gate, `bd`) is unchanged. `setup-agentic-flow --tool claude|cursor[,…]` scaffolds the chosen adapter(s).
   - **Graceful floor:** a tool WITHOUT subagents still runs the flow inline-sequentially from AGENTS.md — same CORRECTNESS (the Gate enforces the invariant regardless), just no parallelism. MVP ships **Claude Code + Cursor at full parity**; the inline floor covers the rest.
2. **Pre-push Gate ergonomics → a dedicated `pre-push` hook running `beadloom ci`, scoped + fast, distinct from pre-commit.** `install-hooks --pre-push` (and the default `install-hooks` installs both). It runs the Gate (reindex incremental → lint → coverage-lint → sync-check → doctor) and **exits non-zero to block the push** on red, with an actionable message ("docs stale for <refs> — run the tech-writer / `/coordinator` then re-push"). Avoid double work: pre-commit stays the light check (lint + sync-check warn); **pre-push is the authoritative blocking Gate**. Keep it fast via incremental reindex + (S4) index cache; `--no-verify` remains the escape hatch (documented, discouraged).
3. **Coordinator loop encoding → a deterministic state machine in `/coordinator` (+ AGENTS.md prose for non-Claude).** Formalize: `for each wave: dev → test → review`; then `tech-writer`; then `run Beadloom Gate`; `while Gate red: run tech-writer on the drifted refs; re-run Gate`; `Gate green → push → PR`. This is encoded as explicit tool steps (call `beadloom ci`, branch on its exit code), not narrative the agent must remember. The same loop is written tool-neutrally in AGENTS.md so a Cursor agent follows it inline.
4. **Symbol-level scope → narrow `sync-check`'s stale set with a changed-symbol ∩ doc-referenced-symbol filter (conservative).** `code_symbols` holds per-symbol entries; drift today is file-level (`symbols_hash`). New: compute the SET of symbols whose hash changed in the touched file (vs the `--since` baseline) ∩ the symbols the doc references (its chunks/links); empty ∩ ⇒ the doc didn't depend on the change ⇒ drop from the agent run and `sync-update`-baseline it deterministically (so `sync-check` still goes green). **Conservative fallback:** ambiguous attribution ⇒ keep the doc in scope. Lives in `ai_techwriter/scope.py` (+ a reusable helper) so BOTH the local flow and the CI agent benefit.
5. **CI parallelism + cache → bounded executor (default 3) with back-off; hash-keyed index cache.** `runner`: replace the sequential `_repair_each_doc` with a bounded pool, per-session 429/5xx exponential back-off, global rate guard for the $30 plan, RAM-aware (8GB VPS ≈ 3 sessions). `ci.yml` ai-techwriter job: `setup-uv` cache + cache `.beadloom/beadloom.db` keyed on hash(`.beadloom/_graph/**` + `src/**` + `docs/**`); hit ⇒ skip reindex.
6. **Slice order → S1 (flow + Gate hook + loop) → S2 (tool-agnostic) → S3 (scope) → S4 (CI boost) → S5 (fix + docs).** S1 lands the invariant-as-tool (the philosophy) first; S2 broadens it; S3 is the shared speed win; S4 speeds the rare CI fallback; S5 folds the minor + docs.

## Thread A — Formalize the flow as tools (S1)

- **`services/cli.py` `install-hooks`:** add a **`pre-push`** hook template running `beadloom ci` (block-on-red) with the actionable message; `--pre-push` / `--pre-commit` selectors, default installs both. Idempotent; `command -v` guards; safe no-op outside a flow repo.
- **`.claude/commands/coordinator.md`** (+ re-vendor to the agentic-flow templates): encode the Gate-enforced loop (§Decision 3) as explicit steps. The coordinator calls `beadloom ci`, branches on exit code, runs the tech-writer role on the drifted refs, re-gates.
- Document the canonical flow (`task-init → coordinator → dev/test/review → tech-writer → push → Gate`) as the shipped standard.

## Thread B — Tool-agnostic (S2)

- **Canonical roles + coordinator loop** in `.beadloom/AGENTS.md` (tool-neutral) as the single source; **generate per-tool adapters** from it: the Claude-Code set (`.claude/agents/*.md` + `.claude/commands/*`, as today) and a **Cursor set** (`.cursor/agents/*.md` for dev/test/review/tech-writer + Cursor rules + the coordinator as a Cursor orchestrator mode). A **drift-guard test** asserts every adapter matches the canon (BDL-048 vendoring-guard pattern), so a role edit can't silently desync across tools.
- **`onboarding`: `setup-agentic-flow --tool claude|cursor[,…]`** scaffolds the chosen adapter(s); `config_sync` keeps AGENTS.md + adapters in sync. Both tools run the full parallel coordinator→roles flow; docs note the inline-sequential floor for tools without subagents.
- Verify the Cursor path end-to-end (a real task-init→coordinator→roles→Gate run on Cursor) as the S2 acceptance.

## Thread C — Symbol-scope (S3)

- `ai_agents/ai_techwriter/scope.py` + a shared scope helper: `narrow_by_changed_symbols(stale, project_root, since)`; baseline-the-dropped-clean; conservative fallback. Reused by the local flow's tech-writer invocation + the CI agent. Unit-tested incl. the god-file case.

## Thread D — CI agent boost (S4)

- `ai_agents/ai_techwriter/runner.py`: bounded parallel sessions + back-off (seam-mocked tests). `.github/workflows/ci.yml` (ai-techwriter job): uv + index cache. No change to the agent's logic/verdict/trigger — pure speed.

## Thread E — Folded fix + docs (S5)

- `services/cli.py`: `beadloom active-sync --stage` (stage exactly `ReconcileResult.changed_files` + the jsonl); both hook templates use it (closes `beadloom-cugq`).
- Docs/CHANGELOG/ROADMAP + adopter guide: the formalized flow, pre-push Gate, tool-agnostic setup, scope/parallel/cache knobs, local-primary/CI-fallback model.

## Component / file impact

| Component | Change | Slice |
|-----------|--------|-------|
| `services/cli.py` `install-hooks` | NEW pre-push Gate hook (block) + selectors | S1 |
| `.claude/commands/coordinator.md` (+ re-vendor) | Gate-enforced loop encoded | S1 |
| `.beadloom/AGENTS.md` + roles + Cursor adapter | tool-neutral flow + per-tool adapters | S2 |
| `onboarding/{agentic_flow_setup,config_sync,branch_protection?}.py` + templates | `--tool` scaffolding, sync | S2 |
| `ai_agents/ai_techwriter/scope.py` (+ shared helper) | symbol-level narrowing | S3 |
| `ai_agents/ai_techwriter/runner.py` | bounded parallel + back-off | S4 |
| `.github/workflows/ci.yml` (ai-techwriter job) | uv + index cache | S4 |
| `services/cli.py` + hook templates | `active-sync --stage` (closes `beadloom-cugq`) | S5 |
| docs/guides + CHANGELOG/ROADMAP + adopter guide | the model + knobs | S5/G9 |

## Alternatives considered

- **Non-blocking / post-merge docs (the first draft).** Rejected: lets `main` hold transient undocumented code — violates the hard invariant.
- **Retire the CI Goose+Qwen agent (local-only).** Rejected: keep it as the mandatory fallback for PRs that bypass the local flow (external contributors); it just runs rarely now.
- **Local Goose+Qwen.** Rejected: the dev already has a coding agent; the local tech-writer is that agent performing the role.
- **Single tool-neutral prose only (no per-tool subagent adapters).** Rejected: Cursor HAS subagents/orchestration (verified June 2026), so we'd be leaving full parity on the table; we ship real `.claude/` + `.cursor/` adapter sets (from one canon) + a drift-guard, with an inline-sequential floor for subagent-less tools.
- **thinking-OFF / model swap for speed.** Rejected (PRD non-goal): quality-first; speed comes from scope + parallelism + rarity.

## Risks & mitigations

- **Pre-push Gate too slow / annoying.** → incremental reindex + (S4) index cache; scope the check; `--no-verify` escape (documented). It runs on push (less frequent than commit).
- **Tool-agnostic upkeep** (two adapter sets drift apart). → ONE canonical source + a drift-guard test (per-tool adapters generated/verified from the canon, BDL-048 pattern). Cursor has subagent/orchestration parity (verified June 2026), so full parity is achievable — the risk is maintenance, not capability; the drift-guard handles it. Tools lacking subagents fall to the inline-sequential floor (still correct).
- **Symbol-scope UNDER-refreshes.** → conservative fallback (ambiguous → include); dropped-clean pairs still `sync-update`-baselined; measure on real PRs.
- **Parallel CI sessions: rate-limit / OOM.** → low default (3), 429 back-off, RAM-aware, fall back to sequential on repeated 429.
- **Stale index cache.** → hash-keyed on graph+src+docs; miss → full reindex.
- **Coordinator loop infinite-loops** (Gate never greens). → bounded retries on the tech-writer→re-Gate loop; surface a clear failure (flagged) instead of spinning.
- **New modules (scope helper, etc.) trip coverage-lint (error).** → classify as nodes + docs in-slice (BDL-051 lesson).

## Rollout

Epic, 5 trunk-based slices (each a PR on `ci.yml`, dev→test→review; one tech-writer pass): **S1** flow formalization + pre-push Gate hook + coordinator loop → **S2** tool-agnostic (Claude+Cursor) → **S3** symbol-scope → **S4** CI agent parallel+cache → **S5** `--stage` fix + docs. Dogfood throughout: from S1 on, Beadloom's own pushes go through the pre-push Gate + the coordinator loop. Each slice green on `ci.yml`.

---

## Addendum (owner discussion, 2026-06-14) — role configurator + rule restoration

This **expands Threads A/B** and re-scopes the slices. Confirmed with the owner.

### Why
Two findings: (1) the `commands/`→`agents/` repackaging (BDL-035) **dropped most agent quality rules** — old `/dev` was 340 lines (DDD, Code Patterns, Clean Code, Naming, annotation steps, API-CHANGE-log), current `agents/dev.md` is 44; same for test/review/tech-writer. (2) The flow must run across **different stacks + tools** for the owner's team (Python/FastAPI; JS/TS/Vue3; later Kotlin/Swift/C++/RN/FSD/Apollo; Claude Code + Cursor). Hardcoding Python+Claude into the roles is wrong.

### Design — roles = CORE + OVERLAYS + TOOL-adapters, driven by `.beadloom/flow.yml`
- **CORE role defs (universal, restored + modernized from the 1.9.0 review):** dev/test/review/tech-writer protocols that DON'T depend on stack/tool — DDD + architecture-discovery, TDD/AAA, **annotation discipline** (`# beadloom:domain/feature/component=` — the dev emits these by construction), Clean Code, naming PRINCIPLES, validation/Gate loop, API-CHANGE-log (dev→review/tech-writer), review checklists (readability/architecture/typing/error-handling/security/testing/doc-freshness), tech-writer two-sources-staleness + update-workflow + parallel-exec, checkpoints. Modernized to today's best practices (not a verbatim paste).
- **ARCHITECTURE overlays — FIRST-CLASS, first batch: `ddd` AND `fsd` (peers, owner requirement).** Architecture methodology is its own config dimension: **DDD** (Domain-Driven Design — backend, e.g. Python/FastAPI: domains/layers, dependency direction, boundary imports) and **FSD** (Feature-Sliced Design — frontend, e.g. Vue/TS: layers `app → processes → pages → widgets → features → entities → shared`, the lower-cannot-import-higher rule, slice/segment structure). The CORE role says "respect the project's declared architecture + emit the right `# beadloom:` annotations"; the `ddd`/`fsd` overlay supplies the specific layer rules + the annotation vocabulary for that methodology. (Note: deeper Beadloom GRAPH-model support for FSD layers — coverage-lint/boundaries understanding FSD slices — may be a follow-up; this epic delivers the FSD **role overlay** at parity with DDD.)
- **STACK/framework overlays, first batch:** `python`, `fastapi`, `javascript`, `typescript`, `vuejs`. Each adds stack-specific Code Patterns + lint/type/test commands (Python: ruff/mypy/pytest, dataclasses, SQL-params, yaml.safe_load; TS: eslint/tsc/vitest; Vue: SFC/composition patterns; FastAPI: router/dep-injection/pydantic; …). (Kotlin/Swift/C++/RN/Apollo-Federation next.)
- **TOOL adapters, first batch:** `claude` (`.claude/agents/*.md` + `.claude/commands/*`) and `cursor` (`.cursor/agents/*.md` + Cursor rules + coordinator orchestrator mode), GENERATED from CORE+selected overlays.
- **Config `.beadloom/flow.yml`:** `tools: [claude, cursor]`, `architecture: [ddd]` (backend) or `[fsd]` (frontend), `stack: [python, fastapi]` or `[javascript, typescript, vuejs]`, `quality: [clean-code, tdd]`. `beadloom setup-agentic-flow` **composes** CORE + architecture + stack overlays → writes the per-tool adapters; a **drift-guard test** keeps every generated adapter consistent with `CORE+overlays` (BDL-048 pattern). `config-check` covers `flow.yml`.

### Parallelism (owner point 1)
`coordinator.md` already specifies wave-based parallel dev beads + `merge-slot`; the gap was execution. S1 makes the parallelism **explicit + mandatory** in the coordinator loop ("independent ready beads in the same wave → launch concurrently"), and the coordinator (me) actually uses it.

### Re-scoped slices (was 5 → now 6)
- **S1 — flow mechanics:** pre-push Gate hook (block) + coordinator Gate-loop + **explicit parallelism**.
- **S2 — CORE roles (restore + modernize):** review 1.9.0 dev/test/review/tech-writer → modernized tool/stack-neutral CORE role defs (incl. annotation discipline + API-CHANGE-log).
- **S3 — configurator:** `.beadloom/flow.yml` (`architecture: [ddd|fsd]` + `stack` + `tools`) + architecture overlays (`ddd`, `fsd` — peers) + stack overlays (`python, fastapi, javascript, typescript, vuejs`) + compose → `.claude/agents/` + `.cursor/agents/` + `setup-agentic-flow --tool/--stack/--architecture` + drift-guard.
- **S4 — symbol-scope** (shared local + CI).
- **S5 — CI agent parallel + cache.**
- **S6 — `active-sync --stage` (closes `beadloom-cugq`) + epic docs (tech-writer).**

Source for the restoration review: `git show cb4f0a6:.claude/commands/{dev,test,review,tech-writer}.md` (340/275/166/193 lines).
