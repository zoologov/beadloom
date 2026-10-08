# PRD: BDL-080 — The portal is a service, and the viewer serves a Feature-Sliced frontend

> **Status:** Approved
> **Created:** 2026-10-08

---

## Problem

The owner's observations on the 8.0.0 portal, verbatim and in order:

- 2026-10-05: «У нас сайт имеет app, entities, features, pages, shared, widgets — но, например, на
  графе только component и в ноде fsd-widgets. Получается что наш архитектурный вьювер будет
  бесполезен для команд frontend?»
- 2026-10-06: «С точки зрения архитектуры Beadloom это такой же сервис как TUI, только тот в
  консоли разработчика, а vitepress — на виду у всей команды и руководителей. Все закрывается
  одной версией Beadloom и является частью продукта.»
- 2026-10-06: «надо максимально декомпозировать у нас же принцип cohesion. В ddd python у нас
  хорошо все разбито. В fsd надо так же делать (это надо наверное роли править?)»
- 2026-10-07: the Source link of a locally built portal is a 404 on every node; «Rule findings:
  none» and «Debt 0» on a box say nothing about their population.
- 2026-10-08: blue arrows on the overview with no legend entry.

Measured (2026-10-05 and 2026-10-08, file:line in `axes.md` and the beads):

1. **One layer rule is drawn.** `architecture_view.py` takes the first `layers` rule by name
   (`LIMIT 1`). This repository declares two, so its twenty site slices are grey, have no lane,
   no Layer-filter value and never a red edge, while `lint` judges them. Any repository with a
   backend and a frontend is the same case.
2. **`vitepress-site` is `kind: site`**, a kind no rule can match (`VALID_NODE_KINDS` lacks
   it), that gets no doc skeleton, lands under `other/` in the portal's pages and is left out of
   its nav. It is in truth a service of the product: its own runtime, build, dependencies, tests
   and layer rule, consuming a declared contract (the data files `beadloom` produces).
3. **One node owns the whole viewer.** `widgets/graph-viewer/**` is 43 files under
   `site-graph-viewer`; every BDL-078 viewer bead was serialised by `beadloom waves` on that
   node alone. The DDD side is decomposed by cohesion and has a `domain-size-limit`; the FSD side
   has no such rule, and the `fsd` role overlay tells agents to map layer → domain, slice →
   feature, segment → component — the mapping this repository rejected.
4. **`init` knows no FSD.** No preset detects `app/pages/widgets/features/entities/shared`; no
   layer rule is generated; the slice public-API rule (no import past a slice's `index`) is prose
   in the overlay only. No adopter fixture is FSD.
5. **The portal does not name what it reports over.** The Source link is a permalink to the
   built commit (dead when that commit is on no remote); `Rule findings: none` is
   indistinguishable from "lint never ran" and the 36 node-less findings appear nowhere; a box's
   `Debt` is its own score while its activity rolls up; the legend omits a kind that is on the
   canvas (`uses`, indigo, solid at the overview while the sample is dotted).

## Impact

A frontend team (the second use of the vision, a team of solos) gets a viewer that shows their
layers, their slices as nodes and their rule violations; this repository's own portal shows its
frontend honestly; the viewer's beads can run in parallel; `init` on an FSD project needs no
hand-written rule; every number and colour on a card or legend names its population.

## Goals

1. **`vitepress-site` is a service.** This repository's graph declares it `kind: service`,
   `part_of beadloom`, with the data files as a declared contract (`beadloom` produces, the portal
   consumes). The product keeps accepting `kind: site` (removing a kind from the graph schema
   would be MAJOR) but treats it everywhere as a service: rules can match it, it gets a doc
   skeleton, a `services/` page and a nav entry. *Done when* the own portal shows the site as a
   service box with its page under `services/`, and `lint`, `docs generate` and `doctor` treat it
   as one.
2. **Every layer rule is drawn.** The data file carries every `layers` rule with the nodes each
   one stratifies; a rule applies to the subtree whose nodes carry its tags (derived; an optional
   explicit `scope:` on the rule — a new, backwards-compatible key — names the container when
   derivation is ambiguous). The legend lists layers per rule, the Layer filter offers every
   layer, a box's lanes follow its own rule, a layer's token reads its name (not `fsd-widgets`),
   six layers get six tones. *Done when* this portal's site slices are coloured by the FSD rule
   and `lint`'s FSD findings are red on the canvas; the six fixtures unchanged.
3. **The viewer is decomposed by cohesion, and the rule says so.** `widgets/graph-viewer` is
   split into FSD slices that are graph nodes (the overview router, the levels/map model, routes
   and heads, bundles, the selection walk, the card's data — the RFC derives the cut from the
   files' import graph), each its own `.beadloom/_graph` node with its tag; a cohesion rule for
   components (`component-size-limit` or the FSD equivalent of `domain-size-limit`) is declared
   in this repository's rules and shipped as a default of the FSD preset; the `fsd` role overlay
   and the explore/dev protocols state the cohesion rule as the DDD overlay states it for Python
   packages, and the overlay's layer → domain mapping is replaced by slice → component with the
   layer as a tag. *Done when* no viewer node owns more than the limit, `beadloom waves` over
   BDL-078's viewer beads (re-declared against the new nodes) places at least two in one wave,
   and the Playwright suite is unchanged in count and green.
4. **`init` serves an FSD project.** A preset detects the six-folder layout, writes one node per
   slice (`component`, tagged with its layer, `part_of` the frontend service), the FSD `layers`
   rule, the slice public-API rule (a `forbid_import` from outside a slice past its `index`, with
   the owner's wording in `rules.yml` comments), and the cohesion rule; a seventh adopter fixture
   (an FSD project with TypeScript) joins `tests/fixtures/site/` and the `site-adopters` matrix.
   *Done when* `init` on the fixture needs no hand edit for `lint --strict` to judge its layers,
   and the fixture's portal is green under the browser suite.
5. **Every population is named.** The Source link resolves on a build from an unpushed commit
   (branch or default branch, with a note on the card); `Rule findings` names lint's reach
   (`none — this project: 0 errors, 70 warnings on 28 nodes`) and node-less findings have a home
   on the project box's card and the dashboard; a box's card shows debt own and inside, by
   reason; the legend names every stroke colour and dash on the canvas at every level, and an
   aggregated line of one kind keeps that kind's dash. *Done when* a case holds "every colour
   and dash on the canvas has a legend entry" at every level on this portal and the fixtures.

## Non-goals

- Federation; the hub/satellite landscape.
- SemVer in the shipped flow (`beadloom-tvjp`) and the rules decomposition (`beadloom-j4gi`) —
  the second epic. Where this epic adds rules to `rules.yml`, it adds them in the file as it is
  today; `j4gi` moves them.
- A slice/segment model finer than one node per slice.
- Changing how the DDD side is modelled.

## User Stories

- **US-1** As a frontend developer on an FSD project, I run `beadloom init`, and the portal shows
  my six layers, my slices as nodes, and a red line where a slice imports a sibling or reaches
  past another slice's `index`.
- **US-2** As a reader of this repository's portal, I see the site as a service beside `tui`,
  coloured by its own layers, and a click on it opens a page under `services/`.
- **US-3** As the coordinator, I launch two viewer beads at once because `beadloom waves` says
  their nodes are disjoint.
- **US-4** As a reader of any card, I know what `none` and `0` were counted over.

## Acceptance Criteria (overall)

- `lint --strict` 0 errors on this repository with the new nodes and rules; `beadloom ci` rc 0.
- The own portal: the site box coloured by the FSD rule; at least one FSD finding drawn red when
  one is introduced on purpose in a test; the legend lists both rules' layers.
- The FSD fixture: `init` → `lint --strict` judges its layers without a hand edit; the browser
  suite green; the `site-adopters` matrix has seven legs.
- `beadloom waves` over three re-declared BDL-078 viewer beads: at least one wave of two.
- Metrics cases: every colour and dash on the canvas has a legend entry; `Rule findings` and
  `Debt` on a box name their population; the Source link of a local build from an unpushed
  commit returns 200 on this repository's remote.
- The version: MINOR (every change adds; `kind: site` stays accepted), unless the RFC finds an
  incompatible change — then it is named and the owner rules.

## Slices (one PR each, as agreed 2026-10-08)

- **S1** the site is a service + every layer rule drawn (goals 1, 2).
- **S2** the viewer decomposed + the cohesion rule + the roles (goal 3).
- **S3** `init` for FSD + the seventh fixture (goal 4).
- **S4** every population named (goal 5).

## Rulings

- 2026-10-06, owner: `vitepress-site` is a service like `tui`; decompose by cohesion; the roles
  say so.
- 2026-10-08, owner: two epics by cohesion — this one (be6e + pre3) and the rules one (j4gi +
  tvjp); PR per slice.

## Answers (owner, 2026-10-08)

1. **Scope of a layer rule — by FSD best practice.** FSD's layers belong to one application
   root: a rule stratifies the slices of the frontend service that holds them (derived from the
   service whose nodes carry its tags; an explicit `scope:` stays available and optional). Cross
   imports inside one layer are forbidden by the rule, as FSD prescribes.
2. **The FSD fixture is JavaScript + TypeScript** — the mixed project FSD teams actually have.
3. **The cohesion limit — by FSD best practice.** FSD gives no file count; it gives the shape: a
   slice is one business entity or feature, with the standard segments (`ui`, `model`, `lib`,
   `api`, `config`) and a public API in `index`. The rule therefore judges shape first (a slice
   whose `lib/` or `model/` grows past the standard segments, or that reaches past another
   slice's `index`, is a finding) and keeps a calibrated symbol-count signal second, measured on
   this repository as `domain-size-limit` was — a signal, not a target. The RFC states the
   numbers it measures.

**Resolved:** the PRD is approved with these answers («ОК»); the RFC follows.
