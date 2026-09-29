# PRD: BDL-075 — Release 7.0.0 with the documentation current

> **Status:** Approved
> **Created:** 2026-09-29

---

## Problem

PyPI's latest is 6.0.0. `main` at `11b5ad0d` carries BDL-072, BDL-073 and BDL-074, and none of
them is published. `CHANGELOG.md` has no `[Unreleased]` section and no line naming any of the
three. So an adopter who runs `pip install beadloom` today gets none of the following:

- tests bound to graph nodes, and the four suite rules;
- per-change and weekly mutation;
- the stack-neutral test role;
- the Rich-markup fixes. Before them, `why` printed `----` for every edge.

**The documentation an adopter reads first is wrong on the published version as well.** Read-only
audits on 2026-09-29 measured:

- **README.ru.md (the source):** 16 stale lines, which are 12 distinct defects.
  - It says macOS is checked on every CI run. CI has never run on macOS.
  - `uv sync --dev` installs no pytest, so the contributor instructions fail.
  - The Gate sample lacks three legs.
  - `guard` has six outcomes, not four. The Gate exits 1, not 2. `impact` takes a path or a
    symbol. `search` does not index symbols.
  - The `[tui]` and `[languages]` extras are never named.
  - `README.md` repeats every one of these, and differs from the Russian in content in three places.
- **ROADMAP.md:** 22 false or stale statements.
  - "What is being worked on now" holds three shipped items and nothing that is in progress.
  - The only open P0 bug, `beadloom-jwfc`, is not listed.
  - Nine open P1 bugs and the next release are not listed either.
- **BDL-UX-Issues.md:** 153 entries judged.
  - 55 open entries describe defects that are fixed; 11 of them say so themselves and were never
    moved.
  - Entries sit open and closed at once.
  - The numbering is out of order.
  - The chronology stops at 2026-08-26.
  - `issue-number check` cannot see the duplicates.

## Impact

Adopters, and the owner's planning. An adopter reads a README that is wrong about how to install
and what commands do, and installs a version without the last three work items. The owner plans
from a ROADMAP whose "now" section is stale, and from an issue log where a third of the open
entries are already fixed.

## Goals

- [ ] **7.0.0** is published from `main` and carries BDL-072, BDL-073 and BDL-074. The version is
      major under the bar 4.0.0 recorded and BDL-071 applied ("a JSON value-set change makes it
      major"). The explore supplement found two breaking changes:
  - the debt report's untested count now comes from the test binding, so
    `status --fail-if score>N` can change verdict on an unedited graph;
  - `ctx` / MCP `extra.tests` keeps its four keys, but their values change: `framework` can be a
    `+`-joined name, and the counts are the union over descendants.

  A Python-import removal (`beadloom.context_oracle.test_mapper`) is breaking for importers only.
- [ ] `CHANGELOG.md` gains a `[7.0.0]` section. It names both breaking changes and the removed
      module, and lists what was added and fixed. No history line is rewritten.
- [ ] Every place that states the **current** version moves to 7.0.0. The explore supplement found
      nine files; `tests/self_check/config/test_version_surface.py` pins them.
- [ ] **README.ru.md first, then README.md.**
  - The 12 defects are fixed.
  - The capabilities 7.0.0 publishes are described: tests bound to graph nodes, the suite rules,
    per-change and weekly mutation, and `docs/guides/testing.md`.
  - The pair is equal in content, not only in shape.
- [ ] **ROADMAP.md.**
  - The 22 statements are corrected.
  - Shipped items leave "being worked on".
  - Open work is ranked in the order the owner accepted: `jwfc` → the adopter-bug sweep → `tsqz` →
    this release → the three lessons of BDL-074 → `r9t5` → the class gaps → BDL-066 → `uxqc` →
    the mutation follow-ups → `cxal`.
  - Federation is recorded as deferred until a need for it appears, with higher priorities first.
- [ ] **BDL-UX-Issues.md.**
  - The fixed open entries move to Closed, each with a line of evidence.
  - Partly fixed entries say what remains.
  - Open/closed duplicates are removed and the number order restored.
  - The broken `<details>` and the second H1 are fixed.
  - The chronology is marked historical up to 2026-08-26.
  - The `issue-number check` blind spot is filed as a bead.
- [ ] 7.0.0 is verified on the wheel **downloaded from PyPI**, not on the local build.

## Non-goals

- **No product code change** beyond the version literal. Defects found on the way are filed.
- **Not fixing** the open bugs the ROADMAP now ranks (`jwfc`, the adopter sweep, `tsqz`, …). They
  are ranked here and done later.
- **Not scheduling federation.** It is recorded as deferred.
- **Not rewriting history.** A line that states what 6.0.0 or an earlier version was or did keeps
  saying it.

## User Stories

### US-1: An adopter upgrades to what `main` already holds
**As** a project on 6.0.0, **I want** 7.0.0 on PyPI with an upgrade note that names both breaking
changes, **so that** I know my debt score or my `extra.tests` readers may change before they do.

**Acceptance criteria** — non-behavioural. The behaviour 7.0.0 ships was specified and tested by
BDL-072–074, and a release is an artifact verified on the published package.
- [ ] The wheel downloaded from PyPI reports `7.0.0`.
- [ ] On a project that is not this repository, that wheel shows the documented behaviour: `ctx`
      shows tests bound through the mirror, and `beadloom mutation --changed-since` states its
      population.

### US-2: A reader of the README is told the truth about the installed version
**As** someone reading `README.ru.md` or `README.md`, **I want** every command, number and install
step it states to hold on 7.0.0, **so that** I can follow it without meeting an error it did not
mention.

**Acceptance criteria:**
- [ ] Each of the 12 audited defects is fixed, measured against 7.0.0.
- [ ] The two files agree in content; `readme-pair` passes.

### US-3: The owner plans from current records
**As** the owner, **I want** ROADMAP's "now" section and the issue log's Open section to hold only
what is open, **so that** the next work item is chosen from the truth.

**Acceptance criteria:**
- [ ] No item under "being worked on" is shipped, and every open P0/P1 bug is named.
- [ ] No Open entry in the issue log describes a defect the audit measured as fixed, and no number
      appears as both open and closed.

## Acceptance Criteria (overall)

- [ ] One GitHub release, `v7.0.0`, targeting a commit on `main`, with a green publish run.
- [ ] The wheel downloaded from PyPI reports 7.0.0. This is checked because the upload runs with
      `skip-existing: true`, so a green run is not evidence on its own.
- [ ] The Gate is green on the release commit and the suite is green on it, measured before
      publishing.
- [ ] `ROADMAP.md` states 7.0.0 as the current version, verified on the downloaded wheel.
- [ ] The nine checks are green on the pull request that carries the release.
