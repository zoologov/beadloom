# /coordinator — Multi-agent Work Coordinator

> **When to invoke:** during parallel work with multiple agents
> **Focus:** task distribution, synchronization, quality control

---

## Principles of multi-agent work

1. **One bead = one agent** at any given time
2. **Synchronization through files**, not through chat
3. **CONTEXT.md is the source of truth**
4. **Only independent beads run in parallel** (no shared dependencies)

---

## Agent roles

| Role | Skill | Tasks |
|------|-------|-------|
| Developer | `/dev` | Implementing beads, TDD |
| Reviewer | `/review` | Code review, quality |
| Tester | `/test` | Tests, coverage |
| Coordinator | `/coordinator` | Distribution, synchronization |

---

## Task distribution protocol

```bash
# 1. View available beads
bd ready

# 2. Check the DAG
bd graph --all

# 3. Select independent beads for parallel work
# Example: BEAD-02 and BEAD-04 do not depend on each other

# 4. Assign to agents
bd update <bead-id-1> --assignee "agent-1" --status in_progress
bd update <bead-id-2> --assignee "agent-2" --status in_progress
```

---

## Wave-based execution

```
Wave 1: Independent beads (parallel)
├── Agent-1: BEAD-01 (P0)
└── Agent-2: BEAD-04 (P0, independent)

Wave 2: After Wave 1 completion
├── Agent-1: BEAD-02 (depended on BEAD-01)
├── Agent-2: BEAD-03 (depended on BEAD-01)
└── Agent-3: BEAD-06 (independent)

Wave 3: Integration
└── Agent-1: BEAD-05 (depended on 02, 03, 04)
```

---

## Context Overflow Protection

> **CRITICAL:** Parallel agents overflow the parent context window.
> Without protection, `/compact` fails and the session is lost.

### Rule 1: Background agents (MANDATORY for waves)

ALWAYS launch parallel agents with `run_in_background: true`:

```python
Task(
    prompt="...",
    subagent_type="general-purpose",
    run_in_background=True,    # MANDATORY — results go to file, not context
)
```

- Agent results go to an `output_file`, NOT into parent context
- Parent checks progress via `bd list` + `bd comments <id>`
- Parent reads `output_file` only if needed (tail last 20 lines)

### Rule 2: Agent return contract

Every agent prompt MUST include this instruction:

```
RETURN CONTRACT: When done, return ONLY a 2-3 line summary:
"BEAD-XX done. N tests added. Files: list."
Write ALL details to bead comments via `bd comments add`.
Do NOT return file contents, diffs, or verbose test output.
```

### Rule 3: Compaction between waves

After each wave completes:

```bash
# 1. Verify all beads in wave are closed
bd list --status=in_progress

# 2. Read ACTIVE.md (will survive compaction)
# Update ACTIVE.md with wave results

# 3. /compact — compress parent context

# 4. After compaction: read ACTIVE.md to restore state
# Then launch next wave
```

### Rule 4: One bead = one agent

Do NOT batch multiple beads into one agent (e.g., "BEAD-02 + BEAD-08").
Each bead gets its own agent. This keeps individual agent contexts smaller
and makes failures isolated.

---

## Launching sub-agents

**ALWAYS use `run_in_background: true` for parallel agents.**

```
Coordinator launches sub-agents in parallel (background):

Agent-1 (developer, background):
- Bead: BEAD-XX
- Skill: /dev
- Context: CONTEXT.md, ACTIVE.md
- Return: 2-3 line summary only

Agent-2 (developer, background):
- Bead: BEAD-YY
- Skill: /dev
- Context: CONTEXT.md, ACTIVE.md
- Return: 2-3 line summary only
```

---

## Requirements for sub-agent upon completion

**MANDATORY for each sub-agent:**

```bash
# 1. All tests pass
uv run pytest

# 2. Beadloom validation
beadloom reindex
beadloom sync-check
beadloom lint --strict

# 3. Add checkpoint with results (THIS is where details go)
bd comments add <bead-id> "$(cat <<'EOF'
COMPLETED:
- What was done: [list]
- Decisions: [if any]
- Tests: [result]
- Files: [changed files]
- TODO: [if any]
EOF
)"

# 4. Close the bead
bd close <bead-id>

# 5. Return ONLY a 2-3 line summary (NOT full details)
```

---

## Coordinator checklist before wave commit

```
BEFORE WAVE COMMIT:

□ All sub-agents have completed their beads
□ bd comments shows checkpoints for ALL beads in the wave
□ CONTEXT.md is up to date:
  - Phase matches reality
  - "Related files" includes new modules
  - "Last updated" is filled in
□ ACTIVE.md reflects completed work
□ All tests pass (uv run pytest)
□ beadloom reindex — index is fresh
□ beadloom sync-check — no stale docs
□ beadloom lint --strict — no architecture violations
□ beadloom doctor — graph integrity ok
□ All beads are closed (bd close)
```

---

## File synchronization

| File | Who updates | When |
|------|-------------|------|
| CONTEXT.md | Coordinator | After wave, architectural decisions |
| ACTIVE.md | Sub-agent | During work |
| beads (comments) | Sub-agent | Checkpoints, completion |
| PLAN.md | Coordinator | When DAG changes |

---

## Conflict resolution

If a discrepancy is found:

1. **Stop all sub-agents**
2. Report the discrepancy to the user
3. Wait for a decision
4. Update files according to the decision
5. Restart sub-agents

---

## Changing the DAG mid-process

```bash
# 1. Stop work
# 2. Add dependency
bd dep add <bead-id> <depends-on-id>

# 3. Check the graph
bd graph --all

# 4. Notify the user
```

```
┌─────────────────────────────────────────────────────────┐
│ DAG CHANGE: {ISSUE-KEY}                                 │
│                                                         │
│ New dependency discovered:                              │
│ BEAD-XX now depends on BEAD-YY                          │
│                                                         │
│ Reason: [description]                                   │
│ Impact on critical path: [yes/no]                       │
│                                                         │
│ Do you confirm the change?                              │
└─────────────────────────────────────────────────────────┘
```

---

## Wave status

Output for the user:

```
┌─────────────────────────────────────────────────────────┐
│ WAVE 2 STATUS: {ISSUE-KEY}                             │
│                                                         │
│ [✓] BEAD-02 — Agent-1 — Done                           │
│ [⏳] BEAD-03 — Agent-2 — In Progress (75%)             │
│ [✓] BEAD-06 — Agent-3 — Done                           │
│                                                         │
│ Remaining: 1 bead                                       │
│ Next wave: BEAD-05 (waiting on 02, 03)                  │
└─────────────────────────────────────────────────────────┘
```
