# RFC: BDL-075 — Release 7.0.0 with the documentation current

> **Status:** Approved
> **Created:** 2026-09-29

---

## Overview

Publish 7.0.0 from `main` with BDL-072, BDL-073 and BDL-074, and bring the four documents an adopter
or the owner reads first — `README.ru.md`, `README.md`, `ROADMAP.md`, `BDL-UX-Issues.md` — into line
with the product and the tracker. The only product edit is the version literal.

## Motivation

### Problem

See PRD. In short: three work items are merged and unpublished, and the README, ROADMAP and issue
log each state things that are false on `main` and, for the README, false on 6.0.0 as well.

### Solution

One release commit series on `features/BDL-075`: the version bump and change log first, then the
three documentation passes in parallel, a verification on the built wheel, a review, one pull
request, and a publish from the merged `main` verified on the wheel downloaded from PyPI.

## Technical Context

### Constraints

- **The version comes from `src/beadloom/__init__.py` at build time**, nothing checks it against
  the tag, and the upload runs with `skip-existing: true` (`.github/workflows/pypi-publish.yml`,
  triggered on `release:`). A green publish run is not evidence; the downloaded wheel is.
- **`tests/self_check/config/test_version_surface.py:60-80`** fails unless nine files state the
  current literal — `CHANGELOG.md`, `ROADMAP.md` and the docs-audit SPEC among them — so the bump,
  the change log and the ROADMAP's version line land together.
- **`.claude/CLAUDE.md:118` is rendered from `__version__`** (`onboarding/scanner/claude_md.py:203`)
  and its hash is recorded in `.beadloom/flow-manifest.json`: regenerate it with
  `beadloom setup-agentic-flow`, never by hand.
- **History is not rewritten.** Lines that state what 6.0.0 or earlier did keep saying it; if the
  docs audit reads such a line as a stale current-version claim, it gets a `docs_audit.ignore`
  triple with its reason, as BDL-071 did for 4.0.0.
- **The README pair:** Russian is the source, English follows; `readme-pair` compares shape only,
  and `docs audit` reads 0 mentions in `README.ru.md`, so no check reads the source's numbers —
  every number is measured by hand against the 7.0.0 build.
- **Publishing is outward-facing**: the tag and the GitHub release are created only after the owner
  agrees to merge and to publish.

### Affected Areas

The version surface (Axes below), `CHANGELOG.md`, `README.ru.md`, `README.md`,
`.claude/development/ROADMAP.md`, `.claude/development/BDL-UX-Issues.md`, the tracker (one new bead
for the `issue-number check` blind spot; `beadloom-txeq` reconciled).

## Axes

`beadloom impact src/beadloom/__init__.py --section` finds no seed — no declared effect reaches the
version literal — so the working surface comes from the explore role's supplement
(`axes.md`, derived by `beadloom version-surface`, `grep` and `sync_state`).

> **Derived by:** `beadloom impact src/beadloom/__init__.py` over `src/beadloom`; supplement by `beadloom version-surface` at `11b5ad0d`
> **Seed:** none — every `impact` axis is unresolved, not empty
> **Unresolved:** a place stating a version other than `6.0.0` is invisible to the sweep; `.json` files are not read

| Axis | Node | Sites | Owns unread | In scope | Why |
|---|---|---|---|---|---|
| co-writers | — | unresolved — no effect rule found a sink | — | no | Nothing to rule: no declared effect. |
| callers | — | no site found by `impact`; ten readers found by `grep`, rows below | — | no | Superseded by the `readers` rows. |
| current-version | beadloom | `src/beadloom/__init__.py:6` | none | **yes** | The literal the build publishes. |
| current-version | beadloom | `docs/getting-started.md:45` | none | **yes** | States the current version. |
| current-version | cli | `docs/services/cli.md:858` (`:857` is `bd`'s version, left) | none | **yes** | States the current version. |
| current-version | docs-audit | `docs/domains/doc-sync/features/docs-audit/SPEC.md:112-113` | none | **yes** | Pinned by the version-surface test. |
| current-version | — | `.beadloom/_graph/beadloom.yml:5`, `.claude/CLAUDE.md:118` (regenerated), `tests/test_integration_v1.py:17,27,33`, `ROADMAP.md:3,8` | — | **yes** | Each states the current version; CLAUDE.md through `setup-agentic-flow`. |
| pinning-test | — | `tests/self_check/config/test_version_surface.py:60-80` | — | **yes** | Must stay green on the release commit; not edited unless its file list is wrong. |
| release-notes | — | `CHANGELOG.md:8` | — | **yes** | A `[7.0.0]` section. |
| audit-config | — | `.beadloom/config.yml:120-151` | — | **yes** | New `docs_audit.ignore` triples only if the audit reads a true 6.0.0 history line. |
| paired-docs | beadloom | `docs/architecture.md`, `docs/getting-started.md`, `docs/guides/ci-setup.md` | none | **yes** | Paired with `__init__.py`; read and re-attested by ref after the bump. |
| — (not derived; owner 2026-09-29) | onboarding | `src/beadloom/onboarding/templates/agentic_flow/commands/templates.md.txt:278` — the PLAN template's bead table | — | **yes** | Ruled in by the owner with CONTEXT/PLAN: `beadloom-10er`, bead T1. |
| readers | cli-commands, mcp-server, doctor, reindex, wave-plan, docs-audit, version-surface | ten lines reading `__version__` at run time | none | no | They read the literal; none states it. |
| history | — | `CHANGELOG.md`, `ROADMAP.md`, `.beadloom/config.yml`, `BDL-UX-Issues.md`, BDL-071 docs — lines naming 6.0.0 as history | — | no | History is not rewritten. |

**Documentation surface, not derivable by `impact`** (Markdown under `.claude/` and the repository
root): `README.ru.md`, `README.md`, `ROADMAP.md`, `BDL-UX-Issues.md` — ruled **yes** by the PRD.

## Proposed Solution

### Approach

- **R1 — the bump (dev).** `__version__` = `7.0.0`; every `current-version` row above;
  `setup-agentic-flow` for `CLAUDE.md`; `CHANGELOG.md` `[7.0.0]` with `### Breaking` (the debt
  report's untested count from the binding; `extra.tests` values — `framework` may join names,
  counts are the union), `### Removed` (`beadloom.context_oracle.test_mapper`,
  `_store_test_mappings`), `### Added`, `### Fixed`, compiled from the explore supplement and each
  work item's docs; `ROADMAP.md:3,8` written as 7.0.0 **not yet verified** (BDL-071 R5 precedent);
  `docs_audit.ignore` triples only where the audit flags a true history line. Gate and suite green.
- **D1 — README pair (tech-writer).** `README.ru.md` first: the 12 audited defects, measured
  against the R1 build; the capabilities 7.0.0 publishes, one section, using the audit's proposed
  Russian as a draft under the owner's language rule. Then `README.md` follows the corrected
  Russian, including the three content differences the audit found.
- **D2 — ROADMAP (tech-writer).** The 22 findings; shipped items out of "being worked on"; the
  owner's ranking; federation deferred until needed; `beadloom-txeq` reconciled with its merged PR.
  Leaves the version line to R1.
- **D3 — issue log (tech-writer).** The 55 fixed entries to Closed with one line of evidence each;
  the 21 partly fixed amended; duplicates removed; number order restored; `<details>` and the
  second H1 fixed; Chronology marked historical to 2026-08-26; a bead filed for `issue-number check`
  missing summary-line duplicates.
- **V1 — the built wheel (test).** Build the wheel from the release commit; on a project that is not
  this repository, run the harness: `--version` 7.0.0, `ctx` shows mirror-bound tests,
  `mutation --changed-since` states its population, the debt report's `test_population`; follow the
  README's install and first-run steps literally in a fresh environment.
- **R — review**, authors' accounts withheld, clean launch prompt.
- **P — publish (coordinator, owner-gated).** Merge the PR; tag `v7.0.0` on the merge commit; create
  the GitHub release; after the publish run, download the wheel from PyPI (`UV_NO_CACHE=1`) and
  rerun V1's harness on it; mark ROADMAP's version line verified in the close-out.

### Changes

| File / Module | Change |
|---|---|
| `src/beadloom/__init__.py` | `6.0.0` → `7.0.0` |
| version surface (Axes) | the current literal |
| `CHANGELOG.md` | `[7.0.0]` |
| `README.ru.md`, `README.md` | the audit's defects; the 7.0.0 capabilities |
| `ROADMAP.md` | the audit's findings; ranking; federation deferred |
| `BDL-UX-Issues.md` | Open holds only open entries; structure repaired |

### API Changes

None beyond the version string. The breaking changes shipped in BDL-074 and are documented here.

## Alternatives Considered

### Option A: 6.1.0
Rejected: two changes alter a verdict and a JSON value set on an unedited project — the bar 4.0.0
recorded and BDL-071 applied makes that major.

### Option B: publish now, fix the documents afterwards
Rejected by the owner: the README describes the installed version, so it ships with the release
that publishes what it describes.

### Option C: add BDL-074's capabilities to the README before releasing
Rejected: the README would promise what `pip install beadloom` does not deliver.

## Risks

| Risk | Probability | Impact | Mitigation |
|---|---|---|---|
| The docs audit fails on a true 6.0.0 history line after the bump | Medium | Gate red | A `docs_audit.ignore` triple with its reason (BDL-071 precedent) |
| The upload is skipped silently (`skip-existing`) | Low | A green run with no 7.0.0 | Verify on the downloaded wheel |
| A README claim true on `main` differs on the built wheel | Low | False README | V1 measures on the wheel, not the tree |
| `uv` resolves a stale index right after upload | Medium | False "not published" | `UV_NO_CACHE=1`, `/pypi/beadloom/7.0.0/json` |

## Open Questions

- [ ] None blocking. The version number is proposed as 7.0.0 in the PRD and approved with it.
