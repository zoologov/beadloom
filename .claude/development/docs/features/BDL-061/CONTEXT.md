# CONTEXT: BDL-061 — Enforced agentic flow

> **Status:** Approved
> **Created:** 2026-08-22
> **Last updated:** 2026-08-23

---

## Goal

Turn the scaffolded multi-agent flow from prose the model may ignore into mechanisms the
harness executes, so that what the flow asks for is what actually happens — and so that what
remains in prose is short enough to survive a long session.

## Key Constraints

- **Tool-agnostic is non-negotiable.** No behaviour may exist only inside Claude Code. Guard
  conditions are a Beadloom CLI primitive; harness files are thin adapters over it.
- **`beadloom ci` remains the single source of true enforcement.** Guards are a faster local
  catch, never the only line of defence.
- **No adopter's green project turns red on upgrade.** New checks ship as `warn` and name what
  they did not verify.
- **Guards are read-only** with respect to the index they inspect.
- **No guard may depend on how compliant a given model is today.** That is the variable which
  changes silently underneath us.
- The flow is a **shipped product**: everything here reaches adopters via
  `setup-agentic-flow`, so defaults matter more than our own preferences.
- DDD layering holds; guards read the graph through the existing repository seam.
- One slice at a time, each merged to `main` on its own PR (sequencing principle 1).

## Code Standards

### Language and Environment
- **Language:** Python 3.10+ (type hints, `str | None` syntax)
- **Package manager:** uv
- **Virtual environment:** uv venv

### Writing standard (applies to every document this epic produces)

Held to the same bar the epic builds. Mechanised where possible (S4), prose where not:

- A goal carries an explicit measurable clause; "make it better" is not a goal.
- A decision carries its **reason**, and the reason explains *why*, never restates the decision.
- A risk carries a concrete mitigation; "monitor it" is not one.
- An open question states **both** sides of the trade-off, not only the chosen one.
- A non-goal names what was rejected **and why**.
- Claims carry numbers and the word *measured*, not adjectives.
- No filler section intros; headings are neutral and descriptive.
- Lines wrap around 95 columns so diffs stay reviewable.
- No template placeholder survives into an approved document.

### Methodologies

| Methodology | Application |
|-------------|-------------|
| TDD | Red → Green → Refactor; a test that cannot be shown to fail is not a test |
| BDD | Behaviour-bearing work states acceptance criteria as executable Gherkin scenarios |
| Mutation | Test strength on pure domain cores only; per slice; never in pre-commit |
| DDD | `services → application → domains → infrastructure`; one nameable responsibility per module |
| Clean Code | snake_case, SRP, DRY, KISS |

### Testing
- **Framework:** pytest + pytest-cov (+ pytest-bdd for acceptance scenarios)
- **Coverage:** minimum 80% on changed code
- **Every guard ships with a test that proves it FAILS on the condition it guards.**

### Code Quality
- **Linter:** ruff (lint + format)
- **Typing:** mypy --strict

### Restrictions
- No `Any` without justification
- No `print()` / `breakpoint()` — use logging
- No bare `except:` — only `except SpecificError:`
- No `os.path` — pathlib only
- No f-strings in SQL — parameterized queries `?`
- No `yaml.load()` — safe_load only
- **No structured-document edit by string-offset slicing** without asserting the anchor is
  unique — this epic's own preparation destroyed ~1000 lines of the issue log that way

## Architectural Decisions

| Date | Decision | Reason |
|------|----------|--------|
| 2026-08-22 | **A guard is data, not code in a hook.** Declared in `flow.yml`, evaluated by Beadloom, bound by a thin adapter | Portability, testability, and conditions phrased in terms of the graph — the only reason this belongs in Beadloom rather than a shell script |
| 2026-08-22 | **Strictness is per rule and per work kind; default `warn`** and the warning names what was not checked | An adopter who goes red on upgrade disables everything, and a disabled guard is worse than none |
| 2026-08-22 | **Every exclusion carries `reason` and `until`**; one with neither is a config error | An unnamed exclusion is how a gate is quietly switched off |
| 2026-08-22 | **`skip` is a first-class outcome and always says why** | A guard that silently does not apply is indistinguishable from one that passed |
| 2026-08-22 | **Guards are read-only**, which requires closing #147 first | A check that writes to the artifact it checks cannot be trusted about it |
| 2026-08-22 | **S2 (fix the lying checks) runs first** | S3's acceptance criterion is deleting the rules those bugs forced into the prose; it cannot be met earlier |
| 2026-08-22 | **`config-check` verifies the composition result, not file bytes** | Keeps drift detection while making project extension possible (#139, #152) |
| 2026-08-22 | **Overlays are append-only**; suppressing a core rule needs a named reason, an exit condition, and is itself reported | Silent override is a way to disable the gate without saying so |
| 2026-08-22 | **The `.feature` file is the source of truth; the PRD states intent and references it** (option б) | An executable artifact cannot silently lie; a generator between statement and executable becomes a synchronisation problem |
| 2026-08-22 | **Documentation spaces are TO-BE / AS-IS / WORKING**, not TODO/DONE | Nothing changes status: a PRD stays the record of intent while a *different* artifact (AS-IS) is updated. The checkable claim is a relation between two artifacts |
| 2026-08-22 | **WORKING (ACTIVE) is exempt from freshness by declaration** | It is neither intent nor reality; checking it against code is meaningless and would pollute every rule written for the other two |
| 2026-08-22 | **`beadloom waves` decides, it does not advise** | An advisory wave shape is the same failure this epic exists to remove; a human override is recorded as an exclusion |
| 2026-08-22 | **`.claude/development/` does NOT move in this epic** (Q4) | Indexing delivers the value immediately; moving paths mid-epic is a breaking change with no added signal. The vendor-directory naming problem is a separate, isolated step |
| 2026-08-22 | **Doc templates move from string literals into `templates/docs/`** and compose like roles | An adopter has nothing to adapt today, and nothing holds document shape after generation |
| 2026-08-22 | **The writing standard becomes shared and language-configurable**, composed into all four roles instead of living in `tech-writer` alone | The roles that produce TO-BE documents have no standard at all; and a team writing in Russian should be held to it in Russian (#136) |
| 2026-08-22 | **Section *qualities* are checkable, not only section presence** — measurable goal, decision with a reason, risk with a mitigation, no pending question in an approved doc, no unfilled placeholder | These planning documents read well because of conventions written down nowhere; a practice that is not a mechanism does not survive the session |
| 2026-08-22 | **Q1: the project overlay lives in `.beadloom/flow/`** (`roles/`, `commands/`, `claude/`) | It is flow *configuration* in Beadloom's schema and dies with the tool — unlike documentation, which must survive it |
| 2026-08-22 | **Q2: the guard registry lives in `application/guards/`** | Guards orchestrate domain reads to answer a process question — that is application-layer work. A separate domain would be premature until something outside the flow needs them |
| 2026-08-22 | **Q3: `.feature` default location is `tests/acceptance/{features,steps}/`, configurable from the start** | Matches the layout proven in the dogfood project; configurable because the flow ships to projects with their own conventions |
| 2026-08-22 | **Q5: the mutation tool is the project's choice; Beadloom ships the role duty, the scope convention and the check that a declared target is inside the configured source paths** | Owning a mutation runner is out of scope and would break tool-agnosticism; the failure worth catching is a declared target that runs zero mutants |
| 2026-08-22 | **#91 closes as verified, with the caveat that this is the first believable result** | Its evidence is stale (the god-package was decomposed in BDL-059) and `lint --strict` is clean — but only since #159 taught the cycle rule to see nested imports |

## Related Files

Discover via `beadloom ctx <ref-id>` — never hardcode. Primary refs for this epic:
`flow-config`, `role-composer`, `role-adapters`, `agentic-flow-setup`, `config-check`,
`ci-gate`, `reindex`, `sync-check`, `rule-engine`, `graph`, `infrastructure`, `cli-commands`,
and the new `flow-guards`.

## Standing Verification Rules

Carried from the dogfood project's hard-won section, because they apply to every role here and
each one is an incident, not a theory.

**Cite these by NAME, never by number.** Numbers are not stable: S2 retired three rules, so
every citation to a number has already shifted onto a different rule. The coordinator sent
briefs citing "rule 9" — which did not exist — where CLEAN-ROOM REVERT was meant; at least one
agent reported the mismatch instead of guessing, which is the only reason it was caught. Same
defect as BDL-UX #171: one identifier, two sources of truth.

1. **FAKES PROVE FAKES** — a test on a fake proves the fake's contract. Transport, git and
   subprocess need a test against the real thing.
2. **TESTS MUST BITE** — sabotage the fix and confirm the test reddens; and check the harness
   itself, because `ERROR` / `no tests ran` is not `FAILED`. Compare collected/passed NUMBERS,
   not colour, and name the tests that reddened. A sabotage that does NOT redden is data about
   the test, not reassurance about the code.
3. **REPORTS ARE NOT EVIDENCE** — an agent's report is not evidence. The coordinator
   re-verifies gates itself, on the final tree state.
4. **CLEAN-ROOM REVERT** — remove sabotage by reverse edit, never `git checkout <file>`; verify
   byte-identity by sha256. In a parallel wave, only pointwise: restoring a whole file next to a
   neighbour's active work erases it.
5. **NO CALLER, NO CAPABILITY** — a permission without a caller is not a capability. An
   allowlist entry, or a function nothing calls, reads as "the feature exists" (#160).
6. **ONE PLATFORM IS NOT VERIFIED** — a claim measured on one OS, one Python and one locale is
   true there and unknown everywhere else. CI caught two defects (`.36`) that a 5574-test local
   suite could not see, because the local suite varied coverage and not ENVIRONMENT. Where the
   environment cannot be arranged, construct the failure instead (`.37`'s ambient-codec double)
   rather than concluding it is absent.
7. **A GREEN COUNT IS NOT A CHECKED COUNT** — `12 rules, 0 violations` and `13 mentions fresh`
   were both partly vacuous while being literally true (#172, #173). Ask what fraction of the
   declared surface a green result actually covered, and make anything that cannot fire report
   itself. S2 fixed three NAMED checks (#142, #146, #147) and left the class open: `.6` measured
   seven further false-greens and `.7` an eighth, filed as #173, #174, #175 and beads `.45`–`.51`.

### Retired in S2

CLEAN-DB LINT, COMPONENT BLINDNESS and LINT WRITES are gone. Each was a workaround for a defect
that `.5` fixed, and each retirement was re-derived through the CLI by `.6` and again by `.7` in
a clean room rather than accepted from a report. Two of them leave a sentence instead of a rule,
and both sentences now live in the CLI reference (`docs/services/cli.md`, under `beadloom lint`
and `beadloom sync-check`), where a reader meets them rather than in an epic document that dies
with the epic: plain `beadloom lint` reindexes first and therefore writes the index, by design,
so the default never lints a stale graph; and `sync-check` names the pairs it could not check,
with the reason, so its count describes what was checked.

**The habit that outlived its rule is retired, and the tool no longer depends on it.** CLEAN-DB
LINT taught every role to verify on a freshly built database, which was right for `lint` and for
the test suite and vacuous for `sync-check`: a rebuild adopted the current tree as its own
baseline, so a clean-DB `sync-check` — and the `beadloom ci` around it — reported every pair
fresh by construction (BDL-UX #175, bead `.47`). Beads `.46`/`.47` moved the baseline out of the
database: a pair records where its baseline came from, one fabricated by a rebuild is
corroborated against git `HEAD`, and where git cannot answer the pair reads `unverified` rather
than fresh. A clean database is therefore no longer a way to get a green `sync-check`, and no
role instruction anywhere asks for one.

**One measurement is worth carrying past this epic**, because it shapes how a wave should be run:
`symbols_hash` is computed per `ref_id` over every symbol annotated to the node, so ONE new module
— or four new private helpers in one file — makes every pair of that node stale, including sibling
files nobody touched. Neither an incremental nor a full reindex clears it, by design. The only
fixpoint is to update the document and then `sync-update <ref> --yes`. In S2b that turned a
four-file change into 28 gate lines about one README, which is why the slice's staleness looked
larger than it was.

**What still costs something, and is stated rather than left to be rediscovered:** the git leg
compares the working tree against `HEAD`, so it catches drift a rebuild absorbed but does not
judge whether a long-committed doc still describes its code. `--since <ref>` answers that, and
an incremental reindex on an existing index keeps the stronger accumulated baseline. Prefer the
incremental path when one exists; it is now an optimisation, not a correctness requirement.

## Current Phase

- **Phase:** Development — S1 and S2 complete, S2b closing, S3 next (`.9`)
- **Current bead:** `.55`, the S2b documentation pass; live status is in ACTIVE.md and the tracker
- **Blockers:** none. `.42` (the locale legs' first run) is open, which is why the two
  `tests-locale` contexts are not yet part of `main`'s live protection — see ACTIVE.md
