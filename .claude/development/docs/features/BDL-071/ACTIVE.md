# ACTIVE: BDL-071 — Release 5.0.0, then 6.0.0: the population report ships before the verdict change

> **Last updated:** 2026-09-14
> **Phase:** Completed

---

## Current Bead

**Bead:** none — every bead of BDL-071 is closed, and the epic closes with this commit.
**Result:** 5.0.0 and 6.0.0 are on PyPI, each verified on the wheel downloaded from it; the records
landed in PR #76 (`ddd7c52c`).

## Progress

- [x] Docs folder, Explore axes and the version-surface supplement (2026-09-13)
- [x] PRD, RFC, CONTEXT and PLAN approved (2026-09-13)
- [x] Beads created: epic `beadloom-gskk` + 8, one plan, 7 edges confirmed against the titles
- [x] 5.0.0: published 2026-09-13 (tag `v5.0.0` → `d6eaee60`, run 34784341146) and verified on the wheel downloaded from PyPI
- [x] 6.0.0: published 2026-09-13 UTC (PR #75 → `058ef59e`, tag `v6.0.0`, run 34788772241) and verified on the wheel downloaded from PyPI
- [x] R8: the records — ROADMAP rows and verified current version, BDL-UX #301 and #302, #293 amended (PR #76 → `ddd7c52c`)

## Results

> The bead id is the FIRST cell of every row: the focus-document medium reads the first cell only (BDL-UX #272).

| Tracker | Bead | Status | Details |
|---|---|---|---|
| `beadloom-2716` | R1 | Done | release/5.0.0 pushed: bump, 3 audit triples, [5.0.0]; ci rc 0, suite green on Darwin/3.12 |
| `beadloom-2kty` | R2 | Done | harness in scratchpad (sha256 5d132afb…): 4.0.0 rc 0 no key; 5.0.0 rc 0, 8 keys; main rc 1, 5 keys; mismatch exits 3 |
| `beadloom-u7jp` | R3 | Done | review of 5.0.0 before publishing |
| `beadloom-7foi` | R4 | Done | publish 5.0.0 and verify the downloaded wheel |
| `beadloom-h784` | R5 | Done | 6.0.0 PR open (URL in bead comment): [5.0.0] diff vs d6eaee60 empty; ci rc 0, suite green on Darwin/3.13 |
| `beadloom-p02a` | R6 | Done | OK, 2 minor + 1 nitpick, all handed to R8; suite green on Darwin/3.12 at `78166c20` |
| `beadloom-bicw` | R7 | Done | merged `058ef59e`; wheel sha256 09668b53… from PyPI: harness exit 0, 5 keys, verdict change |
| `beadloom-tmgp` | R8 | Done | ROADMAP: 6.0.0 verified, rows for 5.0.0 and 6.0.0; issue log #301, #302, #293 amended; merged `ddd7c52c` |

## Notes

- The version is taken at build time from `src/beadloom/__init__.py` and both uploads run with
  `skip-existing: true`, so a green publish run proves nothing; the downloaded wheel does.
- Measured before planning: bumping only the true current-version places leaves `beadloom ci` rc 1 —
  three dated history lines fail `docs-audit`, and two paired documents fail `sync-check`.
