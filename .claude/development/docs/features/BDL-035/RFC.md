# RFC: BDL-035 — Multi-Agent Process Modernization

> **Status:** Approved
> **Created:** 2026-05-29

---

## Overview

Modernize the project's multi-agent process docs (`.claude/CLAUDE.md`, `.claude/commands/*`) and add first-class role subagents (`.claude/agents/*`) so the workflow maximally uses **Beads 1.0.4**, current **Claude Code**, skills, and **Beadloom** (dogfooding). No Beadloom product code changes here — that is Epic 2 (Phase 0).

## Motivation

### Problem
See PRD. The process predates bd 1.0.4 and re-implements coordination that bd now provides natively, references a stale subagent tool (`Task`), under-uses Beadloom, and contains an honesty gap (§E).

### Solution
A documentation/configuration refactor across `.claude/`, grounded in commands verified live against `bd 1.0.4` and `beadloom 1.9.0`. Each role becomes a first-class subagent; the coordinator orchestrates via bd's native `swarm`/`gate`/`merge-slot`.

## Technical Context

### Constraints
- Beads 1.0.4 (embedded Dolt), Beadloom 1.9.0, current Claude Code (Agent tool, auto-compaction, `.claude/agents/`).
- Methodology unchanged (PRD/RFC/CONTEXT/PLAN/BRIEF + beads).
- Every documented command MUST exist in the installed versions — the implementation bead **verifies each `bd`/`beadloom` invocation via `--help` before writing it** (no assumed flags).

### Affected Areas
`.claude/CLAUDE.md`, `.claude/commands/{coordinator,dev,review,test,tech-writer,checkpoint,task-init,templates}.md`, new `.claude/agents/*`. (`epic-init.md` is deprecated — untouched.)

## Proposed Solution

### Approach

**1. Single source of truth for roles (anti-drift).**
`.claude/agents/{dev,test,review,tech-writer}.md` become the **canonical** role definitions: frontmatter (`name`, `description`, scoped `tools`, optional `model`) + the working protocol as the subagent system prompt. The existing `.claude/commands/*` skills become **thin wrappers** that say "adopt role X — follow `.claude/agents/X.md`", so the protocol lives in exactly one place (the review flagged hand-maintained adapter drift, e.g. #93). The coordinator launches them via the `Agent` tool with `subagent_type: dev|test|review|tech-writer`.

**2. Claude Code currency (`coordinator.md`).**
- `Task(...)` → `Agent(...)` (fields `subagent_type` / `run_in_background` / `description` / `prompt`).
- Reframe the `/compact`-between-waves section around **automatic compaction + file memory** as the real protection (keep the background-agent + 2-3-line return-contract rules — still correct and valuable). Mention optional `TaskCreate`/`TaskUpdate` for in-session progress.

**3. bd 1.0.4 native coordination (`coordinator.md`).**
| Workflow need | bd 1.0.4 primitive |
|---|---|
| Epic → DAG → waves | `bd swarm create` / `swarm validate` (pre-flight DAG check) / `swarm status` (progress) |
| Gate review→tech-writer; wait on CI | `bd gate` (`human`/`bead` gate for review→docs; `gh:run`/`gh:pr` for CI — ties to STRATEGY-3 CI gate) |
| Serialize parallel merges/commits | `bd merge-slot create/acquire/release` (prevents agent merge races — the exact problem the old "overflow protection" worked around) |
| Epic completion | `bd epic status` / `epic close-eligible` |

**4. Setup + audit (`CLAUDE.md`, role docs).**
- Document one-time `git config beads.role maintainer` (contributor for non-owners).
- Close steps use `bd close <id> --session "$CLAUDE_SESSION_ID" --suggest-next`; dev start may use `bd ready --claim`.

**5. Beadloom dogfooding placements.**
| Command | Where | Purpose |
|---|---|---|
| `beadloom diff <git-ref>` | `/review` | show graph/arch changes introduced by the bead |
| `beadloom snapshot save` / `compare` | coordinator (wave start/end) | track architecture evolution across waves |
| `beadloom install-hooks` | `CLAUDE.md` setup | enforce lint/sync-check at commit (bridge to STRATEGY-3 CI) |
| `beadloom link` (bead ↔ node) | `/dev` claim step | bind the claimed bead to the graph node it touches |

**6. §E coherence note (`dev.md`, `review.md`).**
Replace "lint --strict enforces boundaries" with an honest statement: boundaries are *checked* by `beadloom lint --strict`; cycle/layer rules are restored to `error` in **Epic 2 / Phase 0** (`STRATEGY-3.md` §Phase 0) — until then also verify cycles via `beadloom doctor`. (Note removed when Phase 0 merges.)

**7. task-init efficiency.**
Document `bd create --graph <plan.json>` to create the whole bead DAG in one command (replacing the manual create+`dep add` loop), keeping the "beads only after PLAN approved" gate.

### Changes

| File / Area | Change |
|---|---|
| `.claude/CLAUDE.md` | setup (`beads.role`, `install-hooks`); bd essentials += swarm/gate/merge-slot, `--session`, `ready --claim`; beadloom essentials += diff/snapshot/link; agents reference |
| `coordinator.md` | major: swarm/gate/merge-slot orchestration; `Agent` tool; `/compact` reframe; snapshot per wave |
| `.claude/agents/{dev,test,review,tech-writer}.md` | NEW canonical role subagents (frontmatter + protocol) |
| `commands/{dev,test,review,tech-writer}.md` | become thin wrappers → `.claude/agents/*` |
| `dev.md` (wrapper aside) | `ready --claim`, `--session` close, §E note, `link`, `install-hooks` |
| `review.md` | `beadloom diff`, §E note, `--session` |
| `test.md` / `tech-writer.md` | `--session`; tech-writer already strong |
| `checkpoint.md` | `--session`; `/compact` reframe |
| `task-init.md` | `bd create --graph`; `beads.role` setup ref |

### API Changes
None (process/config only).

## Alternatives Considered

### Option A: Keep roles only as skills (no `.claude/agents/`)
Rejected: misses the current Claude Code first-class subagent model (scoped tools, cleaner coordinator context, isolated failures) — a core goal.

### Option B: Duplicate the role protocol in both `commands/*` and `agents/*`
Rejected: two copies drift (the review's adapter-drift lesson). Single source of truth in `agents/*` with thin skill wrappers.

### Option C: Document swarm/gate/merge-slot as target but keep manual orchestration
Partially adopted as a **fallback**: if a primitive proves too rough on the smoke test, document it as the target and keep a lightweight manual path, labeled honestly ("not fully wired yet") per the `honest ≠ complete` principle — rather than blocking the whole epic.

## Risks

| Risk | Probability | Impact | Mitigation |
|---|---|---|---|
| Assumed swarm/gate/merge-slot CLI differs from real | Med | Med | Impl bead verifies each subcommand via `--help` before documenting; smoke test exercises them |
| `agents/*` ↔ `commands/*` drift | Low | Med | Single source of truth; wrappers are 3-5 lines |
| §E note left stale after Phase 0 | Med | Low | Tracked; removed in Epic 2 |
| Scope creep / over-ceremony (review's warning) | Med | Med | Changes proportionate; no new methodology; smoke test, not exhaustive |

## Open Questions

| # | Question | Decision |
|---|----------|----------|
| Q1 | Canonical role location | Decided: `.claude/agents/*` canonical, `commands/*` thin wrappers |
| Q2 | Per-agent model assignment | Decided: **Opus for all four roles** (anti-drift; the project's currency is accuracy/honesty, and test/docs are the highest drift-risk surfaces). Sonnet only as an explicit per-bead opt-in for mechanical + beadloom-verified work (e.g. F4 CI tech-writer). |
| Q3 | Adopt swarm/gate/merge-slot now vs target-with-fallback | Decided: adopt; fallback per Option C if a primitive is too rough |
