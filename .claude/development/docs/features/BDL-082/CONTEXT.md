# CONTEXT: BDL-082 — FSD by the specification 2.1

> **Status:** Approved
> **Approval:** delegated by the owner on 2026-10-11.
> **Created:** 2026-10-11

---

## Goal

Beadloom's FSD rules, `init` and overlays say feature-sliced.design 2.1: `@x` cross-imports on
the entities layer, slice groups, pages-first, custom segments by purpose, the public API of the
unsliced layers. A spec-following project gets no false finding and every real one.

## State

Branch `features/BDL-082` from `main` at `30605b71` (9.0.0 released). The measurement is in
`axes.md`; the owner's eight rulings are in PRD.md; the decisions D1–D6 in RFC.md.

## Key Constraints

- The specification's text wins over Steiger where they differ (`@x` on entities only); the
  difference is documented.
- The version is MINOR by the public-API guide: additive keys and values; exit codes move only
  on inputs 9.0.0 read wrongly, and the CHANGELOG measures both directions.
- `beadloom waves` decides the waves; two-level verification; one bead per agent; commits by
  path under the landing lock; documents in English; no owner project name in any artifact.
- The scratch projects of the specification's own examples are the acceptance probes.

## Code Standards

Python >= 3.10, ruff, mypy --strict, pytest; documents in English; commits
`[BDL-082] <type>: <description>`; one PR per slice; merge on green CI.

## Architectural Decisions

| Date | Decision | Why |
|---|---|---|
| 2026-10-11 | `@x` is a derived edge fact written by the reindex; the layer rule stays a graph rule; the public-API rule owns the file check; entities only | Owner's rulings 1, 2 |
| 2026-10-11 | A slice holds a standard segment or an index; a folder holding neither whose children are slices is a group; ref id `<layer>-<group>-<slice>` | Owner's ruling 3 |
| 2026-10-11 | No cohesion check for `pages` (pages-first); `insignificant-slice` on for adopters; the shape rule is a deny-list by purpose; `shared`/`app` segments have a public API with per-component indexes as entries | Owner's rulings 4–7 |
| 2026-10-11 | Monorepo FSD after the adoptions | Owner's ruling 8 |
| 2026-10-11 | Every title is drawn inside its box: a box is never smaller than its title needs; title plates for nodes are retired (S2c) | Owner, on the 9.0.0 portal («все надписи должны быть в блоках») |
| 2026-10-11 | The public-API guide: removing a false finding on an input a rule read wrongly is a fix, not Breaking; adding findings on unchanged input stays MAJOR — BDL-082 is MINOR | Owner («согласен с minor»); written by S2W |

## Related Files

`src/beadloom/graph/rules/{slices.py,layers.py,layer_crossings.py}`, `src/beadloom/graph/import_resolver.py`
(the edge fact), `src/beadloom/onboarding/scanner/{fsd_layout.py,rules_gen.py,steiger_script.py}`,
`src/beadloom/onboarding/templates/roles/architecture/fsd/*`, `tests/fixtures/site/{vue-fsd,rn-fsd}`,
`docs/guides/public-api.md`, the rule-engine and agent-prime SPECs.

## Current Phase

- **Phase:** Development
- **Current bead:** see ACTIVE.md
- **Blockers:** none

- 2026-10-13 (owner, after S2R's third pass): **ruling 3 refined, option (c).** A folder that holds code files at its top is a group only when at least one child holds a standard segment (`ui`, `model`, `api`, `lib`, `config` — Steiger's own slice test), and a slice when its children carry only an index; a folder with no code at its top is a group when its children are slices, at any depth. Measured probes: a pre-migration slice `features/checkout/{..., components/Summary/index.ts}` stays one node; the specification's group `features/auth/{helpers.ts, login/{index, ui/}, register/{index, ui/}}` stays two nodes with `register → login` an error. Fix bead `beadloom-us5r.3` had landed option (a) (code at the top ⇒ always a slice), which hid that crossing; superseded.
