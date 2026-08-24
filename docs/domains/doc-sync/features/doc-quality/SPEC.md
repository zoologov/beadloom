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

- **A number is necessary for a measurable clause and not sufficient.** `#142 and #146 close` is a
  checkable claim and `we improved 3 things` is not, and nothing here tells them apart. A goal
  whose criterion is a binary event with no quantity in it is reported although it is checkable.
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

## Public API

| Symbol | Kind |
|--------|------|
| `CHECK_NAMES` and the five check constants | constant |
| `APPROVED_STATUSES` | constant |
| `QualityFinding` / `QualityReport` | dataclass |
| `document_status` / `is_approved` | function |
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
