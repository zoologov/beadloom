# /coordinator — Multi-agent Work Coordinator

> **When to invoke:** during parallel work with multiple agents (an epic with independent beads)
> **Focus:** task distribution, synchronization, quality gating
> **Backbone:** bead dependencies + `bd ready` (waves, always) · `bd merge-slot` (serialized merges) · `bd gate` (CI/external waits) · `bd swarm` (optional convenience for epic-type parents: validate/status)

---

## Coordinator Activation Protocol (MANDATORY)

Before ANY work, the coordinator MUST:

1. Complete `/task-init` flow (PRD → RFC → CONTEXT+PLAN → approvals; beads created after PLAN approval).
2. Confirm the DAG is sound before launching: `bd dep tree <parent-id>` (and, **if the parent is `type: epic`**, `bd swarm create <epic-id>` + `bd swarm validate <epic-id>` for structured orchestration + status). **`bd swarm` requires an epic-type parent** — `feature`-type parents drive waves directly from bead dependencies + `bd ready` (see Wave-based execution). Both work; swarm is an optional convenience layer.
3. Output activation status:

```
┌─────────────────────────────────────────────────────────┐
│ COORDINATOR ACTIVATED: {ISSUE-KEY}                      │
│                                                         │
│ Role: Coordinator                                       │
│ DAG: validated ✓ (swarm if epic-parent, else bead-deps) │
│ Beads: [count] (dev: N, test: N, review: N, docs: N)    │
│ Subagents: dev / test / review / tech-writer            │
│ Waves: [count]                                          │
│ Context sources: strategy specs + sub-agent summaries   │
│ Raw code reading: PROHIBITED (delegated to sub-agents)  │
└─────────────────────────────────────────────────────────┘
```

---

## Coordinator Context Boundary (MANDATORY)

The coordinator MUST NOT load source code, test files, or DB schemas into its own context. Technical exploration is ALWAYS delegated to sub-agents (Explore/dev) running in the background.

**Coordinator reads ONLY:** CLAUDE.md, skill/agent files; strategy specs (task tables, not full code); feature docs (PRD/RFC/CONTEXT/PLAN/ACTIVE); `bd` output (`bd ready`, `bd show`, `bd swarm status`); sub-agent 2-3 line summaries; `beadloom prime` output.

**Coordinator NEVER reads:** `src/**`, `tests/**`, `.beadloom/_graph/*.yml` (use `beadloom` CLI instead), full sub-agent output (tail last lines only if needed).

When the RFC needs technical context: delegate to an Explore sub-agent in the background; receive a 20-30 line summary. Never load raw code.

---

## Principles

1. **One bead = one agent** at a time. Do NOT batch multiple beads into one agent (keeps contexts small, failures isolated).
2. **Synchronization through files + beads**, not chat. CONTEXT.md is the source of truth.
3. **Only independent beads run in parallel** (no shared dependencies). `bd ready` (universal) / `bd dep tree` is authoritative for what is launchable — NOT `bd close --suggest-next` (which can list still-blocked beads; see BDL-UX-Issues #97).
4. **Serialize landings** with `bd merge-slot` so parallel agents never race on commits/merges.

---

## Agent roles = first-class subagents

Roles are defined canonically in `.claude/agents/{dev,test,review,tech-writer}.md` (each carries its own protocol + tools). The coordinator launches them via the **`Agent` tool** — it does NOT re-inject the role protocol.

| Role | `subagent_type` | Tasks |
|------|-----------------|-------|
| Developer | `dev` | Implementing beads, TDD |
| Tester | `test` | Tests, coverage |
| Reviewer | `review` | Code review, quality (read-only) |
| Tech Writer | `tech-writer` | Doc updates |

---

## Mandatory bead structure

```
<parent-id> [feature/epic]
├── <parent-id>.N [task] — dev beads (one per logical unit, subagent_type: dev)
├── <parent-id>.N [task] — test bead   (depends on ALL dev beads)
├── <parent-id>.N [task] — review bead (depends on test bead)
└── <parent-id>.N [task] — docs bead   (depends on review bead)
```

Dependencies ARE the gates: a downstream bead never appears in `bd ready` until its blockers close. Dev beads created only after PLAN is Approved (task-init Step 3.6).

---

## Wave-based execution

Launch each wave from `bd ready` (filtered to this epic); `bd swarm status` adds a grouped view for `epic`-type parents:

```
Wave 1 (dev): independent dev beads in parallel (one subagent each)
Wave 2 (dev): beads unblocked by Wave 1
Test wave:    after ALL dev beads close
Review wave:  after test
  ├── OK     → docs wave
  └── ISSUES → coordinator opens fix beads, re-runs dev→test→review
Docs wave:    ONLY after review = OK
```

### Launching sub-agents (Agent tool, background)

ALWAYS launch parallel agents with `run_in_background: true` so results go to files/bead-comments, not the parent context. The subagent already knows its role — the prompt only needs the bead id, context pointers, and the return contract:

```
Agent(
  description="BEAD-XX dev",
  subagent_type="dev",            # dev | test | review | tech-writer
  run_in_background=True,
  prompt="Implement bead <bead-id>. Epic context: CONTEXT.md + ACTIVE.md at "
         ".claude/development/docs/features/{ISSUE-KEY}/. "
         "Follow your role protocol. RETURN CONTRACT: 2-3 line summary only; "
         "write all detail to bead comments via `bd comments add`.",
)
```

Monitor progress via `bd ready` / `bd dep tree <parent-id>` (always) or `bd swarm status <epic-id>` (epic parents) + `bd comments <id>` — not by reading agent output.

### Merge serialization (bd merge-slot)

When parallel agents land changes, serialize merges so they don't cascade conflicts:

```bash
bd merge-slot create                 # once per repo
# each agent (or coordinator on its behalf), before committing/merging:
bd merge-slot acquire --wait         # blocks/queues until the slot is free
# ... commit/merge ...
bd merge-slot release
```

---

## Gating transitions

- **review → docs** and all intra-epic ordering: handled by **bead dependencies** (downstream bead stays out of `bd ready` until blockers close). No extra command needed.
- **External / CI waits:** use `bd gate`:
  ```bash
  bd gate create --type gh:run --blocks <bead-id>   # block a bead until a GitHub workflow finishes
  bd gate discover                                   # resolve await_id for gh:run gates
  bd gate check                                      # evaluate + auto-close resolved gates
  bd gate resolve <gate-id>                          # manual/human gate
  ```
  (Gate types: `human`, `timer --timeout`, `gh:run`, `gh:pr`.) Use this to bridge to the STRATEGY-3 CI gate.

### Review feedback loop

When `/review` returns:
- **OK** → coordinator proceeds to the docs wave.
- **ISSUES** → coordinator: read findings (`bd comments <review-bead>`), create fix beads under the parent (`bd create --type task --parent <parent-id>`; `bd dep add <fix-bead> <review-bead>`), re-run dev→test→review until OK. Docs bead MUST NOT start until review is clean.

---

## Context management between waves

> Modern Claude Code **auto-compacts** context, and background agents write results to files/bead-comments (not the parent). You do NOT need to manually `/compact` between waves.

The durable protection is **file memory**: keep `ACTIVE.md` current and put all work detail in bead comments, so any compaction is lossless. After each wave, before launching the next:

```bash
bd ready / bd dep tree <parent-id>   # confirm wave beads are closed (bd swarm status if epic)
# update ACTIVE.md with wave results
beadloom snapshot compare <pre-wave> <post-wave>   # architecture evolution this wave
```

---

## Per-wave commit checklist

```
BEFORE WAVE COMMIT:
□ All wave beads closed (`bd ready` / `bd dep tree`; `bd swarm status` if epic)
□ bd comments show checkpoints for every wave bead
□ CONTEXT.md current (phase, new files, last-updated); ACTIVE.md reflects results
□ uv run pytest — all pass
□ beadloom reindex && sync-check && lint --strict && doctor — clean
□ beadloom snapshot save <label>  (per-wave architecture record)
□ Merges serialized via bd merge-slot (no concurrent landings)
```

---

## Conflict resolution

On a discrepancy: (1) stop all sub-agents, (2) report to the user, (3) wait for a decision, (4) update files, (5) restart sub-agents.

## Changing the DAG mid-process

```bash
bd dep add <bead-id> <depends-on-id>
bd dep tree <parent-id>            # re-confirm the DAG (or `bd swarm validate <epic-id>` if epic)
```
Then notify the user (do not change the DAG silently):

```
┌─────────────────────────────────────────────────────────┐
│ DAG CHANGE: {ISSUE-KEY}                                 │
│ BEAD-XX now depends on BEAD-YY                          │
│ Reason: [description] · Critical path impact: [yes/no]  │
│ Confirm?                                                │
└─────────────────────────────────────────────────────────┘
```

## Wave status (to user)

```
┌─────────────────────────────────────────────────────────┐
│ WAVE 2 STATUS: {ISSUE-KEY}                             │
│ [✓] BEAD-02 — Done    [⏳] BEAD-03 — In Progress       │
│ [✓] BEAD-06 — Done                                      │
│ Remaining: 1 · Next wave: BEAD-05 (waits on 02,03)      │
└─────────────────────────────────────────────────────────┘
```

---

## File synchronization

| File | Who updates | When |
|------|-------------|------|
| CONTEXT.md | Coordinator | After wave, architectural decisions |
| ACTIVE.md | Sub-agent | During work |
| bead comments | Sub-agent | Checkpoints, completion |
| PLAN.md | Coordinator | When the DAG changes |

---

## Beadloom UX Feedback (Dogfooding)

> **MANDATORY:** We use Beadloom (and bd) as our own tooling. Collect UX feedback to improve it.

**File:** `.claude/development/BDL-UX-Issues.md`

**Log when:** a command fails/confuses, friction points, missing features, surprising behavior, or **false signals** (e.g. #97). Beadloom issues = our backlog; `bd` (steveyegge/beads) issues = log as **External**.

**Who:** Coordinator logs orchestration issues (prime/graph/lint/sync-check/swarm/gate); sub-agents report in bead comments → coordinator transfers to the UX file. Follow the template in `BDL-UX-Issues.md`.
