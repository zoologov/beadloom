# RFC: BDL-048 — Agentic-flow packaging

> **Status:** Approved
> **Created:** 2026-06-10
> **PRD:** ./PRD.md

---

## Summary

Two deliverables, one principle: **the packaged flow is the CURRENT proven flow, 1:1.**

1. **`beadloom setup-agentic-flow`** (setup-* family) scaffolds the proven `.claude/` flow into any repo: the `agents/*` + `commands/*` are vendored **byte-identical** to Beadloom's own live `.claude/` (a drift-guard test keeps them in sync — the same vendor pattern as the F4.1 harness), and the `CLAUDE.md` auto-regions are **generated per-project** (project name / stack / version / commands) by reusing the existing `onboarding/config_sync.py` machinery. So a new repo gets the exact, proven process mechanics — not a rewrite — with only the project-specific facts swapped.
2. **MCP process-tools "with teeth"** added to `services/mcp_server.py` (same `mcp.Tool` registration + `call_tool` dispatch as the 14 existing tools): `task_init`, `bead_context`, `complete_bead`, `checkpoint`. These make the flow's deterministic steps real, refusable operations over the substrate — available to ANY MCP client.

**Orchestration stays in the harness** (G4, non-negotiable): MCP can't spawn sub-agents or run the main loop. The coordinator + `Agent`-spawn remain Claude-Code-native (scaffolded by part 1). MCP gives deterministic process-tools (part 2), not orchestration.

## Preserving the flow 1:1 (the owner's hard requirement)

The flow's effectiveness/stability lives in the EXACT wording of `.claude/agents/*.md` + `.claude/commands/*.md` (the role protocols, the coordinator playbook, the honesty gotchas) — refined over ~46 epics. **We do not rewrite or summarize them.** Mechanism:

- The scaffold's templates for `agents/*` + `commands/*` are **vendored copies of Beadloom's own live `.claude/`** (Beadloom is the reference implementation). A **drift-guard test** asserts the vendored template == the live `.claude/` file byte-for-byte (mirrors the F4.1 `sync_vendored_harness` drift-guard). If the live flow improves, the test fails until the templates are re-vendored → the scaffold always ships the latest proven flow.
- **Project-specific bits are NOT in those files.** The agents/commands are already project-agnostic (they describe the *process*, not Beadloom's domains). The only project-specific content — version, stack, package list, CLI command list — lives in the `CLAUDE.md` **auto-regions** (`<!-- beadloom:auto-start --> … <!-- beadloom:auto-end -->`), which `config_sync.py` already **generates per-project** and `config-check` already drift-checks. The scaffold reuses that verbatim.
- Net: identical process mechanics on every repo; correct per-project facts; `config-check` keeps both honest.

## Part 1 — `beadloom setup-agentic-flow`

- **Command, not a flag** (RFC decision): a `setup-agentic-flow` command in the setup-* family — consistent with `setup-rules`/`setup-mcp`/`setup-ai-techwriter`, and it reuses their generate+diff/`config-check` plumbing. (An `init --agentic-flow` alias can call it if desired; the command is canonical.)
- **What it scaffolds** into the target repo, idempotently:
  - `.claude/agents/{dev,test,review,tech-writer}.md` — vendored byte-identical (drift-guarded).
  - `.claude/commands/{coordinator,task-init,checkpoint,templates}.md` — vendored byte-identical (drift-guarded).
  - `.claude/CLAUDE.md` — the auto-regions generated per-project via `config_sync` (reuses `setup-rules --refresh`); user prose outside the regions is never touched.
  - (Optionally) a pointer in AGENTS.md / IDE rules so non-Claude tools find the flow (reuse `setup-rules`).
- **Idempotent + `config-check`-aware:** re-running regenerates only the auto-regions + re-drops the vendored files; `config-check` reports drift if a scaffolded repo's flow diverged from the shipped templates (extend `config_sync` to cover the agentic-flow files).
- **Honest boundary doc:** the scaffolded `CLAUDE.md`/guide states that the coordinator + Agent-spawn are Claude-Code-native, and the MCP process-tools (part 2) are the tool-agnostic substrate the flow calls.

## Part 2 — MCP process-tools (`services/mcp_server.py`)

Added next to the 14 existing tools (`mcp.Tool(name=…)` + a `call_tool` branch each). These are **action** tools (like the existing `update_node`/`mark_synced` write tools), reusing existing application/substrate code — NOT reimplementing logic:

| Tool | Does | Reuses |
|------|------|--------|
| `task_init(type, key)` | Create `.claude/development/docs/features/<key>/` + the doc templates (PRD/RFC/CONTEXT/PLAN/ACTIVE or BRIEF) + a **valid bead-DAG** (mandatory 4-role structure + deps) via `bd create --graph <plan.json>`. Returns created bead ids + paths. | `/templates` content; `bd` CLI (shelled, like the harness shells `beadloom`) |
| `bead_context(bead)` | One structured payload: `ctx(ref)` + `why(ref)` + the bead's CONTEXT.md/ACTIVE.md excerpt + the **active rules** for the bead's area (from the rule engine). The substrate giving the agent scoped, deterministic context. | `context_oracle` (ctx/why), `graph/rule_engine` (active rules) |
| `complete_bead(bead)` | The **refusing gate**: run `beadloom ci` (reindex→lint→sync-check→config-check→doctor) **and** the test suite; return structured PASS/FAIL + findings. On PASS: close the bead (`bd close --suggest-next`) and return next-ready. On FAIL: do NOT close — return the failures so the agent must fix. | `application/gate.run_ci_gate`; `bd` |
| `checkpoint(bead, text)` | Canonical `bd comments add <bead> <text>` + append a progress note to ACTIVE.md. | `bd`; file write |

- **Dependency on `bd`:** `task_init`/`complete_bead`/`checkpoint` shell out to `bd` (steveyegge/beads, already a flow dependency) — wrapped thinly (a `run_command`-style seam) so it's mockable + testable without `bd`. If `bd` is absent, the tool returns a clear error (the flow already requires `bd`).
- **No new orchestration:** none of these spawn agents or loop; they are single deterministic operations an agent/harness calls.

## Decisions on the open questions

1. **Command vs flag → `setup-agentic-flow` command** (setup-* family). Canonical; optional `init --agentic-flow` alias delegates to it.
2. **Internals:** `task_init` → `bd create --graph` (one-shot DAG, the documented 1.0.4 path); `complete_bead` → `application/gate.run_ci_gate` + tests; `bead_context` → context_oracle + rule_engine. All reuse existing code.
3. **Tools-only for v1.** MCP `prompts` (porting the coordinator/role personas) deferred — client support is uneven in 2026, and the `.claude/` scaffold already delivers the personas Claude-Code-native. Prompts = a later optional slice.
4. **config-check integration:** extend `config_sync.py` so `config-check` drift-checks the scaffolded agentic-flow files (vendored agents/commands byte-match + CLAUDE.md auto-regions), exactly as it does the other auto-managed config.

## Component / file impact

| Component | Change | Tested by |
|-----------|--------|-----------|
| `src/beadloom/onboarding/agentic_flow_setup.py` (NEW) | `setup-agentic-flow` scaffold (vendor agents/commands + generate CLAUDE.md regions); idempotent | unit + CLI |
| `src/beadloom/onboarding/templates/agentic_flow/` (NEW) | vendored `.claude/agents/*` + `commands/*` assets (byte-identical to live; drift-guarded) | drift-guard test |
| `src/beadloom/onboarding/config_sync.py` | extend drift/refresh to cover the agentic-flow files for `config-check` | unit |
| `src/beadloom/services/cli.py` | `setup-agentic-flow` command (+ optional `init --agentic-flow` alias) | CLI test |
| `src/beadloom/services/mcp_server.py` | 4 new process-tools (`task_init`/`bead_context`/`complete_bead`/`checkpoint`) + a mockable `bd` seam | unit (bd + gate mocked) |
| docs (guide), CHANGELOG, ROADMAP | tech-writer | — |

The MCP tools are unit-tested with `bd` + the gate **mocked** (deterministic, no external `bd`/network); the real end-to-end is the dogfood (G6).

## Alternatives considered

- **`init --agentic-flow` flag (only).** Rejected as primary: the setup-* family is the consistent home + reuses config-check; a flag can alias it.
- **Rewriting/condensing the flow into a leaner packaged form.** Rejected hard (owner requirement): the flow's effectiveness is the exact proven wording — vendor it 1:1, don't rewrite.
- **Putting orchestration in MCP (sampling/sub-agents).** Rejected: structurally impossible (MCP can't spawn sub-agents / own the loop); orchestration stays in the harness.
- **Generating the agents/commands per-project (templated).** Rejected: risks drifting from the proven flow; vendor byte-identical + only template the CLAUDE.md facts.

## Risks & mitigations

- **Scaffolded flow drifts from the proven one.** Mitigate: drift-guard test (vendored == live `.claude/`) + `config-check` on scaffolded repos. Re-vendor when the live flow improves.
- **Over-claiming MCP "runs the flow".** Mitigate: G4/G5 honest framing in docs — MCP = deterministic process-tools + distribution; orchestration + true enforcement (CI) stay where they are.
- **`complete_bead` running the full gate+tests is slow / heavy in an MCP call.** Mitigate: it's an explicit, occasional action (bead completion), not hot-path; return progress; allow a `--no-tests` fast variant if needed (RFC-open, decide in dev).
- **`bd` coupling.** Mitigate: thin mockable seam; clear error if absent; `bd` is already a flow prerequisite.

## Rollout

Single epic, waves: dev (1: `setup-agentic-flow` + vendored templates + config-check drift → 2: the 4 MCP process-tools + bd seam) → test → review → **dogfood (G6: scaffold on a fresh test dir + drive the process-tools; `complete_bead` refuses a red gate, passes green)** → tech-writer. Each step keeps Beadloom green on its own `beadloom ci`. Beadloom's own `.claude/` remains the reference the templates are vendored from.
