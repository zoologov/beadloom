# Beadloom Roadmap

> **Current version: 9.0.0** (PyPI, published 2026-10-10, verified on the wheel downloaded from PyPI: 24 of 24 checks).
> from PyPI). The release before it, 8.0.0, is the latest on PyPI, published 2026-10-08 and
> verified on the wheel downloaded from PyPI: 11 of 11 checks.
>
> Rewritten 2026-10-05 against the tracker, re-ranked 2026-10-14 (BDL-082 shipped; federation and the team's operating model first). This file answers one question: what to do next,
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
  half, federation, was deferred until a need for it appeared (owner, 2026-09-29). The need
  appeared on 2026-10-12: the owner's team adopts Beadloom entity by entity as every monorepo is
  split into its own repository, and the hub is what joins them (owner, 2026-10-14).

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
Since 2026-10-12 the three sit inside a split: every monorepo the owner holds is being cut into
one repository per entity — the colleague's PDF-viewer library out of the frontend's `shared/lib`
first, the backend into microservices, the frontend into its own repository, configuration into an
infrastructure repository. **The order of adoption is the order of the split**: the cheapest moment
to put an entity under Beadloom is the birth of its repository, with the graph written as intent
and the rules in force from the first commit.

---

## In progress

Nothing. BDL-082 shipped on 2026-10-14 (PR #101 on 2026-10-11, PR #102 on 2026-10-14). The order
below is the owner's of 2026-10-14, set after the team-topology discussion of 2026-10-11/12; the
owner's note of that discussion holds the measurements behind it.

---

## What to do next, in order

**The owner's order of 2026-10-14** (a program of sequential work items, each with its own
`/task-init`, slices and PRs — never one bag). It replaces the order of 2026-10-11: the team's
adoption across split repositories is the need federation was waiting for, and the team's way of
working is designed before the hub, because the hub's PRD takes its input from it.

1. **The team's operating model** — a design item, no code. How several people, each with their
   own agent, work under Beadloom in one repository and across repositories. Seven decisions:
   who owns the graph and the rules (path ownership in the repository, not an agreement); the unit
   of work (one work item is one branch, one document folder and one coordinator — waves and the
   shared tree stay inside one person, people separate through git); the tracker between people
   (a local database per clone, the exchange through the tracked file — closes already get lost on
   branch merges, and two people closing beads in parallel is unmeasured); the files that change by
   themselves (the metrics history and the interactions journal change in every session and
   conflict on every merge — out of git, or a merge strategy); review (the human in the PR, the
   agent's brief per bead, the tech-writer on CI — which blocks and which advises); a newcomer's
   entry (three commands and nothing by hand; the roles compose from `flow.yml` and are committed,
   so every agent is the same — verified, not assumed); who feeds the hub (a satellite exports on
   its merge to `main`, the hub aggregates on CI in the infrastructure repository). Form: a short
   model with its assumptions written down; the tracker and the self-changing files measured on
   two clones; the rest checked on the pilot satellite of item 3. Output: a guide under `docs/`
   and a bead per gap found. **Needs `/task-init`** (type task, BRIEF).
2. **The CI trust boundary** (`beadloom-dlb6`, BDL-UX #321): a short standalone item — read-only
   token by default with elevation on one job, the tech-writer job limited to same-repository
   PRs, fork runs approved for every outside contributor, the stale protection comment corrected.
   From an outside audit of 2026-10-11, verified by line. Runs beside item 1 while the owner
   reads the model's draft: it needs no owner decision.
3. **Federation: the hub as a product** — the deferral of 2026-09-29 lifted (*Federation* below).
   In order: the hub over three to five satellites (a portal page for the federated graph, a CI
   recipe for the hub, hub-level rules — a contract removed while a consumer in another repository
   holds it, a satellite whose export is older than its term); the mount point by name (a
   satellite declares the packages and contracts it publishes, the hub joins exports by those
   names — the frontend depends on the library as a package, a service on a service as a
   contract; mounting by path inside a monorepo is withdrawn together with nested roots); the
   platform satellite from manifests (Helm, Kubernetes YAML, compose, Terraform — nodes of kind
   cluster, queue, storage and database, edges from services derived from configuration or
   declared and marked *not verified*; the graph says of every edge whether it was measured or
   declared). `beadloom-147x` (a token in the export's repository name) closes inside it. The
   pilot satellite is the colleague's PDF-viewer library in its own repository — the cheapest
   split (158 files, one index, one external dependency), its first findings known in advance.
   **Needs `/task-init`**, with item 1's guide as the PRD's input.
4. **The catalog**, after the Backstage trial — a separate product over the hub, not the core
   (the two *Won't do* lines below are reworded accordingly). The vocabulary is borrowed from
   Backstage either way — Domain, System, Component, API, Resource, Group, User; owns, provides,
   consumes, depends on, part of — so an export to `catalog-info.yaml` stays trivial. The trial
   measures: whether three satellites' exports carry over without loss; whether *verified by code*
   can be shown where a person looks; the cost of owning a Node application with a database, auth
   and plugins against a static portal from CI; TechDocs against the portal; the audience
   (architects through PRs, or the whole company with permissions and search). A bought
   on-premise system and the planned integrations between projects enter as declared nodes of
   kind *external system*, confirmed from our side when a satellite's export brings the measured
   edge. **The owner decides after the trial; no `/task-init` before it.**
5. **The setup wizard v1** as a main-loop skill (`beadloom-nbpb`) — a thin protocol over `init`,
   `config-check`, `doctor` and `setup-*`, its second pass written from the adoption's findings —
   and **the graph reviewer v1** as a role (`beadloom-e6s2`) over today's `doctor` and `lint`;
   `uxqc`'s mechanics stay in Debt to zero. One addition since 2026-10-11: the wizard knows
   satellites and the hub from its first day, and its adoption levels are what keeps a teammate
   with one agent on a young service from paying for ceremony that does not pay back.
6. **Adoption in the split's order** (item 1 below): the library first, as item 3's pilot; the
   backend microservices as each is split out; the frontend when it gets its own repository; the
   infrastructure repository as the platform satellite and the hub's home. A nested project root
   gets an honest refusal, not support (`beadloom-7pd6`, BDL-UX #325); the FSD-root-inside-the-
   repository key stays a stopgap, taken only if the frontend's split runs past about six months.
7. **The findings into the BDL-UX log; ROADMAP and the log re-ranked** by what the adoptions found.
8. **Debt to zero brought up to date and done** (`beadloom-ba9w`, slices A–I, plus a slice
   that re-measures every `high` entry on 9.0.0 — stale ones close, live ones rank by the
   adoption; slice E reworded for the team, see below).

Items 5 to 14 below keep the owner's order of 2026-09-29; items 1 to 4 were placed first on
2026-10-05, 2026-10-07 and 2026-10-08.

### 1. Adoption in the split's order: the library, the microservices, the Vue frontend, the React Native app (owner, 2026-10-12)

The order of adoption is the order of the split (*Vision* above). First the colleague's PDF-viewer
library in its own repository — the pilot satellite of order item 3; measured 2026-10-12 by imports
(nothing run): 158 files, one top-level index, one external dependency, a microkernel-shaped
inside (facade, coordinator, managers, an event bus with 131 event names in strings, 48 files on
the bus) that is, from the frontend's side, one `shared/lib` slice with a public API. Beadloom holds
it as a node with child nodes and two rule sets of different reach: FSD outside, its own rules
inside (the core imports no module, modules import no module, subsystems cross only through
`shared`) — four core files and two `page → list` imports become its first findings. Then the
backend microservices as each is split out, each at the birth of its repository. Then the two
frontends, in this order: the Vue frontend first, when it has its own repository — it is already
FSD, runs Steiger, and its GitLab remote exercises the Source link's second forge; the React Native
app second — it needs S3's resolver work and the Expo module bridge, and its own process RFC asks
Beadloom for more (item 4). Each adoption is a work item of its own: `init`, the graph read by the
owner, `lint --strict` over the rules, the portal published, the export into the hub, the findings
filed as BDL-UX issues. What those adoptions find is what ranks the rest of this list. During the
transition nothing reads inside a monorepo: an entity not yet split out is *not yet under
Beadloom*, and the hub shows it as a declared, unverified node.

### 1c. `beadloom-nbpb` — the setup wizard, a main-loop skill (P1, not started; between the two adoptions — owner, 2026-10-10)

A skill, not a subagent: it needs the person's decisions, like `/task-init`. It walks a person
through adopting Beadloom — detect the stack, `init`, read the graph together, declare the site
and the forge, hooks, CI, branch protection, the roles in `flow.yml` — as a thin protocol over
`init`, `config-check`, `doctor` and `setup-*`, every step's options enumerated, the report
naming what it set up and what it did not. It offers adoption **levels**, each useful alone —
context only; plus architecture checks; plus documentation control; plus the agentic flow — so
a person who stops at the first gets a working tool and a report of what was not set up (owner,
2026-10-11; expected to be the first feedback from a teammate with one agent). It knows satellites and the hub from its first day (owner, 2026-10-14). It knows nothing by prose: the keys live in
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
rewritten, in a claim / was / is table, and — for the team (owner, 2026-10-14) — whether that
version runs against a remote Dolt database, with import and export around every commit and
tracker-to-file coherence judged by the Gate; **F the agents' capability check** — Claude Code and
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
Owner, 2026-10-11, slice **I the context says what the Gate judges** (`beadloom-ba9w.12`, BDL-UX
#317, high): `ctx` surfaces 2 of the 17 rule types and its Markdown output none, and its matcher
reads two of the linter's five fields — one applicability derivation for `lint` and `ctx`, and a
list that is complete or says where it is not. With it, from the same outside audit (2026-10-11,
every claim verified by file and line): the Gate's per-step exception boundary and an `ERROR`
status (`.13`, #318), a token budget and focus-first chunk order for `ctx` (`.14`, #319), the
subgraph contract at the node cap (`.15`, #320). Ranked with the rest after the Vue adoption.
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
overlay and a contracts hub over `export`/`federate` for its backend services — served by order
item 3 (the deferral lifted on 2026-10-14). Rank inside the item: the ones the first
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
  artifact's repository name. Closes inside order item 3.
- `beadloom-uz8x` (#215): the Gate reports an index problem as a rules configuration error.
- `beadloom-0mb5` (#221): attribution keys on the whole node.
- `beadloom-tgo8` (#222): the cross-check computes an attribution rule the implementation dropped.
- `beadloom-hdky` (#224): a new test file on an existing path deletes its scenarios, suite green.
- `beadloom-qil0` (#229): the review brief does not name the tracker export as a channel.
- `beadloom-bdnv` (#230): a branch suffix after the work-item key names no work item.
- `beadloom-mj2o` (#227): open in the tracker while the log records #227 as closed on 2026-09-10.
  One of the two is wrong; reconcile.

### Federation (BDL-060 S5/S6) — the deferral lifted on 2026-10-14

Owner decision 2026-09-29 deferred epic `beadloom-8qqp` and its eight S5/S6 beads until a need
appeared. The need appeared on 2026-10-12 — the team's adoption across split repositories — and
the owner lifted the deferral on 2026-10-14 (order item 3). The eight beads stay `deferred` in the
tracker until item 3's `/task-init` decides which of S5 (live cross-repo `ctx`) and S6 (the
`unverified` lifecycle, the undeclared sweep, review-gated bootstrap) it absorbs and which it
re-plans; `export` and `federate` (S1–S4, shipped) are its base, and what is missing — the hub's
portal page, its CI recipe, hub-level rules, the mount point by name, the platform satellite — is
listed in item 3.

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
- A roles overlay for architectures outside DDD and FSD — layered by contract, or user-declared —
  and an event-bus edge reader (`emit`/`on` names as edges, marked by their channel), from the
  colleague's library measurement of 2026-10-12: a microkernel inside a `shared/lib` slice whose
  131 event names the graph cannot see.
- Work items crossing by axes: `waves` one level up — which open work items collide on graph
  nodes, read from their `## Axes` sections, with a portal page of who holds which nodes.
- A fragment folder for the shared files no bead owns (this file, the issue log, the Unreleased
  section of `CHANGELOG.md`): one fragment per change, the file composed — the issue log's number
  claims are the first step of it.

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
- A live web application or a SaaS hub **in the core**. The portal is static and CI-generated;
  the catalog, if built, is a separate product over the hub (order item 4; owner, 2026-10-12).
- A plugin marketplace.
- DSL or OPA-Rego rules, autofix patches, chat integrations.
- A Backstage replacement **in the core**. Feed Backstage, or build the catalog as a separate
  product over the hub — the owner decides after the Backstage trial (order item 4).
- Full bootstrap accuracy upfront, C#, pattern detection, dependency-weight analysis.
