# PRD: BDL-066 — Agent behaviour observability, trace and result

> **Status:** Draft
> **Created:** 2026-08-31

---

## Problem

The owner can see the conversation with the coordinator. He cannot see what the
coordinator tells its subagents, what they actually do, or whether their reports
are true. Every multi-agent wave this project runs is, from his side, a black box
that returns a summary.

This is measured, not suspected. On 2026-08-27 the coordinator added five
constraints to a subagent brief, three of them saying "return VERBATIM". One
locked the section headings of a document the owner had spent a day arranging to
have rewritten by a different model. The lock defeated the purpose of the work.
It lived entirely inside a prompt the owner never saw, and he found it only by
reading the output and asking why the text still sounded like the coordinator's.
The constraint protected nothing: the document had zero anchors and nothing
linked to its sections.

The same session produced dozens of unverifiable claims in role reports — "ran
the full suite", "green in a clean room over 33 files", "reverted to a clean
diff", "four neuterings, each reverted". Every one was accepted on trust. Some
were later found wrong by other agents rather than by any check.

The industry frame is the same shape one level up. CLTR's analysis reports AI
loss-of-control incidents worsening, and the risk heuristic recorded in this
repository's own safety notes multiplies capability by access, autonomy,
duration and irreversibility. A wave of background subagents maximises three of
those five terms, and this project runs them daily.

None of this requires misalignment. A well-meaning agent optimising for
defensibility produces it, which is what the 2026-08-28 session retrospective
concluded about the coordinator's own behaviour.

## Goals

- The coordinator's instructions to subagents become visible without depending
  on the coordinator to record them.
- A claim in a role report can be checked against what the agent actually did.
- Work that left the scope its bead declared is named.
- A change that reduces the owner's ability to observe — an edited hook, a
  lowered severity, a new suppression — is reported separately from ordinary
  work.
- A retrospective over an epic reports **how** the work was done, in numbers
  first, with a bounded set of process changes tied to observations.
- All of it is optional. With no event store the checks say **not verified**,
  never *pass*.

## Non-goals

- **Not an observability platform.** Beadloom does not build a collector, a
  dashboard or a proxy. Third-party tools already do this well; Beadloom reads
  their store and applies checks.
- **Not prevention.** Every mechanism here raises detectability. None stops a
  determined agent, and the shipped documentation must say so in those words.
- **Not grading agents.** The output is measurements and process changes, not a
  score per role.
- **Not the system prompt, in the first release.** Capturing it requires routing
  all traffic through a local proxy and stores secrets. The failure classes above
  are covered by hook events.

## Success criteria

1. Replaying the 2026-08-27 heading-lock incident against the trace names it:
   the brief carried a constraint absent from the bead, and the result metric it
   governed came back unchanged. Both halves stated, no causal claim invented.
2. At least three claim types are verified mechanically against the trace, and a
   deliberately false claim in a role report is caught.
3. A bead whose diff leaves its declared node scope is named. A bead that
   declares no scope reports **not verified**, not clean.
4. With the event store absent, every check in this feature reports not-verified
   and `beadloom ci` says so on its own line.
5. A wave that never passed through separate roles is named from the tracker
   alone, with no event store present. A wave whose actors are indistinguishable
   reports not-verified rather than pass.
6. The retrospective report states how many events it read out of how many exist.
7. A live secret that passed through an agent's arguments does not reach a
   committed file, and the store path is git-ignored by construction.

## Out of scope for the first release

The proxy adapter that captures the system prompt, and any per-agent scoring.
Both are recorded here so they are not mistaken for oversights.
