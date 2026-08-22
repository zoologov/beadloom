# PRD: BDL-061 — Enforced agentic flow

> **Status:** Approved
> **Created:** 2026-08-21

---

## Problem

The multi-agent flow Beadloom scaffolds is **advisory**, and advisory flows are silently
skipped. This is measured, not suspected.

**Measured on a real project run through the scaffolded flow** (#153): 0 of 6 beads reviewed,
1 of 6 mutation-gated, 0 `.feature` files written, 0 `/task-init` invocations — while the ONE
rule backed by a machine check blocked the agent **four times in the same session**. The owner
did not work around the rules; he demanded the harness follow them. The rules were right. The
enforcement was absent.

The root cause is structural, not a discipline failure. `CLAUDE.md` arrives as context the
model may deem inapplicable, and instruction-following degrades as the file grows and the
session lengthens — so the rules are least effective exactly when a long session needs them
most (#156, context rot). Adding more prose makes it worse.

Five defects compound it.

**Prose is the only place a project can put its own rules.** All eight shipped flow files
(`.claude/agents/*`, `.claude/commands/*`) are byte-identical between our repo and the
dogfood project — verified. The drift guard works, and *that is why nothing project-specific
could go in.* The dogfood project's four role-specific duties (dev writes behavior expressible
as `.feature`; test writes them plus a mutation gate; review checks behavior coverage;
tech-writer treats scenarios as living docs) and its coordinator-specific verification rules
all ended up in the one file it could edit — `CLAUDE.md`. Role rules became global prose,
which is precisely the form context rot destroys. The gap is filed twice, independently:
composed adapters are drift-guarded with **no methodology/quality overlay slot** (#139), and
overlays resolve only inside the installed package so a project has no supported place for its
own additions (#152). Attempting it corrupts the file (#132), the scaffolded flow is
English-only with a hardcoded stack and no overlay awareness (#136), and a cross-major re-init
orphans command files while skipping changed vendored ones as "hand-edited" (#137).

**Some of the prose exists only because Beadloom lies.** The dogfood project's standing
verification section opens with two rules that are workarounds for our own open bugs:
`beadloom lint` must be run on a wiped database because incremental reindex does not refresh
import edges (#142 — a module cycle passed through an entire verification pass including an
independent re-check, and was found a day later by accident), and `sync-check` reports "clean"
for `component` nodes because no pairs exist for them (#146). A user had to write defensive
instructions because the gate reports green having checked nothing. A third bug makes the
guards themselves awkward: `lint` MUTATES the index and has no read-only mode (#147), so a
check that runs on every edit would write to the artifact it is checking.

**Acceptance criteria bind to nothing.** The PRD template ships `- [ ] Criterion 1` — free
prose, verified by a human ticking a box. Every neighbouring artifact is machine-checked: the
graph binds code to docs and checks freshness, beads bind work into a gated DAG, `beadloom ci`
checks lint, sync and prose facts. The criterion — the statement of what the work must achieve
— is the weakest link in the chain, and BDD/Gherkin appears in **zero** of our templates, role
templates and command templates (verified).

**Parallel work has no shape and no oversight discipline.** The flow runs agents in parallel
via `/coordinator`, but nothing decides *what* may run in parallel: parallel agents pay off on
independent subgraphs and rot on richly interdependent code, and only Beadloom holds the
code-level interdependence needed to decide (#155). The same source records conformity
cascades — identical context produces identical mistakes, and shared state is the vector — and
that a reviewer fed the author's summary converges on it, so the reviewer must see the diff
and the spec before any advocacy. Oversight patterns are unimplemented: asynchronous
monitoring is not separated from blocking intervention, gates ship no machine-readable "does
not cover" note, spawning does not narrow authority, and no gate can prove it is still alive
(#154). Mechanically, parallel waves in a shared tree collide on the pre-commit hook (#118)
and per-worktree baselines cause mass false re-baselining on integration (#133).

**There is no writing standard for the documents the flow produces.** One exists — in the
`tech-writer` core template — and it applies to the AS-IS space and to that one role. The three
other roles have none, and the TO-BE documents are written by whoever runs `/task-init`, by the
coordinator, and by dev and review updating CONTEXT. Templates supply *headings*, not
requirements on what a heading must contain: `- [ ] Criterion 1` asks for a criterion, never
for a measurable one. So whether a goal is measurable, a decision carries its reason, a risk
carries a real mitigation, or an approved document still hides a pending design question
depends entirely on who held the keyboard that day. This epic's own planning documents are the
evidence in both directions: they read well because a set of conventions was applied that is
written down nowhere and will not survive the session.

**Document shape is unchecked, in both spaces.** There is no template artifact for a domain
`README.md`, a feature `SPEC.md` or a component `DOC.md` — the skeleton is assembled from
string literals inside `onboarding/doc_generator.py`, so an adopter has nothing to adapt and we
have nothing to compose. Nor is the shape checked afterwards: `sync-check` compares hashes and
symbols (`hash_changed`, `symbols_changed`, `untracked_files`, `missing_modules`,
`surface_drift`) and none of them notice that a document lost a required section. The generator
sets the shape once, at creation, and nothing holds it. Drift is already visible in our own
three feature specs after three months and a single author — `API` and `Invariants` have
swapped order, `Constraints` appears in one of three — and the gate reports green throughout.
This is #161's shape one level up: the audit checks numbers inside a document, and nobody
checks that the document still has the sections it is supposed to have.

**The development-documentation space is invisible.** `.claude/development/` holds roughly
twice the volume of `docs/` and is indexed by nothing, so an agent cannot trace where a design
decision came from. Its location is also a naming lie: the planning space is not
Claude-specific, yet it lives under one vendor's directory.

> Evidence that the failure class is not confined to the product: while preparing this epic, an
> edit to the issue log itself destroyed ~1000 lines by computing a block boundary from a
> non-unique anchor and reporting success. Same shape — an operation that verified nothing and
> said it worked. The log is restored; the incident stays here because it is the argument.

## Impact

**The flow is a shipped product, not our local configuration.** `setup-agentic-flow` scaffolds
it into any repository, so every defect above reaches adopters. An adopter today receives a
process that asks for reviews, mutation gates and behavior specs, provides no mechanism for
any of them, gives their project nowhere to add its own rules, and includes advice that
silently reports success for work it did not do.

If this is not fixed: the flow's value stays proportional to the operator's vigilance, which
is exactly the property that does not scale to agents. Beadloom's whole thesis — that
architecture, contracts and documentation should be *checked*, not *asked for* — does not
apply to its own process. That is the gap this epic closes.

Second-order impact, in Beadloom's favour: **guard conditions and wave shape can be derived
from the graph.** "This diff touched a pure domain core, so a mutation note is required."
"This diff crossed a service boundary, so it stops for a human." "These two beads touch
independent subgraphs, so they may run in parallel." No generic hook snippet can do any of
that, because it does not know which file belongs to which node. This is the part only
Beadloom can build.

## Goals

- [ ] **G1 — Rules become mechanisms.** Every rule in the shipped `CLAUDE.md` is classified as
      (a) enforced by a guard, (b) covered by an existing gate, or (c) genuine judgment.
      Measurable: the shipped `CLAUDE.md` shrinks, and every line removed is attributable to a
      specific mechanism that replaced it — not to editing.
- [ ] **G2 — Enforcement is real, portable and side-effect free.** Guard conditions live in
      Beadloom as a CLI primitive usable by any harness; Claude Code hooks and the Cursor
      equivalent are thin adapters. Measurable: the same guard verdict from the CLI and from
      the hook, and **no guard mutates the state it inspects** — which requires closing #147.
- [ ] **G3 — Guards prove they are alive.** The flow can demonstrate that its guards fired.
      Measurable: a guard disabled or misconfigured is reported, not silent (#154).
- [ ] **G4 — Strictness is configurable per rule and per work kind**, defaulting to a loud
      warning that names what it did not check. Every exclusion carries a named reason and an
      exit condition. Measurable: an adopter's green project does not turn red on upgrade.
- [ ] **G5 — A project can extend the flow without breaking the guard.** `CLAUDE.md`, roles and
      commands are composed from a shipped core plus a project-owned overlay; the guard verifies
      the composition result rather than the file text; language and stack are configuration,
      not hardcoded; an upgrade preserves the project layer and does not orphan command files.
      Measurable: #139, #152, #132, #136 and #137 close.
- [ ] **G6 — Two rules disappear because the product stopped lying.** #142 and #146 are fixed,
      and the corresponding defensive instructions are deleted rather than reworded.
- [ ] **G7 — Acceptance criteria are executable.** Behavior-bearing work states its criteria as
      Gherkin scenarios that run; a scenario binds to a graph node and to a bead; a feature node
      with no scenario is a lint finding. Non-behavioral criteria remain checkboxes but are
      labelled as such, so the absence of a scenario is a stated decision. Mutation testing
      gates the strength of those tests on pure domain cores only. **Document shape is a
      checkable claim too:** every doc kind declares its required sections, a missing section is
      reported, and the templates become shipped artifacts with a project overlay rather than
      string literals in the generator — so a project can adapt the shape without forking it.
      **And so are the qualities that make a section useful:** a goal with no measurable clause,
      a decision with no reason, a risk with no mitigation, an approved document still carrying
      a pending open question, or a shipped template placeholder never filled in are all
      reported. What cannot be mechanised — tone, absence of filler, full sentences — becomes a
      **shared writing standard** applied by every role that writes a document, not by one, and
      configurable per language so a team is held to it in the language it writes in.
- [ ] **G8 — Both documentation spaces are first-class and named.** Doc roots are configurable.
      **TO-BE** (PRD / RFC / BRIEF / CONTEXT / PLAN) records intent; **AS-IS** (SPEC / DOC /
      README) records reality and is what `sync-check` holds against the code; **WORKING**
      (ACTIVE) is ephemeral progress state and is deliberately exempt from freshness, so it
      cannot pollute the statistics of any rule written for the other two. The TO-BE space is
      indexed and bound to beads, and the claim *"the intent recorded in TO-BE is reflected in
      AS-IS"* becomes checkable — note this is a relation between two artifacts, not one item
      changing status. Our own ROADMAP and issue log become instances of shipped kinds with
      computed facts, so a hand-written count can no longer be wrong.
- [ ] **G9 — Parallel work is shaped by the graph and safe in a shared tree.** What may run in
      parallel is decided from code-level interdependence rather than guessed; a reviewer sees
      the diff and the spec before any author summary; integration of parallel waves does not
      mass-falsify doc baselines. Measurable: #155 acted on, #118 and #133 close.

## Non-goals

- **Not a redesign of the rules.** The rules are right; they are unenforced. Rule content
  changes only where a mechanism replaces it or a role owns it.
- **Not a wiki, a tracker integration, or Confluence/Jira ingestion.** The spec space binds
  local, checkable claims; prose may live anywhere and is linked, not imported.
- **Not model-specific tuning.** No guard may depend on how compliant a given model is today —
  that is the variable which changes silently underneath us.
- **Not a portal redesign.** Portal views come last and only over data already honest.
- **Not mutation testing everywhere.** Pure domain cores only, deliberate per-slice runs, never
  in pre-commit.
- **Not auto-merge or autonomous escalation.** Guards stop work and inform; a human decides.
- **Not #91.** Its evidence is stale — the god-package it names was decomposed in BDL-059, the
  cycle comment is gone, the rule is `severity: error`, and a full reindex with `lint --strict`
  reports 0 violations on 12 rules. It closes as verified, with the caveat that this is the
  first result worth believing, because until #159 the cycle rule could not see nested imports.

## User Stories

### US-1: The flow is executed because it is enforced, not because it is remembered

**As** an engineer working through agents, **I want** the process rules executed by the
harness, **so that** compliance does not decay with session length or instruction count.

**Acceptance criteria** (scenarios — placement per RFC):
- [ ] `Scenario: Editing a file with no claimed bead is refused`
- [ ] `Scenario: Editing a file outside the claimed bead's scope is refused`
- [ ] `Scenario: Ending a turn with a red gate is refused`
- [ ] `Scenario: A guard reports what it did NOT check when it is configured to warn`
- [ ] `Scenario: A guard leaves the index unchanged` (read-only, #147)
- [ ] Non-behavioral: the same guard verdict is produced by the CLI and by the hook adapter

### US-2: A project extends the flow without forking it

**As** an adopter, **I want** to add my own rules to `CLAUDE.md`, roles and commands, **so
that** my project's hard-won practice survives an upgrade and does not disable the guard.

**Acceptance criteria:**
- [ ] `Scenario: A project overlay survives a flow upgrade`
- [ ] `Scenario: Drift in the shipped core is still detected while a project overlay exists`
- [ ] `Scenario: Suppressing a core rule requires a named reason and an exit condition`
- [ ] `Scenario: An overlay cannot silently override a core rule`
- [ ] `Scenario: A re-init across a major version reports orphaned command files` (#137)
- [ ] Non-behavioral: language and stack come from configuration, not from a hardcoded template

### US-3: Behavior is specified before it is built, and the specification runs

**As** a product or engineering reader, **I want** acceptance criteria expressed as executable
scenarios bound to the graph, **so that** "done" is demonstrated rather than asserted.

**Acceptance criteria:**
- [ ] `Scenario: A behavior-bearing bead without a scenario is reported`
- [ ] `Scenario: A scenario naming no bead is reported`
- [ ] `Scenario: A scenario referenced by a PRD but absent from the suite is reported`
- [ ] `Scenario: A chore declares itself non-behavioral with a named reason and is accepted`
- [ ] `Scenario: A mutation target outside the configured source paths is reported` — declaring
      a target that runs zero mutants is a gate that does not exist
- [ ] `Scenario: A document missing a section its kind requires is reported`
- [ ] `Scenario: A goal stated without a measurable clause is reported`
- [ ] `Scenario: A decision recorded without a reason is reported`
- [ ] `Scenario: A risk recorded without a mitigation is reported`
- [ ] `Scenario: An approved document still carrying a pending open question is reported`
- [ ] `Scenario: An unfilled template placeholder is reported` — scaffolded and abandoned is
      the same failure as documented and never wired
- [ ] Non-behavioral: the writing standard is shared by all four roles and is language-configurable
- [ ] `Scenario: A project overlay adds a required section without forking the shipped template`
- [ ] Non-behavioral: doc templates are files under `templates/`, not string literals in code

### US-4: An agent can see why the code is the way it is

**As** an agent picking up work, **I want** the development documentation indexed and bound to
the nodes I am touching, **so that** I do not confidently undo a decision I cannot see.

**Acceptance criteria:**
- [ ] `Scenario: The TO-BE space is indexed and searchable`
- [ ] `Scenario: An epic whose beads are closed but whose criteria never reached AS-IS is reported`
- [ ] `Scenario: A count stated in the issue log is computed, not written by hand`
- [ ] `Scenario: A WORKING document is exempt from freshness checks`
- [ ] Non-behavioral: our own ROADMAP and issue log validate against the shipped kinds

### US-5: The gate stops claiming work it did not do

**As** anyone trusting a green gate, **I want** the known false-green paths closed, **so that**
the defensive instructions written around them can be deleted.

**Acceptance criteria:**
- [ ] `Scenario: A boundary violation introduced after an incremental reindex is caught` (#142)
- [ ] `Scenario: A component node's documentation freshness is actually checked` (#146)
- [ ] `Scenario: A gate reports the checks it did not perform` (#154's "does not cover" note)
- [ ] Non-behavioral: the corresponding rules are removed from the shipped `CLAUDE.md`

### US-6: Parallel agents are scheduled by the graph, not by optimism

**As** a coordinator, **I want** the wave shape derived from code-level interdependence, **so
that** parallelism helps where the subgraphs are independent and is refused where they are not.

**Acceptance criteria:**
- [ ] `Scenario: Two beads touching independent subgraphs are allowed to run in parallel`
- [ ] `Scenario: Two beads touching the same node are serialised`
- [ ] `Scenario: A reviewer receives the diff and the spec without the author's summary` (#155)
- [ ] `Scenario: Integrating a parallel wave does not re-baseline untouched doc pairs` (#133)
- [ ] Non-behavioral: parallel agents no longer collide on the shared pre-commit hook (#118)

## Acceptance Criteria (overall)

- [ ] The shipped `CLAUDE.md` is measurably smaller, and every removed rule maps to the guard,
      role template, or product fix that replaced it — the mapping is recorded, not asserted.
- [ ] `beadloom ci` remains the single source of true enforcement; guards are a faster local
      catch and never the only line of defence.
- [ ] Adopters upgrading from 2.2.0 do not go red: new checks ship as warnings that name what
      they did not verify.
- [ ] Every guard is exercised by a test that proves it FAILS on the condition it guards —
      a guard that cannot be shown to bite does not ship.
- [ ] The flow's own rules are dogfooded: this epic is executed under the flow it builds, and
      the friction encountered is recorded as findings rather than worked around.
