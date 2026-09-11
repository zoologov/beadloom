# ACTIVE: BDL-069 — The checks an adopter meets first, and the populations they run over

> **Epic:** `beadloom-rqma`
> **Created:** 2026-09-10
> **Last updated:** 2026-09-11

---

## Current focus

Planning is done. PRD, RFC, CONTEXT and PLAN are all Approved, twelve beads exist, and no wave
has been launched.

## Beads

| Bead | Slice | What | Pri | Blocked by | Status |
|---|---|---|---|---|---|
| `beadloom-qylh` | S1 | the init skeleton names the modules it already knows | P0 | — | ready |
| `beadloom-h7b3` | S1 | a remediation that can be followed, and a stale line that names its pair | P0 | `qylh` | blocked |
| `beadloom-cgco` | S2 | a root node and the sole package cannot share one `ref_id` | P0 | — | ✓ done |
| `beadloom-4ad3` | S2 | measure what each of the six direct readers reads for | P1 | — | ✓ done |
| `beadloom-39ap` | S2 | the loader reports the reduction instead of performing it | P0 | `cgco`, `4ad3` | in progress |
| `beadloom-w4cd` | S3 | the reader behind `version-surface` | P1 | — | in progress |
| `beadloom-jtcx` | S3 | the `version-surface` command | P1 | `w4cd` | blocked |
| `beadloom-19m6` | S4 | the declared document pair and the block comparison | P2 | — | ✓ done |
| `beadloom-dibq` | S4 | the `readme-pair` gate leg | P2 | `19m6` | ✓ done |
| `beadloom-956f` | — | test: the acceptance scenarios | P0 | `h7b3`, `39ap`, `jtcx`, `dibq` | blocked |
| `beadloom-qae9` | — | review, under withholding, in a clean room | P0 | `956f` | blocked |
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

## Waves

None launched. The first wave can hold `qylh`, `cgco`, `4ad3`, `w4cd` and `19m6` — the five
roots — and `beadloom waves --parent beadloom-rqma` derives that membership rather than taking a
list typed by hand.

## Blockers

None.
