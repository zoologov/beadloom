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
| `measurable-goal` | a goal that states an unbounded improvement and names no witness | the `## Goal` / `## Goals` section |
| `decision-reason` | a decision row whose reason cell is empty | any table with a Reason / Rationale / Why column |
| `risk-mitigation` | a risk row with no mitigation, or one that names no action | any table with a Mitigation column |
| `pending-in-approved` | a question still answered `Pending` | the `## Open Questions` section of a document whose status is Approved or Accepted |
| `unfilled-placeholder` | a shipped template token nobody replaced | the whole document, outside fenced blocks and inline code |

All five are `warn`. `beadloom docs quality` exits 0 with findings unless `--strict` is given, and
the `docs-quality` gate step never blocks.

### What each check can and cannot decide

Stated here rather than discovered by a reader who trusted it.

- **`measurable-goal` decides one named form, not measurability in general.** A goal is reported
  when BOTH legs hold: its predicate is an unbounded improvement — `improve`, `enhance`,
  `establish`, `clean up`, or `make`/`keep` something *better / faster / simpler / useful /
  intuitive* — and it names no witness. A witness is a quantity (`440 -> 371 lines`), a named
  artifact (an inline code span, a `--flag`, a file name, a `snake_case` identifier), or an
  observable outcome (`exits`, `fails`, `passes`, `detects`, `renders`, `produces`, `green`). The
  three sibling checks all work this way — name the empty form, do not guess at the good one —
  and `risk-mitigation`'s list of non-mitigations is the same construction one check over.
- **Why it changed (`beadloom-mr2l.70`).** As shipped it looked for a digit and called its
  absence "no measurable clause". On this repository that reported **154 of 235** goal statements;
  review `beadloom-mr2l.15` sampled 18 of them and could defend **one**. Among the false ones were
  `beadloom lint --strict` **fails** (non-zero) and `beadloom federate --fail-on <verdicts>` exits
  non-zero — the exit-code form BDL-UX #148 exists to insist on — and `Graph YAML writes are
  atomic (temp + os.replace)`, a property any reader can check for. Paying that debt as written
  would have inserted numerals into 154 sentences that were already checkable, which teaches an
  author to write for the checker; that is the failure BDL-UX #169 was fixed by explicitly NOT
  rewording the document. The re-scoped criterion reports **4 of 232** on the same corpus, and the
  four are the standard's own example ("Make Beadloom enjoyable and intuitive").
- **The limit, measured rather than asserted: precision was bought with recall.** Of the 150
  statements the re-scope newly accepts, **27 name no witness either** — they are accepted because
  their predicate is not an unbounded improvement, and about those this check now decides nothing
  ("Turn prose into mechanisms", "Clear separation between policy and fact sections"). A goal this
  check accepts is not thereby proved measurable. The trade was made deliberately: a check firing
  on 66% of a corpus does not get satisfied, it gets `--check`-excluded, and an excluded check
  decides nothing about 100% of it.
- **The population did not move to make the count smaller.** Every goal statement is still read
  and still counted; the denominator fell 235 -> 232 for one unrelated reason, that three of the
  235 were a markdown horizontal rule closing a Goal section (review `beadloom-mr2l.15` m1). There
  is no tolerance, no excluded document and no suppression in this check.
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

### These five are not the whole of `docs quality`

Since BDL-068 S1.4 the `docs-quality` surfaces report **nine** checks, assembled by
`application/planning_report.py` so the Gate step and the CLI read one run. The four this
module does not own are the structural pair (`missing-section`, `empty-section`, in
[doc-shape](../doc-shape/SPEC.md)) and the axes pair (`axes-without-a-seed`,
`axis-without-a-scope-decision`, in [axes-section](../axes-section/SPEC.md)). `CHECK_NAMES`
here still means the five writing-standard checks; the composition's own `CHECK_NAMES` means
all nine.

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
| `measurable-goal` | 4 | 232 goal statements |
| `decision-reason` | 0 | 269 decision rows |
| `risk-mitigation` | 0 | 138 risk rows |
| `pending-in-approved` | 2 | 69 open-question rows |
| `unfilled-placeholder` | 0 | 243 documents |

Three of those checks report nothing here, and that is a CHECKED green rather than a vacuous one:
each was shown to fire on a real document of this repository under a single reverse-editable edit
made in memory — a blanked reason cell in `BDL-061/CONTEXT.md`, a mitigation replaced by
*Monitor it* in `BDL-040/RFC.md`, and `[Name]` put back into `BDL-061/PRD.md`'s title — 0
findings before, 1 after. `measurable-goal`'s four are live findings on
`BDL-002`, `BDL-004`, `BDL-005` and `BDL-006`'s CONTEXT; `beadloom-mr2l.65` pays them.
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
