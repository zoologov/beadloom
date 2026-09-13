# ACTIVE: BDL-071 — Release 5.0.0, then 6.0.0: the population report ships before the verdict change

> **Last updated:** 2026-09-13
> **Phase:** Development

---

## Current Bead

**Bead:** R6 `beadloom-p02a` — review of 6.0.0 before it is merged
**Goal:** an independent verdict on PR #75 at `78166c20`, while its nine checks run.
**Done when:** the reviewer's own `diff` shows `[5.0.0]` byte-identical to `d6eaee60`, the `### Removed`
entry matches the shapes measured at `7efa4006` and on `main`, and the version surface is re-derived.

## Progress

- [x] Docs folder, Explore axes and the version-surface supplement (2026-09-13)
- [x] PRD, RFC, CONTEXT and PLAN approved (2026-09-13)
- [x] Beads created: epic `beadloom-gskk` + 8, one plan, 7 edges confirmed against the titles
- [x] 5.0.0: published 2026-09-13 (tag `v5.0.0` → `d6eaee60`, run 34784341146) and verified on the wheel downloaded from PyPI
- [ ] 6.0.0: R5 → R6 → R7 (published and verified on the downloaded wheel)
- [ ] R8: the records

## Results

> The bead id is the FIRST cell of every row: the focus-document medium reads the first cell only (BDL-UX #272).

| Tracker | Bead | Status | Details |
|---|---|---|---|
| `beadloom-2716` | R1 | Done | release/5.0.0 pushed: bump, 3 audit triples, [5.0.0]; ci rc 0, suite green on Darwin/3.12 |
| `beadloom-2kty` | R2 | Done | harness in scratchpad (sha256 5d132afb…): 4.0.0 rc 0 no key; 5.0.0 rc 0, 8 keys; main rc 1, 5 keys; mismatch exits 3 |
| `beadloom-u7jp` | R3 | Done | review of 5.0.0 before publishing |
| `beadloom-7foi` | R4 | Done | publish 5.0.0 and verify the downloaded wheel |
| `beadloom-h784` | R5 | Done | 6.0.0 PR open (URL in bead comment): [5.0.0] diff vs d6eaee60 empty; ci rc 0, suite green on Darwin/3.13 |
| `beadloom-p02a` | R6 | Ready | review of 6.0.0 before merging |
| `beadloom-bicw` | R7 | Blocked | publish 6.0.0 and verify the downloaded wheel |
| `beadloom-tmgp` | R8 | Blocked | records: ROADMAP and the issue log |

## Notes

- The version is taken at build time from `src/beadloom/__init__.py` and both uploads run with
  `skip-existing: true`, so a green publish run proves nothing; the downloaded wheel does.
- Measured before planning: bumping only the true current-version places leaves `beadloom ci` rc 1 —
  three dated history lines fail `docs-audit`, and two paired documents fail `sync-check`.
