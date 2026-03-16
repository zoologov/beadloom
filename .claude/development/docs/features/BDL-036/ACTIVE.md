# ACTIVE: BDL-036 — Phase 0: Foundation / Honesty Gate

> **Last updated:** 2026-05-30
> **Phase:** Development

---

## Epic

**Parent (epic):** `beadloom-5ge`  — `bd swarm validate beadloom-5ge` confirmed (Wave 1 = 4 issues).
**Goal:** `beadloom doctor && lint --strict && sync-check` honestly green on Beadloom + clean fresh bootstrap.

## ⚠️ Bead-ID ↔ BEAD-NN mapping (suffixes differ — test bead created after 06/07)

| BEAD label | bead-id | Role | Issue(s) |
|------------|---------|------|----------|
| BEAD-01 | `beadloom-5ge.1` | dev | #92 + #93 |
| BEAD-02 | `beadloom-5ge.2` | dev | #88 + #94 |
| BEAD-03 | `beadloom-5ge.3` | dev | #91 split + rules→error 🎯 |
| BEAD-04 | `beadloom-5ge.4` | dev | #86 |
| BEAD-06 | `beadloom-5ge.5` | dev | #89/#90 |
| BEAD-07 | `beadloom-5ge.6` | dev | #71 |
| BEAD-05 | `beadloom-5ge.7` | test | exit-criterion |
| BEAD-08 | `beadloom-5ge.8` | review | — |
| BEAD-09 | `beadloom-5ge.9` | tech-writer | — |

## Current Bead

**Bead:** BEAD-03 (`beadloom-5ge.3`) — 🎯 #91 split `application` layer + rules→error (Wave 2, solo + merge-slot)
**Goal:** move reindex/doctor/debt_report → `src/beadloom/application/`; add application layer to graph; restore cycles/layers to error; lint --strict genuinely clean.

## Progress

### Wave 1 (parallel dev — independent honesty fixes) ✅ COMMITTED 960f325
- [x] BEAD-01 (.1) — #92 doctor version + #93 MCP count
- [x] BEAD-02 (.2) — #88 reindex totals + #94 excepts
- [x] BEAD-04 (.4) — #86 flow-style YAML → GraphParseError
- [x] BEAD-06 (.5) — #89/#90 sync-check → genuine 100% (E2E proven)
- [+] BEAD-10 (.10) — #98 git_activity date-flake (NEW, found in assembly; blocks BEAD-05)

### Wave 2 (dev) — 🎯 #91
- [x] BEAD-03 (.3) — split `application` layer + rules→error. Moved reindex/doctor/debt_report/watcher → `src/beadloom/application/`; added `application` node (tag `layer-application`) + layer order services→application→domains→infrastructure; restored cycles+layers to `error`. lint --strict: 0 violations (exit 0). doctor exit 0. Resolved phantom `application↔beadloom` cycle by making reindex's `__version__` read function-local (edge-free, mirrors doctor.py). pytest 2604 pass / 1 pre-existing #98 date-flake (BEAD-10, untouched git_activity). ruff+mypy clean.

### Wave 3-6
- [ ] BEAD-07 (.6) — #71 clean bootstrap (after rules=error)
- [ ] BEAD-05 (.7) — test: full suite + exit-criterion
- [ ] BEAD-08 (.8) — review
- [ ] BEAD-09 (.9) — tech-writer

## Results

| Bead | Status | Details |
|------|--------|---------|
| beadloom-5ge.1 | Pending | — |
| beadloom-5ge.2 | Done | #88 true totals on incremental path; #94 narrowed to sqlite3.OperationalError (missing-table only). 4 tests added. |
| beadloom-5ge.3 | Done | #91 split: 4 orchestrators → application/; rules→error; lint --strict 0 violations; doctor clean; 2604 tests pass (1 pre-existing #98 flake). |
| beadloom-5ge.4 | Pending | — |
| beadloom-5ge.5 | Pending | — |
| beadloom-5ge.6 | Pending | — |
| beadloom-5ge.7 | Pending | — |
| beadloom-5ge.8 | Pending | — |
| beadloom-5ge.9 | Pending | — |

## Notes

- First real-code dogfood of the BDL-035 process. `bd swarm` validated on the epic parent (the BDL-035 #97/swarm fix works).
- #91 (BEAD-03) is the high-risk refactor — runs solo with `bd merge-slot`; mechanical move preserving APIs.
- `honest ≠ complete`: #89/#90 (BEAD-06) may re-scope with evidence if deeper than Phase 0.
