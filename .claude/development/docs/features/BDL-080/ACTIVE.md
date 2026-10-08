# ACTIVE: BDL-080 — The portal is a service, and the viewer serves a Feature-Sliced frontend

> **Created:** 2026-10-08

---

## Current Bead

**Bead:** S1 — `beadloom-je0i` (S1a), `beadloom-kgh6` (S1b), then `beadloom-i3zs` (S1c); T, R, W, PR.

## Progress

| Bead | Role | Status | Note |
|---|---|---|---|
| `beadloom-je0i` | S1a | ✓ done | site is an alias of service: `KIND_ALIASES` in `graph/loader.py` (not `rules/types.py`: a cycle, measured); the doc skeleton applies it too; lint 0 errors, `architecture-layers` judged 381 -> 425 of 434, no finding |
| `beadloom-kgh6` | S1b | ✓ done | `layer_rules` + per node `layer_rule`/`layer_rule_rank` (new `application/site/layer_rules_view.py`); `scope:` parsed, validated, indexed, narrows evaluator/reach/liveness through `layers.within_scope`; site slices placed by `site-fsd-layers` (scope `vitepress-site`), `cli` by `architecture-layers` (scope `beadloom`); lint 0 errors / 69 warnings before and after; existing keys byte-identical |
| `beadloom-i3zs` | S1c | in progress | a layer is (rule, rank); legend grouped per rule; filter offers `rule: layer` where two rules are drawn; card names the rule; sixth tone a portal cyan (`brand` is VitePress's indigo); a rule scoped to a box inside the frame draws one box per layer in it (this portal: six in `vitepress-site`), stacked by layout-only lane edges because ELK reads no partition inside a box; one FSD finding drawn red; fixtures drawn alike with and without the new keys; full chromium 317 of 318 (the 318th `diagram-links`, red on HEAD since S1a) |
| `beadloom-lsev` | S1T | blocked | criteria; full tree once |
| `beadloom-m7xq` | S1R | blocked | review, bead id only |
| `beadloom-we9t` | S1W | blocked | docs |
| `beadloom-z30s` | S1P | blocked | PR, merge on green |

## Results

(filled per wave)

## Notes

- **S1b closed (2026-10-08):** `a20b7df3` — `layer_rules` top-level, per node `layer_rule` / `layer_rule_rank`, `violation` the union over rules; old keys unchanged (schema 2; this portal's old keys and edges byte-identical; six fixtures identical but the new keys); `scope:` on a `layers` rule parsed, validated, indexed, applied through `layers.within_scope`; derived scopes: `architecture-layers` -> `beadloom`, `site-fsd-layers` -> `vitepress-site`; 109 nodes under the first rule, 20 under the FSD rule, 1 under none. Lint identical before/after. 65 stale pairs -> S1W; 14 new test files bind to no node -> S1T. S1c launched.

- **S1a closed (2026-10-08):** `3c798da3` — `KIND_ALIASES`/`canonical_kind` in `graph/loader.py` (not beside `VALID_NODE_KINDS`: the rule engine imports the loader, a cycle); the doc generator reads YAML directly and applies the same table through `onboarding.graph_files`; reindex prints an `[info]` for an alias; `vitepress-site.yml` kind service, `layer-service`; `lint --strict` 0 errors, 70 -> 69 warnings, `architecture-layers` judges 381 -> 425 of 434 edges, no new finding; the own portal page under `services/`. 5,469 passed on the touched packages; sync-check 15 stale pairs -> S1W. S1b launched.

- Epic `beadloom-af99`; branch `features/BDL-080` from `main` at `7b9a9b65` (8.0.0); the branch's first commit is BDL-079's close-out. Later slices' beads are created when the slice starts.
