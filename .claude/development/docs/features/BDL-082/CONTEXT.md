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

## Related Files

`src/beadloom/graph/rules/{slices.py,layers.py,layer_crossings.py}`, `src/beadloom/graph/import_resolver.py`
(the edge fact), `src/beadloom/onboarding/scanner/{fsd_layout.py,rules_gen.py,steiger_script.py}`,
`src/beadloom/onboarding/templates/roles/architecture/fsd/*`, `tests/fixtures/site/{vue-fsd,rn-fsd}`,
`docs/guides/public-api.md`, the rule-engine and agent-prime SPECs.

## Current Phase

- **Phase:** Development
- **Current bead:** see ACTIVE.md
- **Blockers:** none
