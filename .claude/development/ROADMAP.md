# Beadloom Roadmap

> **Current version: 7.0.0** (PyPI, published 2026-09-29).
>
> Rewritten 2026-10-05 against the tracker, brought up to date 2026-10-07. This file answers one question: what to do next,
> and why that and not something else. It holds open work only. What shipped is in the GitHub
> releases and in `CHANGELOG.md`; the previous revision of this file, with its records of why,
> is `archive/ROADMAP-until-2026-10-05.md`. Open defects are in `BDL-UX-Issues.md`.
>
> A bead's state is checked with `bd show <id>`, not read from here.

---

## Vision and the rule that ranks this list

Beadloom is an honest, effective tool. Market reach and outside adoption are not goals. Two uses
rank everything:

- **Solo multi-agent flow** — Claude Code + Beadloom + Beads + GitHub. Building large projects
  alone with an AI fleet.
- **A team of solos** — each member runs that flow on their own service. Its cross-repository
  half, federation, is deferred until a need for it appears (owner, 2026-09-29).

Every P0 and P1 item must serve one of them. Items serving only adoption or market are demoted
to *Off-north-star*.

**Sequencing principles:** one end-to-end thread at a time, made honest before the next · honest
is not complete, and dogfood is acceptance · a published lie is worse than a missing feature ·
intent-vs-reality is the moat, context bundles are commoditising · single-repo honesty is a
prerequisite of federation · CI is the only true enforcement point · top-tier models, no tiering
by role.

**The owner's next step outside this list** is outside validation: Beadloom on another project,
then a team on their own services. Its state is the owner's to record.

---

## In progress

### BDL-078 — the viewer looks finished, and five defects are fixed

Epic `beadloom-btkd`, branch `features/BDL-078`, work item
`.claude/development/docs/features/BDL-078/`. Done on the branch: the five defects, the activity
metric (changed lines, relative levels, boxes among boxes, a shallow history named), and the
viewer — one line weight, the overview's own routing inside the project frame, whole arrowheads
at every zoom, small nodes as boxes with their titles, levels that open by readability, one count
per node and per line, a click on a box framing it whole, layer colours, gesture cost back to
BDL-077's. The owner looked twice (2026-10-06, 2026-10-07: «все круто!»). Left: rounded corners on
boxes, then the test, review and docs beads, the PR, merge on green CI, and a release.

BDL-076 and BDL-077 (the viewer and its edges) are on `main` and in no release yet. They ship
with BDL-078 in the next one.

---

## What to do next, in order

Items 4 to 13 keep the owner's order of 2026-09-29. Items 1 to 3 were placed first by the owner
on 2026-10-05 and 2026-10-07, in this order: FSD, then the rules and the card populations.

### 1. `beadloom-be6e` — the portal is a service, and it serves a Feature-Sliced frontend (P1, not started)

**Needs `/task-init`.** Owner rulings of 2026-10-05 and 2026-10-06, in the bead:

- `vitepress-site` is a **service** of the product, like `tui` — own runtime, build, dependencies,
  tests and layer rule, one product version covering all of them; the data file is a declared
  contract (`beadloom` produces, the portal consumes). What rests on `kind: site` is enumerated
  first, and whether the kind survives is decided then.
- The viewer draws exactly one layer rule, the first by name. This repository declares two, so
  its twenty site slices are grey, unfiltered and never red, while `lint` still judges them. A
  service carries its own layer rule, which is the natural form of "draw every layer rule".
- **Decompose by cohesion.** Every BDL-078 viewer bead was serialised by `beadloom waves` because
  all of them change one node, `site-graph-viewer`. Split the FSD side into slices that are nodes
  (the overview router, the levels model, heads and bundles, the selection walk, the card), and
  make the roles say so for an FSD project — the `fsd` overlay and the explore/dev protocols
  state the cohesion rule as the DDD overlay states it for Python packages.
- `init` has no FSD preset and writes no layer rule; the `fsd` agent overlay maps layers to
  domains, the mapping this repository rejected; the public-API rule of a slice is checked
  nowhere. No adopter fixture is FSD.
- The portal's Source link is a permalink to the built commit; a local build from an unpushed
  commit links to a 404 on every node (BDL-UX #307).

**Why first:** without it the viewer is weak for a frontend team, and a team of solos has them.

### 2. `beadloom-j4gi` — the rules leave the graph folder and are decomposed (P1, not started)

**Needs `/task-init`.** Owner, 2026-10-07: `.beadloom/_graph/rules.yml` is 860 lines in the
graph's folder — 19 rules, ~330 lines of dated commentary, ~190 lines of baselines. The approved
structure: `.beadloom/rules/` beside `_graph/`, one file per rule family (structure, layers,
imports, coverage, tests); the loader reads `rules.yml` or `rules/*.yml`, `init` writes the split
layout, `config-check` reports a project with both; baselines (exempt file lists) in
`rules/baselines/<rule>.yml`; the dated rationale leaves YAML for the rule family's document
under `docs/`, where `sync-check` and the audit can judge it — the first instance of rationale
bound to what it is about so that it can go stale. Explore enumerates every reader first.

### 3. `beadloom-pre3` — a card names the population it reports over (P2, not started)

`Rule findings: none` is indistinguishable from "lint never ran" (#305); a box's `Debt 0` is the
box's own score while its activity rolls up from its parts (#306); the 36 findings bound to no
node are shown nowhere. The card names the population, a box shows debt own and inside, and
project-level findings get a home on the project box's card and the dashboard.

### 4. `beadloom-jwfc` — the pre-push Gate crashes on a full pipe and reports it as stale docs (P0, BDL-UX #226)

The only open P0. Under `git push` the Gate's stdout is a non-blocking pipe, one large write
raises `BlockingIOError`, and the hook then says the docs are stale. Each occurrence teaches
`--no-verify` for a reason that is false. **Done when** the report survives a full pipe and the
hook tells a Gate that crashed from a Gate that failed.

### 5. The adopter's first commands (five P1 bugs)

Each sits in a command an outside user runs first.

- `beadloom-l22o` (#220): `init --bootstrap` ends in a traceback on a graph file that does not
  parse.
- `beadloom-gv0z` (#217): domains an earlier `init --mode import` left are parented by no later
  run.
- `beadloom-6i5q` (#218): `init` holds three hand-written step sequences. Needs `/task-init` and
  an RFC before code.
- `beadloom-f7kb` (#225): `impact` under-reports on `src/<package>` beside Python outside `src/`.
- `beadloom-is2z` (#291): the debt report reads `rules.yml` from paths the product never writes,
  so its rule-violation count is zero on every standard project.

### 6. `beadloom-tsqz` — `scope-check` never runs in CI (P1, #300)

A pull request is checked out on a detached HEAD, no branch names a work item, and the leg skips.
**Done when** the leg judges a pull request whatever its branch is called.

### 7. Three lessons of BDL-074 into the shipped flow (not yet a bead)

**Needs `/task-init`.** Today they live in one coordinator's memory and reach no adopter.

1. Before replacing a component, the RFC enumerates what the old one did, from its source, with a
   test or an owner ruling per row. Checkable as a `docs quality` finding.
2. A question to the owner carries every option the agent found. Prose, in `/coordinator`.
3. A withheld-accounts review gets a launch prompt with no observation of the coordinator's own,
   declared as a duty so `config-check` stops on a role that loses it.

The same organ, open as bugs: `beadloom-tm76` (P1, #219, withholding does not cover commit
messages), `beadloom-6rfz` (P2, #297), `beadloom-qhxr` (P2).

### 8. `beadloom-r9t5` — four populations are called "stale docs" (P1, not started)

**Needs `/task-init`.** Nineteen surfaces report a number under one name over four different
populations, and one table row shows two of them. What each surface should count is a product
decision per surface.

### 9. The three class gaps (not yet a bead)

**Needs `/task-init`.** Stated under *The class behind most defects* below. Order: a rule made
impossible to break; allocation for `ACTIVE.md` (#257); an expiry on a recorded finding.

### 10. BDL-066 — agent behaviour observability (drafted, no beads)

Docs are `Draft` in `.claude/development/docs/features/BDL-066/`. The owner sees the conversation
with the coordinator and nothing of what the coordinator tells its subagents. Two slices are
re-derived before `/task-init`: scope drift overlaps item 6, and the brief delta is the inspection
item 7 declares uninspected. Everything here raises detectability and prevents nothing.

### 11. `beadloom-uxqc` — `doctor` audits the produced graph, not only the code (P1, #162)

Four graph defects shipped past every role and a green Gate, and each was found by a person
clicking a node. The bead turns those hand audits into checks: an island, an unexplained leaf, a
claim without evidence.

### 12. Follow-ups filed by BDL-074 to BDL-077 (P2 and P3)

- `beadloom-inmv`: mutation survivors outside the rule engine — kill them or record why each is
  equivalent.
- `beadloom-k6ou`: 167 test files still unplaced, each excused.
- `beadloom-o9rl`: the execution half of `scenario_binding`.
- `beadloom-fi8m`: a scenario count that names the Outline rows beside the declared scenarios.
- `beadloom-xg0y`: `clean-room` builds its environment without `uv.lock`.
- `beadloom-tu41`: `docs audit` gives a version to the product named earlier on the line.
- `beadloom-s34t`: `issue-number check` reads only column-0 entries.
- `beadloom-j1ke`: `impact` reads Python only, though the index holds JS and Vue imports.
- `beadloom-v4ql`: an index built without the languages extra silently holds no JS or Vue symbols.
- `beadloom-zd4m`: `.mjs` and `.cjs` are not code extensions of the reindex.
- `beadloom-ikj6`: precomputed code-level impact in the viewer (feature).
- `beadloom-0e3m`: `init --project .` writes a root node with an empty `ref_id`.
- `beadloom-55x2`: `reindex` with `scan_paths: ['.']` reads `node_modules`.
- `beadloom-y1ew`: `sync-update --pair` crashes when the pair's code file was deleted.
- `beadloom-gvdy`: grammar-cache fixtures leak a loader swap into the next test file.
- P3: `beadloom-uvgy`, `beadloom-phjj`, `beadloom-m6eb`, `beadloom-xx30`.

### 13. `beadloom-cxal` — the style guide, and Qwen as the writer of Russian documentation (P2)

A speech style guide for all four roles, shipped as data so it reaches a Claude adapter, a Goose
recipe and a machine check. With it, BDL-065: a **role runtime** in `flow.yml` that names which
executor runs a role. Measured 2026-08-31: Qwen rewrote the multi-agent guide and the owner judged
it clearly better. BDL-065 has no bead. **Needs `/task-init`.**

### Open P1 bugs this order does not rank

- `beadloom-147x`: `export` publishes a git remote's query string (a token) in the federation
  artifact's repository name.
- `beadloom-uz8x` (#215): the Gate reports an index problem as a rules configuration error.
- `beadloom-0mb5` (#221): attribution keys on the whole node.
- `beadloom-tgo8` (#222): the cross-check computes an attribution rule the implementation dropped.
- `beadloom-hdky` (#224): a new test file on an existing path deletes its scenarios, suite green.
- `beadloom-qil0` (#229): the review brief does not name the tracker export as a channel.
- `beadloom-bdnv` (#230): a branch suffix after the work-item key names no work item.
- `beadloom-mj2o` (#227): open in the tracker while the log records #227 as closed on 2026-09-10.
  One of the two is wrong; reconcile.

### Deferred until a need appears — federation (BDL-060 S5/S6)

Owner decision 2026-09-29. Epic `beadloom-8qqp` and its eight beads are `deferred`. S5 is live
cross-repo `ctx`; S6 is the `unverified` lifecycle, the undeclared sweep and review-gated
bootstrap.

---

## Standing debt outside the list (open P2)

| Bead | What |
|---|---|
| `beadloom-9glj` | `sync-update` can re-attest a doc nobody read (#163) |
| `beadloom-431c` | `docs audit` never checks that a documented identifier still exists (#161) |
| `beadloom-1d70` | no signal for a bounded context too large by subtree (#158) |
| `beadloom-2qwb` | centralise the remaining inline node reads |
| `beadloom-g0c5` | `test_tui.py` connection leak during textual GC |
| `beadloom-l27n` | 102 planning documents depart from the shape their peers keep (#223) |
| `beadloom-4axf` | the graph-file skip policy is restated by three readers |
| `beadloom-oew7` | `gate.py` holds both the orchestration and each leg's rendering |
| `beadloom-ovam` | two minors from BDL-069's review |
| `beadloom-ui47` | `get_node_tags` raises a bare `AttributeError` on a malformed `extra` (#294) |
| `beadloom-efcb` | a truthy non-iterable `extra.tags` fails every tag question (#295) |
| `beadloom-vu0a` | the TUI lint panel branches on a severity that does not exist (#292) |
| `beadloom-l5jb` | `issue-number allocate` accepts an empty holder (#299) |
| `beadloom-g79p` | deferred — AsyncAPI ingestion is documented and wired to nothing (#160) |

---

## The class behind most defects

Across BDL-067 and BDL-068 nearly every defect had one shape: **a check reports on a population
narrower than the question it appears to answer, and nothing in its output says so.** The check
is right about what it looked at and silent about what it did not. Stronger, more autonomous
agents make this worse: they pass an empty check without effort, and nobody is around to notice.
The full argument is in `archive/ROADMAP-until-2026-10-05.md`.

What already answers it and should keep being built: populations that are derived, never
authored · substitutable environments · instruments that name what they could not reach ·
withholding review · recording the offer, not only the decision.

**Three gaps are still open** (item 9):

1. **A rule made impossible to break, rather than written down.** Seven instances exist. The
   clean-room verdict wording, the landing-lock form and the commit-message rule are still text
   an agent must recall. This subclass has the highest measured failure rate.
2. **An expiry on a recorded finding.** A finding carries no date it was measured against, and
   three of six checked on 2026-09-08 were false.
3. **Allocation for shared resources no scope owns.** `ACTIVE.md` is written by every bead and
   belongs to no bead's code scope, so `beadloom waves` cannot see it (#257).

---

## Backlog — ideas, not ranked

- Ownership from CODEOWNERS, with a drift check.
- PR bot: an inline comment on a layer violation or a breaking contract.
- REST/OpenAPI as a contract source.
- Federation MCP server; `why <contract> --landscape` across repositories.
- Governance scorecard per service from existing inputs.
- Architecture decay report over snapshots and metrics history.
- Auto-bootstrap of the graph from code, tied to `unverified`.
- A versioned schema-migration framework.

## Off-north-star — raise only on a concrete need

- Import intent from import-linter, ArchUnit or dependency-cruiser.
- Semantic search, only at a scale of 1000+ nodes.
- **Semantic docs audit.** The `docs audit` detector binds numbers by English keyword proximity,
  so it mislabels them and is blind in a non-English document (#205, #206, #209, all open). The
  nine `docs_audit.ignore` suppressions are a workaround; a fix needs semantic classification.
- Marketplace GitHub Action, VS Code extension, gRPC and proto sources, plugin system, daemon,
  Bitbucket recipes, and the rest of the market or hygiene list in the archived revision.

## Won't do

- A built-in LLM or bundled weights.
- **Model tiering** — the same job on a cheaper model. A role runtime is a different thing: a
  different requirement and a different executor, declared in `flow.yml` and verified.
- A live web app or SaaS hub. The portal is static and CI-generated.
- A plugin marketplace.
- DSL or OPA-Rego rules, autofix patches, chat integrations.
- A Backstage replacement. Feed Backstage instead.
- Full bootstrap accuracy upfront, C#, pattern detection, dependency-weight analysis.
