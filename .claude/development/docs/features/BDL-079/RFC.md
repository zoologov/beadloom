# RFC: BDL-079 — Release 8.0.0: the viewer ships, and the public API is declared

> **Status:** Approved
> **Created:** 2026-10-08

---

## Overview

A release by the BDL-075 scheme: bump, change log, documentation made current, the built wheel
verified on another project, review, one PR, a GitHub Release that publishes, the downloaded
wheel verified. New in this release: the public API is declared first, and the version number is
derived from the declaration and the measured diff rather than from precedent.

## Motivation

### Problem

See PRD. In one line: the viewer is on `main` and not on PyPI, and nothing says what the public
API is, so no version number can be argued from the standard.

### Solution

Declare the API, classify every measured change against it, name the release by the
classification, publish, verify on the artifact an adopter downloads.

## Technical Context

### Constraints

- `__version__` in `src/beadloom/__init__.py` is the single source (hatch dynamic version).
  Checked places (9 in 8 files, `beadloom version-surface`): `.beadloom/_graph/beadloom.yml:5`
  (graph-summary-facts), `.claude/CLAUDE.md:118` (doctor), `README.md:111`, `README.ru.md:111`,
  `docs/getting-started.md:52`, `docs/services/cli.md:917` (docs-audit),
  `tests/test_integration_v1.py:27,33` (suite). Unchecked: `ROADMAP.md:3`, `CHANGELOG.md`,
  `tests/test_integration_v1.py:17`, `docs/domains/doc-sync/features/docs-audit/SPEC.md:112-113`.
- `.claude/CLAUDE.md` is composed; its version line is updated through the flow's project layer
  the way BDL-075 did it (R1 reads BDL-075's bead for the exact path).
- The scaffold's `package.json` version is not in the sweep; R1 states whether it carries a
  version and whether it must move.
- Publishing: a GitHub Release tagged `v8.0.0` triggers `pypi-publish.yml` (build → TestPyPI →
  PyPI); `deploy-site.yml` redeploys the portal from `main`. After upload, `uv` must run with
  `UV_NO_CACHE=1`; expect CDN lag.
- `main` is protected; one PR; merge on green CI (the owner's standing word).

### Affected Areas

`cli-commands` (version), `vitepress-site` (the TODO marker, the scaffold's package.json),
`doc-sync` (docs-audit facts), the README pair, `CONTRIBUTING.md`, `CHANGELOG.md`, `ROADMAP.md`.

## Axes

> **Derived by:** `beadloom impact src/beadloom/__init__.py` over `src/beadloom` (Explore, 2026-10-08)
> **Seed:** none — no name the target reaches performs a declared effect under rule `reaches-an-effect-sink`, so every axis below is unresolved and not empty
> **Unresolved:** 1 no-seed, 1 node-owns-unread-files

| Axis | Node | Sites | Owns unread | In scope | Why |
|---|---|---|---|---|---|
| co-writers | — | unresolved — no declared effect rule found a sink this target reaches, so there is no commit point to ask who else writes through | — | no | the version constant has no code co-writer; its writers are documents, listed under Constraints |
| callers | — | no site found | — | no | nothing calls `__version__` through a graph edge; the readers are the version-surface instruments (`doc-sync`), ruled in below |

Ruled in by the owner's goals rather than by a derived row: `doc-sync` (docs-audit facts and the
version surface), `vitepress-site` (the TODO marker, `package.json`), `cli-commands` (the root
node's summary, `--version`). The derivation reaches no code because a release changes a constant
and documents; the four `beadloom impact` runs over the version readers are saved in the session
scratchpad and name only code callers of the readers, not places that state the version.

## The measured diff, v7.0.0 → main (539ed4a3)

| Surface | Change | SemVer kind |
|---|---|---|
| CLI commands | none added, removed, renamed | — |
| CLI options | `docs site --pages-workflow` | added |
| Exit codes | `docs site`, `config-check`, `ci` refuse an unusable `site:` / `activity:` block (unread before) | Breaking, stated: a config that was ignored can now fail |
| `reindex` output | an `Activity:` line only on a shallow history, naming it (never the level names) | added |
| `docs site` | writes the scaffold into `--out` (282 → 467 files), keeps files it did not write | added |
| `config.yml` | `site.*`, `activity.exclude`, `tests.flat_tests` added; none removed | added |
| Activity level values | `hot/warm/cold/dormant` by commits → `hot/warm/cool/quiet/dormant` by changed lines, boxes among boxes; `cold` never emitted | **Breaking** |
| `ctx --json`, MCP `get_context`, `docs polish --format json`, the portal data file | `lines_30d`, `lines_90d` added; level values as above (`export` carries no activity — Explore's row was wrong, corrected by R1) | added + Breaking (above) |
| Debt report | keys unchanged; `dormant` and `high_fan_out` counts move on an unedited tree | Breaking, stated (7.0.0's precedent) |
| `status`, `prime` | keys unchanged; counts move (`.vue`, Go, Swift, JVM imports indexed) | Changed |
| Test binding | `named`, `imported` placements, only under `flat_tests: true` (init declares it for Python) | added |
| Portal data file | schema 1 → 2, superset; the viewer accepts both | added |
| Pages workflow | new, `--pages-workflow`, `fetch-depth: 0` | added |
| `init` | `site/` in `.gitignore`; skips a generated portal; `flat_tests` for Python | added |
| MCP tools, role templates | no diff | — |
| Python import paths | 40 names moved under `beadloom.application.site.*`, one removed; not public API | — |
| Runtime dependency | `markdown-it-py>=4.0,<5` | Changed |

## Proposed Solution

### Approach

R1 (dev): the bump in every place, the public API declared in `CONTRIBUTING.md` (a *Public API*
section) and in `docs/guides/public-api.md` (the same list with the stability promise), the
`[8.0.0]` CHANGELOG section from the table above with each line's PR. D1 (tech-writer): the
README pair (RU → EN) tells of the viewer and the portal if it does not; the eight drifted
reference documents read and corrected or attested; the `TODO` marker filled with the count from
PR #94's site-e2e run; the unchecked version places. V1 (test): the wheel built from the branch
installed on a project that is not this repository — the version everywhere, `docs site` and the
portal build, the activity line — as a script that is then re-run on the downloaded wheel; the
same script red on 7.0.0. R (review, bead id only). P (coordinator): PR, merge on green, the
Release `v8.0.0`, the publish run, the downloaded-wheel verification with `UV_NO_CACHE=1`, the
published portal's activity read, close-out.

### API Changes

None by this release beyond the version. The release *declares* the API.

## Alternatives Considered

### 7.1.0
Every change is an addition if value vocabularies are outside the public API. Rejected by the
owner's composition: vocabularies are in, so `cold` disappearing is incompatible.

### Publish without the declaration
Repeats the 7.0.0 argument-by-precedent. Rejected: SemVer's first rule.

## Risks

- A README claim about the viewer goes wrong on the published portal (the Source link, the
  activity on a shallow clone) — V1 reads the live portal after deploy.
- CDN lag after upload makes the downloaded wheel read 7.0.0 for minutes — retry with
  `UV_NO_CACHE=1`, as BDL-071/075 recorded.
- The docs audit misreads a number in new prose — reword, as W did in BDL-078.

## Open Questions

None for the owner: the version and the API composition are ruled.
