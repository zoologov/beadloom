# Agentic Dev Flow (packaged)

Beadloom's #1 value is a **solo multi-agent development flow**: Claude Code +
Beadloom + Beads + GitHub, run as waves of role subagents (dev → test → review →
tech-writer) gated by bead dependencies. That flow is the process that built
Beadloom itself. BDL-048 **packages** it so any repo can adopt it with one
command, and exposes its deterministic steps as MCP tools any MCP client can
call.

This guide covers:

- what the packaged flow is and how to scaffold it (`beadloom setup-agentic-flow`),
- the **trunk-based development model** the flow runs on (BDL-049),
- how `beadloom config-check` keeps the scaffolded flow honest (`--fix` restores it),
- the four MCP **process-tools** (`task_init` / `bead_context` / `complete_bead` / `checkpoint`),
- the tool-agnostic angle (any MCP client via `beadloom setup-mcp`),
- the **honest boundary**: orchestration stays in the harness; CI is the true enforcement.

## Trunk-based development (BDL-049 · BDL-050 consolidated CI)

The coordinator flow is **trunk-based**: `main` is the integration point and is
**branch-protected** (no direct push). Each epic/feature runs on a short-lived
branch and integrates via a single PR:

1. **Branch off main** — `git switch -c features/<ISSUE-KEY>`.
2. **Commit per wave** onto that branch (dev → test → review → tech-writer).
3. **Open ONE PR to `main`** per epic/feature (or shippable slice) — not one PR per
   commit.
4. **The PR triggers** the consolidated CI pipeline (`.github/workflows/ci.yml`,
   BDL-050): `gate` (the `beadloom ci` verdict) ∥ `tests` (the 3.10–3.13 matrix) ∥
   `site-build` (the VitePress build) run in parallel, then the
   [AI tech-writer](./ai-techwriter.md) job runs **only after all three are green**
   (`needs: [gate, tests, site-build]`) and commits its doc refresh **into the PR
   branch** — code + docs in one reviewable PR, no orphan doc-PRs.
5. **Merge when green** — a human merges once CI is green and any doc refresh has
   landed. No auto-merge; no direct push to `main`, so `main` stays always-green.

Protect `main` once per repo (idempotent; safe to re-run):

```bash
beadloom setup-branch-protection --repo OWNER/NAME
```

This requires a PR to `main` with the consolidated `ci.yml`'s **7 check-runs as
required status checks** — `gate`, `tests (3.10)`, `tests (3.11)`, `tests (3.12)`,
`tests (3.13)`, `site-build`, `ai-techwriter` (BDL-050). Strict trunk-based keeps
`enforce_admins: true` (even the owner integrates via a PR) with 0 required reviews,
so the solo maintainer self-merges but `main` is never bypassed (BDL-049). The
vendored `.claude/CLAUDE.md` §6 (Git) and
`.claude/commands/coordinator.md` describe this same model, so a scaffolded repo
gets the trunk-based flow by default. **CI on the PR is the true enforcement** — the
agent's refresh and the deterministic gate are proposals/checks; the human merges.

## What the packaged flow is

The flow lives in a project's `.claude/` tree, in two kinds of unit:

- **Role subagents** — `.claude/agents/{dev,test,review,tech-writer}.md`. The
  canonical role protocols (TDD dev, test, read-only review, doc-refresh
  tech-writer), launched as isolated subagents.
- **Slash skills** — `.claude/commands/{coordinator,task-init,checkpoint,templates}.md`.
  `task-init` scaffolds a work item, `coordinator` orchestrates the waves,
  `checkpoint` saves progress, `templates` holds the doc templates.

Plus a `.claude/CLAUDE.md` entry point whose **auto-regions** carry the
per-project facts (name / stack / version / commands).

The effectiveness of this flow lives in the **exact wording** of those files,
refined over many epics. So Beadloom does **not** rewrite or summarize them: it
**vendors them byte-identical** from its own live `.claude/` and templates only
the per-project facts in the CLAUDE.md auto-regions. A drift-guard test asserts
the vendored templates equal the live files byte-for-byte, so the scaffold always
ships the latest proven flow.

## `beadloom setup-agentic-flow`

One command scaffolds the flow into the current repo. It is in the `setup-*`
family alongside `setup-rules` / `setup-mcp` / `setup-ai-techwriter`.

```bash
beadloom setup-agentic-flow [--project DIR] [--force]
```

It drops, idempotently:

- `.claude/agents/{dev,test,review,tech-writer}.md` — vendored byte-identical.
- `.claude/commands/{coordinator,task-init,checkpoint,templates}.md` — vendored byte-identical.
- `.claude/CLAUDE.md` — the base file (only when absent, or with `--force`), then
  its `project-info` auto-region is regenerated for **this** project via the same
  `refresh_claude_md` machinery `setup-rules --refresh` uses. The scaffolded
  CLAUDE.md version comes from Beadloom's own `__version__` (BDL-UX #92).

**Idempotent.** Re-running re-drops the vendored files and re-refreshes the
auto-regions. A vendored file that already matches is left alone; a file you
hand-edited is **skipped** (reported as such) so your edits are never silently
clobbered. `--force` overwrites hand-edited flow files. User prose outside the
CLAUDE.md auto-regions is never touched.

`--project DIR` targets a different repo root (default: current directory).

## Keeping it honest: `beadloom config-check`

`config-check` is the AgentConfigAsCode freshness gate. As of BDL-048 it also
**drift-checks the scaffolded agentic-flow files**: when a repo has the flow
scaffolded, each vendored `agents/*` + `commands/*` file is byte-compared against
the shipped template, and the CLAUDE.md auto-regions are checked as before.

```bash
beadloom config-check [--project DIR]         # exit 1 on drift, 0 when clean
beadloom config-check --fix [--project DIR]   # restore drifted files, then re-check
```

`--fix` re-drops the vendored flow files (via `refresh_agentic_flow_files`) and
regenerates the CLAUDE.md auto-regions, then re-checks. The fix is gated on the
flow already being scaffolded — `config-check --fix` never forces the flow onto a
repo that did not adopt it.

## The four MCP process-tools

The flow's deterministic steps are also exposed as **action tools** on Beadloom's
MCP server (`services/mcp_server.py`), next to the existing read/write tools — the
catalog is now **18 tools** (was 14). These are single deterministic operations
that reuse existing substrate code; they do **not** orchestrate or spawn
subagents.

The three bead-touching tools (`task_init`, `complete_bead`, `checkpoint`) drive
the `bd` (beads) CLI through a thin, mockable seam (`services/bd_seam.py`,
`run_bd`). If `bd` is not installed they return a clear error (the flow already
requires `bd`).

### `task_init(type, key)`

Scaffolds a work item: creates `.claude/development/docs/features/<key>/` with the
per-type doc skeletons (PRD/RFC/CONTEXT/PLAN/ACTIVE for `epic`/`feature`;
BRIEF/ACTIVE for `bug`/`task`/`chore`) **and** a valid 4-role bead DAG
(dev → test → review → tech-writer, wired with the standard dependencies) via
`bd`. Returns the created bead ids + doc paths.

### `bead_context(bead)`

Returns **one** structured payload for a bead: graph context (`ctx`) + impact
analysis (`why`) + a CONTEXT.md/ACTIVE.md excerpt (when present) + the **active
architecture rules** for the bead's area. It resolves the bead's graph ref from a
`ref:` (or `area:`) token in the bead's design/description via `bd show`.
Read-only and deterministic; reuses `context_oracle` (ctx/why) and
`graph/rule_engine` (active rules).

### `complete_bead(bead, run_tests=true)`

The **refusing completion gate**. It runs `beadloom ci` (reindex → lint →
sync-check → config-check → doctor, via `application/gate.run_ci_gate`) and, by
default, the test suite. Then:

- **On PASS** it closes the bead (`bd close --suggest-next`) and returns the
  next-ready output.
- **On FAIL** it does **NOT** close the bead — it returns the structured findings
  so the agent must fix them first.

Set `run_tests=false` for a fast gate-only check (skips the suite). This tool is
**advisory-strong**, not the true enforcement point — see the honest boundary
below.

### `checkpoint(bead, text)`

Records a checkpoint: adds `text` as a bead comment (`bd comments add`, preserving
history) and, best-effort, appends a timestamped progress note to the bead's
ACTIVE.md (skipped cleanly if the file cannot be located). Deterministic; no
orchestration.

## Tool-agnostic via MCP

The process-tools are plain MCP tools, so any MCP client — Claude Code, Cursor,
Continue, Windsurf — gets the same deterministic operations over the Beadloom
substrate. Wire them up once:

```bash
beadloom setup-mcp --tool {claude-code,cursor,windsurf}
```

This is the "one context for everyone" angle: the `.claude/` scaffold delivers the
Claude-Code-native personas + coordinator, while the MCP tools deliver the
tool-agnostic substrate any client can call.

## The honest boundary

This is stated deliberately, not glossed over:

- **Orchestration stays in the harness.** MCP serves *tools*, not orchestration —
  it cannot spawn subagents or run the main loop. The coordinator and the
  `Agent`-spawn waves remain Claude-Code-native/harness concerns (scaffolded by
  `setup-agentic-flow`). The MCP process-tools are the deterministic substrate the
  flow *calls*, not a replacement for the harness.
- **`complete_bead` is advisory-strong, not the source of truth.** The model still
  chooses to call it. It is stronger than Markdown instructions (it actually
  refuses a red gate) but weaker than CI.
- **CI is the single source of true enforcement.** `beadloom ci` runs
  independently in CI (lint / sync-check / config-check / doctor); that is the gate
  nothing can route around.

## See also

- [CLI reference](../services/cli.md) — `setup-agentic-flow`, `config-check`, `ci`, `setup-mcp`, `setup-branch-protection`.
- [AI tech-writer guide](./ai-techwriter.md) — the PR-triggered doc-refresh loop on the trunk-based model.
- [MCP server](../services/mcp.md) — the full tool catalog (18 tools).
- [Onboarding domain](../domains/onboarding/README.md) — the scaffold + config-sync internals.
- [CI setup guide](./ci-setup.md) — `beadloom ci` as the enforcement gate.
