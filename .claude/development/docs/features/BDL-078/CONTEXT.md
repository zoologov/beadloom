# CONTEXT: BDL-078 — The viewer looks finished, and five defects are fixed

> **Status:** Approved
> **Created:** 2026-10-05
> **Last updated:** 2026-10-05

---

## Goal

A viewer without visual artefacts — one thin line weight, a calm routed overview, open boxes that
stay readable — an activity metric that separates busy nodes from quiet ones on a squash-merged
history, and five open defects fixed.

## Key Constraints

- **BDL-077's constraints stand:** one ELK layout from which everything is derived; boxes never
  move; Cytoscape 3.34.1; elkjs 0.12 in a worker; literal colours; exact pins; FSD
  (`site-fsd-layers`); the test handle `window.__beadloomViewer`; performance bounds per
  environment (`e2e/support/environment.js`).
- **The owner's fourteen rulings in the PRD are the specification.** A reading that departs from
  their wording is surfaced to the owner, not adopted (lesson of BDL-077's hub bound).
- **Schema stays 2.** `activity` may gain keys through the pinned allow-list; never author data.
- **Removed features take their cases with them** (bridges, junction dots, the gradient); no other
  bar is lowered.
- **Shipped code is project-neutral** (no node ids, bead ids or "this repository").
- **Tests first:** each rule lands with a case seen failing first; browser cases assert state, with
  oracles in `e2e/support/` independent of the viewer's own functions.
- **Commits and suites:** only your own files by explicit path (`git commit --only`), only after
  `bd merge-slot acquire --holder <bead-id>` exits 0, then release with the same holder; never
  pipe a command whose exit code is the answer; long suites in the foreground; restore
  `.beadloom/metrics_history.json` if a run rewrites it. Do not push.
- **The owner looks at the viewer in a browser before the merge;** merge on the owner's word.

## Code Standards

### Language and Environment
- JavaScript (ES modules) and Vue 3 for the viewer; Python 3.10+ for the fixes and the activity
  metric. Node 22 (`$HOME/.nvm/versions/node/v22.9.0/bin`); uv.

### Methodologies

| Methodology | Application |
|---|---|
| TDD | Red → Green → Refactor; Playwright cases and pytest seen failing first |
| Clean Code | pure functions in `lib/`, effects in `model/`; SRP, DRY, KISS |
| Architecture | FSD for the viewer; `services -> application -> domains -> infrastructure` for Python |

### Testing
- pytest + pytest-cov (≥ 80% on changed modules); Playwright on the built portal and the six
  adopter fixtures; the `performance` project.

### Code Quality
- `uv run ruff check src/ tests/`, `uv run mypy src/`, `npm run docs:build`, the browser suite,
  `beadloom ci` rc 0.

### Restrictions
- No `Any` / `# type: ignore` without a reason; no `print()`; no bare `except:`; pathlib; SQL `?`
  parameters; `safe_load`. No `console.log`; no global state beyond the test handle.

## Architectural Decisions

| Date | Decision | Reason |
|---|---|---|
| 2026-10-04 | Bridges removed; a followed edge is drawn on top with a casing (two passes) | Owner ruling 1; bridges read as crutches |
| 2026-10-04 | Rounded merges, no junction dots | Owner ruling 2 |
| 2026-10-04 | No direction gradient; arrowheads carry direction | Owner ruling 3; reverses BDL-076's "light to dark" |
| 2026-10-04 | One line weight, thin, always; counts on pills; one arrowhead per shared final run; separate arrivals stay separate | Owner rulings 4, 10 |
| 2026-10-04 | Node status as a corner mark | Owner ruling 5 |
| 2026-10-04 | Activity by changed lines over 30 days, levels relative to the project, boxes roll up | Owner ruling 6; commits under squash merges mean "merges" |
| 2026-10-04 | Selecting a node zooms to its neighbourhood | Owner ruling 7 |
| 2026-10-04 | The overview has its own routing between fixed boxes and is calm by default (probe V5) | Owner ruling 8; head overlaps 12 → 0, min gap 0.8 → 7.1 px |
| 2026-10-04 | An open box keeps its outward edges aggregated; a node's own outward edges on hover/selection; a "+N" mark | Owner rulings 9, 14; replaces BDL-077's "drawn as itself once both ends are drawn" |
| 2026-10-05 | A box opens when its nodes are readable (≥ 24 px tall), not at 600 px | Owner ruling 12 |
| 2026-10-05 | Loops from a node to its own container stay drawn | Owner ruling 13; the owner looks before the merge |
| 2026-10-04 | Deferred: an overview for projects whose top level does not fit the canvas | Owner ruling 11 |
| 2026-10-05 | Activity levels rank boxes among boxes and leaves among leaves; lock files and generated files do not count as change (`beadloom-btkd.1`) | Owner, after F-activity: 7 of 10 hot nodes were boxes; `package-lock.json` was 3,912 of vitepress-site's 17,714 lines |
| 2026-10-05 | Flat Python tests bind through `tests: {flat_tests: true}`, written by `init`; not a default | `beadloom-76mk`; binding by name stays opt-in (2026-09-28 ruling); surfaced to the owner, not objected |
| 2026-10-05 | A line enters its arrowhead correctly at every zoom at which the edge is drawn; 'correct' is defined by geometry AND confirmed on rendered pixels (`beadloom-btkd.2`, between V2 and V3) | Owner, after looking at V1: «все равно стрелки сломаны, линия должна заходить в наконечник стрелки правильно»; V1's measure (0 of 139 broken at zoom 1) passed what the owner sees as broken |
| 2026-10-05 | At the overview every top-level node is a well-formed box with its title inside; a small node is drawn at a minimum size that holds its title, and the plate beside the box is the exception, counted (`beadloom-btkd.3`, after the arrowheads, before V3) | Owner, after looking at V2: «у tui, mcp_server, ai_agents - кривые блоки нод, а надписи вне блока ноды… Это надо поправить»; the overview itself he accepted: «Стало значительно лучше» |
| 2026-10-06 | P: the PR opens when T, R, W are done and the Gate is green; merge on green CI without a further browser look; a release work item follows (the BDL-075 scheme) | Owner: «все проверь, делай pr и после ci - сливай… готовь новый релиз с обновленным вьювером и выпускай по отработанной схеме» |
| 2026-10-06 | One count per node and per line: the '+N' mark, hover and click agree; a selected node's aggregated line carries the selected node's count; a click on a box shows outward edges as hover does (`beadloom-btkd.7`). tui takes its layer's colour; the project box is visible (`beadloom-btkd.8`) | Owner, after the look at 9237d115: «Выглядит чище, стрелки - отлично» and five observations (verbatim in the beads) |
| 2026-10-06 | A click on a box: the box opens and is framed whole; its contents at full strength; its outward edges one line per neighbouring box with a count, as on hover; the card describes the box; a click on a node inside behaves as for a node (`beadloom-btkd.7`) | Owner: «при клике на CLI… внутри все приглушено, показываются какие-то непонятные связи… выглядит как плохой ui/ux»; the coordinator's five-point proposal, owner «Согласен» |
| 2026-10-06 | Verification in two levels for the rest of the epic: a bead runs its own cases, the specs it touches, the site-related pytest parts, ruff, mypy, lint; the full combined tree (four pytest parts, whole Playwright, six adopter stacks) runs once, by the last viewer bead (`beadloom-btkd.10`), and CI runs the stacks. For a change a user sees, the behaviour rule (hover, click, zoom-out) is written and agreed with the owner before code | Owner, on why the viewer beads took 4-6 hours each: «Первый и третий да, запусти» |
| 2026-10-07 | The overview's boxes have rounded corners like the nodes — one style (`beadloom-btkd.16`, after btkd.15) | Owner, after the look at 5bcb6881: «все круто! Мне очень нравится! Единственное, я бы сделал блоки общего вида со скругленными углами, как у узлов» |

## Related Files

Discover with `beadloom ctx site-graph-viewer`, `beadloom ctx vitepress-site`,
`beadloom ctx import-resolver`, `beadloom ctx git-activity`, and `axes.md`.

## Current Phase

- **Phase:** Review findings being fixed (btkd.17, btkd.18), then re-review, docs, Gate, PR (2026-10-07)
- **Current bead:** see ACTIVE.md
- **Blockers:** none
