# CONTEXT: BDL-035 — Multi-Agent Process Modernization

> **Status:** Approved
> **Created:** 2026-05-29
> **Last updated:** 2026-05-29

---

## Goal

Modernize the multi-agent process (`.claude/CLAUDE.md` + `.claude/commands/*` + new `.claude/agents/*`) to maximally use Beads 1.0.4, current Claude Code, skills, and Beadloom dogfooding — for stable, efficient multi-agent development. (Immutable after approval.)

## Key Constraints

- **Docs/config only** — no Beadloom product code changes (that is Epic 2 / Phase 0).
- **Reference-accuracy:** every `bd` / `beadloom` command written into the docs is verified live via `--help` against the installed `bd 1.0.4` / `beadloom 1.9.0` before being documented.
- **Single source of truth:** role protocols live only in `.claude/agents/*`; `commands/*` role files are thin wrappers (anti-drift).
- **honest ≠ complete:** any not-fully-wired primitive (e.g. a rough `swarm`/`gate`) is documented as the target with a labeled lightweight fallback, never presented as done.

## Code Standards

Deliverables are Markdown + agent frontmatter (not Python), so the usual lint/type gates do not apply. The relevant standards:

| Standard | Application |
|----------|-------------|
| Reference accuracy | Every command verified via `--help` before documenting |
| Single source of truth | Role protocol in `agents/*`; wrappers stay 3-5 lines |
| Concise & honest docs | No aspirational claims; label gaps |
| Methodology unchanged | PRD/RFC/CONTEXT/PLAN/BRIEF + beads flow stays |

**Subagent model policy:** **Opus** is the default for all four roles (dev/test/review/tech-writer) — anti-drift, since the project's currency is accuracy/honesty and test/docs are the highest drift-risk surfaces. Sonnet is allowed only as an explicit per-bead opt-in for mechanical + beadloom-verified work, with justification.

**Commit format:** `[BDL-035] <type>: <description>`.

## Architectural Decisions

| Date | Decision | Reason |
|------|----------|--------|
| 2026-05-29 | `.claude/agents/*` canonical; `commands/*` role files = thin wrappers | Anti-drift — two copies diverge (review's #93 lesson) |
| 2026-05-29 | Opus default for all 4 role subagents | Project currency = accuracy/honesty; test/docs highest drift-risk; not cost-constrained |
| 2026-05-29 | Adopt `bd swarm`/`gate`/`merge-slot`; Option C fallback if a primitive is too rough | Native coordination > hand-rolled; honest≠complete fallback |
| 2026-05-29 | BDL-035 executed on the CURRENT process; Epic 2 (Phase 0) dogfoods the NEW process | Chicken-and-egg — the modernized process does not exist until BDL-035 ships |

## Related Files

Target files (`.claude/` — not Beadloom graph nodes, so not discoverable via `beadloom ctx`):
- `.claude/CLAUDE.md`
- `.claude/commands/{coordinator,dev,review,test,tech-writer,checkpoint,task-init,templates}.md`
- NEW: `.claude/agents/{dev,test,review,tech-writer}.md`
- `CHANGELOG.md` (note the process change)

## Current Phase

- **Phase:** Planning
- **Current bead:** (none yet — created after PLAN approval)
- **Blockers:** none
