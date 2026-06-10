# PLAN: BDL-048 — Agentic-flow packaging

> **Status:** Approved
> **Created:** 2026-06-10
> **PRD/RFC/CONTEXT:** ./PRD.md · ./RFC.md · ./CONTEXT.md

---

## Beads (described — NOT created until this PLAN is Approved)

Parent: `BDL-048` (epic) — Agentic-flow packaging.

| Bead | Role | Title | Depends on |
|------|------|-------|------------|
| .1 | dev | **setup-agentic-flow scaffold** — new `onboarding/agentic_flow_setup.py` + `onboarding/templates/agentic_flow/` (vendored `.claude/agents/{dev,test,review,tech-writer}.md` + `commands/{coordinator,task-init,checkpoint,templates}.md`, byte-identical) + a **drift-guard test** (template == live `.claude/`); generates CLAUDE.md auto-regions via `config_sync`; idempotent; `setup-agentic-flow` CLI command (+ optional `init --agentic-flow` alias). | — |
| .2 | dev | **config-check integration** — extend `config_sync.py` so `beadloom config-check` drift-checks the scaffolded agentic-flow files (vendored byte-match + CLAUDE.md regions). | .1 |
| .3 | dev | **MCP process-tools** — add `task_init` / `bead_context` / `complete_bead` / `checkpoint` to `services/mcp_server.py` (`mcp.Tool` + `call_tool` dispatch), reusing `gate.run_ci_gate`, `context_oracle`, `rule_engine`, `/templates`; thin **mockable `bd` seam**; `complete_bead` REFUSES on red gate. | — |
| .4 | test | pytest for .1–.3 (scaffold idempotency + drift-guard; config-check drift; the 4 MCP tools with `bd`+gate mocked, incl. complete_bead red→FAIL / green→PASS). Coverage ≥ 80% changed. | .1, .2, .3 |
| .5 | review | quality/architecture/honesty review (read-only); verify flow 1:1, boundary honesty (G4/G5), no overclaim. | .4 |
| .6 | dogfood | scaffold on a fresh temp dir + drive the process-tools end-to-end: `task_init` a small bead → `bead_context` → `complete_bead` REFUSES a deliberately-red gate, PASSES when green. Capture friction in `BDL-UX-Issues.md`. | .5 |
| .7 | tech-writer | guide (agentic-flow setup + MCP process-tools + honest boundary) + CHANGELOG + ROADMAP status. | .6 |

## Dependencies / DAG

```
.1 ─┬─> .2 ─┐
    │       ├─> .4(test) ─> .5(review) ─> .6(dogfood) ─> .7(tech-writer)
.3 ─┴───────┘
```

## Waves

- **W1 (parallel):** `.1` (scaffold + vendor + drift-guard) ∥ `.3` (MCP process-tools + bd seam) — disjoint files (`onboarding/` vs `services/mcp_server.py`).
- **W2:** `.2` (config-check, ← .1).
- **W3:** `.4` test (← .1, .2, .3).
- **W4:** `.5` review (← .4).
- **W5:** `.6` dogfood (← .5).
- **W6:** `.7` tech-writer (← .6).

Commit per wave; Beadloom stays green on its own `beadloom ci` + pytest after each.

## Acceptance (maps to goals)

- **G1** ← .1 (+ .2): one-command scaffold, flow 1:1 (drift-guard), idempotent, config-check-aware.
- **G2** ← .3: the 4 process-tools, `complete_bead` refuses red.
- **G3** ← .3 (MCP) + .6 (verified callable).
- **G4/G5** ← .1/.3 honest framing + .5 review.
- **G6** ← .6 dogfood.
- **G7** ← .7.
