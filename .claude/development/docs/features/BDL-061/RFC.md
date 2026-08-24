# RFC: BDL-061 — Enforced agentic flow

> **Status:** Approved
> **Created:** 2026-08-22

---

## Overview

Turn the scaffolded multi-agent flow from prose the model may ignore into mechanisms the
harness executes. The unit of change is a **guard**: a named, declarative condition evaluated
by Beadloom, invoked by whatever harness the project uses, returning a verdict the harness can
act on. Guards whose conditions are derived from the architecture graph are the part no
generic hook can replace.

Four consequences follow and are in scope: rules that become guards leave `CLAUDE.md`; rules
that exist only because a Beadloom check lies leave it once the check stops lying; rules that
belong to a role move into the role's template; and rules a project invents get a supported
place to live. What remains is short enough to survive a long session.

## Motivation

### Problem

See `PRD.md`. In one line: the flow is advisory, advisory flows are skipped (measured 0/6
beads reviewed while the one machine-checked rule blocked the agent four times), and the
places where a project could put its own rules, express its acceptance criteria, or trace a
decision either do not exist or are locked by a drift guard.

### Solution

A guard is *data*, not code in a hook. It is declared once, evaluated by Beadloom, and bound
to a harness by a thin adapter. That gives portability (any tool can call the CLI), testability
(a guard is exercised like any other check), configurability (strictness per rule and per work
kind), and — critically — the ability to phrase conditions in terms of the graph, which is the
only reason this belongs in Beadloom rather than in a shell script.

## Technical Context

### Constraints

- Python 3.10+, SQLite (WAL mode), mypy `--strict`, ruff.
- **Tool-agnostic is a hard requirement.** No behaviour may exist only inside Claude Code.
  Harness-specific files are adapters over a CLI primitive, never the primitive.
- **`beadloom ci` stays the single source of true enforcement.** Guards are a faster local
  catch and are never the only line of defence.
- **No adopter's green project may turn red on upgrade.** New checks ship as warnings that
  name what they did not verify.
- **Guards must be read-only** with respect to the index they inspect.
- DDD layering holds: `services → application → domains → infrastructure`. A guard reads the
  graph through the existing repository seam; it does not grow its own data access.
- The flow is a shipped product: everything here reaches adopters through
  `setup-agentic-flow`, so defaults matter more than our own preferences.

### Affected Areas

| Node | Source | Why |
|---|---|---|
| *(new)* `flow-guards` | `src/beadloom/application/guards/` | guard registry, evaluation, verdicts, liveness |
| `role-composer` | `onboarding/role_composer.py` | gains a project layer; generalised beyond roles |
| `role-adapters` | `onboarding/role_adapters.py` | per-tool emission for roles, commands, `CLAUDE.md` |
| `agentic-flow-setup` | `onboarding/agentic_flow_setup.py` | scaffolds guards + overlay skeleton; upgrade semantics |
| `config-check` | `onboarding/config_sync.py` | verifies the composition **result**, not file bytes |
| `flow-config` | `onboarding/flow_config.py` | strictness, language, stack, overlay paths |
| `ci-gate` | `application/gate.py` | runs guards; emits the "does not cover" note |
| `reindex` | `application/reindex/` | #142: refresh import edges incrementally |
| `sync-check` | `doc_sync/engine.py` | #146: `component` nodes get pairs |
| `rule-engine` | `graph/rules/` | `scenario-coverage` rule; wave-independence query |
| `graph` (linter) | `graph/linter.py` | #147: a read-only evaluation path |
| `infrastructure` | `infrastructure/` | configurable doc roots; guard-firing record |
| `cli-commands` | `services/commands/` | `beadloom guard`, `beadloom waves`, spec-space verbs |

## Proposed Solution

### Approach

**One primitive, six slices.** Everything below is an application of the same idea: *a rule is
a claim, and a claim must be checkable, bound to the graph, and honest about what it did not
check.*

**S1 — The guard primitive.**
`beadloom guard <name> [--json] [--context <k=v>...]` evaluates one declared guard and returns
a verdict `{guard, outcome: pass|warn|block|skip, why, not_covered[], remediation}`. Exit code
carries the outcome so a shell adapter needs no parsing. Guards are declared in
`.beadloom/flow.yml` with a strictness per work kind:

```yaml
guards:
  bead-claimed:
    on: edit
    strictness: { default: warn, epic: block, chore: off }
    exclusions:
      - path: "scripts/**"
        reason: "operational scripts are not bead-scoped"
        until: "BDL-0xx introduces a scripts node"
```

Every exclusion carries `reason` and `until` — an exclusion with neither is a config error, not
a convenience. `skip` is a first-class outcome and always reports *why*, because a guard that
silently does not apply is indistinguishable from one that passed.

**S2 — Guards stop lying, and the prose written around the lies is deleted.**
Fix #142 (incremental reindex re-extracts imports for changed files), #146 (`component` nodes
produce sync pairs), #147 (a read-only lint evaluation path so a guard never writes to the
index it inspects). Each fix is paired with the deletion of the corresponding defensive rule
from the shipped `CLAUDE.md`, and the deletion is the acceptance criterion — a fix that does
not let a rule go was not a fix.

**S3 — Composition with a project layer, for the whole flow.**
Generalise `compose_role` into `compose(core, architecture, stack, project)` and apply it to
roles, commands **and** `CLAUDE.md`. The project layer lives in `.beadloom/` (it is flow
configuration, in Beadloom's schema, and dies with the tool — unlike documentation, which must
survive it). `config-check` changes from "the file equals the shipped bytes" to "the file
equals the composition of its declared layers", so drift detection survives while extension
becomes possible. Overlays are **append-only**; suppressing a core rule requires a named
reason and an exit condition, and is itself reported. Language and stack move from hardcoded
template text into `flow.yml` (#136); a cross-major re-init reports orphaned command files
rather than silently skipping them (#137).

**S4 — Behavior is specified executably.**
Acceptance criteria become Gherkin scenarios; the `.feature` file is the source of truth
(decision: option (б) — the executable artifact cannot silently lie, so it holds the text, and
the PRD states intent and references it). A scenario declares its bead and its graph node in a
header comment, mirroring the discipline measured in the dogfood project (51/51 scenarios
referenced a bead). A new `scenario-coverage` rule reports a behavior-bearing node with no
scenario, and a scenario naming no bead. Mutation testing enters the role templates as the
strength check on the scenarios, scoped to pure domain cores only, run per slice, never in
pre-commit. Role templates gain the four duties currently stranded in the dogfood project's
`CLAUDE.md`.

Document **shape** joins document content as a checkable claim. Today the skeleton for a
domain `README.md`, a feature `SPEC.md` and a component `DOC.md` is assembled from string
literals in `onboarding/doc_generator.py`: an adopter has nothing to adapt, we have nothing to
compose, and nothing holds the shape after generation — `sync-check`'s five reasons all
compare content, never structure. The templates move out of code into `templates/docs/` and
run through the same composition as roles and commands (S3), so a project declares its own
required sections in an overlay instead of forking. A new staleness reason —
`missing_sections` — sits beside the existing five and ships as `warn`, because every adopter's
documentation predates the rule.

Beyond shape, the **qualities that make a section useful** become checkable where they can be.
These read the parsed markdown and cost little: a goal with no measurable clause, a decision
row with an empty reason, a risk row with no mitigation, an open question still `Pending` in a
document marked `Approved`, and a shipped template placeholder (`[Name]`, `Criterion 1`) left
verbatim. The last two are the sharpest — the first catches a plan approved with its design
still undecided, the second catches an artifact that was scaffolded, looks right, and was never
filled in, which is #140's family.

What cannot be mechanised — tone, absence of filler, full sentences, no translationese —
moves out of the `tech-writer` core template, where it applies to one role and one space, into
a **shared writing standard** composed into every role that writes a document. It is
language-configurable (#136): a team writing in Russian is held to the standard in Russian
rather than to an English text it must mentally translate.

**S5 — Both documentation spaces become first-class, and they are named.**
Doc roots become configuration rather than the hardcoded `project_root / "docs"`. Three
categories, because two do not fit the material:

- **TO-BE** — PRD, RFC, BRIEF, CONTEXT, PLAN. Intent: what the system is to become.
- **AS-IS** — SPEC, DOC, README. Reality: what it is. This is the space `sync-check` already
  holds against the code, which is precisely what "as-is" means.
- **WORKING** — ACTIVE. Ephemeral progress state, exempt from freshness by declaration; it is
  neither intent nor reality, and checking it against code is meaningless.

Deliberately *not* TODO/DONE: nothing changes status here. A PRD does not become "done" — it
stays the record of intent while a **different** artifact, the AS-IS doc, is updated to
describe the new reality. The checkable claim is therefore a relation between two artifacts —
*"the intent recorded in TO-BE is reflected in AS-IS"* — and an epic whose beads are closed but
whose criteria never reached AS-IS is reported. In prose the same distinction is the product's
existing "intent vs reality" voice; in configuration it is `to_be` / `as_is` / `working`.

Our own ROADMAP and issue log become instances of shipped kinds with **computed** facts, which
is what removes hand-written counts that can be — and were — wrong.

**S6 — Parallel work is shaped by the graph.**
`beadloom waves <bead>...` answers which beads touch independent subgraphs and may run
concurrently, and which must serialise. Review receives diff and spec without the author's
summary. Integration of a parallel wave stops mass-falsifying doc baselines (#133), and
parallel agents stop colliding on the shared pre-commit hook (#118).

**Liveness runs through all six.** Each guard evaluation appends a record; `beadloom guard
--liveness` reports guards that have never fired, are misconfigured, or are excluded
everywhere. A gate that cannot demonstrate it ran is treated as not having run.

### Changes

| File / Module | Change |
|---|---|
| `application/guards/` *(new)* | registry, evaluation, verdict model, firing record, liveness |
| `services/commands/` | `beadloom guard`, `beadloom guard --liveness`, `beadloom waves` |
| `onboarding/flow_config.py` | `guards:`, `language:`, `stack:`, `overlays:` keys |
| `onboarding/role_composer.py` | generalised composition incl. a project layer |
| `onboarding/role_adapters.py` | emit roles, commands and `CLAUDE.md` per tool |
| `onboarding/config_sync.py` | verify composition result; report suppressed core rules |
| `onboarding/agentic_flow_setup.py` | scaffold guards + overlay skeleton; orphan reporting |
| `application/gate.py` | run guards; emit the machine-readable "does not cover" note |
| `application/reindex/indexing.py` | re-extract imports for changed files (#142) |
| `doc_sync/engine.py` | sync pairs for `component` nodes (#146) |
| `graph/linter.py` | read-only evaluation path (#147) |
| `graph/rules/` | `scenario-coverage`; subgraph-independence query for waves |
| `infrastructure/` | configurable doc roots; guard-firing store |
| `templates/roles/**`, `templates/agentic_flow/**` | BDD + mutation duties; core `CLAUDE.md` shrinks |
| `templates/docs/**` *(new)* | SPEC / DOC / README skeletons move out of `doc_generator.py` into composable template files |
| `templates/roles/core/_writing.md.txt` *(new)* | the shared writing standard, composed into all four roles, language-selectable |
| `onboarding/doc_generator.py` | render from templates instead of string literals |
| `.claude/commands/templates.md` | acceptance criteria become scenarios; BRIEF gains a named non-behavioral decision |

### API Changes

- **New CLI:** `beadloom guard <name>`, `beadloom guard --liveness`, `beadloom waves`.
- **New config keys** in `.beadloom/flow.yml`: `guards`, `language`, `stack`, `overlays`.
- **New config key** in `.beadloom/config.yml`: `doc_roots` (the current `docs/` remains the
  default, so existing projects are unaffected).
- **Changed semantics:** `config-check` compares a composition result rather than file bytes.
  This is the one genuinely breaking change for an adopter who hand-edited a vendored file —
  handled by reporting, not by rewriting (see Risks).
- **New rule type:** `scenario-coverage`, shipped as `warn`.

## Alternatives Considered

### Option A: Write better instructions

Rejected on evidence. Compliance degrades with instruction count and session length, and the
one machine-checked rule outperformed thirty prose rules in the same session. This is the
alternative that has already been tried, at length, by the person requesting the epic.

### Option B: Claude Code hooks only, no CLI primitive

Simpler and faster to build. Rejected because it makes the flow's enforcement exist only
inside one vendor's harness, which contradicts the standing tool-agnostic requirement and
would have to be rebuilt for Cursor. The adapter pattern already proved itself in BDL-052.

### Option C: PRD embeds Gherkin; `.feature` files are generated from it

Matches "acceptance criteria *are* the scenarios" most literally. Rejected: it introduces a
generator between the statement and the executable, and a generator nobody fully trusts
becomes a synchronisation problem. Option (б) keeps the executable file authoritative and
checks the binding in both directions instead.

### Option D: Split into two epics (enforcement; spec space)

Considered and rejected by the owner: the parts share one mechanism, and splitting risks two
half-products with a seam between them. Mitigated by sequencing — one slice at a time, each
merged to `main` on its own PR, exactly as BDL-060 ran. If a slice proves to be an epic in its
own right, that is reported rather than absorbed.

### Option E: Move `docs/` under `.beadloom/`

Rejected. The test is: remove Beadloom tomorrow, and documentation must survive as ordinary
markdown in a conventional, visible place. `.beadloom/` holds what dies with the tool. Only
flow *configuration* — including the project overlay — belongs there.

## Risks

| Risk | Probability | Impact | Mitigation |
|---|---|---|---|
| Guards are too strict; adopters disable the lot | Med | High | Warn-by-default; strictness per rule and work kind; every exclusion named with an exit condition; a disabled guard is *reported*, not silent |
| CLI verdict and hook verdict diverge | Med | High | One implementation, thin adapters; a test asserts identical verdicts from both paths |
| #142 fix makes incremental reindex slow | Med | Med | Re-extract imports only for changed files; measure before/after and record the number rather than claiming "fast" |
| `config-check` semantic change breaks adopters who hand-edited a vendored file | High | Med | Detect the case explicitly and report it as "hand-edited, not composed" with migration guidance; never rewrite the file (that was #151's destructive `--fix`) |
| The epic is large and stalls mid-way | Med | High | Slices are independently shippable; S1–S3 alone deliver the owner's core request; a slice that grows into an epic is surfaced, not absorbed |
| Scenario coverage becomes ceremony on non-behavioral work | Med | Med | `warn` severity; a named non-behavioral decision is a first-class, accepted answer |
| A guard-firing store becomes stale state nobody trusts | Low | Med | It is derived, wipeable, and never an input to correctness — only to the liveness report |

## Open Questions

| # | Question | Decision |
|---|---|---|
| Q1 | Where exactly does the project overlay live — `.beadloom/roles/`, `.beadloom/flow/`, or keyed inside `flow.yml`? | **Decided 2026-08-22: `.beadloom/flow/`** (`roles/`, `commands/`, `claude/`) — it is flow *configuration* in Beadloom's schema and dies with the tool, unlike documentation, which must survive it. Shipped in S3. |
| Q2 | Does the guard registry live in `application/guards/` or as its own domain? | **Decided 2026-08-22: `application/guards/`** — guards orchestrate domain reads to answer a process question, which is application-layer work; a separate domain would be premature until something outside the flow needs them. Shipped in S1. |
| Q3 | Default `.feature` location for adopters — `tests/acceptance/{features,steps}/`, or configurable from the start? | **Decided 2026-08-22: both** — that default, configurable from the start, because the layout is proven downstream but the flow ships to projects with their own conventions. Shipped in S4. |
| Q4 | Does `.claude/development/` move in this epic (and where), or does it stay and only become a configured doc root? | **Decided: it stays.** Indexing delivers the value immediately; moving paths mid-epic is a breaking change for us with no added signal. The naming problem (`.claude/` is a vendor directory) is recorded for a later, isolated move. |
| Q5 | Mutation tool: adopt `mutmut` and ship it as an optional extra, or leave the tool to the project? | **Decided 2026-08-22: the project's choice** — Beadloom ships the role duty, the scope convention and the check that a declared target lies inside the configured source paths. Owning a runner would break tool-agnosticism; the failure worth catching is a declared target that runs zero mutants. Shipped in S4. |
| Q6 | Does `beadloom waves` decide, or advise? | **Decided: it decides.** An advisory wave shape is the same failure this epic exists to remove. A human override is possible but is recorded as an exclusion with a named reason and an exit condition, like every other suppression. |
| Q7 | Slice order — is S2 (fix the lying checks) first, since S3 cannot delete the rules until it lands? | **Decided: S2 runs first.** S3's acceptance criterion is the deletion of the rules those bugs forced into the prose, so it cannot be met before S2 lands. |
