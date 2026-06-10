# PRD: BDL-048 — Agentic-flow packaging

> **Status:** Approved
> **Created:** 2026-06-10
> **Roadmap:** P0 (agentic cluster), serves north-star (a) — solo multi-agent dev flow.

---

## Problem

Beadloom's #1 value (per the vision) is the **solo multi-agent dev flow**: Claude Code + Beadloom + Beads + GitHub, which produced this very codebase (91.6% coverage, mypy-strict, 0 TODO). But that flow today is **~1100 lines of copyable Markdown** — `.claude/commands/` (coordinator, task-init, checkpoint, templates) + `.claude/agents/` (dev/test/review/tech-writer) + the auto-regions of `CLAUDE.md`. Three problems (REVIEW-2 §7/§8):

1. **Not reproducible on a new repo.** A new project (or a teammate's service) must hand-copy + adapt the `.claude/` tree. There's no one-command way to install the flow.
2. **Claude-Code-specific.** The flow lives in `.claude/` and assumes Claude Code's Agent tool. It's not tool-agnostic — Cursor/Continue/other MCP clients don't get it (violates the "one context for everyone / tool-agnostic" principle).
3. **The "gates" are advisory prose.** task-init's "create a valid bead-DAG", the coordinator's "complete the bead only when lint/sync-check/tests pass" — these are *instructions a model may or may not follow*, not enforceable operations. The honesty/quality of the flow rides on the model reading Markdown correctly.

The moat is the **Beadloom substrate** (the graph + ctx/why/lint/sync-check), not the Markdown. But the flow that exercises that substrate isn't packaged into the product.

## Impact

Package the flow into the product so it is (a) **reproducible** via one command, (b) **tool-agnostic** via MCP (any MCP client gets the same deterministic process-tools), and (c) **enforceable** where it can be (the deterministic steps become tools that can refuse). This makes Beadloom's strongest asset — the solo-multi-agent flow — distributable + repeatable on any repo, directly serving north-star (a).

Honesty framing (REVIEW-2 §8, non-negotiable): **orchestration stays in the harness.** MCP serves *tools* (and optionally *prompts*); it cannot spawn sub-agents or run the main loop. The coordinator (which spawns role subagents) remains a harness/Claude-Code concern. MCP gives **deterministic process-tools over the architecture graph** — that's the real upgrade over copyable Markdown — not "the flow now runs inside MCP".

Success criterion: **on a fresh repo, one command scaffolds the agentic flow; an MCP client can call `task_init` / `bead_context` / `complete_bead` / `checkpoint` against Beadloom; and `complete_bead` actually REFUSES when lint/sync-check/tests are red — dogfooded on a real run.**

## Goals

- [ ] **G1 — One-command scaffold of the flow.** `beadloom setup-agentic-flow` (setup-* family, alongside `setup-rules`/`setup-mcp`/`setup-ai-techwriter`; exact name/flag is an RFC decision) scaffolds the `.claude/` flow — agents (dev/test/review/tech-writer) + commands (coordinator/task-init/checkpoint/templates) + the auto-managed `CLAUDE.md` regions — into a target repo. Idempotent + **`config-check`-friendly** (generate+diff the auto-regions only, never user prose — reuse the `setup-rules --refresh` machinery).
- [ ] **G2 — MCP process-tools "with teeth"** on the existing `services/mcp_server.py` (same `mcp.Tool` registration + dispatch as the 14 read tools):
  - `task_init(type, key)` — create the docs folder + a **valid bead-DAG** (the mandatory 4-role structure + dependencies), deterministically (shells `bd create`/`bd dep`).
  - `bead_context(bead)` — return `ctx` + `why` + the relevant CONTEXT/ACTIVE + the **active rules** for the bead's area, in one call (the substrate giving the agent its scoped context).
  - `complete_bead(bead)` — a **gate that can REFUSE**: runs `lint --strict` / `sync-check` / tests and returns a structured PASS/FAIL; on FAIL it does not let the bead "complete" (returns the failures).
  - `checkpoint(bead, text)` — canonical `bd comments add` + ACTIVE.md progress note.
- [ ] **G3 — Tool-agnostic via MCP.** The process-tools work from any MCP client (Cursor/Continue/Claude Code), not just Claude Code — fulfilling "one context for everyone". (Verify against the pinned MCP spec.)
- [ ] **G4 — Orchestration stays in the harness (honest boundary).** MCP provides tools (+ optionally prompts); it does NOT spawn sub-agents or own the main loop. The coordinator + `Agent`-spawn remain harness/Claude-Code-native (the `setup-agentic-flow` scaffold covers that side). Documented explicitly.
- [ ] **G5 — Enforceability stated honestly.** `complete_bead`'s gate is **advisory-strong** (the model still chooses to call it) — stronger than Markdown, weaker than CI. The single source of true enforcement remains `beadloom ci` in CI (principle 7). Don't overclaim.
- [ ] **G6 — Dogfood.** Use the scaffolded flow + the new process-tools on a real run (Beadloom itself or a fresh test repo): scaffold → `task_init` a small bead → `bead_context` → work → `complete_bead` REFUSES on a deliberately-red gate, PASSES when green. Capture friction in `BDL-UX-Issues.md`.
- [ ] **G7 — Docs.** Guide for the agentic-flow setup + the MCP process-tools + the honest boundary; CHANGELOG; ROADMAP status.

## Non-goals (out of scope)

- **Orchestration in MCP.** No sub-agent spawning / main-loop control via MCP — that's structurally impossible and stays in the harness (G4).
- **Replacing the harness or the `.claude/` flow** — this packages + hardens them, it doesn't rewrite the coordinator model.
- **MCP `prompts` if client support is uneven** — start tools-first; role-persona/playbook *prompts* (porting `.claude/commands/*`) are a later/optional slice (RFC decides), since MCP prompt support varies across clients in 2026.
- **Model tiering** (principle 10).
- **A hosted/SaaS flow** — local + CI only.

## Open architecture questions (→ resolved in the RFC)

1. **`beadloom setup-agentic-flow` (setup-* family) vs `beadloom init --agentic-flow` (a flag).** The user phrased it as `init --agentic-flow`; the setup-* family (`setup-rules`/`setup-mcp`/`setup-ai-techwriter`) is the more consistent home + reuses the generate+diff/config-check machinery. RFC picks one.
2. **Process-tool internals** — `task_init` shelling `bd create --graph <plan.json>` for the DAG; how `complete_bead` runs the gate (reuse `application/gate.run_ci_gate`?); what `bead_context`'s "active rules" source is.
3. **Tools-only vs tools+prompts** for v1 (MCP prompt maturity).
4. **config-check integration** — does the scaffolded `.claude/` flow get drift-checked by `config-check` like the other auto-regions?

## User stories

### US-1: Install the flow on a new repo in one command
**As** the maintainer starting a new service, **I want** one command to scaffold the agentic flow, **so that** I get the proven dev process without hand-copying `.claude/`.
**Acceptance:** `beadloom setup-agentic-flow` creates the agents + commands + CLAUDE.md regions; re-running is idempotent; `config-check` reports drift if they diverge.

### US-2: Deterministic, refusing process-tools from any MCP client
**As** an agent (in Claude Code or Cursor), **I want** `task_init`/`bead_context`/`complete_bead`/`checkpoint` as MCP tools, **so that** the flow's deterministic steps are real operations — and `complete_bead` REFUSES a red gate instead of me "deciding" the bead is done.
**Acceptance:** the four tools are callable via MCP; `complete_bead` returns FAIL + the failures when lint/sync-check/tests are red, PASS when green; `task_init` produces a valid 4-role bead-DAG.
