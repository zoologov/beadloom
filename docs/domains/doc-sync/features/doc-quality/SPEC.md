# Doc Quality

Five checkable properties of a planning document.

**Source:** `src/beadloom/doc_sync/doc_quality.py`

---

## Specification

### Purpose

BDL-061's CONTEXT states the reason exactly: *these planning documents read well because of
conventions written down nowhere, and a practice that is not a mechanism does not survive the
session.* Every role's writing standard states the conventions; until this feature nothing read a
document back to see whether they held.

### The five checks

| Check | Reports | Scope |
|-------|---------|-------|
| `measurable-goal` | a goal statement with no number in it | the `## Goal` / `## Goals` section |
| `decision-reason` | a decision row whose reason cell is empty | any table with a Reason / Rationale / Why column |
| `risk-mitigation` | a risk row with no mitigation, or one that names no action | any table with a Mitigation column |
| `pending-in-approved` | a question still answered `Pending` | the `## Open Questions` section of a document whose status is Approved or Accepted |
| `unfilled-placeholder` | a shipped template token nobody replaced | the whole document, outside fenced blocks and inline code |

All five are `warn`. `beadloom docs quality` exits 0 with findings unless `--strict` is given, and
the `docs-quality` gate step never blocks.

### What each check can and cannot decide

Stated here rather than discovered by a reader who trusted it.

- **`measurable-goal` is closer to a numeral detector than a measurability detector, and its
  findings are not yet trustworthy.** It looks for a digit not preceded by a word character, dot
  or hyphen. `#142 and #146 close` is a checkable claim and `we improved 3 things` is not, and
  nothing here tells them apart — but the stronger half of the original claim, that a number is
  *necessary* for a measurable clause, is false. An exit code, a named artifact that either
  exists or does not, and a binary capability are all measurable without a digit. Review
  `beadloom-mr2l.15` sampled 18 of this repository's 154 findings and could defend **one** as a
  true positive; among the false ones are `beadloom lint --strict fails (non-zero)` and
  `beadloom federate --fail-on <verdicts>` exits non-zero — the exit-code form BDL-UX #148 exists
  to insist on. Read the COUNT, which is a real statement about a corpus; do not act on an
  individual finding until the criterion is re-scoped. `beadloom-mr2l.65` carries the re-scope,
  and the owner's decision is to re-scope before paying the debt, because inserting numerals into
  goals that are already checkable would satisfy the regex and improve nothing.
- **A reason is checked for EXISTENCE.** The standard also asks that a reason explain *why*
  rather than restate the decision; no checker decides that, and pretending otherwise would be
  the vacuous green this epic exists to remove.
- **A mitigation is judged against a named set of empty ones** — `monitor`, `monitor it`, `watch
  closely`, `TBD`, `n/a`, a bare dash — matched as the WHOLE cell, so *monitor the queue depth and
  page above 80%* is a mitigation and *monitor it* is not. Whether a stated mitigation would work
  is not decidable.
- **A Draft may have Pending questions.** Only an agreed status (`Approved`, `Accepted`, however
  spelled) is held to the rule; reporting a draft's open questions trains an author to ignore the
  check.
- **A `Pending` outside `## Open Questions` is not a finding.** PLAN's bead table marks unstarted
  beads `Pending`; that is a status, not an undecided design.

### The placeholder vocabulary is derived

`unfilled-placeholder` is given its tokens by the caller, and the application layer derives them
from the **composed `/templates` command** rather than from a list in code. A hand-kept list is a
second source of truth that goes stale the first time a template gains a field, and the check
would then pass documents that were never filled in.

Two exclusions follow from what a placeholder is:

- A token inside an **inline code span** is a command's metavariable — `beadloom ctx <ref-id>` —
  and reporting it would flag the correct documentation of every command the project ships. The
  same exclusion applies when the vocabulary is derived and when a document is scanned.
- A token inside a **fenced block** is a quoted template, not an unfilled document. Without this
  the shipped `/templates` command reports every placeholder it exists to define.

An **enumerated stub** (`Goal 1`, `Criterion 1`, `Step 2`) counts only when it is the whole
bullet, cell or heading, bar a trailing parenthetical. Measured on this repository, substring
matching reported three real headings of BDL-030's RFC (`Step 1 (12.12.1): Detection`).

### The report says what it did not judge

`QualityReport.applicable` counts, per check, how much there was to read, and
`checks_that_read_nothing` names the checks that found nothing at all. A green count over
documents that state no risks is not a statement about risks — the same discipline `docs audit`
applies to a fact no document mentions (BDL-UX #173).

**And per document KIND, because the check count structurally cannot see a per-kind hole.**
`checks_that_read_nothing` is a global OR over the corpus: it goes silent the moment ONE document
carries ONE row, so it can detect a check that is blind everywhere and not one that is blind on an
entire shipped document kind. `QualityReport.by_kind` states what each kind contributed and
`kinds_that_read_nothing` names the kinds no **content** check enters. The judgement is made over
the four checks that read ITEMS — a goal, a decision row, a risk row, an open question — because
`unfilled-placeholder`'s population is documents OPENED and it therefore reads every kind by
construction; judging over all five would report every kind as read, which is a second vacuous
guard in place of the first.

**Measured on this repository, 2026-08-24**, over 243 planning documents:

| Check | Findings | Read |
|-------|----------|------|
| `measurable-goal` | 154 | 235 goal statements |
| `decision-reason` | 0 | 269 decision rows |
| `risk-mitigation` | 0 | 138 risk rows |
| `pending-in-approved` | 2 | 69 open-question rows |
| `unfilled-placeholder` | 0 | 243 documents |

Three of those checks report nothing here, and that is a CHECKED green rather than a vacuous one:
each was shown to fire on a real document of this repository under a single reverse-editable edit
made in memory — a blanked reason cell in `BDL-061/CONTEXT.md`, a mitigation replaced by
*Monitor it* in `BDL-040/RFC.md`, and `[Name]` put back into `BDL-061/PRD.md`'s title — 0
findings before, 1 after.
What that demonstration proves is that the check CAN fire on a real document; it does not prove
the population is complete, which is what the per-kind report below is for.

**The corpus includes the documents that publish these numbers.** These counts are measured over
this repository's own planning documents, so writing a decision row into a CONTEXT moves the
`decision-reason` denominator by one. Re-measure with `beadloom docs quality --json` rather than
quoting a table; what is durable here is the SHAPE of the report — findings over a stated
population, per check and per kind — not any particular row.

**56 of 243 documents (23%) are in a kind no content check enters**, and
`checks_that_read_nothing` was `()` throughout.

| Kind | Documents | goals | decision rows | risk rows | open questions |
|------|-----------|-------|---------------|-----------|----------------|
| ACTIVE | 55 | 1 | 10 | 0 | 0 |
| CONTEXT | 46 | 33 | 211 | 0 | 0 |
| RFC | 45 | 0 | 41 | 121 | 65 |
| PLAN | 42 | 0 | 0 | 0 | 0 |
| PRD | 41 | 201 | 7 | 17 | 4 |
| BRIEF | 11 | 0 | 0 | 0 | 0 |
| SUMMARY | 3 | 0 | 0 | 0 | 0 |

**This is a report, not yet a decision.** BRIEF, PLAN and SUMMARY read zero *by template
construction* — the shipped BRIEF template carries no Goal section, no Reason column, no Risks and
no Open Questions, and it is the kind every `bug`, `task` and `chore` uses. Whether to give those
templates the rows or to state that they are outside these four checks is a product decision with
a migration behind it, and it is open. What has changed is that the state is now printed by
`docs quality` and by the `docs-quality` gate step rather than inferred by a reviewer.

**A kind is judged on the documents that were READ.** `KindCoverage.unreadable` counts the
documents of that kind nothing could decode and they are excluded from `documents`, so a kind
whose every file is undecodable is reported as *unverified* and never as *a kind no check enters*.
Counting a file nobody read as a document carrying nothing would turn an encoding accident into
evidence about the project's templates.

**A document nobody could read is named.** `QualityReport.unreadable` carries `(path, reason)` for
every document the globs matched and the checks could not decode; the CLI prints one line per
document and the gate step prints `UNREADABLE: N` and reports `WARN`. Until BDL-061.66 that
channel was populated and printed nowhere, which left the document silently absent from
`N documents read` — the state the critical fix existed to end.

## Public API

| Symbol | Kind |
|--------|------|
| `CHECK_NAMES` and the five check constants | constant |
| `CONTENT_CHECKS` — the four that read items | constant |
| `APPROVED_STATUSES` | constant |
| `QualityFinding` / `QualityReport` / `KindCoverage` | dataclass |
| `document_status` / `is_approved` / `document_kind` | function |
| `check_document` / `check_documents` | function |

## Dependencies

- Depends on: (none — pure markdown analysis)
- Used by: `beadloom docs quality`, the `docs-quality` gate step

## Parent

`doc-sync`

## Testing

`tests/test_doc_quality.py` — every check proved on a document that violates it and one that does
not, the CLI and gate surfaces, and a class that fires all five at this repository's own planning
documents and fails if any of them reads nothing.

The per-kind rows are proved on a two-kind corpus where every check reads something and one kind
is still entered by none — so `checks_that_read_nothing == ()` and `kinds_that_read_nothing` is
not empty in the same assertion, which is the blind spot stated as a test rather than as prose.
The repository-level rows assert the INVARIANT (every document falls in exactly one kind, and the
per-kind counts sum to the global ones) and not the instance: pinning "BRIEF reads nothing here"
would redden the day the template gains a Goal, which is the outcome the report exists to
produce.
