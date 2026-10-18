# Gate Ownership (component)

Which claimed bead's commits changed the files each finding of a gate run is about, and the verdict
when none did.

**Source:** `src/beadloom/application/gate_ownership.py`

---

## Overview

This project's own branch carried a red Gate across two waves of BDL-068 S6 — two stale docs
owned by no bead in the running plan — and every gate owner in those waves had to be told by
the coordinator, by hand, that the red was not theirs, so their reports would attribute the
finding rather than discount it. Two beads (`beadloom-0mdo.41` and `.61`) each rebuilt a
control room at `HEAD` to prove a second finding was real against a background that already
held one.

A known red trains its reader to discount the next one. This project has measured that three
times: BDL-UX #233 (an intermittently-red check), #258 (one test that cannot pass in any
room, trained into thirty reports' phrasing), and this — the same shape arriving on the
**instrument** rather than in the suite.

So a finding names its owner, and *"rc 1, and none of these findings belongs to your wave"*
is something the Gate says rather than a message somebody writes every time.

**Naming an owner does not change the verdict.** It is not a step: it has no status, it adds
no finding and it moves no exit code. A finding nobody claims is still a finding, and a gate
that went green because no bead owned a red would be the false green BDL-068 exists to
remove. `tests/test_gate_finding_owner.py` fails if that stops being true.

**And the owner is the bead that did the work.** The scenarios of the rule are in
`tests/acceptance/application/gate-ownership/ownership_by_changed_files.feature`, measured on
the monorepo fixture.

## The rule: the files a bead's commits changed

The first rule attributed a finding to every claimed bead whose `refs:` declared the node that
covers the finding's path. The first outside adopter measured what that says (BDL-UX #329): in
a wave of two beads each was told it owned the same nine findings, all of them the first bead's
work, and a second work item's bead was told it owned 36 findings on files it never touched,
because its `refs:` named the node that covers the frontend's source whole. A node that covers
a directory says what a bead may touch, never what it touched.

So since BDL-083 S1c a finding is owned by a **bead the tracker reports `in_progress` right
now** whose **commits on the branch changed a file the finding is about**:

- A commit is a bead's when its message names the bead's id as a whole word — the link bd
  itself reads between a commit and an issue (`bd orphans`). `bd-1` is not read inside `bd-10`
  or `bd-1.2`.
- The commits are those `HEAD` holds against the base `scope-check` compares against
  (`declared_scope.trunk_ref`), listed by `doc_sync.git_baseline.commits_since`. A commit
  already on the trunk is nobody's work in flight.
- A bead's `refs:` attribute nothing. The declaration grammar reads node ids and no file path,
  and a node is the directory-sized claim the defect was made of.

The claim population is still the one `bead-claimed` reads, through the same port
(`application/guards/contract.WorkTracker`). The work item's `## Axes` lose because they
answer `scope-check`'s question and name the work item every agent on the branch shares. A
wave's plan loses because it names beads that have not started and beads whose wave is over.

## The files a finding is about

| Finding | Files it is held against |
|---------|--------------------------|
| locates files | the files its locations name; a document located in the documentation root's frame, as the `sync-check` findings locate one, is re-rooted onto the project's frame through the index's `docs` table |
| a stale or missing pair | its document and its code file — the pair's code file is the finding's second location, after the document |
| locates no file and names a node | the code files that node owns, by the most-specific ownership rule, and the documents declared for it; a nested node's files are not the parent's |
| locates no file and names no node | none — the finding is `unattributed`, and says so |

Everything is read **through the index**, never by opening a graph file by name.

## Two verdicts, and the reason is on every one

| Verdict | What it says |
|---------|--------------|
| `owned` | a claimed bead's commits changed a file the finding is about — the beads are named, with the file that decided it |
| `unattributed` | no claimed bead's commits changed such a file, or the finding is about no file at all |

`unattributed` is the honest answer, never "owned by the neighbour whose node covers the
directory". Two qualifications are counted beside it, because a reader acts on them: how many
of those findings sit on files the working tree changes and no commit holds yet, and how many
are about no file a commit could have changed. A claimed bead that owns nothing is named with
its reason: no commit on the branch names its id, or its commits changed none of the files the
findings are about.

A tracker that cannot answer, a project with no index, and a git that cannot list the branch's
commits against the base are a `reason` on the whole report rather than a page of
`unattributed`. Telling every gate owner "not yours" when nobody was asked would be the false
green this report exists to remove.

## Where it surfaces

Every surface prints the rule it attributed by and the base, from one wording
(`ownership_sentences`) and one payload (`ownership_payload`):

- `beadloom ci --format rich` — a block under the verdict, beside the room and coverage lines:
  the rule over `<base>..HEAD`, then one line per owning bead,
  `owned by <bead>: N finding(s), by the files its commits changed`, the claimed beads that
  own nothing, and the `unattributed` count.
- `--format json` — `ownership: {reason, rule, base, claimed, none_owned, claims[],
  findings[]}`, each finding carrying `verdict`, `beads`, `where`, `files` and `uncommitted`.
- `--format github` — the same sentences, one `::notice::` each.
- the MCP `complete_bead` tool — `owners` on the FAIL payload, the JSON report's payload,
  where the agent reading it holds one of the claimed beads and needs to know whether the
  refusal is about its own work.

The tracker is asked only when the run produced a finding: a green run has nothing to
attribute, and shelling out to `bd` on every push to say nothing is a cost with no reader.

## Related

- `gate-coverage` — the same move one layer under: what a run did *not* do, from its step list.
- `verdict-room` — which rooms a verdict is true of.
- `ci-gate` — the run this component qualifies.
- `sync-check` — `git_baseline`, the one reader of git the commits are listed by.
- `declared-scope` — the base the branch's commits are listed against.
