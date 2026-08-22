# ACTIVE: BDL-061 — Enforced agentic flow

> **Last updated:** 2026-08-22
> **Phase:** Development

---

## Current Bead

**Bead:** none — `.31` closed. Next in the chain: `beadloom-mr2l.3` [review] S1 —
portability, read-only, honest skip.
**Handover for `.3`:** the enumeration, the structural pin and the recording-witness
matrix live in `tests/test_guards_invocation.py` (section 2 states the invariant the
pin is about); the evidence that the pin bites — the measured terminator table, the
two sabotage shapes `.30` walked past, and the quantified "manufactures no root"
claim — is in `tests/test_guards_boundary_escapes.py`. The recording rule and its
three exceptions, the interrupt decision with both sides, the `--project` marker
requirement and the named residuals are in
`docs/domains/application/features/flow-guards/SPEC.md`.

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
- [x] S1 `.28` test — adversarial re-verification: F7–F10 + m1–m3, 151 new tests, suite
      5225 → 5376, no `src/` change (commit `d4bb618`)
- [x] S1 `.29` dev fix-3 (2026-08-22) — ONE invocation boundary (`application/guards/
      invocation.py`) + project discovery (`project_root.py`); F7, F8, F9, F10, m1, m2 closed
      as consequences of it; the strip deleted, the glob anchored, the project located by
      walking up for `.beadloom/` and never manufactured; guard tests 528 → 627, suite
      5376 → 5475, 15 sabotages all FAILED
- [x] S1 `.30` test — the boundary is present but not load-bearing: three escapes
      (an interrupt at exit 1 with no record; the structural pins are spelling checks;
      `--project` need not name a project); 25 tests, suite 5476 → 5501, no `src/` change
      (commit `8bbd84c`)
- [x] S1 `.31` dev fix-4 (2026-08-22) — the pin made as wide as its invariant (scope
      derived from the package, terminators recognised by measured effect, a
      recording-witness matrix run in a subprocess), the last-resort handler widened to
      `BaseException` with the Ctrl-C-now-blocks trade-off argued in the SPEC, and
      `--project` required to carry the marker; also: an empty guard name is no longer
      swallowed, a closed stdin states a cause, and the render step can no longer choose
      the exit code. Guard tests 653 → 713, suite 5501 → 5561, 9 sabotages all FAILED

## Results

| Bead | Status | Details |
|------|--------|---------|
| .1 | Done | Guard primitive: registry, verdict, CLI, hook adapter, liveness (68 tests) |
| .2 | Done | Verdict matrix, exclusion validation, liveness widened (248 tests) |
| .3 | Open | Review: NOT PASSING — 1 critical + 5 major; re-review after `.25` |
| .25 | Done | S1 fix: traversal bypass, probe limit, liveness honesty, `on:` deleted |
| .26 | Done | S1 test: re-verification — F1 backslash bypass, F2 NUL crash, F3–F6 recorded |
| .27 | Done | S1 fix-2: path shape narrowed, `error` outcome, no invocation without a record |
| .28 | Done | S1 test: adversarial re-verification — F7 stdin bytes, F8 six unrecorded, F9 cwd-as-root, F10 the strip |
| .29 | Done | S1 fix-3: one invocation boundary + project discovery; the four symptoms closed as consequences |
| .30 | Done | S1 test: three escapes past the boundary's edges — the interrupt, the spelling-deep pins, `--project` |
| .31 | Done | S1 fix-4: the pin as wide as its invariant, `BaseException` last resort, `--project` must be a project |
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
