# PRD: BDL-061 — Enforced agentic flow

> **Status:** Draft
> **Created:** 2026-08-21

---

## Problem

The multi-agent flow Beadloom scaffolds is **advisory**, and advisory flows are silently
skipped. This is measured, not suspected.

**Measured on a real project run through the scaffolded flow** (BDL-UX #153): 0 of 6 beads
reviewed, 1 of 6 mutation-gated, 0 `.feature` files written, 0 `/task-init` invocations —
while the ONE rule backed by a machine check blocked the agent **four times in the same
session**. The owner did not work around the rules; he demanded the harness follow them.
The rules were right. The enforcement was absent.

The root cause is structural, not a discipline failure. `CLAUDE.md` arrives as context the
model may deem inapplicable, and instruction-following degrades as the file grows and the
session lengthens — so the rules are least effective exactly when a long session needs them
most (#156, context rot). Adding more prose makes it worse.

Four further defects compound it:

**Prose is the only place a project can put its own rules.** All eight shipped flow files
(`.claude/agents/*`, `.claude/commands/*`) are byte-identical between our repo and the
dogfood project — verified. The drift guard works, and *that is why nothing project-specific
could go in.* The dogfood project's four role-specific duties (dev writes behavior expressible
as `.feature`; test writes them plus a mutation gate; review checks behavior coverage;
tech-writer treats scenarios as living docs) and its coordinator-specific verification rules
all ended up in the one file it could edit — `CLAUDE.md`. Role rules became global prose,
which is precisely the form context rot destroys. There is no supported place for a project's
own additions (#152), and `setup-agentic-flow --force` corrupts the file when it tries (#132).

**Some of the prose exists only because Beadloom lies.** The dogfood project's standing
verification section opens with two rules that are workarounds for our own open bugs:
`beadloom lint` must be run on a wiped database because incremental reindex does not refresh
import edges (#142 — a module cycle passed through an entire verification pass including an
independent re-check, and was found a day later by accident), and `sync-check` reports
"clean" for `component` nodes because no pairs exist for them (#146). A user had to write
defensive instructions because the gate reports green having checked nothing.

**Acceptance criteria bind to nothing.** The PRD template ships `- [ ] Criterion 1` — free
prose, verified by a human ticking a box. Every neighbouring artifact is machine-checked: the
graph binds code to docs and checks freshness, beads bind work into a gated DAG, `beadloom ci`
checks lint, sync and prose facts. The criterion — the statement of what the work must
achieve — is the weakest link in the chain, and BDD/Gherkin appears in **zero** of our
templates, role templates and command templates (verified).

**The development-documentation space is invisible.** `.claude/development/` holds roughly
twice the volume of `docs/` and is indexed by nothing, so an agent cannot trace where a design
decision came from. Its location is also a naming lie: the planning space is not
Claude-specific, yet it lives under one vendor's directory.

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

Second-order impact, in Beadloom's favour: hook conditions can be **derived from the graph**.
"This diff touched a pure domain core, so a mutation note is required." "This diff crossed a
service boundary, so it stops for a human." No generic hook snippet can do that, because it
does not know which file belongs to which node. This is the part only Beadloom can build.

## Goals

- [ ] **G1 — Rules become mechanisms.** Every rule in the shipped `CLAUDE.md` is classified as
      (a) enforced by a guard, (b) covered by an existing gate, or (c) genuine judgment.
      Measurable: the shipped `CLAUDE.md` shrinks, and every line removed is attributable to a
      specific mechanism that replaced it — not to editing.
- [ ] **G2 — Enforcement is real and portable.** Guard conditions live in Beadloom as a
      CLI primitive usable by any harness; Claude Code hooks and the Cursor equivalent are thin
      adapters. Measurable: the same guard verdict from the CLI and from the hook.
- [ ] **G3 — Guards prove they are alive.** The flow can demonstrate that its guards fired.
      Measurable: a guard disabled or misconfigured is reported, not silent.
- [ ] **G4 — Strictness is configurable per rule and per work kind**, defaulting to a loud
      warning that names what it did not check. Every exclusion carries a named reason and an
      exit condition. Measurable: an adopter's green project does not turn red on upgrade.
- [ ] **G5 — A project can extend the flow without breaking the guard.** `CLAUDE.md`, roles and
      commands are composed from a shipped core plus a project-owned overlay; the guard verifies
      the composition result rather than the file text. Measurable: an upgrade preserves the
      project layer; #152 and #132 close.
- [ ] **G6 — Two rules disappear because the product stopped lying.** #142 and #146 are fixed,
      and the corresponding defensive instructions are deleted rather than reworded.
- [ ] **G7 — Acceptance criteria are executable.** Behavior-bearing work states its criteria as
      Gherkin scenarios that run; a scenario binds to a graph node and to a bead; a feature node
      with no scenario is a lint finding. Non-behavioral criteria remain checkboxes but are
      labelled as such, so the absence of a scenario is a stated decision.
- [ ] **G8 — The development-documentation space is first-class.** Doc roots are configurable;
      the TOBE space (PRD/RFC/PLAN/ACTIVE/BRIEF) is indexed, bound to beads, and the TOBE → DONE
      transition is checkable. Our own ROADMAP and issue log become instances of shipped kinds.

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

## User Stories

### US-1: The flow is executed because it is enforced, not because it is remembered

**As** an engineer working through agents, **I want** the process rules executed by the
harness, **so that** compliance does not decay with session length or instruction count.

**Acceptance criteria** (scenarios — see `RFC` for placement):
- [ ] `Scenario: Editing a file with no claimed bead is refused`
- [ ] `Scenario: Editing a file outside the claimed bead's scope is refused`
- [ ] `Scenario: Ending a turn with a red gate is refused`
- [ ] `Scenario: A guard reports what it did NOT check when it is configured to warn`
- [ ] Non-behavioral: the same guard verdict is produced by the CLI and by the hook adapter

### US-2: A project extends the flow without forking it

**As** an adopter, **I want** to add my own rules to `CLAUDE.md`, roles and commands, **so
that** my project's hard-won practice survives an upgrade and does not disable the guard.

**Acceptance criteria:**
- [ ] `Scenario: A project overlay survives a flow upgrade`
- [ ] `Scenario: Drift in the shipped core is still detected while a project overlay exists`
- [ ] `Scenario: Suppressing a core rule requires a named reason and an exit condition`
- [ ] `Scenario: An overlay cannot silently override a core rule`

### US-3: Behavior is specified before it is built, and the specification runs

**As** a product or engineering reader, **I want** acceptance criteria expressed as executable
scenarios bound to the graph, **so that** "done" is demonstrated rather than asserted.

**Acceptance criteria:**
- [ ] `Scenario: A behavior-bearing bead without a scenario is reported`
- [ ] `Scenario: A scenario naming no bead is reported`
- [ ] `Scenario: A scenario referenced by a PRD but absent from the suite is reported`
- [ ] `Scenario: A chore declares itself non-behavioral with a named reason and is accepted`

### US-4: An agent can see why the code is the way it is

**As** an agent picking up work, **I want** the development documentation indexed and bound to
the nodes I am touching, **so that** I do not confidently undo a decision I cannot see.

**Acceptance criteria:**
- [ ] `Scenario: The spec space is indexed and searchable`
- [ ] `Scenario: An epic whose beads are closed but whose criteria never reached the DONE space is reported`
- [ ] Non-behavioral: our own ROADMAP and issue log validate against the shipped kinds

### US-5: The gate stops claiming work it did not do

**As** anyone trusting a green gate, **I want** the two known false-green paths closed, **so
that** the defensive instructions written around them can be deleted.

**Acceptance criteria:**
- [ ] `Scenario: A boundary violation introduced after an incremental reindex is caught` (#142)
- [ ] `Scenario: A component node's documentation freshness is actually checked` (#146)
- [ ] Non-behavioral: the corresponding rules are removed from the shipped `CLAUDE.md`

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
