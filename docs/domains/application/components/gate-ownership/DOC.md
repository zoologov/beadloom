# Gate Ownership (component)

Which bead claimed now owns each finding of a gate run, and the verdict when none does.

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

## Where the claim is read from, and why the other two lose

The owner is a **bead the tracker reports `in_progress` right now**, and the nodes its own
`refs:` declare. That is the same population `bead-claimed` reads, through the same port
(`application/guards/contract.WorkTracker`), parsed by the same `waves.scope.resolve_scope`
the wave planner uses — so the gate and the plan cannot come to disagree about what a bead
said.

| Candidate population | Why it is not the owner |
|----------------------|-------------------------|
| the work item's declared `## Axes` | It answers a different question — is this change inside the approval — and `scope-check` already asks it, as a step of the same run. Every finding on one branch is inside one approval, so the owner it derives is the work item, which every agent on that branch shares. |
| a wave's plan | It names beads that have not started and beads whose wave is over, and it exists only where a plan was made. A plan states what *should* run; a claim states what *is* running, and "is this red mine" is about the second. |

## Three verdicts, because they are three different facts

| Verdict | What it says |
|---------|--------------|
| `owned` | a node was derived and at least one claimed bead declares it — the beads are named |
| `unowned` | a node was derived and no bead claimed now declares it |
| `unattributed` | no node could be derived from the finding at all |

`unowned` is the interesting case rather than the failure: it is precisely what the
coordinator had to say by hand. `unattributed` is a different absence — "there was nothing to
claim" rather than "nobody claims it" — and collapsing the two would hide which one happened.

A tracker that cannot answer, and a project with no index, are a `reason` on the whole report
rather than a page of `unowned`. Telling every gate owner "not yours" when nobody was asked
would be the same false green in the new vocabulary.

A claimed bead whose own declaration cannot be read as a scope is reported beside the
verdicts, because it qualifies every `unowned` in the same run: that bead might own any of
them, so "nobody claims this" is a statement about the claims that *were* readable.

## How a finding reaches a node

| Route | Read from | Used when |
|-------|-----------|-----------|
| the finding's `node` field | the step that produced it | a step already knows which node it reports on — the linter has carried it since BDL-067 `.14`, and the `sync-check` findings carry it for this report |
| source ownership of a location path | the index, through `impact.boundary.GraphBoundary` — the same most-specific-wins ownership `scope-check` uses | a finding names a code path |
| the documented node of a location path | the index's `docs` table, joined under the documentation root the project configures | a finding names a document, which no source prefix owns |

Everything is read **through the index**, never by opening a graph file by name.
`beadloom-0mdo.80` replaced `.beadloom/_graph/services.yml` with 100 per-node files plus
`graph-layout.yml`, and nine Gate steps read the graph without noticing precisely because
they read the loader's output.

A bead's scope expands **downward** through `part_of`, as `resolve_scope` defines it: a bead
that declares a domain owns a finding about its component, and a bead that declares the
component does not own a finding about the domain.

## Where it surfaces

- `beadloom ci --format rich` — a block under the verdict, beside the room and coverage lines.
- `--format json` — `ownership: {reason, claimed, none_owned, findings[], unread_claims[]}`.
- `--format github` — one `::notice::` per owning bead, plus the headline when nothing is owned.
- the MCP `complete_bead` tool — `owners` on the FAIL payload, where the agent reading it
  holds one of the claimed beads and needs to know whether the refusal is about its own work.

The tracker is asked only when the run produced a finding: a green run has nothing to
attribute, and shelling out to `bd` on every push to say nothing is a cost with no reader.

## Related

- `gate-coverage` — the same move one layer under: what a run did *not* do, from its step list.
- `verdict-room` — which rooms a verdict is true of.
- `ci-gate` — the run this component qualifies.
- `wave-plan` — the parser that reads a bead's `refs:` declaration.
