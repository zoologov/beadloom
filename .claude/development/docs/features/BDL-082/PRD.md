# PRD: BDL-082 — FSD by the specification 2.1

> **Status:** Done
> **Created:** 2026-10-11

---

## Problem

Beadloom 9.0.0 reads a Feature-Sliced frontend (BDL-080), and the owner's first adoption is a
Vue 3 frontend with 81 slices (ROADMAP step 3 of 2026-10-11). Measured on 2026-10-11 against
feature-sliced.design's reference (layers, slices and segments, public API; `axes.md`), on scratch
projects that follow the specification's own examples:

1. **`@x` cross-imports.** The specification's example (`entities/song/@x/artist.ts`, imported
   from the artist entity) gets 4 false errors and 1 false warning: `fsd-layers` on
   `entities-artist → entities-song`, `fsd-public-api` on three lines, `fsd-slice-shape` on the
   `@x/` folder. Steiger reports nothing. A spec-following project is red on its first `lint`.
2. **Slice groups.** `features/auth/{login,register}` becomes one node `features-auth`: two
   false "no index" errors, two shape warnings, and the real violation (`register` importing
   `login`) invisible to Beadloom while Steiger reports it.
3. **Pages-first.** FSD 2.1 says to start code in `pages` and extract only on real reuse; a page
   slice has no size limit. `fsd-cohesion-pages` fires at 60 symbols (measured: a 90-symbol
   page fires).
4. **Custom segments.** The specification allows purposeful custom segments and discourages
   `components`, `hooks`, `types`; `fsd-slice-shape` is an allow-list of five names, so
   `analytics/` and `components/` get the same warning.
5. **`shared` and `app` segments.** The specification requires a public API per segment of the
   unsliced layers and per-component indexes in `shared/ui` and `shared/lib`; no Beadloom rule
   judges `shared` or `app` (the two slice rules carry only the sliced layers' tags), so two
   sidesteps into `shared` go unreported while Steiger flags them.
6. **The overlays** shipped to adopters contradict the specification on `@x` and on the `pages`
   limit, and say nothing of slice groups, custom segments or the barrel pitfalls (no
   `export *`, no index on a segment, per-component index in `shared`). The `init`-written
   header names 5 of Steiger's 17 recommended rules. Steiger 0.7.0 and plugin 0.8.0 are the
   latest.
7. **Monorepo FSD** (`packages/app/src/…`): `init` chooses `monorepo`, writes no FSD node and
   no rules. For the record; neither owner project is one.

## Impact

The Vue adoption starts without false findings on a spec-following layout; a team of solos
reads one FSD in the overlay and in the rules, the specification's; Steiger and Beadloom agree
on what is a violation and differ only in level (file vs graph).

## Goals

1. **`@x` is legal where the specification says.** An import from slice B into
   `<layer>/A/@x/B` on the entities layer is a cross-import by the specification: the reindex
   records on the derived edge that every import of it lands on `@x/<importing slice>`;
   `fsd-layers` accepts such an edge; `fsd-public-api` reads `@x/<B>` as a second public API of
   A, open to B only; `fsd-slice-shape` knows `@x` as a folder. Outside entities, `@x` is a
   finding with the specification's wording. *Done when* the specification's example is
   clean under `lint --strict`, a `@x` file imported by a third slice is a finding, and a
   `features/a/@x/b` import is a finding.
2. **Slice groups are read as groups.** A folder in a sliced layer that holds no standard
   segment and no index, whose children are slices, is a group: one node per inner slice, ref
   id `<layer>-<group>-<slice>`, the layer's tag; the group has no node and shares no code
   (a code file at the group's top is a finding). *Done when* `features/auth/{login,register}`
   yields two nodes, `register → login` is a `fsd-layers` error, and the false "no index"
   findings are gone.
3. **Pages-first is respected.** No cohesion check is written for `pages`; the other layers
   keep theirs; the overlay states pages-first as the specification does. *Done when* a
   90-symbol page is not a finding and a 90-symbol feature still is.
4. **Custom segments by purpose.** `fsd-slice-shape` turns from an allow-list into the
   specification's rule: the standard segments and any purposeful name are fine; the
   discouraged names (`components`, `hooks`, `types`, `utils`, `helpers`, Steiger's list) are
   findings; the list is editable in `rules.yml`. *Done when* `analytics/` is clean and
   `components/` is a finding.
5. **`shared` and `app` have public APIs.** `fsd-public-api` covers the segments of the
   unsliced layers: a segment is entered through its index, or, in `shared/ui` and
   `shared/lib`, through a per-component index (`shared/ui/button/index`), which is a public
   API entry and not a node. *Done when* the two measured sidesteps into `shared` are findings
   and an import of `shared/ui/button` is clean.
6. **The overlays and the written rules say the specification.** `@x`, groups, pages-first,
   custom segments, the three barrel pitfalls, the public API of unsliced layers; the
   `init`-written header lists all 17 recommended Steiger rules with one line each;
   `insignificant-slice` stays on for adopters, with this portal's switch-off explained as an
   example of a reasoned exception, not a default. *Done when* `docs quality` and the
   overlay self-checks are green and the overlay carries no claim the specification
   contradicts.
7. **The two FSD fixtures and this portal stay green**, and the adopter matrix passes.

## Non-goals

- Monorepo FSD (goal 7 of the measurement): a later item, after the two adoptions.
- `uxqc` (doctor over the produced graph) and the graph reviewer: step 2 of the order.
- Any change to the DDD side.

## Acceptance Criteria (overall)

- The specification's own examples, as scratch projects, produce 0 false findings under
  `lint --strict` after `init --yes`; each real violation in them is a finding.
- `lint --strict` 0 errors on this repository; the eight adopter portals green; Steiger green
  on the scaffold.
- The version: **MINOR** by the public-API guide — new rule behaviour on inputs 9.0.0 could
  not read (`@x`, groups) adds findings on a spec-following project it previously got wrong,
  removes false ones; `fsd-cohesion-pages` no longer written by `init` (an adopter's existing
  `rules.yml` is not edited); the shape rule's new key is additive. The RFC states the
  measured exit-code moves and the ruling.

## Rulings needed (the coordinator's recommendation first)

1. **Where `@x` is judged.** *Recommend: a derived edge fact.* The reindex marks a same-layer
   edge whose every import lands on `@x/<importing slice>`; the layer rule stays a graph rule
   and reads the fact; `slice_public_api` owns the file-level check. (The alternative, the
   layer rule reading `code_imports`, makes it a file rule.)
2. **`@x` only on entities.** *Recommend: the specification's text* — entities only; elsewhere
   a finding that quotes the specification. Steiger is looser; we document the difference.
3. **How a group is recognised.** *Recommend: both tests* — a folder is a slice when it holds
   a standard segment or an index; a folder that holds neither and whose children are slices
   is a group. Ref id `<layer>-<group>-<slice>`.
4. **The `pages` limit.** *Recommend: no cohesion check for `pages`*, by pages-first.
5. **`insignificant-slice`.** *Recommend: on for adopters*; this portal's switch-off stays as
   the documented exception.
6. **Custom segments.** *Recommend: the specification's deny-list*, editable, with the
   standard names listed as the known-good set.
7. **`shared`/`app` public API.** *Recommend: yes*, with per-component indexes in `shared/ui`
   and `shared/lib` read as public API entries, not nodes.
8. **Monorepo FSD.** *Recommend: later*, after the adoptions.
