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

## Launching sub-agents

```
Coordinator launches sub-agents in parallel:

Agent-1 (developer):
- Bead: BEAD-XX
- Skill: /dev
- Context: CONTEXT.md, ACTIVE.md

Agent-2 (developer):
- Bead: BEAD-YY
- Skill: /dev
- Context: CONTEXT.md, ACTIVE.md
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

# 3. Add checkpoint with results
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

# 5. Notify the coordinator
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
