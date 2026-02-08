# /checkpoint — Creating a Checkpoint

> **When to invoke:** every 30 min, after 5 steps, when completing a bead
> **Goal:** protection against auto-compaction, preserving progress

---

## When to create a checkpoint

| Trigger | Required |
|---------|----------|
| Bead completed | **MANDATORY** |
| 5+ steps completed | MANDATORY |
| 30+ minutes elapsed | MANDATORY |
| Before switching tasks | MANDATORY |
| Architectural decision made | Recommended |
| Problem discovered | Recommended |

---

## Checkpoint in beads (primary method)

```bash
bd comments add <bead-id> "$(cat <<'EOF'
═══ CHECKPOINT: YYYY-MM-DD HH:MM ═══

COMPLETED:
- Step 1
- Step 2
- Step 3

DECISIONS:
- Decision X: reason Y

CHANGED FILES:
- src/path/file1.py — what changed
- src/path/file2.py — what changed

NEXT STEPS:
1. Step A
2. Step B

BLOCKERS: [none | description]
EOF
)"
```

---

## Checkpoint when completing a bead

```bash
bd comments add <bead-id> "$(cat <<'EOF'
═══ BEAD COMPLETED: YYYY-MM-DD HH:MM ═══

WHAT WAS DONE:
- Item 1
- Item 2
- Item 3

DECISIONS MADE ALONG THE WAY:
- Decision X: reason Y
- Decision Z: reason W

KNOWN LIMITATIONS/TODO:
- TODO 1
- Limitation 1

TESTS:
- Unit: XX passed
- Integration: XX passed
- Coverage: XX%

FILES:
- src/new-file.py — new module
- src/updated.py — updated
EOF
)"

# Then close
bd close <bead-id>
```

---

## Updating ACTIVE.md

In parallel with the beads checkpoint, update ACTIVE.md:

```markdown
## Work-in-progress notes

### [HH:MM] CHECKPOINT
**Completed:**
- Step 1
- Step 2

**Decisions:**
- Decision X

**Next steps:**
1. Step A
2. Step B
```

---

## Checkpoint in chat (for the user)

```
═══════════════════════════════════════════════════════
CHECKPOINT: {ISSUE-KEY} | BEAD-XX | YYYY-MM-DD HH:MM
═══════════════════════════════════════════════════════

## Status
- Phase: Development
- Bead: BEAD-XX (In Progress)

## Completed
1. [action 1]
2. [action 2]

## Key decisions
- [decision]: [reason]

## Changed files
- `path/to/file.py` — [what]

## Next steps
1. [step 1]
2. [step 2]

## Command to continue
"Continue working on {ISSUE-KEY}"

═══════════════════════════════════════════════════════
```

---

## Protection against auto-compaction

**Problem:** During prolonged work, Claude compresses early context.

**Solution:** All critical information is stored in files:

| Information | Where it is stored |
|-------------|-------------------|
| Current state | CONTEXT.md |
| Plan and progress | ACTIVE.md |
| Work details | `bd comments <bead-id>` |
| Architecture | RFC.md |
| DAG | PLAN.md + beads |

**Rule:** Never rely on "memory" from the chat. Always read files when resuming work.

---

## Recovery after auto-compaction

If context was compressed:

```bash
# 1. Read state from beads
bd show <bead-id>
bd comments <bead-id>

# 2. Read files
# - CONTEXT.md
# - ACTIVE.md

# 3. Continue from the last checkpoint
```

---

## Checkpoint checklist

- [ ] Comment added in beads: `bd comments add`
- [ ] ACTIVE.md updated (notes, progress)
- [ ] CONTEXT.md updated (if decisions were made)
- [ ] User informed (checkpoint in chat)
