# CLAUDE.md — Multi-Agent Development Core

> **Version:** 3.0 (Optimized)
> **Integration:** steveyegge/beads CLI
> **Skills:** `/task-init`, `/dev`, `/review`, `/test`, `/coordinator`, `/templates`, `/checkpoint`, `/tech-writer`

---

## 0. CRITICAL RULES

> **READ FIRST. ALWAYS FOLLOW.**

### BEFORE any work

```bash
# 1. Get project context
beadloom prime                    # compact architecture + health overview

# 2. Check available tasks
bd ready

# 3. Claim task
bd update <bead-id> --status in_progress --claim

# 4. Read context via Beadloom (never hardcode paths)
beadloom ctx <ref-id>             # architecture context for the area you'll touch
beadloom why <ref-id>             # impact: what depends on this?

# 5. Read epic context (if applicable)
# .claude/development/docs/features/{ISSUE-KEY}/CONTEXT.md
# .claude/development/docs/features/{ISSUE-KEY}/ACTIVE.md

# 6. Confirm understanding to user
```

### DURING work

```bash
# Checkpoint every 30 min or 5 steps
bd comments add <bead-id> "CHECKPOINT: [what was done]"

# Update ACTIVE.md after each significant action
```

### WHEN COMPLETING bead

```bash
# 1. Tests pass
uv run pytest

# 2. Code quality (same checks as CI)
uv run ruff check src/ tests/
uv run mypy

# 3. Beadloom validation
beadloom reindex
beadloom sync-check
beadloom lint --strict

# 4. Final checkpoint
bd comments add <bead-id> "COMPLETED: [results]"

# 5. Close bead
bd close <bead-id>
```

---

## 0.1 Project: Beadloom

- **Stack:** Python 3.10+, SQLite (WAL), Click + Rich (CLI), tree-sitter, MCP (stdio)
- **Distribution:** PyPI (`uv tool install beadloom`)
- **Tests:** pytest + pytest-cov (>=80% coverage)
- **Linter/formatter:** ruff (lint + format)
- **Type checking:** mypy --strict
- **Project documentation:** `.claude/development/STRATEGY-2.md`, `.claude/development/BACKLOG.md`, `.claude/development/BDL-UX-Issues.md`, `CHANGELOG.md`
- **Architecture:** DDD packages — `infrastructure/`, `context_oracle/`, `doc_sync/`, `onboarding/`, `graph/` + `services/` (CLI, MCP) + `tui/`
- **Current version:** 1.7.0 (Phases 1-6 + 8, 8.5, 9, 10, 10.5, 11, 12 done)

---

## 1. Skills — Dynamic Loading

| Situation | Command | Description |
|-----------|---------|-------------|
| New work item | `/task-init` | Setup any type: epic, feature, bug, task, chore |
| Code development | `/dev` | TDD, patterns, workflow |
| Code review | `/review` | Quality checklists |
| Writing tests | `/test` | AAA pattern, coverage |
| Parallel work | `/coordinator` | Distribution, synchronization |
| Doc updates | `/tech-writer` | Systematic doc refresh, sync-check fixes |
| Need templates | `/templates` | PRD, RFC, CONTEXT, PLAN, ACTIVE, BRIEF |
| Create checkpoint | `/checkpoint` | Format, rules |

**Rule:** Invoke a skill when you need detailed instructions.

---

## 2. Beads CLI — Essentials

```bash
# Available tasks (no blockers)
bd ready

# All tasks
bd list

# Details + history
bd show <id>
bd comments <id>

# Claim task
bd update <id> --status in_progress --claim

# Add checkpoint (does NOT overwrite description)
bd comments add <id> "checkpoint text"

# Close task
bd close <id>

# Dependency graph
bd graph --all

# Add dependency
bd dep add <id> <depends-on-id>
```

**IMPORTANT:**
- `bd comments add` — for checkpoints (preserves history)
- `bd update --append-notes` — for notes
- NEVER work on a task without `--claim`
- ALWAYS close via `bd close`

---

## 2.1 Beadloom CLI — Essentials

```bash
# Agent context (start of session)
beadloom prime                   # compact context for AI agent injection (<2K tokens)

# Project structure (use instead of hardcoded paths)
beadloom status                  # overview: nodes, edges, docs, coverage, trends
beadloom graph                   # Mermaid architecture diagram
beadloom ctx <ref-id>            # full context: code, docs, constraints
beadloom ctx <ref-id> --json     # structured JSON for parsing
beadloom search "<query>"        # FTS5 search across nodes and docs
beadloom why <ref-id>            # impact analysis: upstream deps + downstream dependents

# Validation (run before committing)
beadloom reindex                 # rebuild index after code/graph changes
beadloom sync-check              # check doc-code freshness (exit 2 = stale)
beadloom lint --strict           # architecture boundary check (exit 1 = violation)
beadloom doctor                  # graph integrity validation

# Documentation
beadloom docs generate           # generate doc skeletons from graph
beadloom docs polish             # structured data for AI doc enrichment

# Setup (one-time)
beadloom init                    # initialize beadloom in a project
beadloom setup-rules             # create IDE rules files referencing AGENTS.md
beadloom setup-mcp               # configure MCP server for IDE

# After changing code
# 1. beadloom reindex            — re-index changed files
# 2. beadloom sync-check         — check if docs went stale
# 3. If stale: update the doc, then beadloom reindex again
# 4. beadloom lint --strict      — verify architecture boundaries
```

**IMPORTANT:**
- NEVER hardcode file paths — use `beadloom ctx`/`graph`/`search` to discover structure
- ALWAYS start sessions with `beadloom prime` for project context
- ALWAYS run `beadloom sync-check` before committing
- If sync-check reports stale docs, update them before proceeding

---

## 3. File Memory (protection against auto-compaction)

```
.claude/development/docs/features/{ISSUE-KEY}/
├── PRD.md       <- REQUIREMENTS: business goals (epic/feature only)
├── RFC.md       <- ARCHITECTURE: technical solution (epic/feature only)
├── CONTEXT.md   <- CORE: state, decisions, standards (epic/feature only)
├── PLAN.md      <- DAG: beads and dependencies (epic/feature only)
├── BRIEF.md     <- COMBINED: problem + solution + plan (bug/task/chore only)
└── ACTIVE.md    <- FOCUS: current work, progress (ALL types)
```

| Priority | File | When to read |
|----------|------|--------------|
| **P0** | CONTEXT.md | Always at the start |
| **P0** | ACTIVE.md | Always at the start |
| **P1** | beads comments | When resuming work |

**Rule:** NEVER rely on "memory" from chat. Read the files!

---

## 4. Agent Roles

| Role | Skill | When to use |
|------|-------|-------------|
| **Developer** | `/dev` | Implementing beads |
| **Reviewer** | `/review` | Quality verification |
| **Tester** | `/test` | Writing tests |
| **Tech Writer** | `/tech-writer` | Documentation updates |
| **Coordinator** | `/coordinator` | Multi-agent work |

### Single agent
Use `/dev` for development, `/checkpoint` for saving progress.

### Multi-agent mode
Coordinator uses `/coordinator` for distribution.
Sub-agents use corresponding roles.

---

## 5. DAG and Priorities

| Priority | Description | Rule |
|----------|-------------|------|
| **P0** | Critical, blocks others | Execute first |
| **P1** | High, important | After P0 |
| **P2** | Medium, improvements | When there is time |
| **P3** | Low, nice-to-have | Last priority |

**Rules:**
- Only take from `bd ready`
- Do NOT take a bead with unresolved dependencies
- Do NOT take P2/P3 while P0/P1 exist

---

## 6. Git

```
Commit format:
[{ISSUE-KEY}] <type>: <description>

Types: feat, fix, refactor, docs, test, chore

Example:
[MCP-001] feat: add health endpoint
```

---

## 7. Anti-patterns (NEVER)

### Planning
- Starting without an agreed plan
- Taking a bead with unresolved dependencies
- Changing DAG without notifying the user

### Work
- Starting without reading CONTEXT.md
- Relying on chat memory
- Working on multiple beads simultaneously
- Ignoring checkpoints

### Completion
- Completing a bead without `bd comments add`
- Completing without `bd close`
- Committing with failing tests

### Beadloom
- Committing without `beadloom sync-check`
- Hardcoding file paths instead of using `beadloom ctx`/`graph`
- Skipping `beadloom reindex` after graph YAML changes
- Ignoring `beadloom lint` violations

### Shell
- Using `cp`, `mv`, `rm` without `-f` flag (may hang on interactive prompts)

### Code
- Using `Any` / `# type: ignore` without reason
- Leaving `print()` / `breakpoint()`
- Writing code without a test (TDD violation)
- Bare `except:` without specifying exception type
- `import *`
- Mutable default arguments (`def f(x=[]):`)

---

## 8. Quick Reference

### Session start
```bash
beadloom prime                        # project context
bd ready
bd update <id> --status in_progress --claim
beadloom ctx <ref-id>                 # architecture context for the area
# Read CONTEXT.md, ACTIVE.md (if epic)
# Confirm to user
```

### During work
```bash
# Every 30 min
bd comments add <id> "CHECKPOINT: ..."
# Update ACTIVE.md
```

### Completing bead
```bash
uv run pytest
bd comments add <id> "COMPLETED: ..."
bd close <id>
bd ready  # what got unblocked?
```

### New work item
```
/task-init
```

### Need templates
```
/templates
```

---

## 9. Agent Checklist

### At start
- [ ] `beadloom prime` -> project overview
- [ ] `bd ready` -> selected a task
- [ ] `bd update <id> --status in_progress --claim`
- [ ] `beadloom ctx <ref-id>` -> architecture context
- [ ] Read CONTEXT.md and ACTIVE.md (if epic)
- [ ] Confirmed understanding to user

### During work
- [ ] Updating ACTIVE.md
- [ ] Checkpoint in beads every 30 min
- [ ] Following TDD (if code)

### At completion
- [ ] Tests pass
- [ ] `bd comments add` — final checkpoint
- [ ] `bd close <id>`
- [ ] ACTIVE.md cleaned

---

> **Need detailed instructions?** Invoke the corresponding skill:
> `/task-init` | `/dev` | `/review` | `/test` | `/coordinator` | `/tech-writer` | `/templates` | `/checkpoint`
