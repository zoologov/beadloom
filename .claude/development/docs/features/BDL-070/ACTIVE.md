# ACTIVE: BDL-070 — The layer a node is in, answered once and reported over its population

> **Last updated:** 2026-09-12
> **Phase:** Development

---

## Current Bead

**Bead:** A1 `beadloom-e64o` — the shared layer lookup, pure and declaration-reading
**Goal:** one `layer_of` reading the rule's declared layers and climbing `part_of`, plus the
population counter everything else reports from.
**Done when:** `layer_of` is pure, a `part_of` cycle terminates, a node with its own tag does not
climb, exactly one ancestry walk is reachable from `graph/rules/`, and no layer tag appears as a
literal in `src/` outside a test fixture.

## Progress

- [x] Step 0: docs folder created (2026-09-12)
- [x] Step 0.5: Explore run; `## Axes` derived, and its supplement derived by hand after the
      derivation reported no seed (2026-09-12)
- [x] PRD approved (2026-09-12)
- [x] RFC approved, with Q1–Q6 decided or deferred to a named bead (2026-09-12)
- [x] CONTEXT + PLAN approved (2026-09-12)
- [x] Beads created: epic `beadloom-5tcc` + 16, one plan, 21 edges confirmed against the titles
- [ ] Wave 1: A1
- [ ] Waves 2–6: Release A
- [ ] Waves 7–12: Release B

## Results

> The bead id is the FIRST cell of every row on purpose: the focus-document medium reads
> the first cell only, and a table carrying the id in its second column reports every bead
> of the wave as having no row (BDL-UX #272).

| Tracker | Bead | Status | Details |
|---|---|---|---|
| `beadloom-e64o` | A1 | Done | `graph/rules/layers.py`: `layer_of` reads the declared `layers`, `part_of_generations` is now the ONE ancestry walk (`import_resolver` calls it), `layer_population` counts evaluated / skipped-untagged. 31 + 5 tests. No verdict moved: lint 0 error(s), 70 warning(s), as before |
| `beadloom-1ylk` | A2 | Done | `evaluate_layer_rules` states its reach: `layer_reach.py` emits one `layer_population` finding per rule (`warn`, never the declared `error`), `node_tags.py` replaces the five identical tag closures. Measured here: 16 of 363 by own tags, 355 of 363 by `part_of`. 30 + 3 tests. No verdict moved — `lint --strict` exit 0 before and after, 0 findings removed, 1 added, and the identity is asserted against the pre-change code path run in the same process |
| `beadloom-2dgz` | A3 | Blocked | LintResult carries a per-rule population |
| `beadloom-q6jh` | A4 | Blocked | the readers that bypass lint() |
| `beadloom-06dz` | A5 | Done | `architecture_view` drops `_LAYER_TAGS`, `_LAYER_RANK`, `_layer_of`, `_own_layers` and `_layer_rank`, reads the declared layer order from the indexed `rules` table and resolves membership through `graph.rules.layers`; `liveness` reads its layer through `own_layer_of` and its tags through `node_tags`, keeping OWN-tag membership so no inert verdict moves. `src/` now holds no layer tag as a literal at all — the guard's exemption set is empty. 10 new tests; 3 existing test files adjusted. Measured here: the artifact is byte-identical over 106 nodes (136 743 bytes), and `lint --strict --format porcelain` is identical line for line after a full reindex — 0 findings removed, 0 added, exit 0 both sides. The view's `dst_rank <= src_rank` predicate is untouched (B4) |
| `beadloom-punn` | A6 | Done | Q5 answered in the bead's comments before any code change, with the re-derivation: the `tags:` catalog is REMOVED, and `load_rules_with_tags` with it — rules.yml declares constraints ON the graph while a node's tags are a property OF it, and an AST scan of every module under `src/` (imports including asnames, calls, attribute calls) found no production reader, so the trap goes rather than the block alone. `validate_rules` gains the `LayerRule` case through `layer_declaration.py`, whose one predicate also feeds the evaluator's `warn` finding — `warn`, never the declared `error` — and stands down when fewer than two layers are populated, because liveness names them there. `rules.yml` has an owner: the `architecture-rules` node, and `beadloom impact .beadloom/_graph/rules.yml` names it owning 1 unread file. 18 new tests. Measured with the index lineage held constant: 71 findings before and after, 0 removed, 0 added, exit 0 both sides; one advisory message moves, `scenario-coverage`'s population 106 → 107 nodes, because this bead adds one. Nothing on this repository triggers the new finding — all four declared tags are carried |
| `beadloom-cfkk` | A7 | Blocked | tests, release A |
| `beadloom-mrof` | A8 | Blocked | review, release A |
| `beadloom-714v` | A9 | Blocked | docs, release A |
| `beadloom-46am` | B1 | Blocked | agent-prime -> reindex |
| `beadloom-xmfs` | B2 | Blocked | the 16 peer crossings |
| `beadloom-ku26` | B3 | Blocked | derived layer + predicate |
| `beadloom-w34m` | B4 | Blocked | architecture_view's predicate |
| `beadloom-bi78` | B5 | Blocked | tests, release B |
| `beadloom-ssz8` | B6 | Blocked | review, release B |
| `beadloom-57wl` | B7 | Blocked | the shipped claim |

## Notes

- **The axes derivation found no seed** and said so. The scope decision rests on a supplement
  derived by name-matching, which is weaker, and A8's done-when requires the reader set to be
  re-derived by a different method.
- **Q5 and Q6 were closed against the `pending-in-approved` check**, not left open: Q6 is decided
  (both the finding and the summary line, for a derived reason), Q5 is deferred to A6 with the
  answer required in writing before code changes.
- `beadloom docs quality` reports the `Waves` table in PLAN.md as NOT CLASSIFIED — the tool stating
  it does not read that table, not a finding against the document.
