# /task-init — Unified Task Initialization

> **When to invoke:** when starting any new work item (epic, feature, bug, task, chore)
> **Result:** docs folder + beads tracking + approval flow

---

## Step 0: Create docs folder (ALL types)

**This step is MANDATORY for every type. No exceptions.**

```bash
mkdir -p .claude/development/docs/features/{ISSUE-KEY}
```

---

## Step 0.5: Explore — derive the axes (ALL types)

**This step is MANDATORY for every type, and it runs BEFORE the type is chosen. No exceptions.**

Launch the Explore role as a subagent — `Agent(subagent_type="explore")` — with the target the request is about (a path or a symbol). It returns one artifact and nothing else: the `## Axes` section `beadloom impact <target> --section` renders, with every site as a path and a line and the `In scope` column left undecided.

```bash
beadloom impact <path|symbol> --section     # what the role runs; do not hand-write the table
```

Then decide the scope with the user: rule each row `yes` or `no` with a reason in the `Why` cell. That decision is the person's half of the section and the role does not take it.

**Why before the type.** The axis count is what says whether a work item is a bug. The one time this project chose the type first, the item was routed `bug` and became 28 beads — and re-deriving the axes afterwards showed the change ranging over four graph nodes. `beadloom docs quality` reports a simplified-flow work item that carries no `## Axes` section, and one whose kept axes name more nodes than the route it took can hold, so this step is checked rather than trusted.

---

## Type detection

**The route is decided from the axes derived in Step 0.5, not from how the request was phrased.**

| Type | Flow | Docs created |
|------|------|-------------|
| `epic` | Full: PRD → RFC → CONTEXT+PLAN → ACTIVE | PRD, RFC, CONTEXT, PLAN, ACTIVE |
| `feature` | Full: PRD → RFC → CONTEXT+PLAN → ACTIVE | PRD, RFC, CONTEXT, PLAN, ACTIVE |
| `bug` | Simplified: BRIEF → ACTIVE | BRIEF, ACTIVE |
| `task` | Simplified: BRIEF → ACTIVE | BRIEF, ACTIVE |
| `chore` | Simplified: BRIEF → ACTIVE | BRIEF, ACTIVE |

The simplified flow writes one BRIEF and passes no approval gate, so it is the route with nothing in it that records a crossing:

- Kept axes naming **one** node — the simplified flow carries the change.
- Kept axes naming **more than one** node — take the full flow, or narrow the work item's scope until the axes name one. The count is a fact about the change and not a preference, so a route taken against it is reported.
- **No axes at all** — the type has not been decided from anything. Go back to Step 0.5.

Paste the section into the work item's BRIEF (simplified) or RFC (full). Both templates carry the `## Axes` heading, so a missing section is a `doc-quality` finding rather than an omission somebody has to notice.

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
   - Describe beads, dependencies, waves — but do NOT create beads yet
3. Show both to user
4. **WAIT for explicit approval**
5. Update both to `Status: Approved`
6. **Create beads in tracker** (ONLY after PLAN is Approved):
   - One-time per clone: ensure `git config beads.role maintainer` is set (see CLAUDE.md §0 Setup).
   - Create parent bead: `bd create --type feature --title "[ISSUE-KEY] Name"` (use `--type epic` if you want `bd swarm` orchestration — swarm requires an epic-type parent; feature parents still work via bead dependencies)
   - Create sub-beads with mandatory structure (see below): `bd create --type task --parent <parent-id>`
   - Set up dependencies: `bd dep add <blocked> <blocker>`
   - **Faster alternative (1.0.4):** create the whole bead DAG in one shot from a JSON plan — `bd create --graph <plan.json>` (define nodes + dependencies in the file).
7. **Immediately proceed to Step 4** (no additional approval needed)

**Process gate:** Do NOT create beads before PLAN is Approved. If PLAN is rejected or modified, no stale beads to clean up.

**Mandatory bead structure (full flow):**
```
<parent-id> [feature/epic] — parent bead
├── <parent-id>.N [task/dev]        — development sub-tasks (one per BEAD)
├── <parent-id>.N [task/test]       — test agent sub-task
├── <parent-id>.N [task/review]     — review agent sub-task
└── <parent-id>.N [task/tech-writer]— doc update sub-task
```

Every feature/epic MUST include sub-tasks for all four agent roles:
- `dev` — implementation beads (one per logical unit of work)
- `test` — test verification bead (depends on all dev beads)
- `review` — code review bead (depends on test bead)
- `tech-writer` — documentation update bead (depends on review bead)

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
2. Paste the `## Axes` section from Step 0.5, with every row ruled `yes` or `no` and a reason
3. Fill in: Problem, Solution, Beads, Acceptance Criteria
4. Create beads in tracker, with each bead's `refs:` generated from the section
   rather than typed — `beadloom axes .claude/development/docs/features/{ISSUE-KEY}/BRIEF.md --refs`:
   ```bash
   bd create --type {type} --title "{ISSUE-KEY}: [Name]" --description "..."
   # If multiple subtasks:
   bd create --type task --title "BEAD-01: [Name]" --parent <parent-id>
   ```
5. Show to user
6. **WAIT for explicit approval**
7. Update `Status: Approved`

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
- [ ] Explore run (Step 0.5) and its `## Axes` section produced
- [ ] Every axis row ruled in or out of scope, with a reason
- [ ] Route checked against the axes: more than one node kept -> full flow
- [ ] PRD.md created with `Status: Draft` (in English)
- [ ] PRD.md → **user approved** → `Status: Approved`
- [ ] RFC.md created with `Status: Draft` (in English)
- [ ] RFC.md → **user approved** → `Status: Approved`
- [ ] CONTEXT.md created with `Status: Draft`
- [ ] PLAN.md created with `Status: Draft` (beads described, NOT created yet)
- [ ] CONTEXT.md + PLAN.md → **user approved** → `Status: Approved`
- [ ] Parent bead created: `bd create --type feature`
- [ ] Dev sub-beads created: `bd create --type task --parent <parent-id>`
- [ ] Test sub-bead created (depends on all dev beads)
- [ ] Review sub-bead created (depends on test bead)
- [ ] Tech-writer sub-bead created (depends on review bead)
- [ ] Dependencies set: `bd dep add`
- [ ] ACTIVE.md created
- [ ] User confirmed start of development

### Simplified flow (bug | task | chore)
- [ ] Created folder `.claude/development/docs/features/{ISSUE-KEY}/`
- [ ] Explore run (Step 0.5) and its `## Axes` section produced
- [ ] Every axis row ruled in or out of scope, with a reason
- [ ] Kept axes name ONE node — otherwise this is not a simplified-flow item
- [ ] BRIEF.md created with `Status: Draft`, carrying the `## Axes` section
- [ ] Beads created in tracker, `refs:` generated by `beadloom axes <BRIEF> --refs`
- [ ] BRIEF.md → **user approved** → `Status: Approved`
- [ ] ACTIVE.md created
- [ ] Work started
