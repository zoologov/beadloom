# Beadloom Roadmap

> **Current version: 8.0.0** (PyPI, published 2026-10-08, verified on the wheel downloaded from PyPI: 11 of 11 checks).
>
> Rewritten 2026-10-05 against the tracker, brought up to date 2026-10-10 (BDL-080 shipped). This file answers one question: what to do next,
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

**The target is three projects under Beadloom** (owner, 2026-10-08): this repository and the
owner's two frontends — a **Vue 3 frontend** (Vite, Pinia, Quasar, TypeScript; already Feature-Sliced
with Steiger, 81 slices and legacy directories beside them; self-hosted GitLab) and a **React
Native app** (Expo Router, Expo Modules with Swift and Kotlin, gluestack with `.web.tsx`, Babel
aliases; FSD planned in its refactoring). Measured 2026-10-08: on both, 44–49 % of imports go
through path aliases the resolver does not read, so a graph built today lies by omission. Every
item below is ranked by what it does for those three. Project names stay out of this repository.

---

## In progress

### BDL-081 — the MAJOR release after BDL-080

Its own work item by BDL-079's recipe (`/task-init`, Explore measuring `v8.0.0..main` per
surface). MAJOR because a `kind: site` node is now judged by the service rules, so `lint`'s exit
code can move on an unedited project. BDL-080 shipped 2026-10-10: S1 as PR #96, S2 + S3 + S4 as
PR #98 (`290507b2`); its findings are BDL-UX #309–#314, all under Debt to zero.

---

## What to do next, in order

Items 5 to 14 keep the owner's order of 2026-09-29. Items 1 to 4 were placed first by the owner
on 2026-10-05, 2026-10-07 and 2026-10-08: the three projects, debt to zero (right after
BDL-080), the rules, the RN project's requirements.

### 1. Adoption on the Vue frontend, then on the React Native app (after BDL-080; owner's step)

The first outside adoptions, in this order: the Vue frontend first — it is already FSD, runs
Steiger, and its GitLab remote exercises the Source link's second forge; the React Native app
second — it needs S3's resolver work and the Expo module bridge, and its own process RFC asks
Beadloom for more (item 4). Each adoption is a work item of its own: `init`, the graph read by
the owner, `lint --strict` over the FSD rules, the portal published, the findings filed as
BDL-UX issues. What those two find is what ranks the rest of this list.

### 1c. `beadloom-nbpb` — the setup wizard, a main-loop skill (P1, not started; between the two adoptions — owner, 2026-10-10)

A skill, not a subagent: it needs the person's decisions, like `/task-init`. It walks a person
through adopting Beadloom — detect the stack, `init`, read the graph together, declare the site
and the forge, hooks, CI, branch protection, the roles in `flow.yml` — as a thin protocol over
`init`, `config-check`, `doctor` and `setup-*`, every step's options enumerated, the report
naming what it set up and what it did not. It knows nothing by prose: the keys live in
`config-check`, the sequence lives in its checklist, which closes #218 (`init`'s three
hand-written step sequences). Place: after the first adoption writes the real checklist, before
the second checks it. Ships via `setup-agentic-flow` with a Cursor adapter. **Needs `/task-init`.**

### 1b. `beadloom-mnuu` — pages and routes are first-class nodes (P1, not started; right after BDL-080 — owner, 2026-10-09)

The graph is built from code, so a site's or an app's screens — generated Markdown, Expo Router
`app/` files, a Vue Router config — are islands or absent: on this portal only two pages have
code, and the dashboard, docs, about and 130 node pages are invisible in the site's box. A node
kind `page` with a reader per framework and edges to the components a page mounts, drawn in the
FSD `pages` layer. Serves all three projects. **Needs `/task-init`.** (BDL-080 S4 does the cheap
half first: a page map on the dashboard and the site service's doc listing its pages.)

### 1a. `beadloom-ba9w` — Debt to zero (P1, not started; right after BDL-080, before the rules epic — owner, 2026-10-08)

Owner, 2026-10-08, reading the 8.0.0 dashboard (Lint 70 warnings, Debt 42.5 high, Doctor 262
warnings): a work item that clears the debt rather than excuses it. Measured: 167 of 786 test
files bound to no node (`beadloom-k6ou`, each excused — the reason the impact panel says "no
bound tests" and the debt report says "not counted"); 49 features with no acceptance scenario;
262 documents with no `ref_id`; complexity smells 35 of the 42.5 points (oversized 9, high
fan-out 10, dormant 14). Four slices, each with its own measure (A tests, B scenarios, C docs,
D smells); BDL-080 S2 takes `site-graph-viewer`'s oversized smell.

Owner, 2026-10-09, three more slices, agreed with two conditions: **E the Beads upgrade** —
every claim the composed CLAUDE.md measured on bd 1.0.4 (the merge-slot forms, `--suggest-next`'s
16-of-23 shapes, the `bd list` caps) is re-measured on the new version and confirmed or
rewritten, in a claim / was / is table; **F the agents' capability check** — Claude Code and
Cursor against their current docs (agent frontmatter, hooks, skills, MCP), the deltas applied to
the role templates and `setup-agentic-flow`; **G dependencies** — Python, the portal scaffold
(VitePress, Cytoscape, elkjs, Playwright) and GitHub Actions, each major verified by the full tree
and the six adopter stacks. The conditions: the work recurs, so the one-off pass lives here and
the recurrence goes into the flow (Dependabot or Renovate for dependencies; a "tooling baseline"
duty in the release role); the epic stays sliced, one PR per slice, never a bag.
Owner, 2026-10-10, slice **H context rot** (`beadloom-ba9w.8`, BDL-UX #156): the composed CLAUDE.md and
the role files are split by function — a short imperative core that survives a long session,
the narrative rationale in referenced companions — every role declares the size and shape of
its hand-back, and `config-check` names a role without that contract; measured by the composed
files' length before and after. The owner: «важный момент».
Owner, 2026-10-09, the template slice (`beadloom-cnty`) covers all six flow documents, not
ACTIVE alone: header fields with a fixed vocabulary (`Status`, `Approval: approved|delegated by
the owner on <date>`), no quotations in metadata, the section set and order enforced by the
Gate — the files are filled by template, without free prose.
**Needs `/task-init`.**

### 2. `beadloom-j4gi` — the rules leave the graph folder and are decomposed (P1, not started; the second epic, with `beadloom-tvjp`)

**Needs `/task-init`.** Owner, 2026-10-07: `.beadloom/_graph/rules.yml` is 860 lines in the
graph's folder — 19 rules, ~330 lines of dated commentary, ~190 lines of baselines. The approved
structure: `.beadloom/rules/` beside `_graph/`, one file per rule family (structure, layers,
imports, coverage, tests); the loader reads `rules.yml` or `rules/*.yml`, `init` writes the split
layout, `config-check` reports a project with both; baselines (exempt file lists) in
`rules/baselines/<rule>.yml`; the dated rationale leaves YAML for the rule family's document
under `docs/`, where `sync-check` and the audit can judge it — the first instance of rationale
bound to what it is about so that it can go stale. Explore enumerates every reader first.

### 3. `beadloom-tvjp` — SemVer as a rule of the shipped flow (P1, not started; with `j4gi`)

Owner, 2026-10-08: SemVer and the declared public API go into the roles and the release rules
that ship to adopters — a release checklist with the version decision as a step, duties for the
review and tech-writer roles (an API CHANGE names its SemVer kind; a verdict states the version
the change requires), a *Public API* template per project, a CHANGELOG check. `beadloom-pre3`
(card populations) folded into BDL-080 S4.

### 4. What the React Native app's process RFC asks of Beadloom (not yet a bead)

**Needs `/task-init`, after the two adoptions start.** The owner's RN project is planning its
delivery process on Beadloom (its RFC §12, 2026-10-01) and lists what it needs that Beadloom
does not have: a `design` role with `react-native` and `gluestack` overlays (design spec,
render, gallery, the owner's feedback loop) and a `qa` role with `detox` and `playwright`
overlays; a `ui-tokens-only` rule (no hex colours or `StyleSheet` in `features`, `entities`,
`shared`); a `ui-accepted` guard on visual baselines; the screen gallery on the portal beside
the landscape; more than one stack in one `flow.yml`; a hook that mirrors beads and documents
into the team's tracker and wiki (Huly) and comments back; a multi-session guard (two
coordinators on one station, never one bead or one branch twice); a `graphql-federation`
overlay and a contracts hub over `export`/`federate` for its backend services — which is the
need the federation deferral below was waiting for. Rank inside the item: the ones the first
adoption blocks on first.

### 5. `beadloom-jwfc` — the pre-push Gate crashes on a full pipe and reports it as stale docs (P0, BDL-UX #226)

The only open P0. Under `git push` the Gate's stdout is a non-blocking pipe, one large write
raises `BlockingIOError`, and the hook then says the docs are stale. Each occurrence teaches
`--no-verify` for a reason that is false. **Done when** the report survives a full pipe and the
hook tells a Gate that crashed from a Gate that failed.

### 6. The adopter's first commands (five P1 bugs)

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

### 7. `beadloom-tsqz` — `scope-check` never runs in CI (P1, #300)

A pull request is checked out on a detached HEAD, no branch names a work item, and the leg skips.
**Done when** the leg judges a pull request whatever its branch is called.

### 8. Three lessons of BDL-074 into the shipped flow (not yet a bead)

**Needs `/task-init`.** Today they live in one coordinator's memory and reach no adopter.

1. Before replacing a component, the RFC enumerates what the old one did, from its source, with a
   test or an owner ruling per row. Checkable as a `docs quality` finding.
2. A question to the owner carries every option the agent found. Prose, in `/coordinator`.
3. A withheld-accounts review gets a launch prompt with no observation of the coordinator's own,
   declared as a duty so `config-check` stops on a role that loses it.

The same organ, open as bugs: `beadloom-tm76` (P1, #219, withholding does not cover commit
messages), `beadloom-6rfz` (P2, #297), `beadloom-qhxr` (P2).

### 9. `beadloom-r9t5` — four populations are called "stale docs" (P1, not started)

**Needs `/task-init`.** Nineteen surfaces report a number under one name over four different
populations, and one table row shows two of them. What each surface should count is a product
decision per surface.

### 10. The three class gaps (not yet a bead)

**Needs `/task-init`.** Stated under *The class behind most defects* below. Order: a rule made
impossible to break; allocation for `ACTIVE.md` (#257); an expiry on a recorded finding.

### 11. BDL-066 — agent behaviour observability (drafted, no beads)

Docs are `Draft` in `.claude/development/docs/features/BDL-066/`. The owner sees the conversation
with the coordinator and nothing of what the coordinator tells its subagents. Two slices are
re-derived before `/task-init`: scope drift overlaps item 7, and the brief delta is the inspection
item 8 declares uninspected. Everything here raises detectability and prevents nothing.

### 12. `beadloom-uxqc` + `beadloom-e6s2` — `doctor` audits the produced graph, and the graph reviewer judges it (P1, #162; one epic — owner, 2026-10-10)

Four graph defects shipped past every role and a green Gate, and each was found by a person
clicking a node. The bead turns those hand audits into checks: an island, an unexplained leaf, a
claim without evidence. On top of the mechanics, a **graph reviewer role** (`beadloom-e6s2`): read-only,
run at the close of a work item before its PR and after `init` on a new project, judging the graph
as a whole — kinds, `part_of`, derived vs authored edges, layers and tags against the code — with
a verdict, findings and a named population; graph edits are a dev bead's. A separate role, not an
extension of the code reviewer: the code review's unit is a bead's diff, so the graph is judged
only where code changed, which is how those four defects slipped past. Ships via
`setup-agentic-flow` with a Cursor adapter. **Needs `/task-init`.**

### 13. Follow-ups filed by BDL-074 to BDL-077 (P2 and P3)

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
- `beadloom-zd4m`: `.mjs` and `.cjs` — **done in BDL-080 S3a**.
- `beadloom-ikj6`: precomputed code-level impact in the viewer (feature).
- `beadloom-0e3m`: `init --project .` writes a root node with an empty `ref_id` — **fixed in BDL-080 S3e** (#313 is the same defect, refiled).
- `beadloom-55x2`: `reindex` with `scan_paths: ['.']` reads `node_modules`.
- `beadloom-y1ew`: `sync-update --pair` crashes when the pair's code file was deleted.
- `beadloom-gvdy`: grammar-cache fixtures leak a loader swap into the next test file.
- P3: `beadloom-uvgy`, `beadloom-phjj`, `beadloom-m6eb`, `beadloom-xx30`.

### 14. `beadloom-cxal` — the style guide, and Qwen as the writer of Russian documentation (P2)

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
bootstrap. **The need has a date now:** the RN project's RFC plans a contracts hub over
`export`/`federate` for its backend services (item 4). The deferral stands until the owner
lifts it.

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

**Three gaps are still open** (item 10):

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
