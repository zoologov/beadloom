# ACTIVE: BDL-069 — The checks an adopter meets first, and the populations they run over

> **Epic:** `beadloom-rqma`
> **Created:** 2026-09-10
> **Last updated:** 2026-09-12

---

## Current focus

Every dev bead and the test bead are closed. What is left is `beadloom-qae9` (review, under
withholding, in a clean room) and then `beadloom-egvd` (tech-writer), which carries two of the
PRD's non-behavioural criteria as well as the three documentation obligations recorded below.

## Beads

| Bead | Slice | What | Pri | Blocked by | Status |
|---|---|---|---|---|---|
| `beadloom-qylh` | S1 | the init skeleton names the modules it already knows | P0 | — | ✓ done |
| `beadloom-h7b3` | S1 | a remediation that can be followed, and a stale line that names its pair | P0 | `qylh` | ✓ done |
| `beadloom-8lmj` | S1 | `init --yes` skeletons carry the Public API table | P1 | — | ✓ done |
| `beadloom-cgco` | S2 | a root node and the sole package cannot share one `ref_id` | P0 | — | ✓ done |
| `beadloom-4ad3` | S2 | measure what each of the six direct readers reads for | P1 | — | ✓ done |
| `beadloom-39ap` | S2 | the loader reports the reduction instead of performing it | P0 | `cgco`, `4ad3` | ✓ done |
| `beadloom-w4cd` | S3 | the reader behind `version-surface` | P1 | — | ✓ done |
| `beadloom-jtcx` | S3 | the `version-surface` command | P1 | `w4cd` | ✓ done |
| `beadloom-19m6` | S4 | the declared document pair and the block comparison | P2 | — | ✓ done |
| `beadloom-dibq` | S4 | the `readme-pair` gate leg | P2 | `19m6` | ✓ done |
| `beadloom-rqma.1` | ext | `waves` compares a plan against beads already in progress (BDL-UX #283) | P1 | — | ✓ done |
| `beadloom-rqma.2` | ext | the axes decision warns an axis is not a role; `impact` names unreadable ownership on the row (BDL-UX #284) | P1 | — | ✓ done |
| `beadloom-yn6i` | ext | three more surfaces count stale pairs as docs; `prime` drops the code file | P1 | — | ✓ done |
| `beadloom-6rgr` | ext | `docs polish` matches a node's source by path component, not string prefix | P1 | — | ✓ done |
| `beadloom-rqma.3` | ext | ~~waves ignores an appended `refs:` line (BDL-UX #285)~~ — withdrawn, not a defect | — | — | ✓ done |
| `beadloom-rqma.4` | ext | one rule for 'a file lies under a node's source', called by routes, `docs polish` and git activity | P1 | — | ✓ done |
| `beadloom-rqma.5` | ext | one computation of the stale-pair count, populations named, in the existing seam | P1 | — | ✓ done |
| `beadloom-956f` | — | test: the acceptance scenarios, on foreign projects and the built artifact | P0 | `h7b3`, `39ap`, `jtcx`, `dibq` | ✓ done |
| `beadloom-qae9` | — | review, under withholding, in a clean room | P0 | `956f` | ready |
| `beadloom-egvd` | — | tech-writer | P1 | `qae9` | blocked |

Confirmed against the titles bd echoes, not against ids: `bd dep tree beadloom-956f` shows all
four dev branches with their sub-dependencies, and `bd ready --limit 0` names exactly the five
roots.

## Source beads this epic takes up

`beadloom-4fdn` (BDL-UX #282), `beadloom-5cpe` (BDL-UX #214) and `beadloom-y8mi` stay open and
carry a comment pointing here. Each closes only after its BDL-UX entry has been **re-run against
current behaviour** and moved to `Closed Issues` — the standard that section sets for itself, and
which a sweep on 2026-09-10 proved necessary by checking four entries and finding three still
live. BDL-UX #281 has no bead of its own; S3 is its bead.

## Progress log

**2026-09-10 — planning.** Four Explore roles derived the axes, one per defect, eighteen sections
in all. The type was decided by the count and not by the request: thirteen nodes in scope, so the
full flow. Four open questions were closed before beads were cut, and two of them were closed by
finding the question itself wrong — Q2 assumed all six direct readers read the graph as a graph,
and at least two do not; Q3 assumed a doubled line, and measurement showed four genuine pairs
whose rendering drops the field that tells them apart.

Two things the derivation reported about itself, and both shape the plan: `beadloom impact`
reads Python, so four of the nine version-stating surfaces are `unreadable-target` and S3 needs
its own reader; and the seven-reader split in `.beadloom/_graph/` is a grep result, not a
derivation — `impact` produced no axis naming it.

**2026-09-11 — S3 dev (`beadloom-w4cd`) landed.** `doc_sync/version_surface.py` derives every
place this project states its own version and attributes each to the instrument whose population
holds it. The instruments are named — `packaging-manifest`, `docs-audit`, `graph-summary-facts`,
`doctor`, `test-suite` — and every population is read from the project's own declarations: the
manifest for the packaging version and the test paths, the rules file for the lint rule, the
scanner's own surface resolution for the audit, and the flow manifest for the agent-instruction
adapters. No place is named in the module, and a test parses the source with its docstrings
stripped and fails if one appears.

Measured on this repository: 41 places across 20 files, read out of 1 375 files; 8 judged and 33
by nothing. All nine of 2026-09-10 are among them with the checkers that measurement recorded.
The count is a floor rather than a ceiling — waves 1 and 2 of this epic added documents that
state the current release, which is the thing the hand-written list of nine kept getting wrong.

Two limits are stated rather than worked around. The sweep is by the CURRENT literal, so a place
that has already gone stale is invisible to it and the command is run BEFORE the bump; the
alternative was measured, not assumed — reading every version token this project's prose
attributes to itself returns 674 claims across 137 files, because the planning archive holds
every version it ever had. And a statement is not told from a record of a measurement by any
structure the module can read, so inside an instrument's population the instrument decides and
outside it the reader does.

**2026-09-10 — S4 dev (`beadloom-19m6`) landed.** `doc_sync/document_pairs.py` compares a
declared pair by SHAPE: the block sequence, the heading levels and the row counts of the lists
and the tables, aligned with `difflib.SequenceMatcher` and reading tables through
`doc_sync/tables.py` rather than becoming a fifth reader of markdown. The pair is declared under
`document_pairs:` in `.beadloom/config.yml`; a project that declares none is not judged.

The brief's red case did not survive measurement and the bead comment carries the numbers. The
pair AGREED at `0404280f` (86 blocks each) and at `aa21caff` (109 each); the divergence was
introduced by the Russian-side edits of 2026-09-10 and lived only between `31f8c9cb` and
`97fafca5`. `31f8c9cb` is what the fixtures carry, and the comparison reports the missing
paragraph there: ru 109 blocks, en 108, 108 compared, one `unpaired-block`. The two files were
362 and 360 lines that day, not equal — still a number nothing reads, and one a translator's
wrapping moves by the same amount.

Verdict: green in a clean room over 10 carried files — pytest 9832 passed, ruff, `mypy --strict`
on each of 3.10-3.13 as a target, and `beadloom ci` all rc 0. The combined tree is
`beadloom-4ad3`'s to measure.

**2026-09-10 — S2 dev (`beadloom-4ad3`) landed.** The seven readers of `.beadloom/_graph/` are
classified by experiment rather than by reading: each was asked the same question over two
directories holding the same nodes and different bytes, and then over two holding different
nodes. Five read for NODES and two read for BYTES — `change_detection._scan_project_files` and
`setup._graph_files_now` — and for those two the policy is inapplicable by nature, because a
file that will not parse still has bytes. Q2's premise was wrong in the way the RFC suspected.

`read_declared_docs` and `link` were routed through `each_graph_file`. The other three node
readers could not be, for ONE boundary rather than three judgements: all three are in `graph`,
the policy is in `onboarding`, and `onboarding` already imports `graph`, so the reverse import is
a cycle `no-dependency-cycles` refuses at error severity. Each names the policy in its own
docstring and the policy names each of them, and both ends are asserted. Two of the three would
keep a behavioural exemption regardless — `load_graph` must report a file it cannot parse rather
than skip it, and `compute_diff` compares a tree against content at a git ref, where a directory
walk covers one side. The remaining duplication is `beadloom-4axf`, filed rather than done
mid-wave, because the RFC says routing that turns out large becomes a bead and not a redesign.

Two of the three shapes of BDL-UX #220 are closed as a consequence, measured over all eight cells
of `init`'s own entry-point-by-mode table. The third is not an unreadable file and no skip policy
reaches it: `added: 2026-09-02` loads as a `datetime.date` and dies in `load_graph` on
`json.dumps`. BDL-067 `.25`'s pin was built to fail on this day and did.

Verdict: green in a clean room over 13 carried files, `room-beadloom-4ad3` built from `9c814e02`
— which already carried S4 — with its own interpreter: 9876 passed, 61 skipped, 17 xfailed,
`mypy --strict` 0 issues over 287 files, ruff clean. That room carries no `.git` and can take no
freshness verdict. Green on the tree, Darwin arm64 CPython 3.13.7: 9924 passed, 13 skipped, 17
xfailed; `mypy --strict` green against all four declared targets, which varies the version the
checker is asked about and not the interpreter it runs under. Of 21 declared rooms this run
entered none.

**2026-09-11 — wave 1 landed.** `beadloom-19m6` at `9c814e02`, `beadloom-4ad3` at `11485a31`.
The gate owner reported both measurements in the words that name them: green in a clean room
over 13 carried files, and green on the tree after both had landed.

Two corrections came out of the wave, and neither was made by the coordinator:

- **The red case in `19m6`'s brief was wrong.** The coordinator named `0404280f` as the commit
  where the README pair diverged. Measured: they agreed there (86 blocks each) and at `aa21caff`
  (109 each); the divergence lived only between `31f8c9cb` and `97fafca5`, because `0404280f` is
  the squash that already contains the fix. The fixtures carry `31f8c9cb`, where the comparison
  reports `ru 109, en 108, one unpaired-block`. Had the brief been believed, the test would have
  been green from birth — the empty population this epic exists to remove.
- **Two axis rows were ruled wrong at planning.** `reindex` and `graph-diff` were marked out of
  scope as blast radius; BEAD-05 measured that both parse nodes, which made touching them its
  assignment. `scope-check` reported the disagreement between the approved axes and what landed.
  The RFC is corrected in place, thirteen nodes to fifteen.

A follow-up was opened rather than absorbed: `beadloom-4axf` — the graph-file skip policy lives
in a domain the graph domain may not import, so three readers restate it. The duplication is
forced by a boundary this project declared, not by carelessness.

**2026-09-11 — wave 2 landed.** `beadloom-cgco` at `63430c9e`, `beadloom-dibq` at `b8b05e16`.
The gate owner reported green in a clean room over 10 carried files and, separately, green on
the tree at `b8b05e16` — pytest 9964 passed, ruff, `mypy --strict` on each of 3.10–3.13, and
`beadloom ci` rc 0 with `readme-pair PASS: 1 pair(s) held, 109 block(s) compared, 0 finding(s)`.
It then named what those two verdicts do NOT cover: both were taken in the same local room, so
the eight Ubuntu legs and the two locale legs remain unmeasured. That sentence is the reason
the wave can be trusted as far as it goes and no further.

`beadloom-cgco` found the defect wider than the plan had it. The plan named two node emitters;
the measurement found five sites — `bootstrap.py` and `doc_classify.py` emit, and
`import_scan.py` and `parent_edges.py` were RECOMPUTING a cluster's `ref_id` rather than reading
the one it was written under. Four independent derivations of one name, agreeing by luck. A
single allocator (`scanner/ref_ids.py`) now hands them out and the others read.

Ten unit cases and all three scenarios were measured red against HEAD before the fix, on a
project built for the purpose. On a repository where the defect does not reproduce, a test that
was never red is a population of zero wearing a green tick.

**2026-09-11 — wave 3 landed.** `beadloom-w4cd` at `e41e7a10`, `beadloom-39ap` at `5cdf1422`.
Gate owner: green in a clean room over 5 carried files, and separately green on the tree after
both landed — `beadloom ci` rc 0, pytest 10034 passed. Neither verdict covers the Ubuntu legs
or either locale leg, and the target-version sweep does not vary the interpreter the checker
runs under; the report says so.

Both beads found the ground wider than the plan:

- **`39ap`: `graph/diff.py` had been reducing duplicates the OPPOSITE way to the loader**, so one
  graph file was two different graphs depending on which reader met it, and `diff` reported
  against a state the loader never saw. The plan asked only that the reduction be reported; the
  attempt found two reducers that disagreed. They share one rule now. This was reachable only
  because wave 1's `4ad3` had counted the readers by name.
- **`w4cd`: the version is stated in 41 places across 20 files.** The coordinator derived seven
  by hand, the instruments found nine, and the derivation finds forty-one — including all nine
  of 2026-09-10 with their checkers. No place is written down in the source and a test enforces
  that, which is the criterion that keeps the module from becoming the checklist it replaced.

**2026-09-11 — S3 dev (`beadloom-jtcx`) landed.** `beadloom version-surface` renders what
`doc_sync/version_surface.py` derives: the source of truth with the manifest chain it was followed
through, every place grouped by file, the instrument each place belongs to, the places no
instrument holds with the reason each falls outside, the five instruments with what each turned
out to hold here, the sweep's own population, and the limit to read first.

The grouping is the decision. Rows group by file AND reason together, so a file whose lines fall
outside for two different reasons reads as two facts rather than one averaged sentence — and the
nine issue-log lines that would otherwise be nine unattributed rows read as one group with one
reason. `beadloom-w4cd` left this as a note: 33 of its 41 rows were unjudged and nine of those
were one file, so a flat per-line list is a report nobody finishes, which fails the same way as
not printing it at all.

Exit `0` when the surface was derived, including when places are checked by nothing: the gap is
what the report exists to state, and a release that has to read it is not a release that failed.
Exit `2` is for a version that could not be derived, with the reason on standard output.

**The answer was checked against what cutting 4.0.0 actually had to edit, rather than against the
brief.** Commit `f3b5593e` added 23 lines carrying the new literal, across 13 files, measured
with `git show --unified=0` on 2026-09-11. The command reports 22 of the 23 at their current line
numbers. The 23rd is in `.beads/issues.jsonl`, the tracker's own export, which the sweep prunes
because no release edits it by hand. `ROADMAP.md:3` was reworded by `0404280f` after the release
and is still reported at that line, because it still states the literal. So every file the
release touched for its version except the tracker export is named, and each of the nine that
BDL-UX #281 lists carries the checker that release recorded for it.

The count moved while this bead was open, and the first account of the move was wrong. The
derivation measured 41 places in 20 files at `e41e7a10`, and 43 in 22 at `3693301d`, after the
wave-3 records commit. This bead's own files then add eleven more, for 54 places in 27 files,
measured by comparing the derivation over `git archive HEAD` with the working tree. They are a
scenario, two test modules, the command module, this record, and the CLI reference, whose sample
output alone holds five. Each states the current release while describing the thing that finds
it. The surface grows with the work, which is the property that makes a written list of it wrong
and a derivation right.

**2026-09-11 — S1 dev (`beadloom-qylh`) landed at `26dfbbb3`.** The node templates gain a
`modules_section` placeholder, and a skeleton written for a directory source names each Python
file directly inside it. The pair is named and never attested at write time. The placeholder
heading is not a required section, so no document written earlier is found to lack it.

The PLAN's premise did not survive measurement. It said the modules "are already in the index
the same `init` run built". On `init --yes` they are not, because `non_interactive_init` writes
the skeletons before its reindex, and on a virgin project no database exists at that moment. A
list read from the index would have been empty on exactly the run BDL-UX #282 measured, so the
list is read off the disk. The same ordering leaves every such skeleton without its Public API
table, which is filed as `beadloom-8lmj` rather than absorbed.

The first attempt imported the scanner's code-extension set and `lint --strict` refused it as a
cycle, because `agent-prime` owns that set and already depends on `doc-generator`. The list is
therefore Python files, which is the population `missing_modules` reads, and a unit test runs
that rule over a generated skeleton to hold the two populations together.

Measured on repositories that are not this one. On the published 4.0.0 wheel the two-package
layout ended `ci` rc 1 over 4 stale pairs, and the single-package layout ended rc 0 over 0 pairs
with `Nodes: 1`. On a wheel built from this tree the two layouts end rc 0 over 4 and over 2 fresh
pairs. The pre-commit scope check reported the three template files outside the declared axes,
because the RFC rules `onboarding` out as a caller. The template is where a skeleton's shape
lives, so the RFC row is what needs correcting.

**2026-09-11 — S1 dev (`beadloom-h7b3`) landed at `44034c81`.** A stale verdict now names its pair, and the remediation
it prints can clear the reason it was printed for. Reproduced first on a foreign repository with
the tree's own `beadloom`: after `init`, one module name taken out of the `ledger` README gave
`ci` rc 1 over `3 stale doc(s)` and one document, three identical findings telling the reader to
run `sync-update ledger`, and `sync-update --yes --all` rc 0 with the verdict unmoved.

Which reasons an attestation clears was measured, not read. Through the real reindex,
`attest_ref` and `check_sync` pipeline, `hash_changed`, `hash_changed_since_head` and
`symbols_changed` cleared, while `untracked_files` and `missing_modules` did not.
`REASONS_ATTESTATION_CLEARS` in `doc_sync/engine.py` holds the three as an allow-list, so a
reason added later is not told to re-attest until it is measured. The measurement found two more
instructions that could not be followed. The gate told a `no_baseline` pair to "attest the pair
with `sync-update`", and the bare form claims no unverified pair, so it attests nothing.
`sync-check --since --report` recommended `sync-update` for a verdict that reads git history,
and attesting every pair left that verdict exactly as stale. Both now name what does clear them.

`sync-update --yes` re-checks after attesting and names every pair still stale with what clears
it. Its exit code and its scope are unchanged, as Q1 decided. The gate's line counts
`stale pair(s)`, and every `sync-check` line that names a pair prints its code file. The
`--json` shape is untouched and a test pins it. Three more surfaces print `stale doc(s)` over a
count of pairs — the TUI, the site dashboard and `prime`. They are outside this bead's scope and
are filed as `beadloom-yn6i`.

Gate owner of a wave of one, two claims. Green in a clean room over 19 carried files, built from
`d09c24ae` with its own interpreter: pytest 10082 passed, `mypy --strict` and ruff clean, and
`beadloom ci` rc 0. That room has no `.git`, so its sync-check verified no pair. Green on the tree
at `1e63bf14`, which includes a coordinator commit landed while this bead ran: pytest 10129
passed, `mypy --strict` against targets 3.10 to 3.13, and `beadloom ci` rc 0 over 460 fresh pairs.
A tree run taken while that commit was landing failed one issue-log test, and the same test
passed at `44034c81` alone and at `1e63bf14`. Neither verdict entered any of the 21 declared
rooms, so the Ubuntu and locale legs are unmeasured.

**2026-09-11 — S1 dev (`beadloom-8lmj`) landed at `0754003a`.** A skeleton's Public API table
is parsed from the code under the node's source, and no longer read from the index.

The half of the bead that had only been read was measured first, and it held. On a wheel built
from this tree, against a foreign project holding `src/ledger/` and `src/billing/`, the wizard
wrote the table and `init --yes` did not. `diff -r` between the two `docs/` trees differed in
exactly the two tables, and `beadloom ci` was rc 0 on both. The measurement found the defect
wider than the bead said. `init --bootstrap` wrote the same table-less documents as `--yes`,
and `docs generate` on a clone wrote them too, because `init` lists the index in `.gitignore`.
Three of four ways to write a skeleton had no index, and only the wizard had one.

That count chose the fix. Reindexing before and after inside `non_interactive_init` would have
closed one of the four. It would also have left the document a function of index state, which
every caller then has to remember — the shape BDL-067 `.18` and `.21` closed at two callers
and the review of `.20` found open at a third. The parser is the one the reindex calls per
file, so the two readers see one population. A test builds a real index and compares them.
They differ in one corner that was measured: the index reader matches by string prefix and
gives `src/ledger/` the symbols of `src/ledger_archive/`. That reader still serves
`docs polish`, and the defect is filed as `beadloom-6rgr`.

The init order is untouched. After the fix, the `--yes` `docs/` tree is byte-identical to the
one the wizard wrote before it. Parsing is lazy because unconditional parsing was measured: on
this repository it walked 17 294 files in about 13 s, for a run that wrote nothing.

**2026-09-11 — extension dev (`beadloom-rqma.1`, BDL-UX #283).** A wave plan is compared
against the beads already in progress under its work item, and a conflict with one is printed
apart from the plan's own serialisations. The first line now reads
`0 serialisation(s), 1 against 1 running bead(s)`, a wave names the running beads a bead of it
waits for, and `--json` carries the same facts under `running`.

Reproduced red first on a bd 1.0.4 rig that is not this repository, with the tree's own
`beadloom` at `e3a0ab1d`: an epic holding one bead in progress and one ready, both declaring
`billing`. `--parent` answered `1 wave(s) for 1 bead(s), 0 serialisation(s)` and a population
notice about the ready bead only, while naming the pair gave `shared_node: billing`. After the
change the same rig answers `1 against 1 running bead(s)` and
`rig283-1mw.2 waits for rig283-1mw.1 — shared_node: billing`.

Three decisions, each with its reason. A conflict with running work is not a finding, because
a serialisation is a decision the shape makes rather than a defect of it. A bead known to be in
progress whose record `bd show` could not return IS a finding, `running_not_compared`, because
the count beside it is then a claim about part of the running work. A running bead with no
declared scope serialises every planned bead behind it and is not exempted, because an unknown
scope is not an empty one. That case is rare: 3 of 51 beads with children here were ever
started. The rig found one wording defect before it shipped. The pair form said
`no bead under <epic> is in progress` while the running bead sat in the plan, and it now says
`outside this plan`.

Gate owner of a wave of one, two claims. Green in a clean room over 18 carried files, built
from `e3a0ab1d` with its own interpreter: pytest 10126 passed, 61 skipped, 17 xfailed; ruff
clean; `mypy --strict` clean against targets 3.10 to 3.13; `beadloom ci` rc 0. That room has no
`.git`, so its sync-check verified none of 461 pairs and its scope-check skipped. Green on the
tree at `801a9a9b`, after this bead landed on top of the coordinator's `5f135109`: pytest 10174
passed, 13 skipped, 17 xfailed, with `HEAD` unchanged across the run; `beadloom ci` rc 0 over
461 fresh pairs. An earlier tree run at the same commit failed one test,
`test_the_live_repo_index_is_byte_identical_after_a_real_evaluation`, because this bead ran
`beadloom waves` and `bd comments add` against the live repository while it ran. That test's
own docstring names that confound, it passed alone, and the full re-run with nothing else
writing is the verdict above. Neither verdict entered any of the 21 declared rooms, so the
Ubuntu legs and both locale legs are unmeasured, and the target sweep does not vary the
interpreter mypy runs under.

Measured on this epic after landing, while this bead was still in progress:
`beadloom waves --parent beadloom-rqma` answered `3 against 1 running bead(s)`. All three ready
beads wait for `beadloom-rqma.1`: `6rgr` over `doc-generator`, and `rqma.2` and `yn6i` over
`agent-prime`. Both nodes are reached through the `onboarding` ref this bead declares.

**2026-09-11 — extension dev (`beadloom-6rgr`) landed at `855f6dff`.** `docs polish`, and the
MCP `generate_docs` tool that returns the same data, give each node the index rows of the files
under its source by path component. A file is under the source when its path is the source or
continues it past a `/`. The instructions in that payload tell an agent to describe the node from
those symbols, and until now `src/ledger/` also took `src/ledger_archive/` and
`src/ledger_tools.py`.

Reproduced red first on a foreign repository with the tree's own `beadloom`, after `init --yes
--mode bootstrap` and `reindex`: `docs polish --ref-id ledger` named `export, record, replay`,
where the package holds `record`. The bead named a sibling directory; a sibling module is taken
as well, measured. After the fix the same command names `record`.

The brief named two fixes, and the measurement chose between them. Routing polish through the
directory walk `beadloom-8lmj` gave the skeleton would have removed a second reader of one fact.
It was rejected for two reasons. Over this repository's 104 nodes the walk took 12.45 s and gave
the site node 68 382 symbols from `node_modules`, while the index took 0.006 s. And every other
field of the polish payload — drift, edges, routes, activity and tests — is read from the index,
so disk symbols would describe a different tree from the rest of one payload after an edit that
was not re-indexed. `infrastructure.repository.source_covers` was rejected too, because it
answers ownership: a package façade covers its package there, which would set the two readers
against each other on that shape. What the two-reader shape costs is held by a test instead:
both readers over one tree holding prefix-sharing siblings, the index built by the real reindex,
for five shapes of source.

Nineteen tests were added, and each was measured red against at least one of three bodies: HEAD,
the naive `startswith(source + "/")` that leaves a single-file source empty, and a string prefix
without its empty-source guard. On this repository the reader returns the same 6 842 symbols
before and after, so no node here had a prefix-sharing sibling, which is why it survived.

The measurement found the defect one field wider. The routes in the same payload come from
`nodes.extra`, which `application/reindex/enrichment.py` fills by string prefix, and on the rig a
FastAPI handler in `src/ledger_archive/api.py` was reported as a route of `ledger`. That is
outside the declared scope `doc-generator` and is filed as `beadloom-rqma.4`.

Gate owner of a wave of one, two claims. Green in a clean room over 7 carried files, built from
`63e38e65` with its own interpreter: pytest 10145 passed, 61 skipped, 17 xfailed; ruff clean;
`mypy --strict` clean against targets 3.10 to 3.13; `beadloom ci` rc 0. That room has no `.git`,
so its sync-check verified none of 461 pairs and its scope-check skipped. Green on the tree:
pytest over `63e38e65` plus exactly those 7 files, `HEAD` unchanged across the run, 10193
passed, 13 skipped, 17 xfailed; and `beadloom ci` rc 0 at `855f6dff` over 461 fresh pairs.
Neither verdict entered any of the 21 declared rooms, so the Ubuntu legs and both locale legs
are unmeasured, and the target sweep does not vary the interpreter mypy runs under.

`bd close --suggest-next` named `beadloom-956f` as unblocked. `bd ready --limit 0` does not
list it, because `rqma.2` and `yn6i` are still open.

**2026-09-11 — extension dev (`beadloom-rqma.2`, BDL-UX #284) landed at `3e1bd77c`.** Two
halves, for the two causes the entry names. Where a person rules axis rows, the shipped sources
now say the axis a node surfaced under is not its role and that a `callers` row can be a work
site: `/task-init` Step 0.5, its BRIEF step and both checklists, both `## Axes` skeletons in
`/templates`, and the Explore role. They were recomposed with `beadloom setup-agentic-flow`.
And `impact` names, on each row, the files the row's node owns and the derivation did not read.
It does this through `ImpactAnswer.unread_ownership`, a `node-owns-unread-files` entry in the
unresolved population, and a new `Owns unread` column in the rendered section.

Reproduced red first on a foreign rig with the tree's `beadloom` at `7eadb4b4`. A node `skel`
owned `templates/domain.md.txt`, which its generator reads after calling the target.
`impact --section` wrote `callers | skel | 1 — src/app/skel/generator.py:8 | ? |` and
`Unresolved: 1 no-seed`, and nothing named the template. After the change both `skel` rows
carry `1 — src/app/skel/templates/domain.md.txt`. On this repository,
`impact src/beadloom/onboarding/presets.py --section` writes
`49 — src/beadloom/onboarding/templates/agentic_flow/CLAUDE.md.txt` on both `onboarding` rows,
which is the node this epic ruled out and re-ruled.

The column is the decision the reader constraint made. A mark inside `Sites` could not tell a
table written before the change from a row whose node owns nothing unread. A column read by
header can: an old table reads `None`, meaning not stated, and a rendered `none` reads `0`.
No hand-written `Sites` cell, such as `1–4`, is parsed for a mark. `beadloom axes` printed
byte-identical `--json`, text and `--refs` output over all 202 planning documents before and
after the change, and BDL-069's `--refs` named the same 23 nodes. It was measured again after
`9b49b4a0` added `git-activity`: the reader at that commit and the changed reader agree on every
document, and on 24 nodes for this RFC.

Gate owner of a wave of one, two claims. Green in a clean room over 26 carried files, built from
`9b49b4a0` with its own interpreter: pytest 10173 passed, 61 skipped, 17 xfailed; ruff clean;
`mypy --strict` clean against targets 3.10 to 3.13; `beadloom ci` rc 0. That room has no `.git`,
so its sync-check verified none of 463 pairs and its scope-check skipped. Green on the tree at
`3e1bd77c`, with `HEAD` unchanged across the run and the tree differing from it only in `.beads/`
and this file: pytest 10221 passed, 13 skipped, 17 xfailed; `beadloom ci` rc 0 over 463 fresh
pairs. Neither verdict entered any of the 21 declared rooms, so the Ubuntu legs and both locale
legs are unmeasured, and the target sweep does not vary the interpreter mypy runs under.

Left for the tech-writer, because the files belong to `cli` and `yn6i` reaches `cli.md`:
`docs/services/cli.md` still lists the `--json` fields without `unread_ownership`, and
`beadloom axes --json` does not print the parsed column. `bd close --suggest-next` named
`beadloom-956f`. `bd ready --limit 0` does not list it, because `yn6i` and `rqma.4` are open.

**2026-09-11 — extension dev (`beadloom-rqma.4`) landed at `9f435a18`.** The rule "a file lies
under a node's source" had three bodies in three domains, and all three now call
`infrastructure.node_source.NodeSource`: `doc_generator._symbols_for_node`, the route
attribution in `reindex/enrichment.py` and `git_activity._map_file_to_node`. A file lies under
a source when its path is the source or continues it past a `/`. The declared source is
normalised once, and a source that declares nothing holds nothing.

Reproduced red first on a foreign repository with the tree's own `beadloom`. After `init --yes
--mode bootstrap`, with a FastAPI handler for `/replay` in `src/ledger_archive/api.py`, `docs
polish` gave `GET /replay` to `ledger` and to the root node, whose source is `''`. After the
change the same steps give it to `ledger_archive` alone. One table of eleven source shapes runs
against all three sites. Before wiring, it found the two copies called correct disagreeing too:
`git_activity` held nothing for a whitespace-padded source, and `doc_generator` held nothing for
a source written with `./`.

The placement was measured rather than chosen by layer name. `git_activity` is infrastructure
and may import nothing above it, so the body lives there. `onboarding-no-direct-infra` refuses
that import to `doc_generator` at error severity, so `rules.yml` carries a stated exemption,
and `lint` reports 8 suppressed crossings where it reported 7. A domain placement passed `lint
--strict` as well, and it was rejected for that reason. `architecture-layers` skips every edge
with an untagged end, so a probe import that made the edge `git-activity -> doc-sync` drew no
finding. That gap
is filed as `beadloom-t6zq`, with one live reverse edge the rule does not report.

The measurement found one more defect in the same function. The route store only ever wrote a
node that had routes, so an incremental reindex after a code change left the misattributed
route in place on the rig, and a route deleted from the code survived too. The store now
withdraws the key from a node that holds no route. An incremental reindex that finds no changed
file still returns before that step, so an index built under the old rule keeps its routes
until a file changes or `reindex --full` runs. The SPEC states that limit.

Gate owner of a wave of one, two claims. Green in a clean room over 17 carried files, built
from `621258f8` with its own interpreter: pytest 10237 passed, 61 skipped, 17 xfailed; ruff
clean; `mypy --strict` clean against targets 3.10 to 3.13; `beadloom ci` rc 0. The room's first
full run was rc 1 on one test, whose copied acceptance run failed in an unrelated scenario when
`uv pip install` exited 1. That test passed alone and in the second full run, and the cause was
not reproduced. The room has no `.git`, so its sync-check verified none of 465 pairs. Green on
the tree at `9f435a18`, with `HEAD` unchanged across the run and the tree differing from it
only in `.beads/` and this file: pytest 10285 passed, 13 skipped, 17 xfailed; `beadloom ci` rc 0
over 465 fresh pairs. Neither verdict entered any of the 21 declared rooms, so the Ubuntu legs
and both locale legs are unmeasured, and the target sweep does not vary the interpreter mypy
runs under.

`bd close --suggest-next` named `beadloom-956f`. `bd ready --limit 0` does not list it, because
`yn6i` is open.

**2026-09-11 — extension dev (`beadloom-yn6i`) landed at `57ece490`.** Three surfaces printed a
count of stale pairs as documents. All three keep counting pairs and now say `pair(s)`. The
terminal dashboard's `s` key says `Sync: N stale pair(s)`. The site dashboard's stale alert says
`N stale pair(s)`, next to the docs card that counts the same rows as `N stale of M tracked`.
`prime` says `Health: N stale pair(s)` under a `## Stale Pairs` heading, and each of its lines
reads `- <doc> <-> <code> (<ref_id>)`, the way `sync-check` renders a pair. Its `--json`
output already carried `code_path` and is unchanged. The alert keeps the kind `stale_doc`,
because that value is a key.

Reproduced red first on a foreign repository, one README over three stale pairs:
`Sync: 3 stale doc(s)`, `3 stale doc(s)`, and `Health: 3 stale docs` above three identical
`- domains/ledger/README.md (ledger)` lines. A distinct-document count was rejected on every
surface, because each shows a number that a neighbouring surface already shows as pairs.
`AlertBanner.vue` needs no change. It renders `a.message` from Python, and its hard-coded
sentence is the all-clear, which states no count. The grep found the same label over a pair count
in `why`, the TUI dependency path, `status` and MCP `get_status`, outside this bead's scope.
Those are filed as `beadloom-rqma.5`, a new open child of this epic.

Gate owner of a wave of one, two claims. Green in a clean room over 14 carried files, built from
`c274e5c0` with its own interpreter: pytest 10250 passed, 61 skipped, 17 xfailed; ruff clean;
`mypy --strict` clean against targets 3.10 to 3.13; `beadloom ci` rc 0. The room has no `.git`,
so its sync-check verified none of 465 pairs and its scope-check skipped. Green on the tree at
`57ece490`, with `HEAD` unchanged across the run and the tree differing from it only in `.beads/`
and this file: pytest 10298 passed, 13 skipped, 17 xfailed; `beadloom ci` rc 0 over 465 fresh
pairs. Neither verdict entered any of the 21 declared rooms, so the Ubuntu legs and both locale
legs are unmeasured, and the target sweep does not vary the interpreter mypy runs under.

`bd close --suggest-next` named `beadloom-956f`, and `bd ready --limit 0` lists it: every dev
bead it depends on is closed.

**2026-09-12 — extension dev (`beadloom-rqma.5`) landed at `4bb56219`.** "How many stale pairs
are there" was computed afresh at every call site, so each site was free to name its own number:
nineteen surfaces read `sync_state` and report a figure, under FOUR populations, all called "stale
docs". One computation now answers it. `infrastructure/repository.py` holds `StaleCount`, built
through `StaleCount.of_pairs(n)` and never directly, so the number and the word for it cannot be
separated at a call site; `count_stale_pairs(conn, ref_ids=None)` returns it and
`stale_node_refs(conn)` is the differently named reader of the different population.
`application/graph_reads.py` re-exports all three, which is how the TUI reaches them.

The placement was measured rather than trusted: `lint --strict` reports 0 errors and the same 8
suppressed crossings `rqma.4` left, so NO new `rules.yml` exemption was needed — the derivation's
paragraph was right, and the measurement is what says so. `onboarding/scanner/prime.py` is the one
surface the computation cannot reach: `onboarding-no-direct-infra` exempts `infrastructure/db` and
not `infrastructure/repository`, and that entry's own exit condition is `prime_context()` moving to
the seam whole (BDL-UX #150). It keeps its copy of the sentence, and a test names it as the one
permitted site.

Twelve surfaces take the sentence from there. Four said the wrong noun over a correct population —
`beadloom why` and the TUI dependency path now say `Stale pairs:` over the same number, `beadloom
ctx` says `## Stale Pairs` and `sync-check --report` says `### Stale Pairs`. The TUI status bar
printed `2 stale`, a number with no noun at all, and now prints `2 stale pair(s)` beside the
dashboard card's `2 stale of 5 tracked pair(s)`; the MCP `get_status` description says stale pair
count. The four `h7b3` and `yn6i` had already fixed keep their output byte-for-byte and now build
it from the shared class, which is what makes a fifth site unable to be born mislabelled: a test
walks every module under `src/` and asserts the literal `stale pair(s)` is spelled in exactly two.

`tui/widgets/node_detail.py` is removed, measured first: no module under `src/` imported
`NodeDetail`, `docs/services/tui.md`'s module map never listed it, and its only readers were seven
tests that asserted nothing but "no exception".

The populations still in question were NOT decided — that half is `beadloom-r9t5`, outside this
epic. Five sites are recorded there with line numbers: the `status` trend row (`status.py:104`
counts stale+missing, `health.py:42` counts stale only, `commands/status.py:257` renders both on
one row), `debt_report` counting nodes under a pair-shaped SPEC, the `doc_status` screen counting
nodes beside per-pair numbers, `site.py:211` printing a fourth population with no noun, and
`site-generation/SPEC.md:58-60`, which states a population its own dashboard code does not use.
One derivation error was corrected by reading the site: `recommendations.py:82` is per NODE, as
its description said and its summary denied.

Gate owner of a wave of one, two claims. Green in a clean room over 23 carried files, built from
`c1e5dac7` with its own interpreter: pytest 10259 passed, 62 skipped, 17 xfailed; ruff clean;
`mypy --strict` clean against targets 3.10 to 3.13; `beadloom ci` rc 0. `--carry` can only add, so
the room reproduced the deletion by removing that one file after it was built. The room has no
`.git`, so its sync-check verified none of 465 pairs and its scope-check skipped. Green on the
tree at `4bb56219`, with `HEAD` unchanged across the run and the tree differing from it only in
`.beads/`: pytest 10308 passed, 13 skipped, 17 xfailed; `beadloom ci` rc 0 over 465 fresh pairs,
after 21 pairs were re-attested to the fixpoint. Neither verdict entered any of the 21 declared
rooms, so the Ubuntu legs and both locale legs are unmeasured, and the target sweep does not vary
the interpreter mypy runs under.

`bd close --suggest-next` named `beadloom-956f` and `beadloom-r9t5`, and `bd ready --limit 0`
lists both.

**2026-09-11 — PAUSED at the owner's request, after the last dev bead landed.**

Every dev bead is closed: the nine planned, and the six taken in the scope extension
(`8lmj`, `yn6i`, `rqma.1` #283, `rqma.2` #284, `6rgr`, `rqma.4`, `rqma.5`), with `rqma.3` (#285)
withdrawn as not-a-defect. No agent is running, no merge slot is held, and nothing is
half-landed. Tree at `8ba896e1` plus this record, pushed.

**Next on resume: the test wave, `beadloom-956f`.** Then `qae9` (review, under withholding) and
`egvd` (tech-writer), then the PR. `egvd` already carries three documentation obligations in its
comments — the stale-index upgrade note from `rqma.4`, `parallel-waves.md:86` from `rqma.1`, and
`cli.md` for the `Owns unread` column from `rqma.2`.

**The decision that was waiting has been split and half of it taken.** `beadloom-rqma.5` was
narrowed by the owner to the MECHANICAL half and is closed (above). The DECISION half is
`beadloom-r9t5`, a new open bug outside this epic: four populations are called "stale docs", and
what each surface SHOULD count is a decision, not a rename. It is NOT wired into the test bead.

**Two out-of-epic items recorded elsewhere:** `beadloom-t6zq` (P0, its own next epic, in the
ROADMAP — `architecture-layers` evaluates 16 of 353 edges) and `beadloom-4axf` (P2).

**2026-09-12 — the test wave (`beadloom-956f`) landed.** The epic's acceptance, measured where
the PRD says it has to be measured rather than where it is convenient.

**Three of the six named scenarios did not exist.** `beadloom lint` reported them at PRD lines
155, 156, 170 and again at 192, 193, 195 — `A virgin init on a multi-package layout is followed
by a green gate`, `A virgin init on a single-package layout keeps every node it reported
writing`, and `A graph file carrying one ref_id twice is reported by every reader of the
directory`. Two of the three existed under DIFFERENT names, which is the same defect in a
different shape: `init_skeleton_names_modules.feature` says "a repository with two packages
under src passes the gate straight after init" and runs `beadloom.services.cli:main`
IN-PROCESS, which is a claim about the working tree. The third's file pinned the loader and
`graph-diff` — two of seven readers — under a name that reads as covering all of them. The PRD
was not renamed to fit; the suite now holds all six under the names the PRD references.

**The two adopter claims, measured on a wheel built from this tree and installed into an
interpreter of its own, against the published 4.0.0 for contrast.** Both projects built for the
purpose; neither exists in this repository.

| project | artifact | `init --yes --mode bootstrap` | then |
|---|---|---|---|
| `myapp`, `src/ledger/` + `src/billing/` | published 4.0.0 | rc 0, `Graph: 3 nodes` | `ci` rc **1**, `6 stale doc(s)`, `missing modules` |
| `myapp`, `src/ledger/` + `src/billing/` | this tree | rc 0, `Graph: 3 nodes` | `ci` rc **0**, `6 pair(s) fresh` |
| `myapp`, `src/myapp/` | published 4.0.0 | rc 0, `Graph: 2 nodes` | `status` **`Nodes: 1`**, `ci` rc 0 |
| `myapp`, `src/myapp/` | this tree | rc 0, `Graph: 2 nodes` | `status` **`Nodes: 2`**, `ci` rc 0 |

The published row of the second pair is the false green the epic was opened for: the node that
was lost is the `domain` carrying `src/myapp/`, and the gate exits 0 over the graph without it.

US-2 was followed end to end on the built wheel rather than asserted: a module name taken back
out of `docs/domains/ledger/README.md` gave `ci` rc 1 with `missing_modules: journal — pair
domains/ledger/README.md <-> src/ledger/core.py — name journal in domains/ledger/README.md;
re-attesting cannot clear missing_modules, because the check reads what the document says, not a
recorded hash`. Naming the module put the gate back to rc 0. The failure no longer prints
`sync-update`, each line names its own pair, and the noun is `pair(s)`.

**The scenarios found two things about their own room before they found anything about the
product.** `beadloom clean-room` runs the suite with `PYTHONPATH=<room>/src`, and a child
process that inherits it imports the room's SOURCE in preference to whatever is installed in its
own interpreter — the first room run reported the wheel's `beadloom.__file__` under `<room>/src`.
The scenario caught it because "the beadloom that ran is the installed wheel and not this working
tree" is one of its assertions rather than an assumption. And the first draft guarded the wheel
build with `pytest.skip`: `tests/test_bead14_s4_binding.py` fails on a step that steps aside
anywhere under `tests/acceptance/steps/`, in every room, and it is right — the build is RED when
it cannot happen, because `uv` is set up by every installing leg of `ci.yml` and a run without it
is a broken room rather than a room this criterion is silent about.

**The reader population is asked whole and bound to the derivation.** All seven are asked for
their whole answer over one file carrying `ledger` twice. Two reduce and both name the file, both
kinds and the dropped node's source; three keep everything they were given
(`read_declared_docs` returns both documents, `update_node_in_yaml` and `link` answer about one
`ref_id` rather than about a set); two read bytes, where the policy is inapplicable by nature.
The list travels with the scenario because the acceptance suite is copied out and run standalone,
and `tests/test_the_acceptance_asks_every_graph_reader.py` is what keeps it equal to
`beadloom-4ad3`'s derivation — an eighth reader fails there, by name.

**Two of the PRD's non-behavioural criteria are still open, and both are `beadloom-egvd`'s.**
The temporary sentence is still in both READMEs at line 177 — "The documents it writes are not
checked the same way yet, so read the first `beadloom ci` rather than assuming it" / "Документы,
которые он пишет, так пока не проверяются…" — and US-1 now holds, so it should go. BDL-UX #282
(line 112) and #214 (line 844) are both still under `Open Issues`; the re-run against current
behaviour that section's standard requires is the table above, so what remains is the move
itself. Neither is a red criterion of this bead: both are documentation, and the bead that owns
them is open.

**A hazard for any future concurrent wave, measured here by accident.** Two full pytest sessions
run at once against this working tree redden each other: several tests open the repository's own
`.beadloom/beadloom.db`, and the second opener gets `sqlite3.OperationalError: disk I/O error`
out of `PRAGMA journal_mode=WAL`. The first tree run of this bead reported three failures, two of
them exactly that, and a serial re-run was green. A clean room isolates the FILES and not that
database, because the room's tests read it by absolute path out of the tree they were copied
from. Two agents measuring at the same time is the ordinary case in a wave, so the finding is
recorded rather than remembered.

Gate owner of a wave of one, two claims. **Green in a clean room over 5 carried files,**
`room-beadloom-956f` built from `76c87d64` with its own interpreter and extras
`dev+graphql+languages+mutation+tui+watch`: pytest 10263 passed, 63 skipped, 17 xfailed; ruff
clean; `mypy --strict` clean over 292 files against each of 3.10, 3.11, 3.12 and 3.13 as a
target; `beadloom ci` rc 0. That room carries no `.git`, so its freshness leg verified 0 of 465
pairs and its scope-check skipped for want of a branch. **Green on the tree,** Darwin arm64
CPython 3.13.7: pytest 10313 passed, 13 skipped, 17 xfailed, coverage 94.55% against a floor of
80; ruff clean; `mypy --strict` 0 issues over 292 files; `beadloom ci` rc 0 over 465 fresh pairs,
with `readme-pair` holding 1 pair over 109 blocks. Neither verdict entered any of the 21 declared
rooms, so the Ubuntu legs and both locale legs are unmeasured, and the target sweep does not vary
the interpreter mypy itself runs under. The gate names its own gap in the same words: `not run by
this gate: the test suite, the style linter, the type checker` — all three were run beside it,
in both rooms.

## Waves

None launched. The first wave can hold `qylh`, `cgco`, `4ad3`, `w4cd` and `19m6` — the five
roots — and `beadloom waves --parent beadloom-rqma` derives that membership rather than taking a
list typed by hand.

## Blockers

None.
