# CONTEXT: BDL-080 — The portal is a service, and the viewer serves a Feature-Sliced frontend

> **Status:** Approved
> **Created:** 2026-10-08

---

## Goal

`vitepress-site` is a service; every layer rule is drawn; the viewer is cut by cohesion and the
roles say so; `init` serves Vue and React Native FSD projects honestly; every number and colour
on the portal names its population. MINOR release after the four slices.

## State

Branch `features/BDL-080` from `main` at `7b9a9b65` (8.0.0). Beads `beadloom-be6e` and
`beadloom-pre3` fold into this epic.

## Key Constraints

- The declared public API rules the version: this epic adds only.
- `beadloom waves` decides every wave; S2's node declarations land before later viewer beads.
- Two-level verification (owner, 2026-10-06): a bead runs its own cases, the specs it touches,
  the site pytest parts, ruff, mypy, lint; the full tree runs once per slice before its review;
  CI runs the stacks. A behaviour rule a user sees is agreed with the owner before code.
- Owner project names never appear in committed artifacts; the fixtures are synthetic.

## Code Standards

Python >= 3.10, ruff, mypy --strict, pytest; JavaScript ES modules in the scaffold, Playwright;
documents in English; README Russian first; commits `[BDL-080] <type>: <description>`; one PR
per slice; merge on green CI.

## Architectural Decisions

| Date | Decision | Why |
|---|---|---|
| 2026-10-06 | `vitepress-site` is a service like `tui`; decompose by cohesion; the roles say so | Owner |
| 2026-10-08 | Two epics by cohesion; this one = be6e + pre3; one PR per slice | Owner |
| 2026-10-08 | Layer-rule scope by FSD practice (per frontend root; optional explicit `scope:`); cohesion by shape first, a calibrated symbol signal second; two fixtures, Vue 3 + TS and React Native + TS, shaped like the owner's projects | Owner's answers to the PRD |
| 2026-10-08 | `site` becomes an alias of `service` at the loader; the data file grows additively (schema 2 kept); the public-API rule is a rule over resolved imports, not a glob; legacy directories beside FSD layers become nodes | RFC D1, D2, D4, D5 |
| 2026-10-08 | Steiger's `recommended` set is the reference for the FSD rules | One owner project runs it; FSD's own linter |
| 2026-10-08 | Layers as drawn boxes at the overview for a scoped rule (derived, not nodes); Steiger on the scaffold, run with the style linters, named by the Gate as not run | Owner: «слои блоками — согласен»; «Steiger должен и у нас появиться» |
| 2026-10-09 | `title:` on a layers rule is the display name (legend, filter, card); the URL keeps the rule's name; a box holding a rule's layer boxes opens only once they are readable, even when selected | Owner: «делай через title, и фильтр тоже так показывай»; the owner's look at S1 |
| 2026-10-08 | Legend from the canvas, not the data; one-kind aggregated lines keep their dash | Owner's two legend observations (#uses, #contracts) |

## Related Files

`src/beadloom/graph/loader.py`, `graph/rules/{loader,types,layers,layer_reach}.py`,
`graph/import_resolver.py`, `application/site/{architecture_view,architecture_card,generate,
repository_link,node_pages,nav}.py`, `onboarding/{presets.py,scanner/bootstrap.py,
scanner/rules_gen.py,templates/roles/architecture/fsd/*}`, the viewer under
`src/beadloom/site_scaffold/.vitepress/theme/**`, `tests/fixtures/site/*`,
`tests/support/adopter_portals.py`, `.github/workflows/site-adopters.yml`, `.beadloom/_graph/*`,
`.beadloom/_graph/rules.yml`.

## Current Phase

- **Phase:** S1 development
- **Current bead:** see ACTIVE.md
- **Blockers:** none
