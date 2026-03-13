# PRD: BDL-035 — Multi-Agent Process Modernization (Beads 1.0.4 + Claude Code)

> **Status:** Approved
> **Created:** 2026-05-29

---

## Problem

The multi-agent development process (`.claude/CLAUDE.md` + `.claude/commands/*`) was authored for **Beads 0.49** and an earlier Claude Code. After the migration to **Beads 1.0.4** (SQLite → embedded Dolt) and with current Claude Code, the process under-uses new capabilities and contains stale references. Verified findings:

1. **Stale Claude Code constructs.** `coordinator.md` launches sub-agents with `Task(...)`; the current tool is `Agent(...)` (and `Task*` now denotes the todo-tracking tools). Manual `/compact`-between-waves guidance predates automatic compaction + the 1M context window.
2. **bd 1.0.4 native multi-agent primitives are re-implemented by hand.** `bd swarm` (epic → DAG → waves), `bd gate` (async waits incl. `gh:run`/`gh:pr`), and `bd merge-slot` (serialized conflict resolution) now exist natively — the coordinator currently does this manually.
3. **No `.claude/agents/` subagents.** Roles (`/dev`, `/test`, `/review`, `/tech-writer`) are skills injected into a `general-purpose` agent; current Claude Code supports first-class custom subagents with scoped tools.
4. **Incomplete Beadloom dogfooding.** `beadloom diff`, `snapshot`, `install-hooks`, `link` are unused in the process despite clear fits.
5. **Undocumented required setup.** `git config beads.role maintainer|contributor` is now required (GH#2950) but absent from setup docs; `--session`/`CLAUDE_SESSION_ID` audit hooks are unused.
6. **Coherence gap.** `dev.md`/`review.md` claim `beadloom lint --strict` enforces architecture boundaries, but rules are currently `warn` (REVIEW §E / #91) — the guides promise enforcement that does not yet hold. (Resolved fully by Epic 2 / Phase 0.)

## Impact

Whoever runs multi-agent work — the maintainer, the team, and their AI tools (Cursor / Claude Code / manual) — gets a process that is harder to run stably, re-implements what `bd` now does natively, and risks confusion or regressions from stale references. Modernizing makes multi-agent development **stable and efficient**, and is itself a dogfood of Beads 1.0.4 + Beadloom. This is the toolkit that Epic 2 (Phase 0 honesty fix) will be executed through.

## Goals

- [ ] Zero stale tooling references: every `bd` / `beadloom` / Claude Code construct in `CLAUDE.md` + `commands/*` is verified against installed `bd 1.0.4` and `beadloom 1.9.0` (no `Task(...)` subagent calls, no non-existent flags/commands).
- [ ] Coordinator orchestration uses bd 1.0.4 `swarm` (waves/DAG), `gate` (review→tech-writer + CI waits), and `merge-slot` (serialized merges).
- [ ] `.claude/agents/{dev,test,review,tech-writer}.md` define first-class subagents with scoped tool access.
- [ ] One-time setup documented (`git config beads.role`); `--session`/`CLAUDE_SESSION_ID` integrated into close steps.
- [ ] Beadloom dogfooding expanded: `diff` in `/review`, `snapshot` per wave, `install-hooks` setup, `link` (bead ↔ graph node).
- [ ] §E coherence resolved honestly (enforcement statement references the Phase 0 epic).
- [ ] A short "process smoke test" is defined and passes.

## Non-goals

- Fixing Beadloom's own code (#91 god-package decouple, #88/#92/#93/#94) — that is **Epic 2 / Phase 0**, run after this epic through the modernized process.
- Changing the document-driven methodology itself (PRD/RFC/CONTEXT/PLAN/BRIEF flow stays).
- New Beadloom product features.

## User Stories

### US-1: Native coordination primitives
**As** a coordinator agent, **I want** native `bd swarm`/`gate`/`merge-slot`, **so that** parallel waves are tracked and merges serialized without manual bookkeeping or races.

**Acceptance criteria:**
- [ ] `coordinator.md` drives waves via `bd swarm` and gates transitions via `bd gate`.
- [ ] Merge/commit serialization uses `bd merge-slot`.

### US-2: First-class role subagents
**As** a dev/test/review/tech-writer subagent, **I want** a dedicated `.claude/agents/*` definition with the right tools + skill, **so that** I start correctly and keep the coordinator's context clean.

**Acceptance criteria:**
- [ ] Four agent files exist with scoped tools and reference their skill.
- [ ] `coordinator.md` launches them via the `Agent` tool with the new subagent types.

### US-3: Frictionless setup
**As** the maintainer onboarding a new repo or teammate, **I want** documented one-time setup, **so that** there are no `beads.role` warnings or confusion.

**Acceptance criteria:**
- [ ] `CLAUDE.md` setup section documents `git config beads.role`.

### US-4: No broken commands mid-flow
**As** any agent following the process, **I want** the docs to reference only commands that exist in the installed versions, **so that** nothing fails mid-flow.

**Acceptance criteria:**
- [ ] Every command reference verified against `bd 1.0.4` / `beadloom 1.9.0`.

## Acceptance Criteria (overall)

- [ ] `CLAUDE.md` + all `commands/*` modernized and reference-verified.
- [ ] `.claude/agents/` created for the four roles.
- [ ] swarm/gate/merge-slot + `--session` + beadloom dogfooding integrated.
- [ ] §E coherence note added (links Phase 0).
- [ ] Process smoke test passes; changes committed.
