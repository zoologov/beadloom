# CONTEXT: BDL-061 — Enforced agentic flow

> **Status:** Approved
> **Created:** 2026-08-22
> **Last updated:** 2026-08-24

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
| 2026-08-24 | **A classification carries a `reason` and deliberately no `until`** (`.13` decision 7, written back here by `.16` after review `.15` m4 measured that it never was), refining the row above | `until` is an exit condition for a DEBT, and `non_behavioural` is not a debt: a vocabulary module does not become behaviour-bearing on a calendar date, so a mandatory date would be a date nobody can choose honestly and every entry would carry a fiction. What keeps the classification from becoming the quiet switch-off the row above forbids is a different mechanism: a declaration that excuses nothing is itself a finding, and a live one prints how many of how many nodes it excused, so the denominator cannot shrink in silence. `for.exclude`, which carries neither a reason nor a report, is REJECTED on that rule type for exactly the reason the row above gives |
| 2026-08-22 | **`skip` is a first-class outcome and always says why** | A guard that silently does not apply is indistinguishable from one that passed |
| 2026-08-22 | **Guards are read-only**, which requires closing #147 first | A check that writes to the artifact it checks cannot be trusted about it |
| 2026-08-22 | **S2 (fix the lying checks) runs first** | S3's acceptance criterion is deleting the rules those bugs forced into the prose; it cannot be met earlier |
| 2026-08-22 | **`config-check` verifies the composition result, not file bytes** | Keeps drift detection while making project extension possible (#139, #152) |
| 2026-08-22 | **Overlays are append-only**; suppressing a core rule needs a named reason, an exit condition, and is itself reported | Silent override is a way to disable the gate without saying so |
| 2026-08-23 | **Append-only is a property of the BYTES, and the project layer is named rather than judged** (`.57`, correcting the row above, which review `.11` measured false) | The core text cannot be deleted; a fragment may still CONTRADICT it in prose, and whether it does is not decidable — "Pair on migrations" and "Do NOT run `beadloom ci`" are the same to any checker. What is decidable is that a layer is in effect, so `config-check` reports it at `warn`. Suppressions are now checked for existence and expiry, so the promise the row above makes is kept where it can be |
| 2026-08-23 | **A composed artifact is a function of its inputs and of nothing else — no clock** (`.57`) | It is the entire licence for `config-check` to compare against a composition rather than stored bytes, and `composer.py` asserted it while `describe()` denied it. Measured by review `.11`: one dated suppression took an untouched repository from 0 findings / exit 0 to 9 errors / exit 1 three days later, under a reason naming three causes that had not occurred. Expiry moved to check time, where CONTEXT already said it belonged |
| 2026-08-23 | **Absence is not evidence: nothing an editor deletes may make a check quieter** (`.57`) | `rm .beadloom/flow-manifest.json` downgraded a hand edit from `error` to `warn` (exit 1 → 0) and `rm .claude/agents/dev.md` switched the flow checks off for every other file, silently. Ownership now rests on two independent signals and every deletion is itself a finding — the same equation as BDL-UX #174, and `unverified` is `sync-check`'s word (`.46`/`.47`) rather than a second vocabulary |
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
| 2026-08-23 | **A composed artifact's write is fingerprinted** (`.beadloom/flow-manifest.json`), and `config-check` reports four states — clean / stale / hand-edited / unmanaged | The composition-result rule alone cannot tell "the shipped core moved" from "a human edited this file", and the two need opposite treatments. Without the fingerprint the check must either rewrite somebody's only copy of an intent, or stop reporting it |
| 2026-08-23 | **Severity follows the state**: hand-edited is an `error` whose remedy is to MOVE the edit; `unverified` is a `warn` | Keeps enforcement no weaker than before (the drift-guard's job did not change, only its remedy) while honouring "no adopter's green project turns red on upgrade" — a repo that predates the manifest genuinely cannot be judged. **The other direction, stated because the original rationale did not** (review `.11` MAJOR 5): `unverified = warn` also turns some RED projects green. A repo that hand-edited a role file before this release has no manifest entry for it, so what used to block now warns — exactly the #139/#151 population this slice exists to serve. `.57`'s manifest-presence rule largely closes it: once a project has a manifest at all, a file missing from it is not "pre-manifest", it is unaccounted for |
| 2026-08-23 | **A downgrade across an upgrade is itself a finding** — a severity reduced for want of evidence carries `weakened_from` and is stated with a count and a remedy; the exit code does not change, and nothing is recorded to compute it (`.58`) | The standing constraint ran one way; review `.11` measured the other. A red is loud and correlates with the release, a downgrade is silent — the project was correctly failing, now passes, and the evidence is gone. Making it BLOCK would be the red-on-upgrade the constraint forbids, so what it needed was to be said; recording a verdict history would make `config-check` a writer, which is #147/#189 |
| 2026-08-23 | **A fact rendered about the adopter is READ from the adopter, or not rendered** — unknown is `None` and the bullet is omitted; no fact computed about Beadloom appears in an artifact composed for somebody else (`.58`) | #183: the version line read TRUE here by coincidence and was false everywhere else, and four slices of review passed over it. The rule is enforced by rendering fixtures that are not Beadloom, because the reason it survived is that we had never rendered a project we could not be accidentally right about |
| 2026-08-23 | **The scaffold RECORDS the selection it composed from** (`.beadloom/flow.yml`, written once, never over an existing one) (`.58`) | A configuration resolved in memory is invisible to every later check: a virgin scaffold left `config-check` at exit 1 on an untouched repo (#187), and `scaffold()` re-resolving from disk meant `--architecture` reached the role adapters and not `CLAUDE.md`. The file the feature is configured by should be on disk |
| 2026-08-23 | **The `CLAUDE.md` body is checked only when the file is Beadloom's** — a manifest entry or the `<!-- beadloom:composed` stamp | A project's own hand-written `CLAUDE.md` is not ours to police; without this boundary the new check reintroduces the #73 false-positive class on every repo that never scaffolded |
| 2026-08-23 | **`sync_agentic_flow` no longer snapshots `CLAUDE.md` or the commands** — the shipped core is authored package data and the live file is composed from it | #177 is a loop, not an instance: enforcing *template == our file* in one direction makes the distributed artifact unable to differ from one project's local text, and any correction survives exactly until the next run. Reversing the direction also removes #132 by construction |
| 2026-08-24 | **When a document's kind and its space's roots disagree, kind wins and the disagreement is itself a finding** (`.77`, closing review `.19` M1) | Three rounds of review counted this repository's population correctly and none of them saw the hole, because Beadloom's own stems agree with its own roots; the reviewer found it by planting a `README.md`-only planning directory. Kind must keep winning — `ACTIVE.md` lives inside the TO-BE tree, so a root-first answer would exempt nothing — but a classifier that overrules a project's own roots in silence put the document in NO population: found by one glob, rejected by one classifier, looked for by nobody. The rule is now arithmetic rather than a list of patched cases: `sum(populations) == |files any declared root matched|` on any tree, and `document_outside_declared_root` names what kind overruled which space. A space that declares no root states nothing about where its documents live and contradicts nothing, which is why the shipped `ACTIVE.md` layout stays silent |
| 2026-08-24 | **An exclusion answers for each half a project declared, not for the declaration as a whole** (`.77`, closing review `.19` M2), and `_KIND_PRECEDENCE` is a decision separate from the report's reading order | Liveness asked of a whole declaration is answered by its luckiest half: one `ACTIVE.md` made a `kinds: [ACTIVE, SPEC]` line covering 39 `SPEC.md` files report nothing at all, and the `SPEC` half had already been beaten by AS-IS's DEFAULT list because `space_of_kind` walked `SPACES` — the order a report reads best, asked to double as a classification precedence. The vocabulary is the one this codebase already has twice (`rules_inert` qualifying lint's count, and the suppressed count printed on every run) rather than a third: `working_reach` prints how many documents each declared half excused, so a single configuration line that switches freshness off for 39 documents has to print the number 39 |
| 2026-08-24 | **A count is carried from the step that measured it, never recomputed by the step that prints it** (`.77`, closing review `.19` M3) | One tree reported `exempt: 0` from `sync-check --json` and `55 WORKING document(s) exempt` from the doc-spaces line, because one word named two populations — documents in the exempt space, and sync pairs the exemption excused. Naming them apart is half the repair; the other half is that `beadloom ci` hands its sync-check step's own number to the doc-spaces step (`GateStep.pairs_excused`), so the two lines cannot drift, and `beadloom docs spaces`, which runs no freshness check, states `null` and makes no pair claim it did not measure |
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
8. **CAPTURE, DON'T RE-RUN** — when a run reports a failure, read the name out of *that* run's
   output. Re-running to inspect it destroys the identity of anything intermittent, and an
   intermittent failure is the one most worth naming. The coordinator did this three times in
   one session before writing it down; each time the finding evaporated. Save the output to a
   file and read the file.
9. **TRUE HERE IS NOT TRUE** — a fact that is correct on this repository *by coincidence* reads
   as verified by every check, review and dogfood run. Every adopter's `CLAUDE.md` stated
   Beadloom's version as the project's own for four slices, because we *are* Beadloom (#183).
   Prove anything adopter-facing against `tests/adopter_project.py`, never against this tree.

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

## What S3 delivered, and what it did not

S3 delivered the request it was written for. `CLAUDE.md` is composed from
`core → architecture → stack → project`; the core measures **440 → 376 lines** with every
removed line mapped to its replacement; a non-Python adopter's core carries no Python command
to run; and the project layer lives in `.beadloom/flow/`, outside every file Beadloom writes,
so it survives an upgrade. `config-check` verifies the composition result, the flow manifest
tells Beadloom's own output from a hand edit, and a suppression carries a reason, an exit
condition and a report.

Three limits are stated in the shipped documentation rather than omitted, because each is a
property of the design and not a bead waiting to be done:

- **The floor on ownership is visibility, not blocking.** Deleting the manifest *and* stripping
  the provenance stamp downgrades the `CLAUDE.md` body from `error` to `warn`. Every ownership
  signal is in band — it lives in the repository the editor is editing — so any of them can be
  deleted. What is guaranteed is that the deletion is visible and the file is named. Raising
  the floor needs a signal from outside the repository, and Beadloom has none.
- **The project layer's prose is not judged.** A fragment may stand a core rule down without
  the reason, exit condition or notice `overlays.suppress` requires. That is a real hole in
  "the guard cannot be silently disabled", it is not decidable by any checker, and an adopter
  meets it in the guide rather than discovering it.
- **`CLAUDE.md` rendered Beadloom's version as the adopter's own** (BDL-UX #183) — **closed in
  S3b by `.58`**, together with four more facts computed about us and rendered about them (a
  constant `DDD` architecture label, a stack vocabulary that was our own dependency list, our
  Python floor, and a package scan that looked for `src/beadloom/` in the adopter's tree), the
  template seed that shipped our nine packages and our version, and — the largest of them —
  `doctor`'s audit of an adopter's `CLAUDE.md` against **our** version, packages, stack and test
  framework. The durable part is `tests/adopter_project.py`: non-Beadloom fixtures rendered in
  tests, because the reason this survived four slices is that we had never rendered a project we
  could not be accidentally right about.

Three further defects were **measured by the tech-writer bead `.12`**, all in the command layer
rather than in the composition, all filed and routed to `.58`:

| # | Measured | Route |
|---|----------|-------|
| BDL-UX #186 | `config-check --fix` rewrites a hand edit in a role adapter byte-identically to the scaffold (sha256), one line after the check printed *"It will NOT be rewritten"* | **closed, `.59`** |
| BDL-UX #187 | A virgin `setup-agentic-flow` without a `flow.yml` leaves `config-check` at exit 1 with four errors; writing a `flow.yml` gives rc 0 | **closed, `.58`** — the scaffold records the selection it resolved; the fix also exposed `--architecture`/`--stack` never reaching the commands or `CLAUDE.md` |
| BDL-UX #188 | `ScaffoldResult.orphans` and `.migration_notes` are computed on every scaffold and have **no caller** — #137's orphan report and S3's migration guidance reach a library caller, not the terminal | **closed, `.58`** — printed; `(hand-edited; use --force)` replaced by the migration note |
| BDL-UX #189 | `sync-update <doc> --check` re-baselines the doc it was asked to report on | **closed, `.58`** — the guard runs before the branch; a read-only `describe_reference_doc` answers it |

### Review `.11`'s minors, routed

Recorded so none is silently dropped. The two that were documentation are fixed in `.12`.

| Minor | Kind | Disposition |
|-------|------|-------------|
| m1 — `gate._config_finding`'s docstring names `hand_edited` where it means `unmanaged` | code (a docstring in `src/`) | `.58` |
| m2 — PLAN's "not a single Python command" is falsified by grep | **documentation** | **fixed in `.12`**: PLAN now carries the re-derived claim and the two surviving references, one of which is the pointer that replaced the command. The residue in the role-description table is a template edit and is `.58`'s |
| m3 — `repository.py` performs string surgery on a SQL fragment | code | `.58` |
| m4 — a `source` naming a nonexistent path reports `no_indexed_code` | code | `.58` |
| m5 — the emitted guard adapter has no `PATH` fallback | code | `.58` |
| m6 — an unreadable managed artifact is indistinguishable from a clean one | code | `.58` |
| m7 — the tracked-write guard attributes a failing test's write to the next test | code (tests) | `.58` |
| m8 — `onboarding` is now the largest bounded context (14 `part_of` children, 31 modules) | judgement, not a defect | Carried to S4 as the signal `domain-size-limit` cannot give, per BDL-UX #158. Not acted on here |
| n1 — three blank lines in `attribution.py` | code | `.58` |
| n2 — an over-long line in the flow-guards SPEC | **documentation** | **fixed in `.12`** |

Review `.11`'s **red-turns-green-on-upgrade** finding (MAJOR 5) was recorded as documentation
and closed in `.12`; **`.58` decided the question the prose left open** and gave it a mechanism.

> **A downgrade across an upgrade is itself a finding.** An upgrade that WEAKENS a verdict is
> worse than one that strengthens it: a red is loud and the adopter correlates it with the
> release, while a downgrade is silent — a project that was correctly failing now passes, nobody
> is told, and the evidence it ever failed is gone.

Every severity Beadloom reduced *for want of evidence* now carries `ConfigDrift.weakened_from`,
and `config-check` states the count and the command that restores the blocking verdict, on the
passing path as well as the blocking one. Two properties are deliberate: the **exit code does not
change** (a `warn` must not block, or fixing the silence would itself be the red-on-upgrade the
constraint forbids), and **nothing is recorded** — the downgrade follows from the finding's own
state rather than from a stored verdict history, because a check that writes on every run to keep
one would be BDL-UX #147/#189 in the command whose job is to look without touching.

## What S4 delivered, and what it did not

S4 delivered the owner's second original request: acceptance criteria are executable Gherkin,
and the shape and quality of a planning document are checkable claims rather than conventions
written down nowhere. Measured on this repository with `--json` and exit codes, 2026-08-24:

- `scenario-coverage` reports **68** findings — 35 `feature` nodes with no bound scenario and 33
  scenarios our own PRD names that do not exist. The population is the honest one
  (`for: {kind: feature}` selects all 40 declared feature nodes, 5 of them covered); a hand-picked
  list would report
  0 by construction. Repointing `features:` at a directory that does not exist takes the number
  to **1**, and that 1 is the liveness finding naming the dead glob — the proof the rule cannot
  be silently zeroed by moving a path.
- The 19 scenarios in 6 `.feature` files **run** under `pytest-bdd`, 0 skipped, and a test binds
  the executed count to the project's own parser count, so a seventh file with no step module
  reddens instead of counting as coverage.
- The five section-quality checks read real populations: `measurable-goal` 154 over 235,
  `pending-in-approved` 2 over 69, and 0 over 269 / 138 / 243 for the other three. Each of the
  three zero rows was shown to fire on a real document of this repository under one
  reverse-editable edit, so it is a checked green rather than a vacuous one.
- **56 of 243 documents (23%) are in a kind no content check enters** — BRIEF 11, PLAN 42,
  SUMMARY 3 — while the global `checks_that_read_nothing` read `()` throughout. The global count
  is an OR over the corpus and structurally cannot see that; per-kind coverage can.

Three limits are stated in the shipped documentation rather than omitted, because each is a
property of the design and not a bead waiting to be done:

- **`measurable-goal` is closer to a numeral detector than a measurability detector, and its
  individual findings are not yet trustworthy.** Review `.15` measured roughly 1-in-18 precision
  on a sample of 18 and found it flags `beadloom lint --strict fails (non-zero)`, which is
  exactly the exit-code form standing note #148 demands. The count is a real statement about a
  corpus; a row is not yet actionable. The owner's decision is to re-scope the criterion before
  paying the debt — `beadloom-mr2l.65` carries it — because inserting numerals into goals that
  are already checkable would satisfy the regex and improve nothing.
- **Windows is unverified by decision.** `.64` withdrew the CI leg on a measured cost (~16-28
  runner-minutes and roughly 3x PR-to-merge latency) and the Windows verdict for the flow guards
  is composed from `ntpath` plus a refusal proved branchless, never observed on a runner. The
  flow-guards SPEC says so under its own heading, and nothing elsewhere in the documentation
  implies Windows support.
- **Whether BRIEF, PLAN and SUMMARY belong inside the four content checks is open.** They read
  zero by template construction, not by accident of content. `.66` deliberately declined to
  write "BRIEF is outside these four checks" into the SPEC, on the grounds that it would convert
  an accident into a decision on no authority, and that judgement stands: the documentation
  reports the measured state and names the decision as open.

Two mechanisms ship **inert on this repository**, stated rather than implied by a green count:
this repo's `rules.yml` declares no `non_behavioural` entry and no `for.exclude` on the
`scenario_coverage` rule, so the excused-population line, the dead-declaration finding and the
`exclude` rejection are proved by unit rows and by acceptance scenarios, and by nothing on this
corpus.

## Current Phase

- **Phase:** Development — S1, S2, S2b, S3 and S4 complete; S5 next
- **Current bead:** `.16` closes S4; `.17` opens S5. Live status is in ACTIVE.md and the tracker
- **Blockers:** none. `main`'s live protection still requires the seven pre-`.38` contexts while
  the scaffolded default declares nine, so `setup-branch-protection` is not re-run here until
  every declared context is observed green — see ACTIVE.md
- **Open after S4, and deliberately unresolved rather than decided in prose:** whether the
  BRIEF, PLAN and SUMMARY templates gain the rows the four content checks read, or are placed
  outside those checks. 56 of 243 documents (23%) are in a kind no content check enters. Both
  sides have a cost: giving the templates a Goal and a Risks table makes every `bug`, `task` and
  `chore` document carry sections most of them have nothing to put in, and declaring the kinds
  out of scope makes the exclusion permanent for the document kind the majority of work uses.
  The measurement is printed by `docs quality`; the decision is the owner's
