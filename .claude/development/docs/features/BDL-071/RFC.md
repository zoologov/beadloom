# RFC: BDL-071 — Release 5.0.0, then 6.0.0: the population report ships before the verdict change

> **Status:** Done
> **Created:** 2026-09-13

---

## Overview

Two versions, published in the order BDL-070's CONTEXT requires. **5.0.0** is cut from `7efa4006`
on a `release/5.0.0` branch and carries BDL-069 and BDL-070 Release A. **6.0.0** is cut from `main`
through a release pull request and carries Release B. Neither changes code. Each is verified on the
wheel downloaded from PyPI before the next step starts.

## Motivation

### Problem

`main` already holds both halves, merged in order: Release A at `7efa4006`, Release B at `692205d7`.
A release from `main` would publish both at once. PyPI's latest is 4.0.0.

### Solution

Publish Release A from the commit where it landed, on a branch that adds only a version bump and a
change-log section. Then publish Release B from `main`, with the change log split so that `[5.0.0]`
on `main` is the text 5.0.0 actually published, and `[6.0.0]` names what 6.0.0 removed from it.

## Technical Context

### Constraints

- **No code change** in either release (PRD non-goal). A defect found on the way is filed.
- **The version is read at build time from `src/beadloom/__init__.py`** through
  `[tool.hatch.version]`. Nothing checks that the tag matches it.
- **The publish step uploads with `skip-existing: true`**, to Test PyPI and to PyPI. A wheel that
  kept a version already on PyPI is skipped **silently, and the run stays green**. So a green publish
  run proves nothing about what was published; the downloaded wheel does.
- **`ci.yml` runs only on pull requests to `main`.** A commit on `release/5.0.0` gets no pull-request
  CI. Its only CI is the publish workflow's own jobs — the 3.10–3.13 test matrix with `ruff`, `mypy`
  and the coverage suite, then `reindex`, `lint --strict` and `sync-check` — which gate the build.
- **`release/*` branches are unprotected**, and 3.0.1 shipped from one — the precedent.
- **The publish workflow triggers on a GitHub release being published**, with no reviewer on the
  `pypi` or `testpypi` environment.

### Affected Areas

The version is one fact restated in documents, a graph summary, a composed instruction file and a
test. The change log is split by release. Three documents state version **history** that the docs
audit reads as a current claim.

## Axes

Rule each row by the node's role in the change: the axis a node surfaced under is not its role.

> **Derived by:** `beadloom impact src/beadloom/__init__.py` over `src/beadloom`
> **Seed:** none — no name the target reaches performs a declared effect under rule
> `reaches-an-effect-sink`, so every axis below is unresolved and not empty
> **Unresolved:** 1 no-seed, 1 node-owns-unread-files

| Axis | Node | Sites | Owns unread | In scope | Why |
|---|---|---|---|---|---|
| co-writers | — | unresolved — no declared effect rule found a sink this target reaches | — | no | Names no node and contributes no work site. The population it exists to name is established by the version-surface block below. |
| callers | — | no site found | — | no | `__version__` is read, not called; its readers are the places the block below lists. |

**Supplement — the places `impact` cannot read, derived by the project's own instrument.** `impact`
reads Python; the version is also stated in YAML, Markdown and tests. `beadloom version-surface`
derives every place, and was run on `main` at `741f1b77` and on `7efa4006` in a worktree running that
revision's own code. The **checked** set is identical on both revisions: 10 places in 8 files. Each
row below is ruled by whether the line states the **current** version (raise it) or version
**history** (never rewrite it), measured by reading every line.

> **Derived by:** `beadloom version-surface` on `main` (`741f1b77`) and on `7efa4006`, each on its own code
> **Seed:** none — a sweep for the literal `4.0.0`, not a reachability derivation
> **Unresolved:** a place that already states a version other than `4.0.0` is invisible to the sweep, as the command itself says

| Axis | Node | Sites | Owns unread | In scope | Why |
|---|---|---|---|---|---|
| current-version | beadloom | `src/beadloom/__init__.py:6` | none | yes | The source of truth the wheel is built from. |
| current-version | beadloom | `docs/getting-started.md:45` | none | yes | "The current release is **4.0.0**" — a current claim, and the docs audit flags it on the bump. |
| current-version | cli | `docs/services/cli.md:820`–`:821` | none | yes | Example sentences quoting the current-release claim; the scanner reads them as claims, and 4.0.0's bump edited them for that reason. |
| current-version | docs-audit | `docs/domains/doc-sync/features/docs-audit/SPEC.md:107`–`:108` | none | yes | The twin of `cli.md:820–821`, read by no check; 4.0.0's bump found it by grep. |
| current-version | — | `.beadloom/_graph/beadloom.yml:5` | — | yes | Node `beadloom`'s summary "(v4.0.0)", in no node's `source`. `lint --strict` fails on it at severity error, measured. |
| current-version | — | `.claude/CLAUDE.md:118` and `.beadloom/flow-manifest.json` | — | yes | "Current version" is rendered by `onboarding/scanner/claude_md.py:203` from `__version__`, so `beadloom setup-agentic-flow` rewrites it; no flow source is edited. `doctor` warns on the drift, measured. |
| current-version | — | `tests/test_integration_v1.py:25`, `:35`, `:41` | — | yes | Asserts `__version__` and `--version` output. |
| current-version | — | `.claude/development/ROADMAP.md:3` | — | yes | "Current version", updated only after the downloaded wheel is verified. |
| release-notes | — | `CHANGELOG.md` `[Unreleased]` | — | yes | Split into `[5.0.0]` and `[6.0.0]`; see Proposed Solution. |
| audit-config | — | `.beadloom/config.yml` `docs_audit.ignore` | — | yes | Three triples for the history rows below, each with its reason. |
| paired-docs | beadloom | `docs/architecture.md`, `docs/guides/ci-setup.md` | none | yes | Paired with `src/beadloom/__init__.py`, so `sync-check` fails on the bump, measured. Neither states a version literal; each is reviewed, then re-attested with `beadloom sync-update beadloom`. |
| history-checked | graph-loader | `docs/domains/graph/components/graph-loader/DOC.md:75` | none | no | "measured on the published 4.0.0 wheel" — dated history. The docs audit reports it stale on the bump and fails the Gate, measured. Not edited: silenced by a `docs_audit.ignore` triple. |
| history-checked | onboarding | `docs/domains/onboarding/README.md:178` | none | no | Same: "measured on the published 4.0.0 wheel". |
| history-checked | cli | `docs/services/cli.md:2316` | none | no | Same: "Measured on this repository on 2026-09-11, against `4.0.0`". |
| history | cli | `docs/services/cli.md:2322`, `:2332`–`:2337` | none | no | A dated sample of `version-surface` output; checked by no instrument. |
| history | agent-prime | `docs/domains/onboarding/features/agent-prime/SPEC.md:57`, `src/beadloom/onboarding/scanner/ref_ids.py:25` | none | no | "Measured on the published 4.0.0 wheel". |
| history | doc-generator | `docs/domains/onboarding/features/doc-generator/SPEC.md:106` | none | no | "Measured on the published 4.0.0 wheel". |
| history | version-surface | `docs/domains/doc-sync/features/version-surface/SPEC.md:135` | none | no | "On 2026-09-11, against `4.0.0`". |
| history | cli-commands | `src/beadloom/services/commands/version_surface.py:7` | none | no | "cutting 4.0.0 met its own defect". |
| history | — | `.beadloom/flow/claude/CLAUDE.md:12`, `:46` and their composed copies in `.claude/CLAUDE.md` | — | no | "the gap is closed as of 4.0.0" — when the branch-protection gap closed. |
| history | — | acceptance `.feature` comments, test docstrings, `.claude/development/` records, `CHANGELOG.md` `[4.0.0]` | — | no | Measurements on, or accounts of, the 4.0.0 release. Around fifty lines. |

**Nodes kept in scope:** `beadloom`, `cli`, `docs-audit`.

## Proposed Solution

### Approach

**Release A first, from its own commit.**

1. Branch `release/5.0.0` from `7efa4006`.
2. Raise every current-version row to `5.0.0`; recompose the flow; add the three
   `docs_audit.ignore` triples; review and re-attest the two paired documents.
3. Rename `[Unreleased]` to `[5.0.0] - <date>`. It already holds BDL-069 and Release A and nothing of
   Release B — measured: no `inherited_evaluated`, `inherited_total`, `unjudged`, `Release B` or
   `357 of 365` in `7efa4006`'s change log. Add a short release note naming the upgrade: population
   reporting, no verdict change.
4. Measure on that commit before tagging: `beadloom ci` rc 0, `ruff`, `mypy`, and the full coverage
   suite — **with no commit or push while the suite runs** (BDL-UX #298).
5. `gh release create v5.0.0 --target <that commit>`. Confirm the tag resolves to the release
   commit, that it descends from `7efa4006`, and that `692205d7` is **not** its ancestor.
6. Watch the publish run to completion.
7. **Verify the downloaded wheel**, in a fresh environment: `beadloom --version` is `5.0.0`; on a
   fixture project that is not this repository, `lint --strict` returns the same verdict as 4.0.0
   and prints the population statement.

**Release B second, from `main`.**

1. Branch from `main`.
2. Raise every current-version row from `4.0.0` directly to `6.0.0`; recompose; add the same three
   triples; re-attest.
3. Split the change log:
   - `[5.0.0]` is copied **byte-for-byte** from the published `release/5.0.0` file;
   - `[6.0.0]` above it carries Release B's text;
   - the "two halves are not two releases" open-decision paragraph goes, because the decision is taken;
   - the sentence claiming no published version carried the three keys is replaced by a
     `### Removed` entry naming `inherited_evaluated`, `inherited_total`, `unjudged` and the sixth
     porcelain field — measured: 8 keys and 6 fields at `7efa4006`, 5 and 5 on `main`.
4. Open a release pull request; wait for nine green checks; merge.
5. `gh release create v6.0.0 --target <merge commit>`; watch the publish run.
6. Verify the downloaded wheel: version `6.0.0`; on the same fixture, the verdict changes as the
   upgrade note states, and `summary.layer_populations[0]` has five keys.
7. Update `ROADMAP.md` "Current version" to 6.0.0, verified on the downloaded wheel.

**Where verification records go.** Into `ROADMAP.md` and the issue log only — never into a document
the docs audit scans. A line such as "measured on the published 5.0.0 wheel" in a scanned document
would become a false stale fact on the 6.0.0 bump, which is the defect this release has to work
around.

### Changes

| File / Module | Change |
|---|---|
| `src/beadloom/__init__.py` | `4.0.0` → `5.0.0` on `release/5.0.0`; → `6.0.0` on `main` |
| `docs/getting-started.md`, `docs/services/cli.md:820–821`, `docs-audit/SPEC.md:107–108` | the current-version claims, same targets |
| `.beadloom/_graph/beadloom.yml` | node summary `(v…)` |
| `.claude/CLAUDE.md`, `.beadloom/flow-manifest.json` | by `beadloom setup-agentic-flow`, not by hand |
| `tests/test_integration_v1.py` | the pinned version |
| `.beadloom/config.yml` | three `docs_audit.ignore` triples, each with its reason |
| `CHANGELOG.md` | `[5.0.0]` on the release branch; `[6.0.0]` above an identical `[5.0.0]` on `main` |
| `.claude/development/ROADMAP.md` | the current version and a release row per version, after verification |
| `.claude/development/BDL-UX-Issues.md` | the docs-audit finding below |

### API Changes

None made here. The releases publish the API changes BDL-069 and BDL-070 already made, and the change
log states them per version.

## Alternatives Considered

### Option A: publish one release from `main`

Rejected by the owner on 2026-09-13. It publishes the verdict change in the release that first makes
its number visible.

### Option B: revert Release B on `main`, release 5.0.0 from `main`, re-apply B

Rejected. It rewrites `main` twice, costs two extra full CI cycles, and moves more history than a
release branch built on the commit where Release A already landed.

### Option C: tag `7efa4006` directly

Impossible. The wheel would build as 4.0.0, which is already on PyPI, and `skip-existing` would skip
it silently while the publish run reported green.

### Option D: reword the three history lines until the docs audit stops reading them

Rejected. The audit attributes a version to another subject only beside `CPython`, `bd` or `git`.
Rewording a true measurement to fit that vocabulary would game the instrument. A
`docs_audit.ignore` triple is the sanctioned route for a confirmed false positive, and it states its
reason where a reader will see it.

### Option E: raise the history lines to the new version

Rejected. It would turn three true statements about 4.0.0 into false statements about 5.0.0.

## Risks

| Risk | Probability | Impact | Mitigation |
|---|---|---|---|
| A wheel keeps an old version and `skip-existing` skips it, while the run reports green | Low | High | Verify `beadloom --version` on the downloaded wheel, not on the run's conclusion. |
| The release tag lands on the wrong commit, or one that contains Release B | Low | High | `--target` names the commit; check its ancestry before and after tagging. |
| `release/5.0.0` gets no pull-request CI | Certain | Medium | Full local verification on that commit, then the publish workflow's test matrix and gates, which block the build. |
| The torn-read flake (#298) fails the publish workflow's suite | Low | Low | Re-run the workflow. Do not change code for it. |
| The docs audit fails the Gate on the three history lines | Certain without mitigation | High | `docs_audit.ignore` triples, plus a filed finding. |
| A 5.0.0 verification note written into a scanned document creates a new false positive on 6.0.0 | Medium | Medium | Records go to `ROADMAP.md` and the issue log only. |
| GitHub service trouble, as on 2026-09-13 | Medium | Low | Wait for recovery; start a stuck run again. |

## Open Questions

| # | Question | Decision |
|---|---|---|
| Q1 | Version numbers | **Decided 2026-09-13, owner:** 5.0.0, then 6.0.0, by the breaking-change bar 4.0.0 recorded. |
| Q2 | Publish both without a further stop | **Decided 2026-09-13, owner:** yes, once every check passes; stop and ask on any failure that is not a flake. |
| Q3 | The three history lines the docs audit flags | **Decided in this RFC:** `docs_audit.ignore` triples with reasons, not rewording and not raising; the audit's inability to tell dated history from a current claim is filed. |
