# Agentic Dev Flow (packaged)

Beadloom's #1 value is a **solo multi-agent development flow**: Claude Code +
Beadloom + Beads + GitHub, run as waves of role subagents (dev → test → review →
tech-writer) gated by bead dependencies. That flow is the process that built
Beadloom itself. BDL-048 **packages** it so any repo can adopt it with one
command, and exposes its deterministic steps as MCP tools any MCP client can
call.

This guide covers:

- the **canonical flow**: `task-init → coordinator → dev/test/review/tech-writer → push → Beadloom Gate`,
- what the packaged flow is and how to scaffold it (`beadloom setup-agentic-flow`),
- the **role configurator** (BDL-052): `.beadloom/flow.yml` + the
  `--tool`/`--stack`/`--architecture` flags, `ddd` vs `fsd`, the CORE + overlay
  set composed into per-tool adapters, the drift-guard, and "roles are
  composer-owned",
- the **pre-push Beadloom Gate** (BDL-052): blocks a push on a red `beadloom ci`
  (`--no-verify` is the escape hatch),
- the **trunk-based development model** the flow runs on (BDL-049),
- how `beadloom config-check` keeps the scaffolded flow honest (`--fix` restores it),
- the four MCP **process-tools** (`task_init` / `bead_context` / `complete_bead` / `checkpoint`),
- the tool-agnostic angle (Claude Code + Cursor adapters; any MCP client via `beadloom setup-mcp`),
- the **honest boundary**: orchestration stays in the harness; CI is the true enforcement.

## The canonical flow

One work item flows through the same wave sequence regardless of tool or stack:

```
/task-init            scaffold the docs folder + a 4-role bead DAG
  → /coordinator      orchestrate the waves, gated by bead dependencies
      → dev           TDD implementation
      → test          tests + coverage
      → review        read-only quality gate
      → tech-writer   doc refresh
  → git push          local authoring (the primary path)
      → Beadloom Gate (pre-push hook) runs `beadloom ci`; blocks the push on red
  → PR to main        CI re-runs the Gate as a required check (the true enforcement)
```

The flow is **local-primary, CI-fallback**: the pre-push Gate catches drift on
the author's machine before a push leaves it, while CI re-runs the same
`beadloom ci` on the PR as the authoritative, un-routable enforcement (see the
[honest boundary](#the-honest-boundary)). The roles, the coordinator, and the
Gate are all generated from one canonical source per the
[role configurator](#the-role-configurator-bdl-052) below.

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

The flow lives in a project's tool tree (`.claude/` for Claude Code, `.cursor/`
for Cursor), in two kinds of unit:

- **Role subagents** — `<tool>/agents/{dev,test,review,tech-writer}.md`. The
  role protocols (TDD dev, test, read-only review, doc-refresh tech-writer),
  launched as isolated subagents. As of **BDL-052** these are **composed**
  per-project from CORE + the repo's architecture + stack overlays (see the
  [role configurator](#the-role-configurator-bdl-052)) — they are no longer one
  fixed monolith.
- **Slash skills** — `.claude/commands/{coordinator,task-init,checkpoint,templates}.md`.
  `task-init` scaffolds a work item, `coordinator` orchestrates the waves,
  `checkpoint` saves progress, `templates` holds the doc templates. The
  slash-command set is **vendored byte-identical** (the configurator owns the
  role *agents*, not the commands).

Plus a `.claude/CLAUDE.md` entry point whose **auto-regions** carry the
per-project facts (name / stack / version / commands).

The effectiveness of this flow lives in the **exact wording** of those files,
refined over many epics. So Beadloom does **not** rewrite or summarize them. For
the slash commands it **vendors them byte-identical** from its own live
`.claude/` and templates only the per-project facts in the CLAUDE.md
auto-regions; for the role agents it composes them deterministically from
versioned CORE + overlay fragments. In both cases a **drift-guard** asserts the
on-disk file equals the recomputed source byte-for-byte, so the scaffold always
ships the latest proven flow.

## The role configurator (BDL-052)

The flow is no longer hardcoded to Python + Claude Code. A repo declares its
**tools**, **architecture methodology**, **stack/frameworks**, and **quality
bars**, and Beadloom composes the matching role files for each tool.

### `.beadloom/flow.yml`

```yaml
tools: [claude, cursor]        # which IDE adapter sets to generate
architecture: [ddd]            # exactly one methodology: ddd | fsd
stack: [python, fastapi]       # one+ stack/framework overlays
quality: [clean-code, tdd]     # quality bars (informational)
```

`flow_config.py` loads + validates this into an immutable `FlowConfig`.
Validation is strict and agent-actionable: an unknown tool / architecture /
stack, an architecture that is not **exactly one** methodology, or an empty
`tools`/`stack` raises a `FlowConfigError` naming the offending value and the
allowed set (the `config-check` signal). For Beadloom itself the config is
`tools: [claude]`, `architecture: [ddd]`, `stack: [python]`.

Supported values: tools `claude` / `cursor`; architecture `ddd` / `fsd`
(peers — pick one); stack `python` / `fastapi` / `javascript` / `typescript` /
`vuejs`.

### Composition: CORE + overlays

`role_composer.compose_role(role, architecture=…, stack=…)` assembles a role
file deterministically, in a fixed order:

1. **CORE** — the universal, stack/tool-neutral role protocol (the single source
   of truth).
2. one **ARCHITECTURE** overlay — `ddd` or `fsd` (peers): the methodology's
   layer/boundary rules + the `# beadloom:` annotation vocabulary. FSD is at
   **parity** with DDD (every role has both overlays).
3. one+ **STACK** overlays in **sorted** order: stack idioms + lint/type/test
   commands.

A missing per-role overlay fragment contributes nothing (overlays are additive
and never break an unrelated role). Because the stack overlays are sorted, the
same `(role, architecture, stack)` always yields **byte-identical** output — the
determinism the drift-guard relies on.

### Per-tool adapters

`role_adapters.generate_adapters(config, project_root)` is the single output
writer: it composes each role once and writes a per-tool adapter set for every
configured tool, with each adapter body **exactly** `compose_role(...)`:

- **claude** → `.claude/agents/<role>.md` (the slash-command set in
  `.claude/commands/*` is vendored separately and is not regenerated here).
- **cursor** → `.cursor/agents/<role>.md` (same composed body) plus a thin
  `.cursor/rules/beadloom-flow.md` orchestrator pointer — the
  coordinator-as-Cursor-mode entry point, so Cursor runs the same flow at parity
  with Claude Code.

### `beadloom setup-agentic-flow` (configurator front-end)

```bash
beadloom setup-agentic-flow [--project DIR] [--force] \
    [--tool claude|cursor]...        # repeatable; default: flow.yml or claude
    [--architecture ddd|fsd]         # default: flow.yml or ddd
    [--stack python,fastapi,...]     # default: flow.yml or auto-detected
```

Selection follows **flag → flow.yml → default** precedence: an explicit flag
overrides the corresponding `flow.yml` field; fields neither flagged nor present
fall back to the defaults (`claude` / `ddd` / a stack auto-detected from the
repo's source-file extensions). It echoes the resolved
`architecture / stack / tools`, writes every configured tool's adapter set, then
drops the vendored slash commands + the per-project CLAUDE.md.

### Roles are composer-owned

Once a `flow.yml` exists, the **composer owns** `.claude/agents/*` and
`.cursor/agents/*`. Do not hand-edit a role adapter: `config-check` byte-compares
every existing `<tool>/agents/<role>.md` against the freshly recomposed body and
flags a hand-edit, a stale CORE, or a stale overlay as drift.

```bash
beadloom config-check [--project DIR]         # exit 1 on drift, 0 when clean
beadloom config-check --fix [--project DIR]   # recompose drifted adapters + restore
```

`config-check --fix` recomposes every configured tool's adapter set from CORE +
overlays (and re-drops the vendored commands + CLAUDE.md auto-regions). An
**invalid** `flow.yml` is itself reported as drift; an **absent** one is not (a
repo may never adopt the configurator — the composer drift-check is then a
no-op).

> **Known limitation — orphaned adapters.** The composed-adapter drift-check
> iterates only over the tools named in `flow.yml`. If you narrow `flow.yml` to a
> subset (e.g. drop `cursor`) after a previously-scaffolded `cursor` adapter set
> was written, those now-orphaned `.cursor/agents/*` files are **left
> un-drift-guarded** — they neither fail the check nor get recomposed. A
> follow-up bead tracks adding an orphaned-adapter lint; until then, remove a
> dropped tool's adapter directory by hand.

## The pre-push Beadloom Gate (BDL-052)

`beadloom install-hooks --pre-push` installs the **Beadloom Gate** — the
authoritative *blocking* enforcement of the hard invariant *"no code in `main`
without current docs."* On every `git push` it runs the full Gate
(`beadloom ci` — incremental reindex → `lint --strict` → sync-check →
config-check → doctor) and **exits non-zero to block the push** on red, printing
an actionable message that points at the tech-writer / `/coordinator` to fix the
drift, then re-push.

- **`--no-verify` is the documented (discouraged) escape hatch** — `git push
  --no-verify` skips the hook.
- **Fail-safe:** in any repo without `beadloom` on `PATH` the hook is a safe
  no-op and never blocks.
- The full Gate lives in **pre-push** (not on every commit) because pushes are
  less frequent than commits; the lighter pre-commit hook stays the warn/block
  `sync-check` + ACTIVE/tracker coherence step.

The pre-push Gate is the **local** half of local-primary / CI-fallback: it is the
same `beadloom ci` that runs on the PR as a required check, so a clean push is
almost always a clean PR. See the [CLI reference](../services/cli.md#beadloom-install-hooks)
for both hooks.

## Scaffold contents + idempotency

`beadloom setup-agentic-flow` (in the `setup-*` family alongside
`setup-rules` / `setup-mcp` / `setup-ai-techwriter`) drops, idempotently:

- `<tool>/agents/{dev,test,review,tech-writer}.md` — **composed** from CORE +
  overlays for each configured tool (see [the configurator](#the-role-configurator-bdl-052));
  `.cursor/agents/*` plus the Cursor orchestrator pointer when `cursor` is
  configured.
- `.claude/commands/{coordinator,task-init,checkpoint,templates}.md` — vendored
  byte-identical.
- `.claude/CLAUDE.md` — the base file (only when absent, or with `--force`), then
  its `project-info` auto-region is regenerated for **this** project via the same
  `refresh_claude_md` machinery `setup-rules --refresh` uses. The scaffolded
  CLAUDE.md version comes from Beadloom's own `__version__` (BDL-UX #92).

**Idempotent.** Re-running re-drops the composed adapters + vendored commands and
re-refreshes the auto-regions; a file that already matches is left alone. A
hand-edited *command* is skipped (reported as such); `--force` overwrites it.
Composed role adapters are owned by the configurator — re-running recomposes
them. User prose outside the CLAUDE.md auto-regions is never touched.
`--project DIR` targets a different repo root (default: current directory).

`config-check` (the AgentConfigAsCode freshness gate) keeps all of this honest —
it byte-checks the composed adapters, the vendored commands, and the CLAUDE.md
auto-regions; `config-check --fix` restores them. See
[Roles are composer-owned](#roles-are-composer-owned) above.

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

## ACTIVE.md stays honest by construction (BDL-053)

Each epic's `ACTIVE.md` carries a **bead-status table** (`| Bead | Role | Status
| … |`) the coordinator reads to know where the wave stands. Historically the
coordinator hand-edited those Status cells, which drifted from `bd` (the source
of truth) whenever a row was missed. BDL-053 makes the table **correct by
construction** instead of by discipline:

- **`beadloom active-sync`** reconciles every epic's bead-status table FROM `bd`
  (rewrites each Status cell to match the bead's `bd` status; a richer
  coordinator note is preserved when its state agrees) and re-exports the tracked
  `.beads/issues.jsonl`. See the
  [CLI reference](../services/cli.md#beadloom-active-sync) for the
  `--epic`/`--check`/`--json`/`--no-export` flags.
- **The pre-commit hook runs it as a guarded auto-fix step.** After the lint /
  mypy / sync-check steps, the hook calls `active-sync` and restages the touched
  `features/**/ACTIVE.md` + `.beads/issues.jsonl`, so the committed table matches
  `bd` on every commit — the coordinator no longer maintains rows by hand. The
  step **never blocks** the commit and runs only when both `bd` and `beadloom`
  are installed.
- **Safe no-op for every adopter.** With no `ACTIVE.md` table, no `bd`, or an
  untracked jsonl, `active-sync` (and the hook step) exits 0 and changes nothing —
  so a repo that has not adopted the flow is never affected; it works
  out-of-the-box.

The reconcile core (`application/active_table.py`) is the **same** tolerant,
fail-safe parser/updater the `checkpoint` / `complete_bead` MCP process-tools use
to flip a single row — so single-row updates and full reconcile share one format
(the `active-table` [component](../domains/application/components/active-table/DOC.md)).

## Tool-agnostic: native adapters + MCP

Tool-agnosticism has two layers:

- **Native role adapters** for the first-class tools. The
  [configurator](#the-role-configurator-bdl-052) generates `.claude/agents/*`
  (Claude Code) and `.cursor/agents/*` + `.cursor/rules/beadloom-flow.md`
  (Cursor) from the **same** composed bodies, so Cursor runs the same waves at
  parity with Claude Code.
- **MCP process-tools** for everything else. The process-tools are plain MCP
  tools, so any MCP client — Claude Code, Cursor, Continue, Windsurf — gets the
  same deterministic operations over the Beadloom substrate. This is the
  **inline floor**: on a tool without a native adapter set, an agent can still
  follow the role protocols inline and call the deterministic process-tools.

```bash
beadloom setup-mcp --tool {claude-code,cursor,windsurf}
```

This is the "one context for everyone" angle: the native scaffolds deliver the
Claude-Code / Cursor personas + coordinator at parity, while the MCP tools
deliver the tool-agnostic substrate any client can call.

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
- **The pre-push Gate is local-primary, not the final word.** The
  [Beadloom Gate hook](#the-pre-push-beadloom-gate-bdl-052) blocks a red push on
  the author's machine — strong, but `git push --no-verify` can skip it, so it is
  a fast local catch, not the un-routable gate.
- **CI is the single source of true enforcement.** `beadloom ci` runs
  independently in CI (reindex → lint → sync-check → config-check → doctor) as a
  required check on `main`; that is the gate nothing can route around (no
  `--no-verify`).

## See also

- [CLI reference](../services/cli.md) — `setup-agentic-flow`, `config-check`, `ci`, `setup-mcp`, `setup-branch-protection`, `install-hooks`, `active-sync`.
- [Active Table component](../domains/application/components/active-table/DOC.md) — the shared ACTIVE.md bead-status table parser/updater + reconcile-from-`bd` core.
- [AI tech-writer guide](./ai-techwriter.md) — the PR-triggered doc-refresh loop on the trunk-based model.
- [MCP server](../services/mcp.md) — the full tool catalog (18 tools).
- [Onboarding domain](../domains/onboarding/README.md) — the scaffold + config-sync internals.
- [Flow Config SPEC](../domains/onboarding/features/flow-config/SPEC.md) — `.beadloom/flow.yml` + the `FlowConfig` loader/validator.
- [Role Composer SPEC](../domains/onboarding/features/role-composer/SPEC.md) — CORE + architecture + stack overlay composition.
- [Role Adapters SPEC](../domains/onboarding/features/role-adapters/SPEC.md) — per-tool adapter generation + the drift-guard.
- [CI setup guide](./ci-setup.md) — `beadloom ci` as the enforcement gate.
