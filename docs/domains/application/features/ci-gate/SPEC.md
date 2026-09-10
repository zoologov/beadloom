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
2. **lint** — `lint --strict`, architecture boundaries. Its summary carries what a `forbid_import` exemption excused (`… 12 rules, 0 violations, 6 crossings suppressed by an exemption`), taken from the linter's own formatter so the Gate line cannot drift from the command it summarises (BDL-061.49). The clause is absent when nothing was suppressed. There is deliberately no matching clause for `rules_inert`: an inert rule always emits a finding, so a non-zero count already flips this summary to the `0 error(s), N warning(s)` branch. This step is also the only one exported under a public name (`lint_step`): `beadloom init` runs it over the graph it has just written and exits 1 when it does not pass, so a divergence between what `init` writes and what `init` requires surfaces at init time rather than at the adopter's first `ci` run (BDL-067, closing BDL-UX #192). Its `LintError` branch — `rules.yml` present and unloadable — is the one place a finding's `rule` is this step's own name rather than a rule's, with the loader's complaint in `why`, so the summary it carries is exported too, as `RULES_CONFIG_ERROR`: a caller that renders findings has to branch on it, and `init` did not, telling an adopter with a hand-edited rules file that a rule called `lint` had failed (BDL-067 `.6`).
3. **sync-check** — symbol-pair doc freshness; fails on stale **and missing**
   pairs, reports `unverified` ones as `WARN` rather than fresh, and states how
   many pairs a WORKING declaration EXCUSED, with the reason it was declared
   with (`… 326 pair(s) fresh, 4 exempt — <reason>`). The clause is absent when
   nothing was excused, so a project that declares no exemption keeps its line.
4. **docs-audit** — numeric/version fact freshness; fails on `stale>0`, and
   states how much of the declared fact surface it covered.
5. **docs-quality** — every check that reads the project's planning documents,
   assembled by `application/planning_report.py` so this step and
   `beadloom docs quality` report ONE run (BDL-068 S1.4). Five writing-standard
   checks (BDL-061 S4b): a goal with a measurable clause, a decision carrying a
   reason, a risk carrying a mitigation, no `Pending` question inside an
   `Approved` document, and no unfilled template placeholder. Two structural
   ones: `missing-section` and `empty-section`, against the sections each
   document kind's own composed skeleton carries. Two about the axes:
   `axes-without-a-seed` and `axis-without-a-scope-decision`. A required section
   no majority of a kind carries is reported once against the KIND, with its
   ratio and no file location, because the fix is in the template rather than in
   every document. Every finding is
   a `warn` and the step is `passed` unconditionally, so a project whose
   documents predate the checks does not go red on upgrade. A project with no
   planning document is a NAMED skip that states the globs it looked under.
   Four states set `not_verified`, and the step then reports **WARN** rather
   than PASS — *unverifiable is not clean*: a check that found no document with
   anything to read (`NOT CHECKED: <checks>`), a document KIND no content check
   enters (`NO CHECK READS: <kinds>`), a table `decision-reason` could not place
   as a table of decisions (`NOT CLASSIFIED: N table(s), M row(s)`), and a
   document nothing could decode (`UNREADABLE: N`). The second exists because
   the first is a global OR over the corpus and goes silent as soon as one
   document carries one row, so it cannot see a check that is blind on an entire
   shipped document kind. The third is BDL-UX #213: a `Reason` column does not
   make a table a decision table, and the check names the tables it did not
   judge instead of reporting a measurement row as a decision with no reason.
   None of the four can redden a project — the step is `passed` unconditionally.
   Measured on this repository, 2026-09-08, the step reports:

   ```
   docs-quality WARN | 259 document(s) read; measurable-goal 4,
                       pending-in-approved 2, missing-section 102,
                       routed-without-axes 12;
                       NO CHECK READS: BRIEF, PLAN, SUMMARY;
                       NOT CLASSIFIED: 12 table(s), 58 row(s)
   ```

   Measured again on 2026-09-02, after S1.4. The two axes checks read **0**
   documents because no planning document in this repository carries an
   `## Axes` section yet, and the line says so rather than reporting them clean.

   **The line prints findings, not what the check stopped deciding about.** After
   `beadloom-mr2l.70` re-scoped `measurable-goal`, 27 of the 150 newly-accepted
   goal statements name no witness either and this check now decides nothing
   about them. That limit is stated in the doc-quality SPEC and is not carried on
   this line — filed by review `beadloom-mr2l.19` as a MINOR, and left as a
   stated limit rather than a silent one.
   
6. **issue-log** — the issue log's numbers (BDL-068 S6). Three legs over a
   numbered log and the ledger that allocates its numbers: `duplicate-number`
   (one number defined by two entries), `unwritten-claim` (a number claimed and
   never written into the log) and `unclaimed-number` (an entry past the
   ledger's floor holding a number no claim holds). Unlike its two neighbours
   this step **BLOCKS**, and the difference is the kind of claim each makes: a
   writing-standard finding is an opinion about prose a project may reasonably
   carry for a release, while a duplicate number is a reference that resolves to
   two entries and to neither — this repository shipped one for fifteen days
   across a CHANGELOG, a ROADMAP, eight test files and thirty-six tracker
   records (BDL-UX #187). Every leg's repair fits in the commit that trips it,
   which is what makes blocking fair. It cannot redden a project that has not
   opted in: the log is DECLARED under `issue_log:` in `.beadloom/config.yml`,
   and a project declaring none is a NAMED skip that states the key to add.
   `not_verified` carries the honest half — before a project's first allocation
   the ledger has no floor, so `unwritten-claim` and `unclaimed-number` enter no
   number at all and the summary says `NOT CHECKED:` rather than reporting them
   clean.

   Since `beadloom-l9ee` the line also carries the PARTIAL case, which is the one
   every adopter is in from their first allocation onwards: `unclaimed-number`
   skips every entry below the floor by design, and the summary said nothing
   about how many that was. The line read `240 entr(ies) uniquely numbered; 5
   claim(s), floor 262` over a log whose leg had entered five of those entries
   (BDL-UX #267). `PARTLY CHECKED` states the population, and it is not a
   finding — an unreached population is coverage, and making it one would redden
   every project that adopts the allocator with a log already written. Measured
   on this repository, 2026-09-09:

   ```
   issue-log PASS | 241 entr(ies) uniquely numbered; 6 claim(s), floor 262;
                    PARTLY CHECKED: 235 of 241 entr(ies) are below floor 262,
                    where unclaimed-number did not enter; 1 number(s) below the
                    highest are stated nowhere and are unaccounted for, not free
   ```

7. **doc-spaces** — the TO-BE → AS-IS relation (BDL-061 S5). Reports an epic
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

   Measured on this repository, 2026-08-26, the step reports:

   ```
   doc-spaces WARN | to_be 194, as_is 100, working 56; 17 node declaration(s)
                     from 38 of 62 epic(s) with closed beads held against the
                     AS-IS space; tracker read from .beads/issues.jsonl;
                     NOT CHECKED: 57 epic(s) declare no node
                     (4 carry no readable intent document);
                     NOT CHECKED: 24 epic(s) the tracker does not name
                     (BDL-001, BDL-003, BDL-005, BDL-006, BDL-007 and 19 more);
                     56 WORKING document(s) in the exempt space,
                     0 sync pair(s) excused
   ```

   Every count on that line is a moving denominator — this repository's own
   planning tree changes it — so the shape is the point and the numbers are
   whatever `beadloom ci` prints today.

   One finding: `BDL-030` declares a node while the tracker export has no record
   of it. `BDL-061`'s `cli-commands` declaration was the second one and closed
   when BDL-062 `.4` gave that node an AS-IS document
   (`docs/services/components/cli-commands/DOC.md`).
8. **scope-check** — did this branch leave the axes its work item declared?
   (BDL-068 S1.6). BRANCH-scoped, `<trunk>...HEAD`, and that is the whole point:
   the tree is shared by several agents, so judging it would fail one agent's
   push on a neighbour's edit, while `<trunk>...HEAD` is exactly what the pull
   request contains and what the approval was spent on. The trunk is the
   `options.trunk` the `working-branch` guard already reads, preferring
   `origin/<trunk>` when that remote-tracking ref exists — measured on this
   repository, a local `main` two commits behind the remote made another work
   item's LANDED change read as this branch's work. `passed=True`
   unconditionally, like `docs-quality` and `doc-spaces`: the check ships as
   `warn` so a project whose work items predate `## Axes` does not go red on
   upgrade. A run that found no branch, no work item, no index, no `## Axes`
   section, no answer from git, or no changed path a node owns is a NAMED SKIP
   with its reason — never a PASS, because a comparison over an empty
   population has verified nothing. The summary states the findings, the paths
   judged, the paths no node owns and the declared rows nobody decided.
9. **config-check** — agent-config drift (AgentConfigAsCode). Since BDL-061 S3
   a drift carries its own severity: `error` blocks the step, `warn` is
   reported and does not. The summary has three forms accordingly —
   `N drifted artifact(s)`, `no blocking drift; N artifact(s) reported (warn)`,
   and `agent-config in sync` — because printing "in sync" over a reported
   finding is the false-green shape this epic exists to remove. The step also
   carries the mutation-SCOPE findings (BDL-061 S4b), each with its own rule
   name and severity `warning`; they are computed BEFORE the step's database
   guard, because a declaration is checkable against the tree whether or not the
   index was built.
10. **doctor** — graph integrity.
11. **federate** — `federate --fail-on` when hub exports are supplied.

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

Since BDL-062 `.3` the line also names the facts the audit declared no value for in
this project: `..., NOT APPLICABLE to this project: cli_command_count`. A fact that
could not be computed used to leave no trace, so the denominator moved in
silence — measured in-process on this repository, an unregistered CLI surface
turned `3/9 declared fact(s) verified` into `3/8` with nothing naming the fact
that had left. The clause appears only when something was declined, so a project
where every declared fact applies reads exactly as it did before.

Since BDL-068 `.81` it also names the version tokens the audit declined to judge:
`..., COULD NOT JUDGE 1 version token(s) naming git — unconfirmed here`. A version
belongs to the subject named beside it, and `git` is confirmed by the environment
rather than by a file the project ships. A directory built by `git archive HEAD` —
every clean room `beadloom clean-room` builds — carries no `.git`, so `git 2.49.0`
was compared against this project's version and every clean-room Gate run on this
repository was rc 1 for one line of one document (BDL-UX #266). An unconfirmed
subject is now unresolved rather than absent, and the token is reported instead of
judged. This clause also appears only when something was declined, so a run in a
git working tree reads exactly as it did before.

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

### The verdict names the room it was taken in

A verdict is true of the room it was taken in, and this project read one as a claim about the
product four times — nine "green on the tree" reports measured on macOS against CI legs on
Ubuntu, with the tenth measurement red on six of them, being the loudest. Since BDL-068 S3.2
`GateResult` carries a `RoomCensus`: the room the run was in, the rooms the project declares
(interpreters from its packaging metadata, legs from every job of every workflow) and the ones
this run did not enter. All three formats print it — under the verdict in `rich`, as a `room`
object in `--format json`, and as one `::notice::room` in `--format github`.

**It is not a step, and naming it changes nothing.** A step has a status, and the room makes no
claim that can pass or fail: the same `ok`, the same exit code, the same findings. What it
changes is that a green is answerable — a reader can see which of the declared rooms it covers.
Do not read a room-naming verdict as a stronger one.

### The verdict names what no step of it performed

`beadloom ci` does not run the test suite, and until BDL-UX #247 it never said so — while
`CLAUDE.md` calls the pre-push hook "the full `beadloom ci`" and the coordinator skill calls it
"the authoritative blocking backstop". Measured twice in one slice: a document change reddened
two tests under a gate that returned rc 0, and a docs wave spilled an inline code span past a
line under a gate that returned rc 0 over that tree twice, after which all six test legs went red
on one assertion that reproduces locally in 0.07 s.

`GateResult` therefore carries a `GateCoverage` beside its room census: the verifications this
project's pipeline declares that no step of this run performed, each with the command the
pipeline runs for it and the workflow job it was read from. On this repository the block names
three — the test suite, the style linter and the type checker. The second and third are the ones
nobody had filed: the gate's own step is called `lint` and checks the architecture boundaries,
not the source style.

**Both sides are derived.** What the run performed comes from its own step list, so a suite step
added to the gate later removes the line by the same act rather than by somebody deleting a
sentence. What the project verifies comes from its workflows, through the same `load_jobs` reader
the room census uses. A project whose pipeline verifies under a name the vocabulary does not hold
is told the population is empty with that limit named, never that nothing is left to run.
`gate-coverage` (DOC) states the vocabulary and the four statements a run can make.

**It is not a step either.** Same `ok`, same exit code, same findings.

### The verdict names who owns what it found

The branch that built this feature carried a red Gate across two waves of BDL-068 S6 — two
stale docs owned by no bead in the running plan — and every gate owner in those waves had to
be told by the coordinator, by hand, that the red was not theirs, so their reports would
attribute the finding rather than discount it. A known red trains its reader to discount the
next one, and the cost is never the red itself but the work of proving a second finding is
real against a background that already holds one.

`GateResult` therefore carries a `GateOwnership` beside its room census and its coverage
statement: one verdict per finding, held against the beads the tracker reports claimed while
the run happened. `owned` names the beads. `unowned` says a node was derived and no claim
covers it. `unattributed` says no node could be derived from the finding at all, which is a
different absence and must not read as the same one. A tracker that cannot answer, and a
project with no index, are a reason on the whole report rather than a page of `unowned`.

**The claim is a bead, not the branch's approval.** The work item's `## Axes` answer whether a
change is inside the approval, which the `scope-check` step of this same run already asks, and
which every agent on one branch shares; a wave's plan names beads that have not started and
beads whose wave is over. `gate-ownership` (DOC) states both trade-offs and the three routes a
finding takes to reach a node.

**It is not a step either, and the tracker is asked only when there is a finding.** Same `ok`,
same exit code, same findings; a green run attributes nothing and shells out to nothing.

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
- The room census never changes the verdict. It adds no step, no finding and no
  exit code, and `tests/test_gate_verdict_room.py` fails if it starts to.
- The coverage block never changes the verdict either, and
  `tests/test_gate_not_run.py` fails if it starts to. It names a verification
  only when the project's own pipeline declares one this report can read.
- The ownership block never changes the verdict either, and
  `tests/test_gate_finding_owner.py` fails if it starts to. A finding nobody
  claims is still a finding; a gate that went green because no bead owned a red
  would be the false green this whole slice exists to remove.
- `fail_on=None` selects the safe default federate set
  (`breaking,drift,orphaned_consumer,undeclared_producer`); the
  no-false-gate verdicts are never included.

## API

Module `src/beadloom/application/gate.py`:

- `GateStep` — one step: `name`, `passed`, `skipped`, `findings`, `summary`,
  `not_verified`, and the `status` property (`PASS` / `WARN` / `FAIL` / `SKIP`).
- `gate_step_line(step) -> str` — the step's own report line, `[STATUS] name: summary`.
  `_format_gate_rich` renders it and `beadloom init` quotes it, so the line `init`
  attributes to `beadloom ci` is the line `beadloom ci` prints (BDL-067 `.14`).
- `GateResult` — aggregate: `steps`, the room census (`room`, a
  `RoomCensus | None`), the coverage statement (`coverage`, a
  `GateCoverage | None`), the ownership report (`ownership`, a
  `GateOwnership | None`), plus the `ok` and `findings` properties. `None` means
  nothing derived it, and a surface that was not told makes no claim.
- `run_ci_gate(project_root, *, fail_on, hub_exports, no_reindex,
  performed_elsewhere=(), tracker=None) -> GateResult` — run every gate step and
  aggregate the result. `performed_elsewhere` names verifications the CALLER runs
  beside the gate, in the vocabulary a step would use: the MCP `complete_bead`
  tool runs the suite itself and passes `("tests",)`, so one run cannot report
  the suite as not run while that run ran it. `tracker` is the read port over the
  work tracker, supplied by the service that runs the gate because the `bd` seam
  lives in the services layer this one must not import; a run given none makes no
  ownership claim rather than reporting every finding as owned by nobody.

Module `src/beadloom/application/gate_coverage.py`:

- `derive_gate_coverage(project_root, *, performed) -> GateCoverage` — the
  verifications the project declares that `performed` does not cover.
- `gate_coverage_lines(coverage) -> list[str]` — the block all surfaces quote.

Module `src/beadloom/application/gate_ownership.py`:

- `derive_gate_ownership(project_root, *, findings, tracker) -> GateOwnership` —
  one verdict per finding, held against the beads the tracker reports claimed.
- `gate_ownership_lines(ownership) -> list[str]` — the block all surfaces quote.

## Testing

Tests: `tests/test_gate.py`, `tests/test_ci_gate.py`,
`tests/test_gate_not_run.py`, `tests/test_gate_finding_owner.py`,
`tests/test_f3_gate_coverage.py`, `tests/test_f3_gate_dogfood.py`
