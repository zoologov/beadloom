<!-- beadloom:composed — this file is CORE + the architecture/stack overlays your
`.beadloom/flow.yml` selects. Put YOUR project's rules in `.beadloom/flow/claude/CLAUDE.md`:
the project layer composes AFTER the core, survives every upgrade, and does not trip
`beadloom config-check`. Editing this body directly is reported and never rewritten. -->

# CLAUDE.md — Multi-Agent Development Core

> **Version:** 3.1 (agents/ + commands/ split)
> **Integration:** steveyegge/beads CLI (1.0.4, embedded Dolt)
> **Process skills (`.claude/commands/`, slash, run in main loop):** `/task-init`, `/coordinator`, `/checkpoint`, `/templates`
> **Role subagents (`.claude/agents/`, launched via the `Agent` tool):** `dev`, `test`, `review`, `tech-writer`
> **See §0.0 Process Architecture for how these fit together.**

---

## 0.0 Process Architecture (entry point → roles)

One entry point, two kinds of unit. This is the whole map:

```
CLAUDE.md  ← entry point: critical rules, setup, bd/beadloom essentials, this map
│
├─ .claude/commands/  — SLASH SKILLS, injected into the MAIN-LOOP session (you, now)
│    /task-init    scaffold any work item (PRD/RFC/CONTEXT/PLAN/ACTIVE or BRIEF) + create beads
│    /coordinator  orchestrate multi-agent work (waves, gates, merge-slot) — MAIN-LOOP only
│    /checkpoint   bd-comment + ACTIVE.md progress saves
│    /templates    document templates used by /task-init
│
└─ .claude/agents/    — ROLE SUBAGENTS, launched via the `Agent` tool (isolated context)
     dev · test · review · tech-writer   (canonical role definitions; scoped tools; model: opus)
```

**Why coordinator is a command, not an agent:** the coordinator IS the main-loop process that *spawns* subagents via the `Agent` tool. A subagent cannot spawn subagents, so orchestration must live in the main loop. `/coordinator` is a skill injected into that loop.

**Two ways a role runs:**
- **Multi-agent (default for epics/features):** `/coordinator` launches roles as subagents — `Agent(subagent_type="dev"|"test"|"review"|"tech-writer", run_in_background=True)`. The role's full protocol lives in `.claude/agents/<role>.md` (single source of truth) and is NOT re-injected by the coordinator.
- **Single-agent (one small bead, no orchestration):** the main loop adopts the role inline by reading and following `.claude/agents/<role>.md` directly. (There are no `/dev` `/test` `/review` `/tech-writer` slash commands — roles are subagents, not skills.)

**Flow:** `/task-init` (docs + beads) → `/coordinator` (waves: dev → test → review → tech-writer, gated by bead dependencies) → commit per wave. Durable state lives in files (`CONTEXT.md`/`ACTIVE.md`) + bead comments, never chat.

---

## 0. CRITICAL RULES

> **READ FIRST. ALWAYS FOLLOW.**

### Setup (one-time, per clone)

```bash
git config beads.role maintainer   # or "contributor" — required by bd 1.0.4 (silences GH#2950 warning)
beadloom install-hooks             # pre-commit (lint + sync-check + ACTIVE/tracker coherence) +
                                   # pre-push Beadloom Gate (full `beadloom ci`; blocks on red, --no-verify to skip)
```

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
# 1. Tests pass, 2. lint + type-check clean
#    -> the concrete commands come from the STACK section below, not from here:
#       the core is stack-neutral and `uv run pytest` is not every project's suite.

# 3. Beadloom validation
beadloom reindex
beadloom sync-check
beadloom lint --strict

# 4. Final checkpoint
bd comments add <bead-id> "COMPLETED: [results]"

# 5. Close bead (shows newly unblocked work)
bd close <bead-id> --suggest-next
# (append --session "$CLAUDE_SESSION_ID" only if that env var is set)
```

---

## 0.1 Project: beadloom

<!-- beadloom:auto-start project-info -->
- **Stack:** Python (>=3.10) — click, rich, pyyaml, tree-sitter, tree-sitter-python, mcp
- **Tests:** pytest + pytest-cov
- **Linter/formatter:** ruff (lint + format)
- **Type checking:** mypy --strict
- **Architecture:** DDD packages -- `ai_agents/`, `application/`, `context_oracle/`, `doc_sync/`, `graph/`, `infrastructure/`, `onboarding/`, `services/`, `tui/`
- **Current version:** 2.2.0
<!-- beadloom:auto-end -->

---

## 1. Skills — Dynamic Loading

**Slash skills (main loop):**

| Situation | Command | Description |
|-----------|---------|-------------|
| New work item | `/task-init` | Setup any type: epic, feature, bug, task, chore |
| Parallel work | `/coordinator` | Orchestrate multi-agent waves (spawns role subagents) |
| Need templates | `/templates` | PRD, RFC, CONTEXT, PLAN, ACTIVE, BRIEF |
| Create checkpoint | `/checkpoint` | Format, rules |

**Role subagents (via the `Agent` tool — see §0.0):** `dev` (TDD implementation), `test` (tests, coverage), `review` (quality, read-only), `tech-writer` (doc refresh). Defined in `.claude/agents/<role>.md`. For a single small bead without orchestration, the main loop adopts a role inline by following its `.claude/agents/<role>.md`.

**Rule:** Invoke a slash skill when you need detailed instructions; launch a role subagent (or follow its agent file inline) to do role work.

---

## 2. Beads CLI — Essentials

```bash
# Available tasks (no blockers)
bd ready
bd ready --claim                  # atomically claim the next ready bead (1.0.4)

# All tasks
bd list

# Details + history
bd show <id>
bd comments <id>

# Claim task
bd update <id> --status in_progress --claim

# Add checkpoint (does NOT overwrite description)
bd comments add <id> "checkpoint text"

# Close task (--suggest-next shows newly unblocked beads; 1.0.4)
bd close <id> --suggest-next

# Dependency graph
bd graph --all

# Add dependency
bd dep add <id> <depends-on-id>
```

**Multi-agent coordination (new in 1.0.4) — used by `/coordinator`:**
- `bd swarm` — epic → DAG → waves (`create` / `validate` / `status`)
- `bd gate` — async wait conditions (review→tech-writer; CI via `gh:run` / `gh:pr`)
- `bd merge-slot` — serialize parallel merges (one agent merges at a time)

**IMPORTANT:**
- `bd comments add` — for checkpoints (preserves history)
- `bd update --append-notes` — for notes
- NEVER work on a task without `--claim`
- ALWAYS close via `bd close`; `--suggest-next` lists *candidate* unblocked beads — **confirm with `bd ready`** (it may list still-blocked beads; verified against bd 1.0.4)
- `--session "$CLAUDE_SESSION_ID"` on close is optional (audit trail; only if the env var is set)

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

# Change tracking & visualization
beadloom diff --since <git-ref>  # graph changes vs a git ref (exit 1 = changes) — use in the review role
beadloom snapshot save           # snapshot architecture state; `snapshot compare <a> <b>` to diff
beadloom link <ref-id> <url>     # link a graph node to an external tracker issue (GitHub/Jira)

# Cross-repo federation (hub + satellites)
beadloom export [--out FILE]     # deterministic federation artifact (schema v1: graph + lifecycle + AMQP contract meta)
beadloom federate <exports...>   # hub: aggregate >=2 satellite exports -> federated graph (drift verdicts + staleness)

# Documentation
beadloom docs generate           # generate doc skeletons from graph
beadloom docs polish             # structured data for AI doc enrichment

# Setup (one-time)
beadloom init                    # initialize beadloom in a project
beadloom setup-rules             # create IDE rules files referencing AGENTS.md
beadloom setup-mcp               # configure MCP server for IDE
beadloom setup-agentic-flow      # compose+write role adapters from .beadloom/flow.yml (ddd|fsd × stack, claude/cursor)
beadloom install-hooks           # pre-commit (lint + sync-check + coherence) + pre-push Beadloom Gate (full `beadloom ci`)

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

<!-- beadloom:auto-start doc-language -->
**Document language:** ALL documents (PRD, RFC, CONTEXT, PLAN, ACTIVE, BRIEF) MUST be written in English — set by `language: en` in `.beadloom/flow.yml`.
<!-- beadloom:auto-end -->

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

| Role | How it runs | When to use |
|------|-------------|-------------|
| **Developer** | `agents/dev.md` (`subagent_type: dev`) | Implementing beads (TDD) |
| **Reviewer** | `agents/review.md` (`subagent_type: review`) | Quality verification (read-only) |
| **Tester** | `agents/test.md` (`subagent_type: test`) | Writing tests |
| **Tech Writer** | `agents/tech-writer.md` (`subagent_type: tech-writer`) | Documentation updates |
| **Coordinator** | `/coordinator` skill (main loop) | Multi-agent orchestration |

### Single agent (one small bead, no orchestration)
The main loop adopts the role inline by following `.claude/agents/<role>.md` directly; use `/checkpoint` for saving progress.

### Multi-agent mode (default for epics/features)
Coordinator MUST be activated before multi-bead work:
1. Invoke `/coordinator` skill (main-loop only — see §0.0).
2. Complete `/task-init` flow BEFORE creating any beads or writing code.
3. Coordinator gets technical context through filtered sources (strategy specs, sub-agent summaries), NEVER reads raw source code directly.
4. Coordinator launches roles as first-class subagents via the `Agent` tool (`subagent_type: dev|test|review|tech-writer`), tracked through `bd swarm` / `gate` / `merge-slot`.

Roles are defined canonically in `.claude/agents/{dev,test,review,tech-writer}.md` (single source of truth; no slash-command wrappers).

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

## 6. Git — Trunk-based development

`main` is **branch-protected** (no direct push). All work integrates via a PR.

```
Trunk-based flow:
1. Branch off main:   git switch -c features/{ISSUE-KEY}
2. Commit per wave    onto features/{ISSUE-KEY} (dev → test → review → tech-writer)
3. ONE PR to main     per epic/feature (or shippable slice) — not one PR per commit
4. The PR triggers     the AI tech-writer (commits its doc refresh INTO the PR branch)
                       + CI (`beadloom ci` is a REQUIRED status check)
5. Merge when green    human merges once CI is green + the doc refresh has landed
                       (no auto-merge; no direct push to main → main stays always-green)
```

```
Commit format:
[{ISSUE-KEY}] <type>: <description>

Types: feat, fix, refactor, docs, test, chore

Example:
[MCP-001] feat: add health endpoint
```

One-time per repo: `beadloom setup-branch-protection` configures `main` protection
(PR required, `beadloom ci` a required check, `enforce_admins: true` — strict
trunk-based, even the owner integrates via a PR — and 0 required reviews → the
owner still self-merges).

> **Idempotent is not harmless.** The command applies whatever
> `DEFAULT_STATUS_CHECK_CONTEXTS` currently says, not whatever is already live, so
> re-running it after an upgrade can require checks your workflow does not yet
> produce — and a required check that never reports makes `main` unmergeable.
> Before re-running, confirm every context it will require exists as a job and is
> green. `gh api repos/:owner/:repo/branches/main/protection` shows what is live now.

---

## 7. Anti-patterns (NEVER)

### Planning
- Starting without an agreed plan
- Taking a bead with unresolved dependencies
- Changing DAG without notifying the user
- Creating beads before PLAN is approved (beads are created in Step 3 of /task-init)
- Coordinator reading raw source code (use strategy specs + sub-agent summaries instead)

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

> Language- and shell-specific anti-patterns live in the STACK section, composed
> from `.beadloom/flow.yml` — they are not universal and the core does not claim
> they are.

---

> **Need detailed instructions?** Slash skills: `/task-init` | `/coordinator` | `/templates` | `/checkpoint`.
> Role subagents (`Agent` tool / follow the agent file inline): `dev` | `test` | `review` | `tech-writer` — see §0.0.

---

## STACK (Python) — composed from `.beadloom/flow.yml`

The core above is stack-neutral. These are this project's concrete commands and
the anti-patterns that only mean something in Python.

### Commands the completion checklist refers to

```bash
uv run pytest                      # 1. tests pass
uv run ruff check src/ tests/      # 2. lint (same check as CI)
uv run mypy src/                   # 2. types (strict)
beadloom ci                        # the full pre-push Gate (rc 0 required)
```

### Anti-patterns (Python)

- Using `Any` / `# type: ignore` without a stated reason
- Leaving `print()` / `breakpoint()` — use logging
- Bare `except:` without naming the exception type
- `import *`
- Mutable default arguments (`def f(x=[]):`)
- `os.path` instead of `pathlib`; f-strings in SQL instead of `?` parameters;
  `yaml.load` instead of `yaml.safe_load`

### Anti-patterns (shell)

- Using `cp`, `mv`, `rm` without `-f` (may hang on an interactive prompt)

---

## Project layer — Beadloom's own rules (`.beadloom/flow/claude/CLAUDE.md`)

Everything above is the shipped CORE plus the overlays `.beadloom/flow.yml`
selects. Everything below is true of **this repository only** and is never
distributed. Before BDL-061 S3 there was nowhere to put it, so it went into the
core and shipped verbatim — including a bead id and a claim about this repo's
branch protection that is false for an adopter (BDL-UX #177).

### `setup-branch-protection` — not safe to re-run right now

`DEFAULT_STATUS_CHECK_CONTEXTS` ships **nine** contexts; `main`'s live protection
has **seven**. Running the command today would require checks that have not been
observed green on this repository, which is how `main` becomes unmergeable.

The count has moved three times, which is the thing to notice rather than the
number: S2 added the two `tests-locale` legs (red until `beadloom-mr2l.42` closed
them — they are green now), S4 added `tests-windows`, and `beadloom-mr2l.64`
withdrew it again by owner decision — ~16-28 runner-minutes per PR and the
pipeline's critical path, for a platform outside this project's audience. So the
declared set can shrink as well as grow, and a withdrawal moves the ci.yml job
and the context together or it leaves a lockout behind.

So the rule is not "wait for a named bead" — that reading was wrong within an
hour of being written. It is: **before running this command, compare the declared
contexts against what actually reports green.**

    gh api repos/:owner/:repo/branches/main/protection \
      --jq '.required_status_checks.contexts'
    gh pr checks <any open PR>

A dimension is added whenever this project learns it was only ever verified along
one axis, so the declared set will keep growing ahead of the green set. That gap
is the normal state, not an incident.

### Concurrent waves share one working tree

Commit only your own files, by explicit path — never `git add -A`. Take
`bd merge-slot acquire --wait` before committing and `release` after. Verify in
a clean room (`git archive HEAD` + only your files) and say so in those words:
"green in a clean room over N files" is a different claim from "green on the
tree" (BDL-UX #181).
