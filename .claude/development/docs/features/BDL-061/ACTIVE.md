# ACTIVE: BDL-061 — Enforced agentic flow

> **Last updated:** 2026-08-22
> **Phase:** Development

---

## Current Bead

**Bead:** `beadloom-mr2l.27` — [dev] S1 fix-2: narrow the guard's path input instead of
normalising it (test `.26` returned F1–F6; two bypasses reproduced through the real CLI)
**Goal:** stop generating path cases — define the accepted shape of an edit target, refuse
everything outside it with a recorded verdict, and never end an invocation without a firing
record.
**Done when (met):** a backslash spelling no longer exempts a file (F1); a NUL reaches a verdict
instead of a traceback on the warn code (F2); a malformed path blocks and is recorded; the SPEC
states the shape and the reasoning for `error` over `skip`/`warn`/exit 3; F3–F6 fixed or
recorded with a measured reason.

## Progress

- [x] PRD → Approved (2026-08-22)
- [x] RFC → Approved (2026-08-22)
- [x] CONTEXT + PLAN → Approved (2026-08-22)
- [x] Epic `beadloom-mr2l` + 24 sub-beads created, linear `.1 → .24` chain wired
- [x] S1 `.1` dev — guard primitive shipped (2026-08-22): `application/guards/` +
      `beadloom guard` + logic-free Claude hook adapter + 2 guards; 68 tests, Gate green
- [x] S1 `.2` test — verdict matrix, exclusion validation, liveness widened to 248 tests
- [x] S1 `.3` review — NOT PASSING: 1 critical + 5 major + 7 minor; fix cycle opened as `.25`
- [x] S1 `.25` dev fix (2026-08-22) — C1 path traversal, M1 `excluded_everywhere`,
      m1 dead exclusion, M2 `on:` deleted, M4 `bd --limit 0`, M5 vacuous real-bd test;
      guard tests 242 → 280, Gate green on a clean DB
- [x] S1 `.26` test — independent re-verification: traversal matrix + F1–F6; guard tests
      280 → 335, no `src/` change
- [x] S1 `.27` dev fix-2 (2026-08-22) — accepted path shape + `error` outcome + a firing
      record for every named-guard invocation; F1, F2, F3, F4, F5, F6 closed, the whole-tree
      liveness flag judged and left out with a measured reason; guard tests 335 → 377

## Results

| Bead | Status | Details |
|------|--------|---------|
| .1 | Done | Guard primitive: registry, verdict, CLI, hook adapter, liveness (68 tests) |
| .2 | Done | Verdict matrix, exclusion validation, liveness widened (248 tests) |
| .3 | Open | Review: NOT PASSING — 1 critical + 5 major; re-review after `.25` |
| .25 | Done | S1 fix: traversal bypass, probe limit, liveness honesty, `on:` deleted |
| .26 | Done | S1 test: re-verification — F1 backslash bypass, F2 NUL crash, F3–F6 recorded |
| .27 | Done | S1 fix-2: path shape narrowed, `error` outcome, no invocation without a record |
| .4 | Pending | S1 tech-writer |
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

**Deferred from review `.3`, deliberately and named:** M3 (the harness owns event routing *and*
the guard list, so `.claude/settings.json` carries two decisions Beadloom cannot see) is S3
work — it is the same defect as M2 from the other end, and wiring it hastily under a fix cycle
would recreate the "capability with no consumer" shape that M2 exists to remove. Minors m2
(no `.gitignore` entry for the firing record in scaffolded projects), m3 (`beadloom guard`
creates `.beadloom/` in a project that does not use Beadloom), m4 (the read-only digest is
narrower than its docstring claims), m5 (the dogfood matcher and the scaffolder's matcher
disagree), m6 (role files do not say the coordinator owns the commit) and m7 (no firing-record
rotation) are not in `.25` and stay for `.4`/S2.

**Carried, not forgotten:** #160 (AsyncAPI wired to nothing) stays deferred with its plan in
ROADMAP; #158 and #161 are separate items this epic's mechanisms may later absorb; #91 closes
as verified with the caveat that it is the first believable result, since only #159 taught the
cycle rule to see nested imports.

**Owner-visible checkpoint:** after `.12` (end of S3) the core request is delivered — the flow
is enforced, stops lying, and is extensible. If a later slice proves to be an epic of its own,
that gets reported rather than absorbed; S5 and S6 are the likely candidates.
