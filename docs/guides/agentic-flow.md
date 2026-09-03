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
- the **project layer** (BDL-061 S3): every flow artifact composes, and the last
  layer is the adopting repository's own — see the dedicated
  [Project Overlays guide](project-overlays.md) for adding rules, declaring a
  suppression and migrating a hand-edited file,
- the **pre-push Beadloom Gate** (BDL-052): blocks a push on a red `beadloom ci`
  (`--no-verify` is the escape hatch),
- the **trunk-based development model** the flow runs on (BDL-049),
- how `beadloom config-check` keeps the scaffolded flow honest,
- the four MCP **process-tools** (`task_init` / `bead_context` / `complete_bead` / `checkpoint`),
- the tool-agnostic angle (Claude Code + Cursor adapters; any MCP client via `beadloom setup-mcp`),
- the **honest boundary**: orchestration stays in the harness; CI is the true enforcement.

## The canonical flow

One work item flows through the same wave sequence regardless of tool or stack:

```
/task-init            scaffold the docs folder + a 4-role bead DAG
      → explore       step 0.5: derive the `## Axes` section, BEFORE the type is chosen
  → /coordinator      orchestrate the waves, gated by bead dependencies
      → dev           TDD implementation
      → test          tests + coverage
      → review        read-only quality gate
      → tech-writer   doc refresh
  → git push          local authoring (the primary path)
      → Beadloom Gate (pre-push hook) runs `beadloom ci`; blocks the push on red
  → PR to main        CI re-runs the Gate as a required check (the true enforcement)
```

**Five roles, four of them in the wave.** `explore` (BDL-068 S1.5) is launched by
`/task-init` at step 0.5 and creates no bead, so the bead DAG stays four-role: it
produces the input the type decision is made from, and the type decides which
document set is scaffolded. The step is mandatory for every type and it runs
before the type table is read, because the axis count is what says whether a work
item is a bug. `beadloom docs quality` reports a simplified-route work item that
carries no `## Axes` section (`routed-without-axes`) and one whose kept axes name
more nodes than that route can hold (`route-not-supported-by-the-axes`), so the
step is checked rather than trusted.

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
   `tests-locale` (the same suite under `C` and `en_US.ISO-8859-1`) ∥
   `site-build` (the VitePress build) run in parallel, then the
   [AI tech-writer](./ai-techwriter.md) job runs **only after all three are green**
   (`needs: [gate, tests, site-build]`) and commits its doc refresh **into the PR
   branch** — code + docs in one reviewable PR, no orphan doc-PRs.
5. **Merge when green** — a human merges once CI is green and any doc refresh has
   landed. No auto-merge; no direct push to `main`, so `main` stays always-green.

Protect `main` once per repo (idempotent — but read the sequencing note below
before re-running it):

```bash
beadloom setup-branch-protection --repo OWNER/NAME
```

This requires a PR to `main` with the consolidated `ci.yml`'s **nine check-runs
as required status checks** — `gate`, `tests (3.10)`, `tests (3.11)`,
`tests (3.12)`, `tests (3.13)`, `tests-locale (C)`,
`tests-locale (en_US.ISO-8859-1)`, `site-build`, `ai-techwriter` (BDL-050; the
two `tests-locale` legs are the environment dimension added in BDL-061.38 — the
same whole suite with the locale **varied, never pinned**). A tenth context, a
`tests-windows` platform dimension, was added in BDL-061.39 and withdrawn by the
owner in `beadloom-mr2l.64`: a Windows runner is billed at 2x and becomes the
pipeline's critical path (~16-28 runner-minutes per PR, roughly tripling
PR-to-merge latency) for a platform outside this project's audience. The job and
the context left together, because a required context whose check-run nothing
produces is a branch nobody can merge.

**Require only checks your pipeline can turn green.** The default set is applied
whole, and `strict: true` blocks a merge until every context in it passes, so
requiring a check-run that is red — or absent from your pipeline — makes the branch
unmergeable until you fix it or narrow the set with `--check`. In this repository
the two `tests-locale` contexts were knowingly red until bead `beadloom-mr2l.42`
turned them green — the delta between legs is the measurement, never any leg's
colour — so `main`'s live protection still carries the other seven while the
declared set names nine.

Strict trunk-based keeps
`enforce_admins: true` (even the owner integrates via a PR) with 0 required reviews,
so the solo maintainer self-merges but `main` is never bypassed (BDL-049). The
composed `.claude/CLAUDE.md` §6 (Git) and `.claude/commands/coordinator.md`
describe this same model, so a scaffolded repo gets the trunk-based flow by
default. **CI on the PR is the true enforcement** — the
agent's refresh and the deterministic gate are proposals/checks; the human merges.

## What the packaged flow is

The flow lives in a project's tool tree (`.claude/` for Claude Code, `.cursor/`
for Cursor), in two kinds of unit:

- **Role subagents** — `<tool>/agents/{dev,explore,review,tech-writer,test}.md`.
  The role protocols (TDD dev, axis-deriving explore, test, read-only review,
  doc-refresh tech-writer),
  launched as isolated subagents. As of **BDL-052** these are **composed**
  per-project from CORE + the repo's architecture + stack overlays (see the
  [role configurator](#the-role-configurator-bdl-052)) — they are no longer one
  fixed monolith.
- **Slash skills** — `.claude/commands/{coordinator,task-init,checkpoint,templates}.md`.
  `task-init` scaffolds a work item, `coordinator` orchestrates the waves,
  `checkpoint` saves progress, `templates` holds the doc templates.

Plus a `.claude/CLAUDE.md` entry point. Its body carries the critical rules; two
**auto-regions** carry the regenerated per-project facts — `project-info` (stack,
tests, linter, type checking, version) and `doc-language` (rendered from
`language:` in `flow.yml`). The project's name is substituted into the
`## 0.1 Project:` heading at scaffold time.

The effectiveness of this flow lives in the **exact wording** of those files,
refined over many epics. So Beadloom does **not** rewrite or summarize them.
Since BDL-061 S3 all three kinds — role agents, slash commands and `CLAUDE.md` —
are **composed** from the same versioned layers: a stack-neutral CORE, the
architecture and stack overlays `flow.yml` selects, and the adopting repo's own
project fragment. A **drift-guard** (`beadloom config-check`) compares each
on-disk file against that composition, so the scaffold ships the latest proven
flow and a project's additions are part of the expected result rather than
drift.

`CLAUDE.md` and the slash commands used to be byte-snapshots of Beadloom's own
live files. That is how a bead id and a false claim about this repository's
branch protection reached every adopter's `CLAUDE.md`, twice (BDL-UX #177):
enforcing *template equals our file* in one direction makes the distributed
artifact unable to differ from one project's local text. Nothing now writes back
into the shipped core, and Beadloom's own project-specific rules live in its
`.beadloom/flow/claude/CLAUDE.md` like everyone else's.

### What each role is held to

The role protocols are not five descriptions of the same job. Each carries duties the
others do not, BDL-061 S4 added three of them, and BDL-068 S1.5 added the fifth role.

| Role | Duties the shipped CORE states |
|------|--------------------------------|
| `explore` | Read-only, and it runs BEFORE the work item has a type — `/task-init` step 0.5, not a wave. One fixed deliverable: the `## Axes` section `beadloom impact <target> --section` renders, every site a path and a line, the `In scope` column left undecided because that half is the person's. No narrative, no recommendation, and the axes are derived from the source rather than read out of a bead comment or a previous plan. |
| `dev` | TDD (red → green → refactor); the `# beadloom:` annotation discipline that keeps the graph honest; architecture boundaries; cohesion-driven design. **BDD (S4):** acceptance criteria are Gherkin scenarios that RUN, written before the unit test and seen red first, each naming its bead and its node — or the work declares itself non-behavioural with a reason. |
| `test` | Coverage ≥ 80% on changed code, as a floor rather than a goal; edge cases; fixtures. **Mutation (S4):** the strength check on the scenarios — pure domain cores only, once per slice, never in pre-commit; a survivor is a finding and the fix is a stronger assertion. Beadloom ships no mutation runner, so the tool is the project's choice; the role reports the counters that tool wrote through `beadloom mutation`, which scores them against the declared target. |
| `review` | Read-only. Typing, error handling, security, testing, doc freshness through two sources rather than one. **BDD is not ceremony (S4):** reject a scenario that restates the implementation, one whose `Then` asserts nothing, one written after the code and never seen red, and a `non_behavioural` reason that restates the exclusion instead of explaining it. **The brief first (S6):** step 1 is `beadloom review-brief <bead>`, both doc-freshness sources are derived from the change rather than from the author's note, and the account is read only after the verdict is recorded. |
| `tech-writer` | Edits documentation only. Two staleness sources — `sync-check` and the dev's `API CHANGE:` notes — because a `reindex` can re-baseline hashes while the prose stays wrong. |
| **all five** | **The writing standard (S4).** It moved out of `tech-writer` into the shared `core:_writing` layer, because the roles that produce intent documents had no standard at all, and a team writing in Russian should be held to it in Russian. **The room a measurement was taken in (BDL-068 S3.2),** in the second shared layer `core:_rooms`: report a verdict in the words that say which room it was measured in, and state the clean room's blindness to a bead running beside you where the result is stated. Naming the room does not make the verdict stronger — it makes it answerable. |

All three of those duties now have a mechanism behind them, and the third one got its
second half last. The BDD duty is checked by the `scenario_coverage` rule
([BDD guide](bdd-scenarios.md)); the writing standard is checked by
`beadloom docs quality` ([document kinds](document-kinds.md)).

The mutation duty has two halves and shipped them two releases apart, which is worth
stating because the first half alone let a claimed check read like a performed one. The
SCOPE half (BDL-061 S4b) checks that a **declared** `mutation.targets` entry lies inside the
configured source paths, exists, and holds a file in an indexed language — the failure worth
catching is a target that runs zero mutants and reports a clean score. The SCORE half
(BDL-068 S3) is [`beadloom mutation`](../services/cli.md#beadloom-mutation): it holds the
counters a run wrote against that declared scope, reports a counter it did not find rather
than reading it as zero, and refuses a score over an empty population instead of printing
`100.0%`. The composed `test` role names the command, so the result is reported rather than
described.

**Beadloom still ships no mutation runner, and adopting this duty does not require one.**
Owning a runner would break tool-agnosticism, so the tool stays the project's choice and
the seam is a JSON object of counters read by name — `killed` and `survived` required,
`timeout`, `no_tests`, `skipped` and `suspicious` optional. A project that runs no mutation
tool at all is still told which of its declared targets is measured by nothing, which is a
report the scope half alone could not produce.

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
language: en                   # the language the flow's documents are written in
overlays:                      # declared stand-downs of a shipped core rule
  suppress:
    - rule: "Anti-patterns / Shell"
      reason: "the team runs on Windows; the -f idiom does not apply"
      until: "a windows stack overlay ships"
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

`language` is a BCP-47-ish tag validated for **shape** rather than against a
closed list — the set of languages a team writes in is not Beadloom's to
enumerate. It selects a `<name>.<lang>.md.txt` fragment in every layer, and a
localisation that has not shipped falls back to the default *and says so*
(BDL-UX #136).

`overlays.suppress` entries each need `rule`, `reason` and `until`; an entry
missing any of them is a configuration error. An unknown key under `overlays` is
rejected too, with the reminder that project *additions* are files under
`.beadloom/flow/` and never keys here. See the
[Project Overlays guide](project-overlays.md).

### Composition: CORE + overlays + the project layer

`composer.compose(kind, name, config=…, project_root=…)` assembles every flow
artifact deterministically, in a fixed order. `role_composer.compose_role(...)`
is the roles-shaped door onto it, so roles, slash commands and `CLAUDE.md` share
one implementation instead of three:

1. **CORE** — the universal, stack/tool-neutral fragment (the single source of
   truth).
2. the **SHARED** core fragments (`SHARED_ROLE_FRAGMENTS`, BDL-061 S4), composed
   as a labelled `core:<name>` layer. Today those are `_writing`, the writing
   standard, carried by every role instead of by `tech-writer` alone (the roles
   that produce intent documents had no standard at all); and `_rooms`
   (BDL-068 S3.2), the statement that a measurement is true of the room it was
   taken in, which reaches all five roles from one file rather than from five
   copies that drift the moment one is edited. Each is a layer and not a role,
   so `compose_role("_writing", …)` raises, and each is language-selectable like
   every other layer (`_writing.ru.md.txt` and `_rooms.ru.md.txt` ship).
3. one **ARCHITECTURE** overlay — `ddd` or `fsd` (peers): the methodology's
   layer/boundary rules + the `# beadloom:` annotation vocabulary. FSD is at
   **parity** with DDD (every role has both overlays).
4. one+ **STACK** overlays in **sorted** order: stack idioms + lint/type/test
   commands.
5. the **PROJECT** fragment from the adopting repository —
   `.beadloom/flow/roles/<role>.md`, `.beadloom/flow/commands/<cmd>.md`,
   `.beadloom/flow/claude/CLAUDE.md` or `.beadloom/flow/docs/<kind>.md`.

A fourth artifact kind, `docs`, composes the same way (BDL-061 S4b): the five
document skeletons `beadloom docs generate` writes moved out of
`doc_generator.py`'s string literals into `templates/docs/`, so an adopter can
extend the shape of their architecture documentation exactly as they extend a
role — and a section the project fragment appends becomes a **required** section
of that document kind by the same act. See
[Document kinds and the writing standard](document-kinds.md).

A missing per-role overlay fragment contributes nothing (overlays are additive
and never break an unrelated role). Because the stack overlays are sorted, the
same `(kind, name, config, project layer)` always yields **byte-identical**
output — the determinism the drift-guard relies on. A composed artifact is a
function of its inputs and of nothing else: not of the clock, not of ambient
state. That is the entire licence for `config-check` to compare against a
composition rather than against stored bytes.

**The core shrank because of layer 4.** Measured on the shipped artifact: the
core `CLAUDE.md` went from **440 lines to 371**, with each removed line mapped to
a replacement — the Quick Reference and Agent Checklist sections restated §0
command for command, and the Python anti-patterns and the `uv run pytest` /
`ruff` / `mypy` block moved into the Python stack overlay, where a TypeScript
adopter no longer meets them. Composing the shipped template today, a `ddd` +
`python` project gets **401** lines back and a project selecting neither keeps the
**371**, its critical rules naming no Python tooling.

### Per-tool adapters

`role_adapters.generate_adapters(config, project_root)` is the single output
writer: it composes each role once and writes a per-tool adapter set for every
configured tool, with each adapter body **exactly** `compose_role(...)`:

- **claude** → `.claude/agents/<role>.md` (the slash-command set in
  `.claude/commands/*` composes through the same `compose()` and is written by
  the scaffold, not here).
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
composes the slash commands and `CLAUDE.md`. A file Beadloom wrote and nobody
touched is recomposed; a hand-edited one is **skipped** and reported
(`Skipped .claude/commands/<name>.md (hand-edited; use --force)`); `--force`
overwrites regardless.

> **Write a `.beadloom/flow.yml` before you rely on the result.** Without one,
> the command composes the role adapters from the auto-detected stack while
> `config-check` expects the plain vendored role files. Measured on a fresh
> TypeScript project: `config-check` exits 1 with four errors immediately after a
> clean scaffold, and adding a `flow.yml` takes it to rc 0 (BDL-UX #187).

### Composed artifacts are Beadloom's; the project layer is yours

Once a `flow.yml` exists, the **composer owns** the composed bodies —
`.claude/agents/*`, `.cursor/agents/*`, `.claude/commands/*` and
`.claude/CLAUDE.md`. Do not hand-edit them: `config-check` compares each against
the freshly recomposed body and reports a hand edit, a stale CORE or a stale
overlay. Put your project's own text in `.beadloom/flow/` instead — the
[Project Overlays guide](project-overlays.md) covers adding it and migrating an
edit you already made.

```bash
beadloom config-check [--project DIR]         # exit 1 on blocking drift, 0 when clean
beadloom config-check --fix [--project DIR]   # recompose what Beadloom owns
```

`config-check --fix` recomposes every configured tool's adapter set from CORE +
overlays and re-runs the scaffold's **non-forcing** path for the commands and
`CLAUDE.md`, so a hand edit there survives it (BDL-UX #151). It does **not** yet
survive on a role adapter: `refresh_composed_adapters` rewrites those
unconditionally and the edit is lost, one line after the check said it would not
be rewritten (BDL-UX #186). Move the text into the project layer first.

An **invalid** `flow.yml` is itself reported as drift; an **absent** one is not
(a repo may never adopt the configurator — the composer drift-check is then a
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
(`beadloom ci` — incremental reindex → `lint --strict` → sync-check → docs audit →
docs-quality → doc-spaces → config-check → doctor) and **exits non-zero to block
the push** on red, printing
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

## Flow guards (BDL-061 S1)

The Gate above runs at push time. **Flow guards** run at edit time. A guard
answers one process question about one situation — "is this edit covered by a
claimed work item?", "is this happening off the protected trunk?" — and returns a
verdict whose exit code a harness acts on without parsing anything, so the flow's
rules stop being prose a model may ignore.

```bash
beadloom guard bead-claimed --context path=src/app.py
beadloom guard --liveness          # which guards are actually protecting something
```

Two guards ship: `bead-claimed` (an edit happens under a claimed work item) and
`working-branch` (work happens off the protected trunk). Both **skip with a
stated reason** when their evidence is unavailable — `bd` not installed, no
branch checked out — because a guard that silently does not apply is
indistinguishable from one that passed.

### Declaring guards in `.beadloom/flow.yml`

```yaml
guards:
  bead-claimed:
    strictness: { default: warn, epic: block, chore: off }
    exclusions:
      - path: "scripts/**"
        reason: "operational scripts are not bead-scoped"
        until: "BDL-0xx introduces a scripts node"
  working-branch:
    strictness: { default: warn }
    options: { trunk: main }
```

- **`strictness`** is resolved per work kind (`--context work_kind=epic`), falling
  back to `default` and then to the shipped `warn`. `off` switches the guard off.
  An absent `guards:` block is not an error — every registered guard runs at
  `warn` — so upgrading Beadloom adds warnings that name what they did not check,
  never a new red build.
- **`exclusions`** must carry both `reason` and `until`. One without either is a
  configuration error, because an unnamed, undated exclusion disables a gate
  permanently by accident. Patterns are POSIX globs in which `**` crosses
  directories and `*` does not, matched against the path *resolved* against the
  project root — so respelling a path cannot turn an exclusion into an opt-out.
- A `guards:` key naming a guard nobody registered is a configuration error too,
  not a no-op, so a typo cannot quietly switch a gate off.
- **A key Beadloom does not read is a configuration error as well** — a guard body
  carries `strictness` / `exclusions` / `options`, an exclusion carries `path` /
  `reason` / `until`, and nothing else. A dropped key is not harmless in both
  directions: `exclude:` for `exclusions:` leaves the guard over-guarding, while
  `option:` for `options:` drops the declared `trunk` and `working-branch` then
  compares against `main` — measured on a project whose trunk is `develop`, an
  edit made directly on `develop` came back `PASS` at exit 0. The verdict does
  print the trunk it used, but a `pass` at 0 is shown to nobody, so the typo is
  answered in the file where it was made.
- The `guards:` block is read by the guard evaluator. `tools` / `architecture` /
  `stack` / `quality` are read by the role configurator. The two readers share one
  file and nothing else.

### The binding, and what it does not cover

`beadloom setup-agentic-flow` writes `.claude/hooks/beadloom-guard.sh` — one
`exec beadloom guard "$1" --hook claude-code`, with no logic of its own — and
registers one `PreToolUse` entry per guard with the matcher
`Edit|Write|MultiEdit|NotebookEdit|Bash`.

`Bash` joined that list in BDL-068 S4. Before it, **a file written through the
shell — `sed -i`, a heredoc, `python3 - <<EOF` — fired no guard at all**, and
`--liveness` could not tell such a session apart from a compliant one: an edit no
guard was asked about leaves nothing behind to report (BDL-UX #170).

A shell command's write set is not decidable, so the binding says so rather than
claiming it. Beadloom reads the targets a declared set of write shapes names — a
redirection, `tee`, `sed -i`, the destination of `cp`/`mv`, `dd of=` — and treats
them as a **lower bound**: they are reported in the verdict's `not_covered` and
they never grant an exclusion, because `sed -i docs/a.md && python3 write_src.py`
names one write and performs two.

`beadloom guard --liveness` reports the binding's surface beside the firings: how
many of the write paths your role adapters grant are named by a registered
matcher, which are not, and which tools nothing here classifies. A guard healthy
on a matcher covering one write path out of three is a third of a guard, and the
firing rows alone cannot say so.

Giving Beadloom its own event vocabulary, so that the adapter forwards *what
happened* rather than *which guard to run*, is S3 work.

### Exit codes, and who is asking

| Code | Outcome | From a shell | Through a hook |
|---|---|---|---|
| `0` | `pass` / `skip` | — | the edit proceeds |
| `1` | `warn` | — | shown to the agent, the edit proceeds |
| `2` | `block` / `error` | — | the tool call is stopped |
| `3` | usage or configuration error | reported | never returned — the class exits `2` |

The harness stops a tool call on `2` and on nothing else, so `3` stopped nothing:
until **BDL-061.33** a `.beadloom/flow.yml` that would not parse left every bound
guard answering "could not tell" while every edit went through — fail-open on the
one file of this feature you edit by hand. `3` still exists, because a defect in
your declared configuration is genuinely not the same thing as a guard that
fired, and Click's own usage errors also exit `2`. It is now answered to the
caller it means something to: run `beadloom guard` yourself and a broken
`flow.yml` is a `3`; the same defect reached through `--hook` is a `2` and stops
the edit. The mapping is in the CLI rather than in the generated script, so a
second harness inherits it instead of re-implementing it.

## Waves, and what a reviewer is handed (BDL-061 S6)

Two decisions the coordinator used to make by hand are now made by the CLI, and both were
built around what is *not* checkable rather than around what is.

**`beadloom waves <bead>...` decides the wave shape from the graph.** A tracker knows which
beads block which. Only the architecture graph knows which code they occupy, so parallelism
follows from the code-level independence of the beads' declared node scopes, and each
serialised pair carries one named reason. The guarantee, in one sentence: for any two beads
placed in the same wave, no medium they share can carry one bead's in-progress state into the
other's result — and where a medium cannot give that guarantee, the wave says so and names the
one bead that measures the combined outcome. Code independence is decided from the graph. The
four media a wave shares regardless — one working tree, one pre-commit hook, one doc-freshness
baseline, one tracker id space — are measured as a **precondition before the wave runs**, and
the wave's conduct afterwards is checked by nothing here and cannot be.

**`beadloom review-brief <bead>` decides what the reviewer reads first.** It hands over the
assignment, the declared scope, the specification and the change, and withholds the bead's own
comments while reporting how many it withheld. `--release` prints them once a verdict is
recorded. It is enforced for what it can see and documented, not enforced, for two defeats it
cannot: a reviewer running `bd comments` itself, and a coordinator pasting a summary into the
launch prompt, which the `coordinator` skill now forbids by name.

Both are described in full, with their measurements and their stated limits, in the
[Parallel waves guide](parallel-waves.md).

## Scaffold contents + idempotency

`beadloom setup-agentic-flow` (in the `setup-*` family alongside
`setup-rules` / `setup-mcp` / `setup-ai-techwriter`) drops, idempotently:

- `<tool>/agents/{dev,explore,review,tech-writer,test}.md` — **composed** from CORE +
  overlays for each configured tool (see [the configurator](#the-role-configurator-bdl-052));
  `.cursor/agents/*` plus the Cursor orchestrator pointer when `cursor` is
  configured.
- `.claude/commands/{coordinator,task-init,checkpoint,templates}.md` — **composed**
  from the same four layers, with the project fragment at
  `.beadloom/flow/commands/<cmd>.md`.
- `.claude/hooks/beadloom-guard.sh` plus one `PreToolUse` entry per guard in
  `.claude/settings.json` — the [flow-guard](#flow-guards-bdl-061-s1) binding.
  Registration is a **merge**: existing hooks survive, re-running adds only what
  is missing, and a `settings.json` that cannot be parsed is reported and left
  untouched.
- `.claude/CLAUDE.md` — **composed** like the rest, with the project fragment at
  `.beadloom/flow/claude/CLAUDE.md`, then its `project-info` and `doc-language`
  auto-regions are regenerated for **this** project via the same
  `refresh_claude_md` machinery `setup-rules --refresh` uses. The version bullet
  in `project-info` still comes from Beadloom's own `__version__` rather than
  from the target project, so it is false for every adopter (BDL-UX #183).
- an ignore block appended once to the project's `.gitignore`, naming Beadloom's
  generated working set under `.beadloom/` — the same whole-set call
  `beadloom init` makes, repeated here for a repository initialised by an older
  release. Written once and never rewritten, so deleting a line is permanent.

**Idempotent.** Re-running recomposes what Beadloom wrote and re-refreshes the
auto-regions; a file that already matches is left alone. A hand-edited *command*
or `CLAUDE.md` is skipped and reported; `--force` overwrites it. Composed role
adapters are owned by the configurator — re-running recomposes them.
`--project DIR` targets a different repo root (default: current directory).

`config-check` (the AgentConfigAsCode freshness gate) keeps all of this honest —
it compares each composed artifact against its composition, classifies the result
against the flow manifest, and reports the project layer that is in effect. See
[Composed artifacts are Beadloom's](#composed-artifacts-are-beadlooms-the-project-layer-is-yours)
above and the [Project Overlays guide](project-overlays.md).

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

The **refusing completion gate**. It runs `beadloom ci` (reindex → lint → sync-check →
docs audit → docs-quality → doc-spaces → config-check → doctor, via
`application/gate.run_ci_gate`) and, by
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
- **Guards see the tool calls the matcher names, and nothing else.** A write that
  reaches the filesystem through `Bash` fires no guard, and no report
  distinguishes that from a compliant session. The surface is bounded by the
  harness binding, not by the guard — see
  [the binding](#the-binding-and-what-it-does-not-cover).
- **CI is the single source of true enforcement.** `beadloom ci` runs
  independently in CI (reindex → lint → sync-check → docs audit → docs-quality → doc-spaces → config-check → doctor) as a
  required check on `main`; that is the gate nothing can route around (no
  `--no-verify`).

## See also

- [CLI reference](../services/cli.md) — `setup-agentic-flow`, `config-check`, `ci`, `setup-mcp`, `setup-branch-protection`, `install-hooks`, `active-sync`.
- [Active Table component](../domains/application/components/active-table/DOC.md) — the shared ACTIVE.md bead-status table parser/updater + reconcile-from-`bd` core.
- [AI tech-writer guide](./ai-techwriter.md) — the PR-triggered doc-refresh loop on the trunk-based model.
- [MCP server](../services/mcp.md) — the full tool catalog (18 tools).
- [Onboarding domain](../domains/onboarding/README.md) — the scaffold + config-sync internals.
- [Project Overlays guide](./project-overlays.md) — the project layer, `overlays.suppress`, and migrating a hand-edited vendored file.
- [Flow Config SPEC](../domains/onboarding/features/flow-config/SPEC.md) — `.beadloom/flow.yml` + the `FlowConfig` loader/validator.
- [Flow Composer SPEC](../domains/onboarding/features/flow-composer/SPEC.md) — the four layers behind roles, slash commands and `CLAUDE.md`.
- [Flow Manifest SPEC](../domains/onboarding/features/flow-manifest/SPEC.md) — the five states that tell Beadloom's own output from a hand edit.
- [Config Check SPEC](../domains/onboarding/features/config-check/SPEC.md) — severities, the ownership boundary, and what is still not checked.
- [Flow Guards SPEC](../domains/application/features/flow-guards/SPEC.md) — the guard primitive: verdicts, strictness, exclusions, liveness, and the enforcement surface.
- [Guard Hooks component](../domains/onboarding/components/guard-hooks/DOC.md) — the emitted hook adapter and its registration.
- [Role Composer SPEC](../domains/onboarding/features/role-composer/SPEC.md) — CORE + architecture + stack overlay composition.
- [Role Adapters SPEC](../domains/onboarding/features/role-adapters/SPEC.md) — per-tool adapter generation + the drift-guard.
- [Parallel waves guide](./parallel-waves.md) — the wave guarantee, the four shared media and their plan-time checks, and reviewer isolation.
- [Wave Plan SPEC](../domains/application/features/wave-plan/SPEC.md) — the decision, the serialisation reasons and the override shape.
- [Review Brief SPEC](../domains/application/features/review-brief/SPEC.md) — what the brief carries and what it cannot enforce.
- [CI setup guide](./ci-setup.md) — `beadloom ci` as the enforcement gate.
