# PRD: BDL-071 — Release 5.0.0, then 6.0.0: the population report ships before the verdict change

> **Status:** Approved
> **Created:** 2026-09-13

---

## Problem

BDL-070's CONTEXT holds that no adopter's Gate may change verdict on upgrade, which is why the
epic was built in two halves and merged in order: **Release A** (PR #72, `main` at `7efa4006`)
makes `architecture-layers` report the population it judged and changes no verdict; **Release B**
(PR #73, `main` at `692205d7`) makes it decide on that population and changes verdicts on a graph
nobody edited.

**Merging in order does not publish in order.** PyPI's latest is 4.0.0, and `CHANGELOG.md`
`[Unreleased]` on `main` holds BDL-069, Release A and Release B together. A single version bump
from `main` would publish the verdict change in the same release that first makes its number
visible — the exact outcome the two halves were built to prevent.

**The split also changes what the release notes must say.** Measured with each commit's own code:

| | `lint --format json` `summary.layer_populations[0]` | porcelain `# layer_population:` |
|---|---|---|
| Release A (`7efa4006`) | 8 keys, including `inherited_evaluated`, `inherited_total`, `unjudged` | 6 fields |
| Release B (`main`) | 5 keys | 5 fields, and the numbers mean something else |

The `[Unreleased]` text on `main` says no published version ever carried those three keys. That is
true only if A and B ship together. Once A ships as its own version, it is false.

## Impact

Adopters, and the credibility of the change log. Published together, an adopter upgrading from
4.0.0 meets a reddened Gate and a population statement for the first time in the same step, with no
release in which to see the number before it bites. And a change log that denies a published
contract existed would be a stated fact that is not true — the class BDL-068, BDL-069 and BDL-070
exist to remove.

## Goals

- [ ] **5.0.0** is published from `7efa4006` and carries BDL-069 and BDL-070 Release A only — no
      Release B code, no Release B text.
- [ ] **6.0.0** is published from `main` and carries Release B, with its change log naming as
      removed the three JSON keys and the porcelain field that 5.0.0 published, and naming the
      verdict change.
- [ ] Every place that states the **current** version is raised on each release, and no place that
      states version history is rewritten.
- [ ] Each version is verified on the wheel **downloaded from PyPI**, not on the local build: the
      reported version matches the tag, and the release's documented behaviour holds.
- [ ] The Gate is green on each release commit before it is published.

## Non-goals

- **No code change.** Neither release fixes anything. Defects found on the way are filed.
- **Not fixing the open findings** from BDL-070 (#290, #291, #294, #295, #297, #298, #299, #300).
- **Not reopening the version numbers.** 5.0.0 and 6.0.0 were decided by the owner on 2026-09-13,
  by the breaking-change bar 4.0.0 recorded: 5.0.0 for the `issue-number check --json` `declared`
  widening from `bool` to `bool | null`; 6.0.0 for the verdict change and the narrowed contract.

## User Stories

### US-1: An adopter upgrades without a Gate turning red
**As** a project on 4.0.0, **I want** a release that shows me how far `architecture-layers` reaches
before a release that acts on it, **so that** I can tag or exempt what the rule will judge before
it judges it.

**Acceptance criteria** — non-behavioural: a release is an artifact, and what an observer sees is
the published package, verified by the checks below rather than by a scenario in the suite.
- [ ] 5.0.0 on PyPI reports `5.0.0`, prints the population statement, and returns the same verdicts
      4.0.0 returns on a project that is not this repository.
- [ ] 6.0.0 on PyPI reports `6.0.0` and changes verdicts as its upgrade note states.

### US-2: A reader of the change log is told what each version shipped
**As** someone reading `CHANGELOG.md`, **I want** each version's section to describe that version
alone, **so that** a contract 5.0.0 published is not described as never having existed.

**Acceptance criteria** — non-behavioural, for the same reason:
- [ ] `[5.0.0]` holds BDL-069 and Release A and nothing from Release B.
- [ ] `[6.0.0]` names the three removed JSON keys and the removed porcelain field under `### Removed`.

## Acceptance Criteria (overall)

**Non-behavioural criteria** — a release publishes an artifact and changes no behaviour of its own;
the behaviour it ships was specified and tested by BDL-069 and BDL-070.

- [ ] Two GitHub releases, `v5.0.0` targeting a commit on `release/5.0.0` descended from `7efa4006`,
      and `v6.0.0` targeting a commit on `main`, each with a green publish run.
- [ ] Each published wheel downloaded from PyPI reports its own version — because the publish step
      uploads with `skip-existing: true`, a wheel that kept an old version would be skipped silently
      and the run would still be green.
- [ ] The Gate green on each release commit, measured before publishing.
- [ ] `ROADMAP.md` states 6.0.0 as the current version, verified on the downloaded wheel.
