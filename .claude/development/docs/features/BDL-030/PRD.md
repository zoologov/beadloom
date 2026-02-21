# PRD: BDL-030 — Agent Instructions Freshness

> **Status:** Approved
> **Created:** 2026-02-21

---

## Problem

CLAUDE.md and AGENTS.md contain hardcoded facts — version numbers, CLI command counts, MCP tool counts, phase completion status, architecture package names — that silently drift during active development. Every release, phase completion, or command addition can introduce stale data in agent instruction files.

Audit during BDL-029 session found 2 drift issues even in a well-maintained project. This problem scales with development velocity: the faster we ship, the faster instructions drift. Agents consuming stale instructions make incorrect assumptions about project state.

## Impact

- **AI agents** receive outdated project context (wrong version, missing commands, stale phase status), leading to incorrect decisions and wasted work
- **Human developers** reading CLAUDE.md/AGENTS.md get a false picture of project state
- **Manual audit burden** grows with every release — currently requires a human to diff facts against reality
- **CI/CD** has no automated gate to catch instruction drift before it reaches agents

## Goals

- [ ] `beadloom doctor` automatically detects stale facts in CLAUDE.md and AGENTS.md
- [ ] `beadloom setup-rules --refresh` auto-fixes dynamic sections while preserving hand-written policy
- [ ] Zero manual audit needed for factual accuracy after running refresh
- [ ] Clear separation between policy sections (preserved) and fact sections (auto-generated)

## Non-goals

- Rewriting CLAUDE.md structure or policy sections
- Validating correctness of hand-written rules/workflows/anti-patterns
- Supporting arbitrary markdown files beyond CLAUDE.md and AGENTS.md
- Cross-repository agent instruction sync (Phase 13+)

## User Stories

### US-1: Detect stale agent instructions
**As** a developer running `beadloom doctor`, **I want** to see which facts in CLAUDE.md/AGENTS.md are outdated, **so that** I can fix them before agents consume stale context.

**Acceptance criteria:**
- [ ] `beadloom doctor` reports version drift (e.g., "1.7.0" vs actual "1.8.0")
- [ ] Reports CLI command count drift
- [ ] Reports MCP tool count drift
- [ ] Reports architecture package name drift
- [ ] Reports phase completion status drift
- [ ] Each drift warning shows expected vs actual value

### US-2: Auto-fix stale agent instructions
**As** a developer after a release, **I want** to run `beadloom setup-rules --refresh` to automatically update facts in CLAUDE.md, **so that** I don't need to manually audit and edit every hardcoded value.

**Acceptance criteria:**
- [ ] Dynamic sections wrapped in `<!-- beadloom:auto-start -->` / `<!-- beadloom:auto-end -->` markers are regenerated
- [ ] Hand-written policy sections (rules, workflows, anti-patterns) are preserved exactly
- [ ] `--dry-run` flag shows what would change without modifying files
- [ ] AGENTS.md is also refreshed (already existing capability, extended)

## Acceptance Criteria (overall)

- [ ] `beadloom doctor` includes "Agent Instructions" check section
- [ ] `beadloom setup-rules --refresh` regenerates CLAUDE.md dynamic sections
- [ ] All existing tests pass, new tests cover both detection and refresh
- [ ] Coverage >= 80%
- [ ] ruff + mypy clean
