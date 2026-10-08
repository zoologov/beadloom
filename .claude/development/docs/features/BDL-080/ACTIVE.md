# ACTIVE: BDL-080 — The portal is a service, and the viewer serves a Feature-Sliced frontend

> **Created:** 2026-10-08

---

## Current Bead

**Bead:** S1 — `beadloom-je0i` (S1a), `beadloom-kgh6` (S1b), then `beadloom-i3zs` (S1c); T, R, W, PR.

## Progress

| Bead | Role | Status | Note |
|---|---|---|---|
| `beadloom-je0i` | S1a | ✓ done | site is an alias of service: `KIND_ALIASES` in `graph/loader.py` (not `rules/types.py`: a cycle, measured); the doc skeleton applies it too; lint 0 errors, `architecture-layers` judged 381 -> 425 of 434, no finding |
| `beadloom-kgh6` | S1b | in progress | every layer rule in the data file; scope: |
| `beadloom-i3zs` | S1c | blocked | the viewer draws every rule; layer boxes |
| `beadloom-lsev` | S1T | blocked | criteria; full tree once |
| `beadloom-m7xq` | S1R | blocked | review, bead id only |
| `beadloom-we9t` | S1W | blocked | docs |
| `beadloom-z30s` | S1P | blocked | PR, merge on green |

## Results

(filled per wave)

## Notes

- **S1a closed (2026-10-08):** `3c798da3` — `KIND_ALIASES`/`canonical_kind` in `graph/loader.py` (not beside `VALID_NODE_KINDS`: the rule engine imports the loader, a cycle); the doc generator reads YAML directly and applies the same table through `onboarding.graph_files`; reindex prints an `[info]` for an alias; `vitepress-site.yml` kind service, `layer-service`; `lint --strict` 0 errors, 70 -> 69 warnings, `architecture-layers` judges 381 -> 425 of 434 edges, no new finding; the own portal page under `services/`. 5,469 passed on the touched packages; sync-check 15 stale pairs -> S1W. S1b launched.

- Epic `beadloom-af99`; branch `features/BDL-080` from `main` at `7b9a9b65` (8.0.0); the branch's first commit is BDL-079's close-out. Later slices' beads are created when the slice starts.
