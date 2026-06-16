# /coordinator — Multi-agent Work Coordinator

> **When to invoke:** during parallel work with multiple agents (an epic with independent beads)
> **Focus:** task distribution, synchronization, quality gating
> **Backbone:** bead dependencies + `bd ready` (waves, always) · `bd merge-slot` (serialized merges) · `bd gate` (CI/external waits) · `bd swarm` (optional convenience for epic-type parents: validate/status)
> **The coordinator is the MAIN-LOOP process, not a subagent** — it spawns role subagents via the `Agent` tool, and a subagent cannot spawn subagents. That is why it lives in `.claude/commands/` (skill injected into the main loop), not `.claude/agents/`.

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
3. **Independent ready beads in the same wave MUST be launched concurrently** — one subagent each, all in the same batch (`run_in_background: true`), NOT one-at-a-time. Parallelism is mandatory, not optional: if `bd ready` lists N independent beads, spawn N subagents now. `bd ready` (universal) / `bd dep tree` is authoritative for what is launchable — NOT `bd close --suggest-next` (which can list still-blocked beads; see BDL-UX-Issues #97).
4. **Serialize landings** with `bd merge-slot` so the parallel agents never race on commits/merges — they run concurrently but land one at a time.

---

## Autonomy: permissions & command hygiene (frictionless flow)

A multi-agent flow stalls if every `git`/`bd`/`beadloom`/test command waits on a
human allow/deny click. Run the loop autonomously, surfacing to the human ONLY at
control points (slice/wave boundaries, approvals, reports) — never for routine
command permission.

**Permission posture (one-time, per operator — `.claude/settings.local.json`, gitignored):**
- A broad `allow` for project tooling families (`Bash(git:*)`, `Bash(bd:*)`,
  `Bash(beadloom:*)`, `Bash(uv:*)`, `Bash(pytest:*)`, `Bash(ruff:*)`, `Bash(mypy:*)`,
  read-only text utils `grep/awk/sed/sort/jq/...`, `Read`), plus
  `defaultMode: "dontAsk"` for genuinely frictionless operation.
- A small **destructive deny-net that always wins over dontAsk**: `rm -rf /`/`~`
  variants, force-push to `main`. Server-side branch protection backs the latter.
- Subagents inherit these settings. Keep the deny-net tight and the allow broad.

**Command hygiene (avoid the hard structural safety gates — these fire regardless
of any allow/deny/dontAsk setting, because the parser can't verify the command):**
- **No `cd` inside a compound command** — use absolute paths; the shell cwd
  persists between calls. `cd /x && cmd > f` trips a path-bypass gate.
- **No output redirection to paths OUTSIDE the project** (`> /tmp/...`) — write
  scratch inside the workspace, or pre-authorize the dir in `additionalDirectories`.
- **No `for`/`while` loops with `$var` expansion** — run explicit separate commands
  (the "simple_expansion" gate blocks variable-expanded loop bodies).
- Need an exit code without pipe-masking? append `; echo EXIT:$?` (no redirect);
  pipe long output through `| tail`. Keep each command simple and parser-safe.

These are operator/Claude-Code-adapter conventions; the orchestration logic below
is tool-agnostic.

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
Wave 1 (dev): independent dev beads in parallel (one subagent each — MUST be concurrent)
Wave 2 (dev): beads unblocked by Wave 1
Test wave:    after ALL dev beads close
Review wave:  after test
  ├── OK     → docs wave
  └── ISSUES → coordinator opens fix beads, re-runs dev→test→review
Docs wave:    ONLY after review = OK (tech-writer)
Gate wave:    run the Beadloom Gate, loop tech-writer until green, THEN push → PR
```

### The Gate-enforced loop (explicit tool steps — do NOT rely on memory)

After the docs wave, the coordinator enforces the hard invariant ("no code in
`main` without current docs") through a deterministic state machine. These are
explicit tool calls, branching on the Gate's exit code — not prose to remember:

```
1. Run the tech-writer subagent on the wave's refs (docs wave above).
2. Run the Beadloom Gate:           beadloom ci        # exit 0 = green, non-zero = red
3. WHILE the Gate is red AND attempts < 3:
     a. Identify the drifted refs    (beadloom sync-check --json / the Gate output)
     b. Run the tech-writer subagent on EXACTLY those drifted refs
     c. Re-run the Gate:             beadloom ci        # re-gate
4. Gate green → push (the pre-push hook re-checks the Gate as a backstop) → open the PR.
5. Gate STILL red after the bound (≤3 attempts) → STOP. Do NOT push. Surface a
   clear failure (flag the bead + a bd comment with the unresolved refs) instead
   of spinning. A human/`/coordinator` re-entry resolves it.
```

The push step relies on the **pre-push Beadloom Gate hook** (`beadloom install-hooks`
installs `pre-push`) as the authoritative blocking backstop: even if the loop above
is skipped, a red Gate blocks the push. `git push --no-verify` is the documented,
discouraged escape hatch.

### Drive deterministic steps through the process-tools

For the deterministic, repeatable steps of the loop — scaffolding, per-bead context, checkpoints, completion — the coordinator SHOULD call the Beadloom MCP process-tools (`task_init` / `bead_context` / `checkpoint` / `complete_bead`) rather than hand-running the equivalent shell. In particular `checkpoint` and `complete_bead` maintain the epic's `ACTIVE.md` bead-status table by construction (`checkpoint` → row `in progress`; `complete_bead` PASS → row `✓ done`), so the table never drifts from `bd`. Honest boundary: orchestration (Agent-spawn, wave gating) stays main-loop — the process-tools cover the deterministic steps, not the spawning.

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

### Subagent write-blocked fallback (observed BDL-036)

A background subagent may report that file-writing tools (`Edit`/`Write`, and sometimes `grep`/`python3` piping) are denied in its environment, so it cannot do its work. (In BDL-036 the background `tech-writer` subagent hit this while parallel `dev` subagents in the same run wrote files fine — cause unconfirmed, likely transient/sandbox; treat it as possible, not guaranteed.)

**Fallback:** if a subagent returns "blocked — could not edit files", the coordinator (main loop) does NOT silently drop the bead. Either (a) re-launch the subagent, or (b) **complete the bead inline in the main loop** using the subagent's analysis (it should still return its findings), then checkpoint + close the bead normally. For write-heavy beads (docs/finalization), inline execution by the main loop is an acceptable first choice when a prior subagent was write-blocked. Record the fallback honestly in the bead comment.

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

When the review subagent returns:
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

> Per-wave commits land on the `features/<ISSUE-KEY>` branch (trunk-based — see below), never directly on `main`.

```
BEFORE WAVE COMMIT:
□ On the features/<ISSUE-KEY> branch (NOT main — main is branch-protected)
□ All wave beads closed (`bd ready` / `bd dep tree`; `bd swarm status` if epic)
□ bd comments show checkpoints for every wave bead
□ CONTEXT.md current (phase, new files, last-updated); ACTIVE.md reflects results
□ uv run pytest — all pass
□ beadloom reindex && sync-check && lint --strict && doctor — clean
□ beadloom snapshot save <label>  (per-wave architecture record)
□ Merges serialized via bd merge-slot (no concurrent landings)
```

---

## Trunk-based branching + PR-gated integration (MANDATORY)

The coordinator runs the whole epic/feature on a **short-lived `features/<ISSUE-KEY>` branch** — `main` is branch-protected (no direct push). The wave/gate model above is unchanged; only *where* commits land and *how* they reach `main` changes:

```
git switch -c features/<ISSUE-KEY>        # once, at activation (branch off main)
# ... waves run; per-wave commits land on features/<ISSUE-KEY> (NOT main) ...
# when the epic/feature slice is green: open ONE PR features/<ISSUE-KEY> -> main
```

- **One branch per epic/feature.** All per-wave commits (dev → test → review → tech-writer) land on `features/<ISSUE-KEY>`, not `main`. The per-wave commit checklist still applies — it just commits to the feature branch.
- **One PR to `main` per epic/feature** (or per shippable slice), opened after the local waves are green. Not one PR per commit — that is the solo-friction trap.
- **The PR triggers the AI tech-writer + CI.** On `pull_request → main`, the AI tech-writer runs ONCE against the PR's diff (`--since` = merge-base) and **commits its doc refresh back INTO the PR branch** (no orphan doc-PR); `beadloom ci` runs as a **required status check**. A loop-guard (`[skip ai-techwriter]` + bot author) stops the agent's own push from re-triggering.
- **Merge to `main` only when green.** Merge the PR only once CI is green AND the agent's doc refresh has landed in the PR. The human merges (no auto-merge). Because CI is a required check, `main` stays always-green.
- **Gate the merge with `bd gate`** (the CI bridge already in this playbook):
  ```bash
  bd gate create --type gh:pr --blocks <merge-bead>   # block the merge bead until the PR's checks pass
  bd gate discover && bd gate check                    # resolve + auto-close when green
  ```
- One-time per repo: `beadloom setup-branch-protection` configures `main` protection (PR required, `beadloom ci` a required check, owner still mergeable). See `.claude/CLAUDE.md` §6 Git.

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
