# CLAUDE.md — Multi-Agent Development Core

> **Version:** 3.0 (Optimized)
> **Integration:** steveyegge/beads CLI
> **Skills:** `/epic-init`, `/dev`, `/review`, `/test`, `/coordinator`, `/templates`, `/checkpoint`

---

## 0. CRITICAL RULES

> **READ FIRST. ALWAYS FOLLOW.**

### BEFORE any work

```bash
# 1. Check available tasks
bd ready

# 2. Claim task
bd update <bead-id> --status in_progress --claim

# 3. Read context
# .claude/development/docs/features/{ISSUE-KEY}/CONTEXT.md
# .claude/development/docs/features/{ISSUE-KEY}/ACTIVE.md

# 4. Confirm understanding to user
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

# 2. Final checkpoint
bd comments add <bead-id> "COMPLETED: [results]"

# 3. Close bead
bd close <bead-id>
```

---

## 0.1 Project: Beadloom

- **Stack:** Python 3.10+, SQLite (WAL), Click + Rich (CLI), tree-sitter, MCP (stdio)
- **Distribution:** PyPI (`uv tool install beadloom`)
- **Tests:** pytest + pytest-cov (>=80% coverage)
- **Linter/formatter:** ruff (lint + format)
- **Type checking:** mypy --strict
- **Project documentation:** `.claude/development/PRD.md`, `.claude/development/RFC.md`
- **Phases:** 0-Onboarding -> 1-Context Oracle -> 2-MCP -> 3-Doc Sync -> 4-Polish

---

## 1. Skills — Dynamic Loading

| Situation | Command | Description |
|-----------|---------|-------------|
| New epic/feature | `/epic-init` | Setup, standards, alignment |
| Code development | `/dev` | TDD, patterns, workflow |
| Code review | `/review` | Quality checklists |
| Writing tests | `/test` | AAA pattern, coverage |
| Parallel work | `/coordinator` | Distribution, synchronization |
| Need templates | `/templates` | PRD, RFC, CONTEXT, PLAN |
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

## 3. File Memory (protection against auto-compaction)

```
.claude/development/docs/features/{ISSUE-KEY}/
├── CONTEXT.md   <- CORE: state, decisions, standards
├── ACTIVE.md    <- FOCUS: current work, progress
├── RFC.md       <- ARCHITECTURE: technical solution
├── PLAN.md      <- DAG: beads and dependencies
└── PRD.md       <- REQUIREMENTS: business goals
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
bd ready
bd update <id> --status in_progress --claim
# Read CONTEXT.md, ACTIVE.md
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

### New epic
```
/epic-init
```

### Need templates
```
/templates
```

---

## 9. Agent Checklist

### At start
- [ ] `bd ready` -> selected a task
- [ ] `bd update <id> --status in_progress --claim`
- [ ] Read CONTEXT.md and ACTIVE.md
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
> `/epic-init` | `/dev` | `/review` | `/test` | `/coordinator` | `/templates` | `/checkpoint`
