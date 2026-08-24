# Document Kinds, Required Sections and the Writing Standard

<!-- beadloom:watches=cli,flow.yml -->

Beadloom checks two families of document, and they are checked by different mechanisms for
different reasons. This guide names both, says what each requires, and states what each check
can and cannot decide.

| Family | Written by | Checked by | Verdict |
|--------|-----------|------------|---------|
| **Architecture documents** — a README or SPEC per graph node | `beadloom docs generate`, then edited | `beadloom sync-check` (phase 5) | `incomplete`, `warn` |
| **Planning documents** — PRD, RFC, CONTEXT, PLAN, ACTIVE, BRIEF | the `/templates` document set | `beadloom docs quality` and the `docs-quality` gate step | `warn` |

Both ship as warnings. A new check that turns an adopter's green project red on upgrade is a
check that gets disabled, and a disabled check is worse than none.

---

## Architecture documents

### The kinds

Five templates ship as package data under `templates/docs/` and compose through the same
`core → architecture → stack → project` assembly the role files use:

| Doc kind | Written for | File |
|----------|-------------|------|
| `overview` | the project | `docs/architecture.md` |
| `domain` | a `domain` node | `docs/domains/<domain>/README.md` |
| `service` | a `service` node | `docs/services/<service>.md` |
| `feature` | a `feature` node | `docs/domains/<domain>/features/<feature>/SPEC.md` |
| `beadloom-readme` | the project | `.beadloom/README.md` |

`overview` and `beadloom-readme` describe the project rather than a node, so they have no sync
pair and their sections are not checked. The other three are bound to a node kind, which is what
makes a section check possible at all. A `component` node's `DOC.md` is authored rather than
generated — there is no `component` doc template — so a component document is checked for
freshness like any other pair and is outside the section check.

Until BDL-061 S4 every one of these was an f-string inside `doc_generator.py`. Two consequences
made the move worth doing: an adopter had **nothing to adapt** — the shape of their architecture
documentation was a Python literal in our package — and **nothing held the shape after
generation**, so a document could lose the sections it was born with and no check could see it.

### A project adds its own sections

```markdown
<!-- .beadloom/flow/docs/feature.md -->
## Runbook

How to operate this feature in production.
```

The fragment appends after the shipped template, exactly as `.beadloom/flow/roles/<role>.md`
appends to a role. **A section required is a section the composed template carries**: adding
`## Runbook` to the fragment makes `Runbook` a required section of every feature SPEC by the same
act. Nothing is declared twice, so nothing can disagree with itself.

A section that reaches the document through a placeholder — `## Public API`, rendered only for a
node that has public symbols — is conditional by construction and is never required of a node
that has none.

`docs` is the only artifact kind composed with `carries_suppressions=False`: a suppression notice
belongs in a role protocol an agent reads, not in the middle of somebody's architecture
documentation.

### The check is peer-relative

The finding this check exists to make is *this document departs from the shape its peers keep*.
So a required section counts as in use for a node kind only when a **majority** of that kind's
documents carry it. A minority — including none — reports the KIND once, with the ratio, because
the fix is then in the template rather than in every file.

Measured on this repository, 2026-08-24, with the requirements derived from the composed
templates (`Source`, `Dependencies` for every kind, plus `Features` for `domain` and `Parent` for
`feature`):

| Kind | In use | Not in use, reported once with its ratio |
|------|--------|------------------------------------------|
| domain | `Features` | `Source (0/7)`, `Dependencies (0/7)` |
| feature | — | `Source (5/39)`, `Dependencies (3/39)`, `Parent (4/39)` |
| service | — | `Source (0/4)`, `Dependencies (0/4)` |

One document is reported: `docs/domains/infrastructure/README.md` carries no heading naming
`Features`, and six of its seven peers do. The honest reading is that `infrastructure` has eight
components and no feature at all, so it announces its children under `## Components`. Renaming a
heading to satisfy a matcher would trade a true finding for a false green, so the row stands as
reported. Section matching is case-insensitive, whole-word and depth-independent, which is why
`## Features and components` counts and `## Featureset` does not.

## Planning documents

### The kinds and what each is for

| Kind | Used for | Ships with |
|------|----------|------------|
| `PRD` | epic, feature | Problem, Impact, Goals, Non-goals, User Stories, Acceptance Criteria |
| `RFC` | epic, feature | Overview, Motivation, Technical Context, Proposed Solution, Alternatives, Risks, Open Questions |
| `CONTEXT` | epic, feature | Goal, Key Constraints, Code Standards, Architectural Decisions, Related Files, Current Phase |
| `PLAN` | epic, feature | Epic Description, Dependency DAG, Beads, Bead Details |
| `BRIEF` | bug, task, chore | Problem, Solution, Beads, Acceptance Criteria, Non-behavioural declaration |
| `ACTIVE` | every type | Current Bead, Progress, Results, Notes |

The kind is the file's stem: `PRD.md` is a `PRD`. A project whose documents are named `prd.md`
gets `prd` as a kind of its own, which is honest — nothing was told the two are the same thing.

**Acceptance criteria in a PRD or a BRIEF reference scenarios by name.** The `.feature` file
holds the text; the document states the intent and points at it. See
[Executable Acceptance Scenarios](bdd-scenarios.md). A criterion no observer can see stays a
checkbox and is **labelled** as non-behavioural with a reason, so its absence from the suite is a
stated decision rather than a gap.

### The five checks

| Check | Reports | Where it reads |
|-------|---------|----------------|
| `measurable-goal` | a goal statement with no number in it | the `## Goal` / `## Goals` section |
| `decision-reason` | a decision row whose reason cell is empty | any table with a Reason / Rationale / Why column |
| `risk-mitigation` | a risk row with no mitigation, or one naming no action | any table with a Mitigation column |
| `pending-in-approved` | a question still answered `Pending` | `## Open Questions`, in a document whose status is `Approved` or `Accepted` |
| `unfilled-placeholder` | a shipped template token nobody replaced | the whole document, outside fenced and inline code |

```bash
beadloom docs quality                                  # the report, exit 0 with findings
beadloom docs quality --check pending-in-approved --json
beadloom docs quality --strict                         # exit 1 when anything is reported
```

Documents are found under `.claude/development/docs/features/*/*.md` by default; a project with
another layout declares its own globs under `doc_quality.paths` in `.beadloom/config.yml`. A run
that matches no document says so and names the globs it looked under, rather than printing a
clean bill of health over nothing.

### What the checks cannot decide

- **`measurable-goal` is closer to a numeral detector than a measurability detector, and it is
  not yet trustworthy.** It looks for a digit; its own stated premise — that a number is
  *necessary* for a measurable clause — is false. An exit code, a named artifact that either
  exists or does not, and a binary capability are all measurable without a digit. Review
  `beadloom-mr2l.15` sampled 18 of this repository's 154 findings and could defend **one** as a
  true positive, and among the false ones is `beadloom lint --strict fails (non-zero)` — the
  exit-code form BDL-UX #148 exists to insist on. **Read the count, do not act on the individual
  findings yet.** The re-scope is `beadloom-mr2l.65`, and the owner's decision is to re-scope the
  criterion before paying the debt, because inserting numerals into goals that are already
  checkable would satisfy the regex and improve nothing.
- **A reason is checked for EXISTENCE.** The standard also asks that a reason explain *why*
  rather than restate the decision. No checker decides that.
- **A mitigation is judged against a named set of empty ones** — `monitor`, `monitor it`, `watch
  closely`, `TBD`, `n/a`, a bare dash — matched as the whole cell. *Monitor the queue depth and
  page above 80%* is a mitigation; *monitor it* is not. Whether a stated mitigation would work is
  not decidable.
- **A Draft may have Pending questions.** Only an agreed status is held to the rule. Reporting a
  draft's open questions trains an author to ignore the check.
- **A `Pending` outside `## Open Questions` is not a finding.** A PLAN's bead table marks
  unstarted beads `Pending`; that is a status, not an undecided design.

### The report says what it did not judge

Two denominators, because one of them structurally cannot see the other's blind spot.

`QualityReport.applicable` counts, per check, how much there was to read, and
`checks_that_read_nothing` names any check that found nothing at all anywhere. That is a global
OR over the corpus: it goes silent the moment one document carries one row, so it can detect a
check that is blind everywhere and not one that is blind on an entire document kind.

`QualityReport.by_kind` therefore states what each kind contributed, and `kinds_that_read_nothing`
names the kinds no **content** check enters. The judgement is made over the four checks that read
items — a goal, a decision row, a risk row, an open question — because `unfilled-placeholder`
counts documents *opened* and would report every kind as read.

Measured on this repository, 2026-08-24, over 243 planning documents:

| Check | Findings | Read |
|-------|----------|------|
| `measurable-goal` | 154 | 235 goal statements |
| `decision-reason` | 0 | 269 decision rows |
| `risk-mitigation` | 0 | 138 risk rows |
| `pending-in-approved` | 2 | 69 open-question rows |
| `unfilled-placeholder` | 0 | 243 documents |

| Kind | Documents | goals | decision rows | risk rows | open questions |
|------|-----------|-------|---------------|-----------|----------------|
| ACTIVE | 55 | 1 | 10 | 0 | 0 |
| CONTEXT | 46 | 33 | 211 | 0 | 0 |
| RFC | 45 | 0 | 41 | 121 | 65 |
| PLAN | 42 | 0 | 0 | 0 | 0 |
| PRD | 41 | 201 | 7 | 17 | 4 |
| BRIEF | 11 | 0 | 0 | 0 | 0 |
| SUMMARY | 3 | 0 | 0 | 0 | 0 |

**The corpus includes the documents that publish these numbers.** These counts are measured over
this repository's own planning documents, so writing a decision row into a CONTEXT moves the
`decision-reason` denominator by one. Re-measure with `beadloom docs quality --json` rather than
quoting a table; what is durable here is the SHAPE of the report — findings over a stated
population, per check and per kind — not any particular row.

**56 of 243 documents (23%) are in a kind no content check enters** — BRIEF, PLAN and SUMMARY —
while `checks_that_read_nothing` read `()` throughout. The three zero rows above are a genuinely
checked green: each of `decision-reason`, `risk-mitigation` and `unfilled-placeholder` was shown
to fire on a real document of this repository under a single reverse-editable edit, so they are
green because there is nothing to report and not because nothing was read.

**Why the three kinds read zero is template construction, and the decision is open.** The shipped
BRIEF template carries no Goal section, no Reason column, no Risks and no Open Questions — and
BRIEF is the kind every `bug`, `task` and `chore` uses. PLAN's criteria live in a "Done when"
list rather than in a Goal section. Whether to give those templates the rows, or to state that
they are outside these four checks, is a product decision with a migration behind it and it has
not been taken. What has changed is that the state is printed by `docs quality` and by the gate
step rather than inferred by a reviewer.

### A document nobody could read is named

A planning document is a UTF-8 contract: Beadloom chooses the codec and decodes explicitly. A
document the globs matched and the checks could not decode is **counted**, carries a named
`unreadable` finding with its reason, and is excluded from the denominators of the kind it
belongs to. Counting a file nobody read as a file carrying nothing would turn an encoding
accident into evidence about a project's templates.

`beadloom docs quality` prints one line per unreadable document; the `docs-quality` gate step
prints `UNREADABLE: N` and reports `WARN`. Until BDL-061.66 that channel was populated and
surfaced nowhere, and before that one undecodable document took the whole `beadloom ci` gate down
with a traceback.

## What the gate does with all of this

`beadloom ci` runs `docs-quality` as its fifth step. It never blocks: `passed` is unconditionally
true and every finding is a warning. It reports **WARN** rather than PASS when any of three
things is true — a check read nothing anywhere, a document kind no content check enters, or a
document nobody could decode. On this repository, measured 2026-08-24:

```
docs-quality WARN | 243 document(s) read; measurable-goal 154, pending-in-approved 2;
                    NO CHECK READS: BRIEF, PLAN, SUMMARY
```

`sync-check` reports the architecture-document side as `incomplete` rows, which are printed by
name and never block. One limit is worth stating: `incomplete` has **no counter** in the
`sync-check --json` summary, so `ok + stale + missing + unverified + unchecked` does not sum to
`total` when any row is incomplete. The rows are in `pairs` and the rich output shows them; a
machine consumer reading only the summary does not see them.

## Related

- [Doc Templates SPEC](../domains/onboarding/features/doc-templates/SPEC.md) — the composition,
  the placeholder syntax and how required sections are derived.
- [Doc Shape SPEC](../domains/doc-sync/features/doc-shape/SPEC.md) — the majority rule and the
  `incomplete` status.
- [Doc Quality SPEC](../domains/doc-sync/features/doc-quality/SPEC.md) — the five checks, the
  placeholder vocabulary and the per-kind report.
- [Executable Acceptance Scenarios](bdd-scenarios.md) — the criteria these documents reference.
- [Project Overlays](project-overlays.md) — `.beadloom/flow/`, suppressions and the mutation
  scope.
