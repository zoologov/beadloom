# /task-init — Unified Task Initialization

> **When to invoke:** when starting any new work item (epic, feature, bug, task, chore)
> **Result:** docs folder + beads tracking + approval flow

---

## Type detection

| Type | Flow | Docs created |
|------|------|-------------|
| `epic` | Full: PRD → RFC → CONTEXT+PLAN → ACTIVE | PRD, RFC, CONTEXT, PLAN, ACTIVE |
| `feature` | Full: PRD → RFC → CONTEXT+PLAN → ACTIVE | PRD, RFC, CONTEXT, PLAN, ACTIVE |
| `bug` | Simplified: BRIEF → ACTIVE | BRIEF, ACTIVE |
| `task` | Simplified: BRIEF → ACTIVE | BRIEF, ACTIVE |
| `chore` | Simplified: BRIEF → ACTIVE | BRIEF, ACTIVE |

---

## Step 0: Create docs folder (ALL types)

**This step is MANDATORY for every type. No exceptions.**

```bash
mkdir -p .claude/development/docs/features/{ISSUE-KEY}
```

---

## Full flow (epic | feature)

### Sequence

```mermaid
graph LR
    PRD[PRD] -->|approval| RFC[RFC]
    RFC -->|approval| CTX[CONTEXT + PLAN]
    CTX -->|approval| ACTIVE[ACTIVE]
```

**EACH step requires explicit user approval before proceeding!**

### Document status lifecycle

Every document follows this strict lifecycle:

```
Draft  →  Approved  →  Done
```

- Create document with `Status: Draft`
- Show to user, wait for explicit approval ("утверждаю" / "approve" / "ok")
- Set `Status: Approved`, proceed to next document
- Set `Status: Done` when epic/feature is completed

**Status format is EXACT — always capitalized, no dates in parentheses:**
```
> **Status:** Draft
> **Status:** Approved
> **Status:** Done
```

### Step 1: PRD

1. Create `PRD.md` from template (see `/templates`) with `Status: Draft`
2. Fill in content based on user's request
3. Show to user in chat
4. **WAIT for explicit approval**
5. Update `Status: Approved`

```
┌──────────────────────────────────────────────┐
│ PRD: {ISSUE-KEY} — [Name]                    │
│ Status: Draft → waiting for approval         │
│                                              │
│ [summary of what PRD contains]               │
│                                              │
│ Approve to proceed to RFC?                   │
└──────────────────────────────────────────────┘
```

### Step 2: RFC

1. Create `RFC.md` from template with `Status: Draft`
2. Fill in technical solution
3. Show to user
4. **WAIT for explicit approval**
5. Update `Status: Approved`

### Step 3: CONTEXT + PLAN

1. Create `CONTEXT.md` from template with `Status: Draft`
   - Code standards: copy from CLAUDE.md §0.1 (do NOT survey the user)
2. Create `PLAN.md` from template with `Status: Draft`
   - Create parent bead: `bd create --type feature --title "[ISSUE-KEY] Name"`
   - Create sub-beads with mandatory structure (see below): `bd create --type task --parent <parent-id>`
   - Set up dependencies: `bd dep add`
3. Show both to user
4. **WAIT for explicit approval**
5. Update both to `Status: Approved`
6. **Immediately proceed to Step 4** (no additional approval needed)

**Process gate:** Do NOT create beads before this step. PRD and RFC must be Approved first.

**Mandatory bead structure (full flow):**
```
<parent-id> [feature/epic] — parent bead
├── <parent-id>.N [task/dev]        — development sub-tasks (one per BEAD)
├── <parent-id>.N [task/test]       — test agent sub-task
├── <parent-id>.N [task/review]     — review agent sub-task
└── <parent-id>.N [task/tech-writer]— doc update sub-task
```

Every feature/epic MUST include sub-tasks for all four agent roles:
- `/dev` — implementation beads (one per logical unit of work)
- `/test` — test verification bead (depends on all dev beads)
- `/review` — code review bead (depends on test bead)
- `/tech-writer` — documentation update bead (depends on review bead)

### Step 4: ACTIVE

1. Create `ACTIVE.md` (no approval needed — working document)
2. Show start confirmation:

```
┌──────────────────────────────────────────────┐
│ READY: {ISSUE-KEY} — [Name]                  │
│                                              │
│ Type: epic | feature                         │
│ Beads: [count]                               │
│ Critical path: BEAD-01 → BEAD-02 → ...      │
│                                              │
│ All docs approved. Ready to start?           │
└──────────────────────────────────────────────┘
```

---

## Simplified flow (bug | task | chore)

### Sequence

```mermaid
graph LR
    BRIEF[BRIEF] -->|approval| ACTIVE[ACTIVE]
```

**One approval, then straight to work.**

### Step 1: BRIEF

1. Create `BRIEF.md` from template (see `/templates`) with `Status: Draft`
2. Fill in: Problem, Solution, Beads, Acceptance Criteria
3. Create beads in tracker:
   ```bash
   bd create --type {type} --title "{ISSUE-KEY}: [Name]" --description "..."
   # If multiple subtasks:
   bd create --type task --title "BEAD-01: [Name]" --parent <parent-id>
   ```
4. Show to user
5. **WAIT for explicit approval**
6. Update `Status: Approved`

### Step 2: ACTIVE

1. Create `ACTIVE.md` (no approval needed)
2. Start work immediately

---

## Template rules

All documents MUST use templates from `/templates`. No improvisation.

**Strict formatting rules:**
- **Language:** ALL documents (PRD, RFC, CONTEXT, PLAN, ACTIVE, BRIEF) MUST be in English
- No numbered sections (use `##` / `###` headings only)
- Status: always `Draft` / `Approved` / `Done` (capitalized, no dates in status)
- Date in separate `Created:` field
- Metadata block uses `>` blockquote syntax

---

## Initialization checklist

### Full flow (epic | feature)
- [ ] Created folder `.claude/development/docs/features/{ISSUE-KEY}/`
- [ ] PRD.md created with `Status: Draft` (in English)
- [ ] PRD.md → **user approved** → `Status: Approved`
- [ ] RFC.md created with `Status: Draft` (in English)
- [ ] RFC.md → **user approved** → `Status: Approved`
- [ ] CONTEXT.md created with `Status: Draft`
- [ ] PLAN.md created with `Status: Draft`
- [ ] Parent bead created: `bd create --type feature`
- [ ] Dev sub-beads created: `bd create --type task --parent <parent-id>`
- [ ] Test sub-bead created (depends on all dev beads)
- [ ] Review sub-bead created (depends on test bead)
- [ ] Tech-writer sub-bead created (depends on review bead)
- [ ] Dependencies set: `bd dep add`
- [ ] CONTEXT.md + PLAN.md → **user approved** → `Status: Approved`
- [ ] ACTIVE.md created
- [ ] User confirmed start of development

### Simplified flow (bug | task | chore)
- [ ] Created folder `.claude/development/docs/features/{ISSUE-KEY}/`
- [ ] BRIEF.md created with `Status: Draft`
- [ ] Beads created in tracker
- [ ] BRIEF.md → **user approved** → `Status: Approved`
- [ ] ACTIVE.md created
- [ ] Work started
