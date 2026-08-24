# CI Gate

The unified `beadloom ci` gate for the application domain.

**Source:** `src/beadloom/application/gate.py`

---

## Specification

### Purpose

Compose Beadloom's individual checkers into ONE `GateResult` with a single `ok`
verdict, so CI is the only true enforcement point — identical for any author,
whether Claude Code, Cursor, or a human. `run_ci_gate` runs every step in order
and never short-circuits, so a later failure is never hidden by an earlier one.

### Steps

`run_ci_gate(project_root, *, fail_on, hub_exports, no_reindex)` runs, in order:

1. **reindex** (unless `--no-reindex`) — rebuild the index.
2. **lint** — `lint --strict`, architecture boundaries. Its summary carries what a `forbid_import` exemption excused (`… 12 rules, 0 violations, 6 crossings suppressed by an exemption`), taken from the linter's own formatter so the Gate line cannot drift from the command it summarises (BDL-061.49). The clause is absent when nothing was suppressed. There is deliberately no matching clause for `rules_inert`: an inert rule always emits a finding, so a non-zero count already flips this summary to the `0 error(s), N warning(s)` branch.
3. **sync-check** — symbol-pair doc freshness; fails on stale **and missing**
   pairs, reports `unverified` ones as `WARN` rather than fresh, and states how
   many pairs a WORKING declaration EXCUSED, with the reason it was declared
   with (`… 326 pair(s) fresh, 4 exempt — <reason>`). The clause is absent when
   nothing was excused, so a project that declares no exemption keeps its line.
4. **docs-audit** — numeric/version fact freshness; fails on `stale>0`, and
   states how much of the declared fact surface it covered.
5. **docs-quality** — the five writing-standard checks over the project's
   planning documents (BDL-061 S4b): a goal with a measurable clause, a decision
   carrying a reason, a risk carrying a mitigation, no `Pending` question inside
   an `Approved` document, and no unfilled template placeholder. Every finding is
   a `warn` and the step is `passed` unconditionally, so a project whose
   documents predate the checks does not go red on upgrade. A project with no
   planning document is a NAMED skip that states the globs it looked under.
   Three states set `not_verified`, and the step then reports **WARN** rather
   than PASS — *unverifiable is not clean*: a check that found no document with
   anything to read (`NOT CHECKED: <checks>`), a document KIND no content check
   enters (`NO CHECK READS: <kinds>`), and a document nothing could decode
   (`UNREADABLE: N`). The second exists because the first is a global OR over
   the corpus and goes silent as soon as one document carries one row, so it
   cannot see a check that is blind on an entire shipped document kind.
   Measured on this repository, 2026-08-24, the step reports:

   ```
   docs-quality WARN | 243 document(s) read; measurable-goal 4,
                       pending-in-approved 2; NO CHECK READS: BRIEF, PLAN, SUMMARY
   ```

   **The line prints findings, not what the check stopped deciding about.** After
   `beadloom-mr2l.70` re-scoped `measurable-goal`, 27 of the 150 newly-accepted
   goal statements name no witness either and this check now decides nothing
   about them. That limit is stated in the doc-quality SPEC and is not carried on
   this line — filed by review `beadloom-mr2l.19` as a MINOR, and left as a
   stated limit rather than a silent one.
   
6. **doc-spaces** — the TO-BE → AS-IS relation (BDL-061 S5). Reports an epic
   with at least one closed bead that declared a graph node with no AS-IS
   document, plus a WORKING exemption that excuses nothing and a WORKING
   declaration the graph contradicts. Every finding is a `warn` and the step is
   `passed` unconditionally, for the same reason as the step above. A project
   with no TO-BE document is a NAMED skip that states the roots it looked under.
   FOUR states set `not_verified` and the step then reports **WARN** rather
   than PASS, because each is a way to print no findings while having checked
   nothing: no tracker export was readable, no epic with closed beads declared a
   node, some epics declare none, and — since `beadloom-mr2l.74` — some epics
   the tracker does not name at all. The *declare no node* clause names the
   composition of that bucket when it holds more than the ordinary case, because
   a directory carrying no readable intent document (`beadloom-mr2l.73`) is not
   an epic whose author forgot to declare a node. That fourth state has its own clause rather
   than only the boolean: `not_verified` was already True here for an unrelated
   reason, so a saturated signal said nothing about an epic that had left the
   export. The tracker is read from the committed `.beads/issues.jsonl` export
   rather than from a `bd` subprocess, so the gate gives the same answer in a
   fresh CI checkout with no tracker installed — a check whose result depends on
   what is on the runner is not a gate. The line names the tracker it read,
   because `beadloom docs spaces` prefers the live `bd` database and the two can
   therefore differ on one tree at one moment. An epic that DECLARES a node and
   that the tracker cannot resolve is reported as `epic_not_in_tracker`: whether
   its work finished is unknown, and unknown is not clean. An epic that declares
   nothing is not reported that way — it is already counted in the *declare no
   node* clause, and one fact under two names makes the line unreadable.

   The exemption clause names **two** populations rather than one word for both.
   `N WORKING document(s) in the exempt space` counts documents; `M sync pair(s)
   excused` counts pairs, and that number is the one the gate's own sync-check
   step measured in the same run — it is carried on `GateStep.pairs_excused`
   and never recomputed, because one run printed `exempt: 0` from `sync-check
   --json` and `55 WORKING document(s) exempt` two lines apart about one tree.
   On this repository the 55 `ACTIVE.md` documents live outside the
   documentation directory the indexer walks, so none of them is a sync pair and
   0 is the honest pair count. When a project DECLARED the exemption, the line
   also states how many documents each declared half reached, so a one-line
   declaration covering 39 documents prints the number 39. A document whose kind
   places it in a space whose roots exclude it adds a final clause with its
   count (`beadloom-mr2l.77`).

   Measured on this repository, 2026-08-24, the step reports:

   ```
   doc-spaces WARN | to_be 190, as_is 93, working 55; 17 node declaration(s)
                     from 37 of 61 epic(s) with closed beads held against the
                     AS-IS space; tracker read from .beads/issues.jsonl;
                     NOT CHECKED: 56 epic(s) declare no node
                     (4 carry no readable intent document);
                     NOT CHECKED: 24 epic(s) the tracker does not name
                     (BDL-001, BDL-003, BDL-005, BDL-006, BDL-007 and 19 more);
                     55 WORKING document(s) in the exempt space,
                     0 sync pair(s) excused
   ```

   Two findings, both true: `BDL-061` declares `cli-commands`, which has no
   AS-IS document, and `BDL-030` declares a node while neither tracker has any
   record of it.
7. **config-check** — agent-config drift (AgentConfigAsCode). Since BDL-061 S3
   a drift carries its own severity: `error` blocks the step, `warn` is
   reported and does not. The summary has three forms accordingly —
   `N drifted artifact(s)`, `no blocking drift; N artifact(s) reported (warn)`,
   and `agent-config in sync` — because printing "in sync" over a reported
   finding is the false-green shape this epic exists to remove. The step also
   carries the mutation-SCOPE findings (BDL-061 S4b), each with its own rule
   name and severity `warning`; they are computed BEFORE the step's database
   guard, because a declaration is checkable against the tree whether or not the
   index was built.
8. **doctor** — graph integrity.
9. **federate** — `federate --fail-on` when hub exports are supplied.

The **docs-audit** step (BDL-057 Layer 1) reuses
`beadloom.doc_sync.audit.run_audit` — the same path `beadloom docs audit` calls —
and fails the step when any documentation mention disagrees with a ground-truth
fact (version, node/edge counts, language/framework counts, MCP-tool count,
CLI-command count). The audit's false-positive masking and per-fact tolerances
keep this honest; targeted exceptions live in `.beadloom/config.yml`
(`docs_audit.tolerances` / `docs_audit.ignore`).

Its summary line carries the audit's own COVERAGE, not only its findings:
`14 mention(s) fresh; 2/9 declared fact(s) verified, NOT VERIFIED: ...`. A bare
`13 mention(s) fresh` was measured on this repo to be thirteen restatements of
ONE of nine declared facts — the line reported the checker's activity and read as
a verdict on the documentation (BDL-UX #173). Coverage is reported, not enforced:
silence in the docs about a fact is not a defect in the code, and a `WARN` every
project would carry on every run would spend the channel `sync-check` needs for a
genuinely missing baseline. `beadloom docs audit --fail-if unverified>N` is the
opt-in for a project that wants every declared fact stated somewhere.

Each step reports a `GateStep` with `PASS` / `WARN` / `FAIL` / `SKIP` — never an
ambiguous green — and its findings in the shared finding shape. `GateResult.ok`
is True only when every step passed.

### Nothing may pass by having less to check

Two step summaries were rewritten because they described the checker's ignorance
as the code's health (BDL-UX #174/#175):

- **sync-check** names what it could NOT check. A pair whose doc, code file, or
  graph-declared doc is gone is `missing` and FAILS the step — deleting a
  document was the cheapest way to satisfy the gate, and the count silently fell
  from 275 to 269 while every step printed PASS. A pair with no baseline is
  `unverified`: the step stays passed but prints `WARN` with the count, because
  a project that cannot supply a baseline is not broken and must not read green
  either. When the committed declared-surface ledger records a larger surface
  than the run found, that is named too. And a pair a WORKING declaration
  excused is counted and its reason stated: the `exempt` verdict was added after
  this summary was rewritten and reintroduced the same shape, printing
  `326 pair(s) fresh` where the same tree without the declaration printed 326 of
  330 (`beadloom-mr2l.76`). Unverifiable, excused and clean are three states and
  do not print one word.
- **doctor** counts the CHECKS that ran, not the findings. `run_checks` returns
  one entry per finding, so `len(checks)` counted problems: deleting a declared
  doc added a `nodes_without_docs` warning and the summary read `21 check(s)
  clean` where it had read 20 — a count that ROSE while the tree shrank. The
  summary is now `N check(s): 0 error(s), W warning(s), I info`, and the word
  *clean* appears only when every check is OK.

## Invariants

- Every step runs; the gate never short-circuits on the first failure.
- A skipped step counts as passed (it cannot block the build).
- `docs-audit` blocks on `stale>0` and never counts an unverified fact as
  passing; `sync-check` `surface_drift`, `unverified` and
  declared-surface-shrink findings are advisory and never fail the gate.
- No step prints a count of something it did not check, and no step prints
  *clean* over a warning.
- `WARN` never changes the exit code: an adopter whose project is green today
  does not go red on upgrade, it only stops reading green where nothing was
  verified.
- `fail_on=None` selects the safe default federate set
  (`breaking,drift,orphaned_consumer,undeclared_producer`); the
  no-false-gate verdicts are never included.

## API

Module `src/beadloom/application/gate.py`:

- `GateStep` — one step: `name`, `passed`, `skipped`, `findings`, `summary`,
  `not_verified`, and the `status` property (`PASS` / `WARN` / `FAIL` / `SKIP`).
- `GateResult` — aggregate: `steps`, plus the `ok` and `findings` properties.
- `run_ci_gate(project_root, *, fail_on, hub_exports, no_reindex) -> GateResult`
  — run every gate step and aggregate the result.

## Testing

Tests: `tests/test_gate.py`, `tests/test_ci_gate.py`,
`tests/test_f3_gate_coverage.py`, `tests/test_f3_gate_dogfood.py`
