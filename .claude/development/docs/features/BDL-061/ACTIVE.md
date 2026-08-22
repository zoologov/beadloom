# ACTIVE: BDL-061 — Enforced agentic flow

> **Last updated:** 2026-08-22
> **Phase:** Development

---

## Current Bead

**Bead:** `beadloom-mr2l.1` — [dev] S1: guard primitive — registry, verdict model, CLI, liveness
**Goal:** the portable primitive everything else binds to — a named guard, declared in
`flow.yml`, evaluated by Beadloom, returning a verdict a harness can act on.
**Done when:** CLI and hook adapter produce identical verdicts; an exclusion without `reason`
or `until` is a configuration error; `skip` always carries a reason; `--liveness` reports
guards that never fired or are excluded everywhere; no guard writes to the index; every guard
has a test proving it FAILS on the condition it guards.

## Progress

- [x] PRD → Approved (2026-08-22)
- [x] RFC → Approved (2026-08-22)
- [x] CONTEXT + PLAN → Approved (2026-08-22)
- [x] Epic `beadloom-mr2l` + 24 sub-beads created, linear `.1 → .24` chain wired
- [ ] S1 `.1` dev — not started

## Results

| Bead | Status | Details |
|------|--------|---------|
| .1–.4 | Pending | S1 guard primitive |
| .5–.8 | Pending | S2 stop the lying checks (#142, #146, #147) |
| .9–.12 | Pending | S3 composition + project overlay (#139, #152, #132, #136, #137) |
| .13–.16 | Pending | S4 BDD, mutation, doc shape + quality, shared writing standard |
| .17–.20 | Pending | S5 TO-BE / AS-IS / WORKING |
| .21–.24 | Pending | S6 waves from the graph (#155, #118, #133) |

## Notes

**Branch:** `features/BDL-061`. Slice boundary is a PR boundary — each slice green on `main`
before the next begins, as BDL-060 ran.

**Ordering is load-bearing.** S1 first because it is the primitive; S2 second because S3's
acceptance criterion is deleting the rules S2's bugs forced into the prose, which cannot happen
earlier.

**Dogfooded under itself.** From S1 onward this epic's own beads run under the guards being
written. Friction is recorded as a finding, never worked around — the record is the point.

**Carried, not forgotten:** #160 (AsyncAPI wired to nothing) stays deferred with its plan in
ROADMAP; #158 and #161 are separate items this epic's mechanisms may later absorb; #91 closes
as verified with the caveat that it is the first believable result, since only #159 taught the
cycle rule to see nested imports.

**Owner-visible checkpoint:** after `.12` (end of S3) the core request is delivered — the flow
is enforced, stops lying, and is extensible. If a later slice proves to be an epic of its own,
that gets reported rather than absorbed; S5 and S6 are the likely candidates.
