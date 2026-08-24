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

## Public API

| Symbol | Kind |
|--------|------|
| `STATUS_INCOMPLETE` | constant |
| `REASON_MISSING_SECTIONS` / `REASON_SECTION_NOT_IN_USE` | constant |
| `document_sections` | function |
| `carries_section` | function |
| `check_section_shape` | function |

## Dependencies

- Depends on: (none — pure markdown and SQL reads)
- Used by: `sync-check`, the CI gate, `beadloom sync-check`

## Parent

`doc-sync`

## Testing

`tests/test_missing_sections.py` — the outlier, the convention, the tie, the phrase match, the
honest limits, both wirings of `check_sync`, the gate and CLI surfaces, and an adopter project
whose own project layer defines the sections.
