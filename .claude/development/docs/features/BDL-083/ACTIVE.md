# ACTIVE: BDL-083 — Debt to zero

> **Last updated:** 2026-10-18
> **Phase:** Development — S1 the gates that lie

---

## Current Bead

**Bead:** S1g — `beadloom-483w`, dev
**Goal:** the adopter's layout as an anonymised fixture under `tests/fixtures/`, indexed green, with a test that asserts its node set
**Done when:** `beadloom reindex` on the fixture is green, the test is green, the fixture's README paragraph is written, committed by path under the landing lock

## Progress

- [x] Step 1: `/task-init` — axes derived (eight targets, 406 rows ruled in the RFC), PRD, RFC, CONTEXT and PLAN approved by the owner on 2026-10-18
- [x] Step 2: S1 beads created as one plan; `beadloom-ba9w.13` and `beadloom-jwfc` wired in as S1e and S1e2
- [ ] Step 3: S1 — the fixture, then the six dev beads in the waves `beadloom waves` derives
- [ ] Step 4: S1 test, review, tech-writer, PR, merge on green
- [ ] Step 5: S2 beads created; S2 — the monorepo on GitLab
- [ ] Step 6: S3 beads created; S3 — the re-measurement; the S4–S7 sections put to the owner
- [ ] Step 7: S4–S7, one PR each
- [ ] Step 8: close-out — documents `Done`, ROADMAP re-ranked, the version MAJOR

## Results

| Bead | Status | Details |
|------|--------|---------|
| S1g (`beadloom-483w`) | Open | not started |
| S1a (`beadloom-7i09`) | Open | blocked by S1g |
| S1b (`beadloom-q8x6`) | Open | blocked by S1g |
| S1c (`beadloom-b23f`) | Open | blocked by S1g |
| S1d (`beadloom-fgu8`) | Open | blocked by S1g |
| S1e (`beadloom-ba9w.13`) | Open | blocked by S1g |
| S1e2 (`beadloom-jwfc`) | Open | blocked by S1g |
| S1f (`beadloom-6xdt`) | Open | blocked by S1g |
| S1T (`beadloom-rupp`) | Open | blocked by S1a–S1f, S1e, S1e2 |
| S1R (`beadloom-pohj`) | Open | blocked by S1T |
| S1W (`beadloom-hfxv`) | Open | blocked by S1R |
| S1P (`beadloom-c5m5`) | Open | blocked by S1W |

## Notes

- The owner's rulings of 2026-10-18 are in PRD.md; D1–D9 in RFC.md. Behaviour rules agreed before code: D1 (the hook fails), D4 (the base), D5 (the exit code), D9 (the re-measurement protocol).
- S2 and S3 beads are created when their slice starts (ruling 6); S4–S7 are designed from S3's result.
- The adopter's project is never named; the fixture is "the monorepo fixture".
- The pre-push Gate crashed on a non-blocking pipe on 2026-10-18 while filing #326–#350 (evidence on `beadloom-jwfc`); pushes from the agent's shell redirect the hook's output to a file until S1e2 lands.
