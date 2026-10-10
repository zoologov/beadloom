# PRD: BDL-081 — Release 9.0.0: the portal is a service, the viewer serves Feature-Sliced frontends

> **Status:** Approved
> **Created:** 2026-10-10

---

## Problem

PyPI's latest is 8.0.0 (2026-10-08). `main` at `290507b2` carries BDL-080 — the site as a
service, every layer rule drawn, the viewer cut into FSD slices with a cohesion rule, the
resolver's JavaScript side (tsconfig paths, aliases, platform suffixes, `.mjs/.cjs`, Expo
modules and Expo Router), the `init` FSD preset with Steiger's rules, two FSD fixtures, every
population named on the portal, the portal's brand — and none of it is published.

The version follows Semantic Versioning 2.0.0 against the public API declared in
`CONTRIBUTING.md` and `docs/guides/public-api.md`. Measured on 2026-10-10 (`v8.0.0` against
`main`, two versions of the code over the same files; the tables are in `axes.md` and the RFC):

- **MAJOR holds.** A `kind: site` node is read as `service`: `lint --strict` and `ci` move from
  exit 0 to 1 on an unedited project with such a node; `ctx --json`, `status --json`
  (`by_kind.site` gone), `export`, the data file and MCP `get_context` show `service`; the
  node's page moves from `other/` to `services/`.
- **`[Unreleased]` understates Breaking.** Its line "nothing is removed or renamed" is false:
  42 scaffold files are removed or renamed, one generated page moves, one JSON key disappears.
  Six further measured exit-code changes sit under *Added* although 8.0.0 classed the same
  classes under *Breaking* (the rulings below).
- Commands: 56 before and after, one option value added (`init --preset fsd`); `config.yml`
  keys only added; MCP schemas identical; `architecture.data.json` schema 2 with six additive
  keys; runtime dependencies unchanged.
- The release harness `tests/release/verify_the_release.py` is unchanged since 8.0.0 and checks
  none of the new surfaces; it installs without the `languages` extra, so it cannot parse a
  TypeScript or Vue project.
- 18 checked version places in 10 files plus the unchecked ones `version-surface` lists; seven
  "since 8.0.0 (MINOR, …)" lines in the public-API guide describe what 9.0.0 ships.

## Impact

Adopters get the FSD support, the honest portal and the brand; the owner's Vue frontend can be
onboarded on a published version (ROADMAP item 1). The CHANGELOG tells an 8.0.0 adopter what
moves under their feet and what to run.

## Goals

1. **The bump, everywhere `version-surface` names.** 9.0.0 in the source of truth and every
   checked and unchecked place the surface lists (the graph summary, CLAUDE.md through
   `setup-agentic-flow`, the getting-started page, the public-API guide's "since" lines, the
   harness's `DEFAULT_RELEASE`, the two test assertions, ROADMAP). *Done when* `version-surface`
   reports every checked place at 9.0.0 and the unchecked ones named in the RFC are read.
2. **`CHANGELOG.md` `[9.0.0]` with Breaking first and complete by the measurement**, then
   Upgrading (reindex; `setup-agentic-flow` for composed roles; `lint --strict` after the new
   import readings; `config-check` for an `imports:` block; the leftover `other/` page), then
   Added / Changed / Fixed / Known limitations. *Done when* every row of the measured diff that
   the rulings class as Breaking is named there, and the "nothing is removed or renamed" claim is
   gone.
3. **The documentation reads the release.** The public-API guide: item 6 states what
   "files generated for an adopter" covers; items 3 and 5 name `landscape.data.json` as
   undeclared beside `dashboard.data.json`; the sentence "no accepted configuration is refused"
   corrected by the measurement; the "since 8.0.0" lines become "since 9.0.0". The README pair's
   Gate paragraph rerun at the release. *Done when* `docs audit`, `sync-check` and
   `docs quality` are green on a fresh index and the pair leg passes.
4. **The leftover page is retired on upgrade** (ruling 6, if "fix"): an 8.0.0 portal rewritten
   by 9.0.0 does not keep `other/<ref>.md` beside `services/<ref>.md`. *Done when* the upgrade
   case in the scaffold tests holds it.
5. **The harness verifies the new surfaces on the published artifact**: installs with the
   `languages` extra; `init` on an FSD tree writes the nine rules and `lint --strict` judges
   them; Steiger's config and `lint:fsd` are written; the brand files and the footer are in the
   wheel; a `kind: site` node reads as a service; fails on 8.0.0 first. *Done when* the script
   exits 0 on the downloaded 9.0.0 wheel and non-zero on 8.0.0.
6. **Published and verified.** PR merged on green, Release `v9.0.0` (title with the `v`),
   `pypi-publish.yml` green, the downloaded wheel verified, the published portal shows the
   brand. Close-out by the template.

## Non-goals

- Any product change beyond the leftover page (goal 4) and the harness. Everything else is
  Debt to zero (`beadloom-ba9w`) or later.
- The role model (`model: opus` in the role templates) stays as it is (owner, 2026-10-10).

## Acceptance Criteria (overall)

- `beadloom version-surface`: every checked place 9.0.0; `beadloom ci` rc 0; the suite green;
  the README pair leg green.
- The harness: 0 on the downloaded 9.0.0 wheel, non-zero on 8.0.0, and its report names what it
  ran.
- The CHANGELOG `[9.0.0]` matches the measured diff under the rulings below, Breaking first.

## Rulings needed (the measurement cannot decide these; the coordinator's recommendation first)

1. **Scaffold theme internals.** *Recommend: not in the promise.* "Files generated for an
   adopter" covers `docs site`'s entry files (`package.json`, the data files, the pages), not
   the theme's internal paths; otherwise every viewer refactor is MAJOR. The guide's item 6 says
   so; the 42 renames stay under Changed.
2. **The new import readings** (`.mjs` importers, tsconfig `paths`, platform files) move
   `lint --strict` 0 → 1 on an unedited JavaScript project. *Recommend: Breaking*, as 8.0.0
   classed the same class; the release is MAJOR anyway and the entry is the honest one.
3. **Composed-role drift** (`config-check` and `ci` exit 0 → 1 until `setup-agentic-flow`
   runs). *Recommend: Breaking, with the Upgrading step*, by the guide's rule 3.
4. **`init` auto-detects `fsd`** on a tree 8.0.0 read as `monolith` (exit 0 → 1, 21 fewer
   documents). *Recommend: Breaking* — the same input, a different verdict — with the reason
   that the old reading was wrong.
5. **The `fsd` overlay's annotation vocabulary** (`feature=` → `component=`). *Recommend:
   Changed, not Breaking* — the overlay described a graph `init` never produced before.
6. **The leftover `other/<ref>.md` after an in-place upgrade.** *Recommend: fix before the
   release* (goal 4): a published page that duplicates another is the class this project names.
7. **`landscape.data.json`.** *Recommend: undeclared*, named beside `dashboard.data.json` in
   the guide.
8. **Configuration 8.0.0 ignored and 9.0.0 reads or refuses** (`imports:`, `scope:`, `title:`,
   `tag_prefix` beside `kind`). *Recommend: Breaking*, as 8.0.0 classed `site:`/`activity:`,
   and the guide's "no accepted configuration is refused" sentence corrected to "…ignored
   silently; such a key is read or refused in the next MAJOR".
