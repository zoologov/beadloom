# Axes Section

The `## Axes` section of a work item's document: the seed it names, the scope decision it
records, and the bead `refs:` generated from it.

**Source:** `src/beadloom/doc_sync/axes_section.py`

---

## Specification

### Purpose

BDL-068 CONTEXT decides Q1 in three parts, and this module holds the middle one: the axes a
change ranges over are **derived** by `beadloom impact`, the document **records** the
derivation's output and the person's scope decision, and the bead's `refs:` is **generated**
from the document. A disagreement between the three is a finding. Two authored homes for one
fact are two things that can disagree, which is the class BDL-068 exists to remove.

### Why the seed is the one thing a section may not leave out

BDL-068 S1.3 measured, at `af26750d`, that the same derivations report **2** writers and **4**
branches seeded with the commit point, and **0** writers and **3** branches seeded with the
function the first dev bead was changing — one tree, one day, one derivation. The axes are a
property of the seed. A section stating axes without naming the seed is a clean, confident
number with no way to tell which of those two runs produced it, so `axes-without-a-seed`
reports it.

An absent seed is **not** an empty axis. `beadloom impact` reports a target it finds no seed
for as `none`, with every axis below it unresolved rather than empty, and the section keeps
that distinction: the word `none` **is** naming the seed and satisfies the check, while a
missing `Seed` field does not.

### The grammar

```markdown
## Axes

> **Derived by:** `beadloom impact src/pkg/writer.py` over `src/pkg`
> **Seed:** `write_yaml` (effect `serialises-yaml`), under rule `reaches-an-effect-sink`
> **Unresolved:** 2 unnameable-callee

| Axis | Node | Sites | In scope | Why |
|------|------|-------|----------|-----|
| co-writers | graph-files | 6 — `src/…/bootstrap.py:216` | yes | the invariant is written here |
| callers | flow-composer | 2 — `src/…/setup.py:88` | no | reads the result only |
```

The first three columns are the derivation's output. The last two are the person's scope
decision, and the split is what lets a check tell "a run nobody has ruled on" from "a decision
somebody took". A blockquote field wrapped over several lines is one value, because these
documents wrap at 95 columns like every other.

### The two checks

| Check | Fires when | Not its job |
|-------|------------|-------------|
| `axes-without-a-seed` | the section states axis rows and carries no `Seed` field | a section with no rows — that is `empty-section`'s finding, and one fault under two names is one fault too many |
| `axis-without-a-scope-decision` | a row's `In scope` cell decides nothing | the empty `Why` cell — `decision-reason` already reports a table row whose reason cell is empty |

`yes / no` — what the shipped skeleton offers — decides **nothing**. The cell is matched whole
rather than by substring, so the template's own prompt cannot be read as a decision because the
word `yes` occurs in it.

### One grammar, read in both directions

`beadloom.application.impact.section.render_axes_section` writes a section from an
`ImpactAnswer` using the names declared here; `read_axes_section` reads one back. The renderer
lives in the application layer because it needs the answer's types, and the grammar lives here
because `doc_sync` is the domain whose subject is documents and may not import upward. A
round-trip case holds the two together: a rendered section reads back as the answer it was
rendered from, which is what stops the writer and the reader becoming two shapes with one name.

Every rendered row is born undecided, so the checks report a freshly pasted section until a
person rules on it. That is the intended state, not a defect: the derivation's half is written
by a command and the other half is not a command's to write.

### `refs:` is generated, not written beside the table

`refs_line` takes the rows kept in scope, in the table's own order, deduplicated — one node
named by two axes is one ref. `beadloom axes <document> --refs` prints it. The order a reader
sees in the document is the order the bead carries, so the two can be compared by eye as well
as by a check.

## Public API

| Symbol | Kind |
|--------|------|
| `AXES_HEADING` / `SEED_FIELD` / `DERIVED_BY_FIELD` / `UNRESOLVED_FIELD` / `NO_SEED` / `COLUMNS` | constant |
| `AXES_WITHOUT_A_SEED` / `AXIS_WITHOUT_A_SCOPE_DECISION` / `CHECK_NAMES` | constant |
| `Axis` / `AxesSection` | dataclass |
| `read_axes_section` | function |
| `refs_line` | function |
| `check_axes_section` | function |

## Dependencies

- Depends on: `doc_sync.doc_shape.read_sections` — the one fence-aware, depth-aware section
  reader, so a `## Axes` quoted inside a fenced block is not read as this document's own; and
  `doc_sync.doc_quality.QualityFinding`, the shape every planning-document finding takes.
- Used by: `application.planning_report` (the one composition behind the Gate step and
  `beadloom docs quality`), `application.impact.section` (the renderer), and the
  `beadloom axes` command.

## Parent

`doc-sync`

## Testing

`tests/test_the_axes_section_is_required_by_the_template.py` — the grammar in both directions,
the wrapped seed field, the offered-but-undecided cell, the stated absence of a seed, the
dedupe in `refs:`, and the round trip. The scenarios are
`tests/acceptance/features/axes_section.feature`.
