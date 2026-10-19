# PRD: BDL-083 — Debt to zero

> **Status:** Approved
> **Created:** 2026-10-18

---

## Problem

Measured on 2026-10-18 at `0f1cb9a3` (Beadloom 9.0.0, bd 1.0.4), the day the first adoption
outside this repository filed its findings:

1. **The issue log holds 125 open entries**: 26 high, 68 medium, 31 low. 58 of them carry
   numbers below the ledger's floor (filed before 2026-09-09). The log's own rule says to
   re-measure before acting on an old entry, because of six entries checked on 2026-09-08
   three had gone false; nothing has re-measured the 58 since.
2. **78 open beads**, 49 of them bugs: two P0 (`beadloom-ba9w` itself and `beadloom-jwfc`,
   the pre-push Gate crashing on a non-blocking pipe, re-met on 2026-10-18 with its traceback),
   19 P1 bugs, the rest P2 and P3; 11 deferred (8 of them federation, owned by ROADMAP item 3).
   `beadloom-ba9w` carries 16 children and nine slices A–I agreed on 2026-10-08 to 2026-10-11
   and not started.
3. **The dashboard** (2026-10-08, 8.0.0): Lint 70 warnings, Debt 42.5 high, Doctor 262
   warnings — 167 of 786 test files bound to no node, 49 features without a scenario, 262
   documents without a `ref_id`, complexity smells 35 of the 42.5 points. On 2026-10-18 the
   Gate reports lint 72 warnings and doctor 277 warnings.
4. **The first outside adoption** (the colleague's monorepo: a Python backend under `backend/`
   with uv, an FSD frontend, self-hosted GitLab CE) produced 25 entries in two days
   (#326–#350). The most severe is a gate that passes without running: the pre-push hook exits
   0 when `beadloom` is not on PATH, pre-commit never runs `beadloom lint`, and an FSD violation
   reached the remote. Four more are false signals that misled reviews (#328 liveness, #329
   ownership, #330 scope base, #331 exit code), and a family of five is one assumption — the
   project is the git root with one Python project at the root and GitHub CI — that the
   team pilot's own layout breaks the same way.
5. **The owner's decision of 2026-10-18:** the project's quality and honesty are the P0; every
   recorded issue is re-verified; debt and defects go to zero; development continues only
   after that, because the count otherwise grows faster than it closes.

## Impact

The team pilot (two people on a GitLab monorepo) starts on a tool whose gates fail loudly or
not at all, whose verdicts name their base and their population, and whose issue log is a
list of live measurements rather than an archive of guesses. Every later item of the ROADMAP
(the team model's measurements, federation as the hub, the adoptions) is measured against a
clean baseline, and the recurrence that keeps the baseline clean is in the flow rather than
in one coordinator's memory.

## Goals

1. **Gates that lie are fixed first.** A gate that did not run says so and fails (#326, #226);
   pre-commit judges graph boundaries for staged paths that belong to a node (#326);
   `rule_liveness` tells a glob that can match nothing from a rule with nothing to ban now
   (#328); `ci` ownership is by the files a bead changed, never by a node that covers a
   directory, and the summary prints the rule it attributed by (#329); `scope-check` judges
   from the merge-base with the branch the work was cut from and prints the base (#330, with
   #300's CI resolution); `issue-number check` exits as the Gate step does (#331); every Gate
   step has an exception boundary and an `ERROR` status (#318), and the verdict survives a
   non-blocking pipe (#226). *Done when* each entry's measurement is re-run green on this
   repository and on the adopter's layout rebuilt as a fixture, and the hook without
   `beadloom` on PATH returns non-zero with a sentence.
2. **A monorepo on GitLab is a supported layout, or refused by name.** `rooms` reads
   `.gitlab-ci.yml` as a source of legs and finds Python projects by `**/pyproject.toml` under
   `scan_paths` (#332); `clean-room` builds the environment from the found project's
   `uv.lock` and derives its hint from it (#333, #311); `config-check` names what it composed
   from and what it compared against, and gives one verdict in a room, a worktree and the
   main checkout (#334); `--carry` of a path the tree no longer holds is a deletion in the
   room (#335); the ruff leg shows stderr, tells "not found" from "violations" and reads the
   owning project's configuration (#327); a project root below the git root is refused in
   words (#325); a Windows checkout pairs the same documents with the same files as a POSIX
   checkout of one commit, and the surface ledger names its pairs (#353, added 2026-10-19).
   The landing lock's release reaches the trunk with the landing, and a push that would leave the
   trunk's export holding the slot is refused (#354, added 2026-10-19).
   The second tool reads the same flow as the first: `setup-agentic-flow --tool cursor` composes
   the core, the project layer, the STACK overlay and the commands for Cursor, `config-check` names
   a tool whose composition lacks a layer the other has, and the MCP configuration carries no one
   machine's path (#356 a, e, g, added 2026-10-19; its b stays in the epic for S3's placement, its
   c, d, f are features filed outside).
   *Done when* a fixture with `backend/pyproject.toml`, `frontend/` and `.gitlab-ci.yml`
   gets a named room, a built environment and the same `config-check` verdict in a room as
   in the checkout, and the matching of `source:` against the index gives one pair set under
   both separators.
3. **Every open entry is re-measured on the current version and closed or owned.** Each of the
   125 entries is re-run against its own `Command` on the version this epic ships from; an
   entry whose issue is gone closes with dated evidence in the archive; an entry whose issue
   is live gets a bead under this epic or a `Won't fix` ruling with a reason, also archived.
   The stub rule for numbers 262 and higher is kept; #196 and #288, stated nowhere, are
   accounted for. *Done when* the open index holds zero entries and `issue-number check`
   is green.
4. **The false-stale family is one family, not seven entries.** A file owned by another node
   is not an untracked file of the directory's node (#347); incremental `reindex` opens pairs
   for new files (#348); `symbols_changed` prints what clears it and which symbols changed
   (#346, the shape of #182); the test mirror requires the module file under a deeper root
   (#339); a test file's import is a test edge and pairs under its own reason (#338, #349); an
   annotation decides ownership, not only the pair (#342); the four populations called
   "stale docs" are named per surface (`beadloom-r9t5`). *Done when* each entry's measurement
   is re-run green and `sync-check` on this repository reports the same population it did
   before, in words.
5. **The debt the epic was opened for goes to its measured zero** (slices A–D of 2026-10-08):
   0 of 786 test files unplaced; 0 features without a scenario or a ruled population change;
   every document without a `ref_id` linked, retired or declared out with a reason; the
   complexity smells answered by a split, a seam or a retire-or-keep ruling each. *Done when*
   the dashboard's debt score is reported with its population and the exemption list in
   `rules.yml` is empty.
6. **The tooling baseline is re-measured and its recurrence is in the flow** (slices E–I of
   2026-10-09 to 2026-10-11): bd upgraded, every bd-1.0.4 claim in the composed CLAUDE.md
   confirmed or rewritten in a claim / was / is table, and the Dolt remote scenario the team
   model needs measured; Claude Code and Cursor capabilities checked against their current
   documentation and the deltas applied to the role templates; dependencies by major verified
   on the full tree and the six adopter stacks, with Dependabot or Renovate taking over; the
   composed CLAUDE.md and roles split into a short core and companions with an output-size
   contract per role (#156); `ctx` surfaces every rule type the Gate judges through one
   applicability derivation (#317), with a token budget (#319) and a defined subgraph
   contract (#320). *Done when* each slice's own measure is recorded with its date.
7. **Every open bead outside the deferred federation set is closed or ruled.** The 19 P1 bugs,
   the standing P2 debt table of the ROADMAP and the 16 children of `beadloom-ba9w` are
   absorbed by goals 1–6 or carried by a slice of their own; a bead that is not fixed closes
   as `Won't fix` with the reason on the bead and in the archive. *Done when*
   `bd list --all --status open` names only this epic's in-flight beads and the 8 deferred
   federation beads.
8. **The count stays at zero by construction.** A recorded finding carries the date and
   version it was measured on, and the issue-log leg reports entries older than a set age as
   unmeasured (ROADMAP class gap 2); the issue-log leg's summary states the open count by
   severity so a reader sees growth; the release role carries a "tooling baseline" duty.
   *Done when* the leg's summary line on this repository reads zero open entries and names
   the age rule.

## Non-goals

- Federation as the hub (ROADMAP item 3): the 8 deferred beads of `beadloom-8qqp` and
  `beadloom-147x` stay deferred and are not counted by goal 7.
- The team operating model's product gaps (the beads-dir resolver, the personal trace, the
  `tracker:` and `beads:` keys, setup-clone, the tracker adapter API): ROADMAP item 1, its own
  work item; this epic hands it a clean Gate, not those features.
- The three flow lessons of BDL-074 (ROADMAP item 8) and the flow-lesson organ
  (`beadloom-tm76`, `beadloom-6rfz`, `beadloom-qhxr`): they are process rules, not debt; they
  keep their own item.
- New features of any kind. A slice that finds a feature behind a bug files the feature and
  fixes the bug.

## Acceptance Criteria (overall)

- The issue log's open index holds 0 entries; every number from the floor up is written as an
  entry, a stub or an archived close; `beadloom issue-number check` is green and its summary
  prints the open count by severity as 0/0/0.
- `bd list --all --status open` names no bug outside this epic's in-flight beads; the deferred
  set is exactly the 8 federation beads.
- The Gate on this repository: `lint --strict` 0 errors and 0 population warnings
  (`features-have-bound-tests`, `scenario-coverage`, `test-files-bind-to-a-node` at 0);
  `doctor` 0 warnings about documents without a `ref_id`; the debt report's score stated with
  its population.
- The adopter's layout as a fixture (`backend/pyproject.toml` + `uv.lock`, `frontend/`,
  `.gitlab-ci.yml`): `rooms` names a room, `clean-room` builds the environment, `ci` in the
  room and in the checkout give one `config-check` verdict, the pre-push hook without
  `beadloom` on PATH returns non-zero.
- Each of the 25 adopter entries (#326–#350) re-run by its own `Command` on the fixture or on
  this repository: green, or closed as `Won't fix` with the reason.
- The version: **MAJOR** by the public-API guide if the RFC's measured exit-code moves hold
  (`issue-number check` and the pre-push hook move from 0 to non-zero on inputs 9.0.0 accepted;
  `scope-check`'s base changes the finding set on every branch cut from a branch); the RFC
  states the measured moves and the ruling.
- The ROADMAP's "What to do next" is re-ranked after close-out with this epic's residue (zero
  entries or the ruled set) as its baseline.

## Rulings needed (the coordinator's recommendation first)

1. **The order of slices.** *Recommend:* S1 gates that lie (goal 1), S2 monorepo and GitLab
   (goal 2), S3 re-measurement of the 125 entries (goal 3), S4 the false-stale family (goal 4),
   S5 the original debt A–D (goal 5), S6 the tooling baseline E–I (goal 6), S7 the remaining
   beads and the recurrence (goals 7 and 8). S1 and S2 before the team model's measurements,
   because the pilot's layout is S2's fixture and S1's silent gate would end the trial in its
   first week; the model's document work runs in parallel. One PR per slice, never a bag.
2. **What zero means.** *Recommend:* zero open entries in the index, where a close is either
   dated evidence that the issue is gone or a `Won't fix` ruling with a reason, both archived.
   A ruling counts as a close; an entry nobody re-measured does not.
3. **The pre-push hook without `beadloom` on PATH.** *Recommend:* fail with a sentence
   (non-zero), not warn. Hooks are installed per clone by `install-hooks`, so a missing binary
   is a setup error the person must see; a warn is the silent pass with one more line.
4. **The `scope-check` base.** *Recommend:* the merge-base with the branch the working branch
   was cut from, detected from the reflog or `--base`, trunk as the fallback, and the base
   printed in the header in every case.
5. **The version.** *Recommend:* MAJOR, measured in the RFC: three exit-code or finding-set
   moves on inputs 9.0.0 accepted. A MINOR would hide a change every adopter's CI sees.
6. **The epic's bead.** *Recommend:* `beadloom-ba9w` stays the feature bead (P0 since
   2026-10-18); children are created per slice as each PLAN section is approved, so the DAG is
   never 80 beads at once; `bd swarm` is not needed for one PR at a time.
7. **Re-measurement as a slice of its own, before the fixes it feeds.** *Recommend:* S3 runs
   after S1 and S2 because those two are measured already (2026-10-16/17, source lines
   re-read); S4–S7 take their bead lists from S3's result, so S3 is the gate between the
   adopter's findings and the older debt.
8. **The expiry on a recorded finding.** *Recommend:* this epic ships it (goal 8): a
   `measured_on` field per entry and an age rule in the issue-log leg, because re-measurement
   is this epic's central act and a count that cannot age is the count that grew to 125.
