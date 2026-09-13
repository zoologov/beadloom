# ACTIVE: BDL-071 — Release 5.0.0, then 6.0.0: the population report ships before the verdict change

> **Last updated:** 2026-09-13
> **Phase:** Development

---

## Current Bead

**Bead:** R1 `beadloom-2716` — release/5.0.0: the bump, the audit triples and the 5.0.0 change log
**Goal:** a release branch on `7efa4006` that builds as 5.0.0 with a green Gate and no Release B in it.
**Done when:** version-surface agrees at 5.0.0, no history line moved, `[5.0.0]` holds no Release B
text, the Gate and the full suite are green on the branch commit, and `692205d7` is not an ancestor.

## Progress

- [x] Docs folder, Explore axes and the version-surface supplement (2026-09-13)
- [x] PRD, RFC, CONTEXT and PLAN approved (2026-09-13)
- [x] Beads created: epic `beadloom-gskk` + 8, one plan, 7 edges confirmed against the titles
- [ ] 5.0.0: R1 → R2 → R3 → R4 (published and verified on the downloaded wheel)
- [ ] 6.0.0: R5 → R6 → R7 (published and verified on the downloaded wheel)
- [ ] R8: the records

## Results

> The bead id is the FIRST cell of every row: the focus-document medium reads the first cell only (BDL-UX #272).

| Tracker | Bead | Status | Details |
|---|---|---|---|
| `beadloom-2716` | R1 | Done | release/5.0.0 pushed: bump, 3 audit triples, [5.0.0]; ci rc 0, suite green on Darwin/3.12 |
| `beadloom-2kty` | R2 | Blocked | three-version harness on a project that is not ours |
| `beadloom-u7jp` | R3 | Blocked | review of 5.0.0 before publishing |
| `beadloom-7foi` | R4 | Blocked | publish 5.0.0 and verify the downloaded wheel |
| `beadloom-h784` | R5 | Blocked | the 6.0.0 release pull request |
| `beadloom-p02a` | R6 | Blocked | review of 6.0.0 before merging |
| `beadloom-bicw` | R7 | Blocked | publish 6.0.0 and verify the downloaded wheel |
| `beadloom-tmgp` | R8 | Blocked | records: ROADMAP and the issue log |

## Notes

- The version is taken at build time from `src/beadloom/__init__.py` and both uploads run with
  `skip-existing: true`, so a green publish run proves nothing; the downloaded wheel does.
- Measured before planning: bumping only the true current-version places leaves `beadloom ci` rc 1 —
  three dated history lines fail `docs-audit`, and two paired documents fail `sync-check`.
