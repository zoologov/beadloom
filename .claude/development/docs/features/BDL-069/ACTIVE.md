# ACTIVE: BDL-069 — The checks an adopter meets first, and the populations they run over

> **Epic:** `beadloom-rqma`
> **Created:** 2026-09-10
> **Last updated:** 2026-09-10

---

## Current focus

Planning is done. PRD, RFC, CONTEXT and PLAN are all Approved, twelve beads exist, and no wave
has been launched.

## Beads

| Bead | Slice | What | Pri | Blocked by | Status |
|---|---|---|---|---|---|
| `beadloom-qylh` | S1 | the init skeleton names the modules it already knows | P0 | — | ready |
| `beadloom-h7b3` | S1 | a remediation that can be followed, and a stale line that names its pair | P0 | `qylh` | blocked |
| `beadloom-cgco` | S2 | a root node and the sole package cannot share one `ref_id` | P0 | — | ready |
| `beadloom-4ad3` | S2 | measure what each of the six direct readers reads for | P1 | — | ready |
| `beadloom-39ap` | S2 | the loader reports the reduction instead of performing it | P0 | `cgco`, `4ad3` | blocked |
| `beadloom-w4cd` | S3 | the reader behind `version-surface` | P1 | — | ready |
| `beadloom-jtcx` | S3 | the `version-surface` command | P1 | `w4cd` | blocked |
| `beadloom-19m6` | S4 | the declared document pair and the block comparison | P2 | — | ready |
| `beadloom-dibq` | S4 | the `readme-pair` gate leg | P2 | `19m6` | blocked |
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

## Waves

None launched. The first wave can hold `qylh`, `cgco`, `4ad3`, `w4cd` and `19m6` — the five
roots — and `beadloom waves --parent beadloom-rqma` derives that membership rather than taking a
list typed by hand.

## Blockers

None.
