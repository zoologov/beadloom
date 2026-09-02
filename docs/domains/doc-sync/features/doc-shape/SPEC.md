# Doc Shape

Whether a document still carries the sections its kind requires.

**Source:** `src/beadloom/doc_sync/doc_shape.py`

---

## Specification

### Purpose

`sync-check`'s five staleness reasons all compare **content**: a hash moved, a symbol set moved,
a file appeared, a module went unmentioned, a declared doc vanished. None of them can see that a
README was edited down to a title, because its bytes changing *is* the thing they measure.

`missing_sections` compares **structure**. It is the only reason in `sync-check` that says
something about a document's shape rather than its currency.

### The check is peer-relative, and that is the design

The finding this check exists to make is *this document departs from the shape its peers keep*.
So a required section counts as **in use** for a node kind only when a **majority** of that
kind's documents carry it.

| Population | Verdict | Row |
|------------|---------|-----|
| A majority of the kind's documents carry the section | it is the convention | each document missing it is reported — `missing_sections` |
| A minority carry it (including none) | it is not the convention | the KIND is reported once, with the ratio — `section_not_in_use` |
| Exactly half carry it | not yet a convention | reported as `section_not_in_use` |

Measured on this repository: `## Parent` is carried by **one** feature SPEC of 36. A
presence-of-one rule reported the 35 documents that follow the project's actual convention, which
inverts the finding. The majority rule reports the convention once, with its denominator
(`Parent (1/36)`), because the fix is in the template rather than in 35 files.

Re-measured 2026-08-24, after S4 added six nodes: `Source (0/7)` and `Dependencies (0/7)` for
`domain`, `Source (5/39)` / `Dependencies (3/39)` / `Parent (4/39)` for `feature`, and
`Source (0/4)` / `Dependencies (0/4)` for `service`. Exactly one document is reported —
`docs/domains/infrastructure/README.md`, missing `Features`, which six of its seven peers carry.
**That row is left standing rather than satisfied.** `infrastructure` has eight components and no
feature, so it announces its children under `## Components`; renaming the heading to match the
matcher would trade a true finding for a false green, which is the trade this check exists to
prevent. It is a live instance of the limit stated below: the check decides whether a fact is
stated under a heading that names it, never whether the name is the right one.

### A section is matched by its name, as a whole-word phrase

`## Features and components` is not a document that lost its Features section. String equality
reported two of this repository's domain READMEs that carry the section under a wider title.
Matching is case-insensitive and whole-word, so `## Featureset` is still a different heading, and
heading depth is ignored: a section promoted to `#` or demoted to `####` still states the fact it
exists for.

**The limit this accepts**, stated rather than left to be discovered: a heading that merely
contains the word satisfies the requirement. The check answers *is this stated somewhere under a
heading that names it*, not *is this stated well* — the second is
[`doc-quality`](../doc-quality/SPEC.md)'s subject.

### Status and severity

`incomplete` is a **new status**, deliberately absent from `BLOCKING_STATUSES`: the check ships
as `warn`, so no adopter's green project turns red on upgrade. It is never written to
`sync_state` — the column would then mean two different things, and a check that writes to what
it inspects cannot be trusted about it (BDL-UX #147).

### The requirements are injected, not read

`doc-sync` and `onboarding` are **peer domains** and this project's graph declares no
domain-to-domain edge, so the required sections cannot be read from the templates here. The
application layer resolves them
([`doc-shape-requirements`](../../../application/components/doc-shape-requirements/DOC.md)) and
`check_sync(..., section_requirements=...)` receives them.

`section_requirements=None` means **structure was not checked**. Four surfaces pass them in — the
CI gate, `beadloom sync-check`, the MCP `sync_check` tool and the TUI dashboard. Three
deliberately do not: `sync-update` (twice), because re-baselining a pair cannot fix a missing
section, and `site_published`, because publishing a site does not judge one.

### The same policy over the flow's planning documents

BDL-068 S1.4 made the peer policy a function of its own — `peer_section_shape` — and ran it over
a second corpus: the BRIEF, RFC, PRD, CONTEXT, PLAN and ACTIVE documents, against the sections
their own composed skeletons carry. One implementation of "does a majority carry this", so the
two corpora cannot disagree about what the rule is.

`check_planning_sections` reports two things, and they answer different questions:

| Check | Peer-relative | Why |
|-------|---------------|-----|
| `missing-section` | yes | a section the archive never adopted is reported once against the KIND, not once per document |
| `empty-section` | no | a heading the author wrote with nothing under it is a defect whatever the peers do, and it is the one a presence check is satisfied by |

Measured on this repository's 259 planning documents when this shipped: requiring every template
heading of every document gives **767** findings, because the archive predates `language: en` and
carries none of today's headings. Under the majority policy the same requirement gives **17**
statements about a kind — including `BRIEF Axes (0/12)` and `RFC Axes (0/48)` — and **102** about
a document. Every one of the 102 is a real departure from the shape its peers keep; they are old
RFCs with no `## Overview` and old PRDs with no `## Impact`. All nine planning checks are `warn`,
so the Gate stays green on them.

### Emptiness is judged over the whole section, not over the heading's own lines

`read_sections` records each heading's DEPTH and propagates content upward: a section whose
content lives in its subsections is not empty. Judging the heading's own lines alone reported
**155** documents on this repository whose `## Code Standards` is a heading over four `###`,
which is why the rule is stated this way rather than the simpler way.

The reader also skips fenced blocks. A `## ` inside a fence is a quoted template, and without
that a BRIEF quoting its own skeleton would be credited with every section the skeleton names.

## Public API

| Symbol | Kind |
|--------|------|
| `STATUS_INCOMPLETE` | constant |
| `REASON_MISSING_SECTIONS` / `REASON_SECTION_NOT_IN_USE` | constant |
| `MISSING_SECTION` / `EMPTY_SECTION` | constant |
| `Section` / `SectionConvention` / `LostSections` / `PlanningShapeReport` | dataclass |
| `read_sections` | function |
| `document_sections` | function |
| `carries_section` | function |
| `peer_section_shape` | function |
| `check_section_shape` | function |
| `check_planning_sections` | function |

## Dependencies

- Depends on: `infrastructure.doc_roots.resolve_docs_dir` — the documents are read from the
  documentation directory the project declared, rather than from a hardcoded `docs/`
  (`beadloom-mr2l.75`); and `doc_sync.doc_quality` for `QualityFinding` and `document_kind`, the
  shape and the naming every planning-document finding already uses. Otherwise pure markdown and
  SQL reads.
- Used by: `sync-check`, the CI gate, `beadloom sync-check`, and `application.planning_report`
  (the one composition behind the `docs-quality` gate step and `beadloom docs quality`)

## Parent

`doc-sync`

## Testing

`tests/test_missing_sections.py` — the outlier, the convention, the tie, the phrase match, the
honest limits, both wirings of `check_sync`, the gate and CLI surfaces, and an adopter project
whose own project layer defines the sections.
`tests/test_the_axes_section_is_required_by_the_template.py` and
`tests/acceptance/features/planning_document_shape.feature` — the same three population cases
over planning documents, the empty section, the nested content that is not one, the fence that
is not a section, and the document kind no template describes.
