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
> **Unresolved:** 2 unnameable-callee, 1 node-owns-unread-files

| Axis | Node | Sites | Owns unread | In scope | Why |
|------|------|-------|-------------|----------|-----|
| co-writers | graph-files | 6 — `src/…/bootstrap.py:216` | none | yes | the invariant is written here |
| branches | onboarding | `detect_preset`: 2 branch(es), 3 exit form(s) | 49 — `src/…/templates/agentic_flow/CLAUDE.md.txt` | yes | owns the templates the fix edits |
```

The first four columns are the derivation's output. The last two are the person's scope
decision, and the split is what lets a check tell "a run nobody has ruled on" from "a decision
somebody took". A blockquote field wrapped over several lines is one value, because these
documents wrap at 95 columns like every other.

### The `Owns unread` column, and the tables written before it

BDL-UX #284. A node surfaces under an axis by its relation to the seed, and that relation says
nothing about the node's role in the change. BDL-069 ruled `onboarding` out as blast radius
because it surfaced as a caller, and the fix lived in that node's `.md.txt` templates, which
`beadloom impact` does not read. The column puts the files a row's node owns and the derivation
could not read on the row a person rules, rather than only in the `Unresolved` count above the
table.

`Axis.owns_unread` holds the cell as written, and `Axis.unread_count` reads it: `N — path` is
`N`, `none` is `0`, and anything else — `—`, `unknown — no index`, or words a person wrote — is
`None` and kept as written rather than guessed at.

Every column is read by its header name, so a table written before the column existed reads
exactly as it did. The one fact that table never stated reads as `None`, meaning not stated,
and never as `0`. Measured on 2026-09-11 over the 202 planning documents under
`.claude/development/docs/features/`, two of which carry an `## Axes` section: `beadloom axes`
printed byte-identical `--json`, text and `--refs` output from the reader before and after the
change. BDL-069's `--refs` named the same 23 nodes with the RFC as it stood at `7eadb4b4`, and
the same 24 once `9b49b4a0` added `git-activity` to it. `beadloom axes --json` does not print the
new field, because that output belongs to `cli-commands`, which this change did not reach.

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

### A slice appends its rows under its own derivation block, and that is a second table

An epic's axes are the UNION of its slices', and the RFC's rule is that each slice appends its
rows under its own `Derived by` line. That is naturally a new table rather than more rows under
one header, so a real section holds one table per slice — BDL-068's holds five.

The reader took the first table's header as the header for everything under the heading, so a
second table's rows were judged against the first table's column index and the second table's
HEADER ROW came back as data: an axis named `Axis` on a node named `Node`, whose `In scope` cell
reads the literal words "In scope" as a yes. Measured on BDL-068's own RFC laid out in the shape
its rule describes — 74 rows in five per-slice tables — the reader returned 78 rows, four of them
header rows, all four approved, and `Node` in the `refs:` line and therefore in the set
`scope-check` compares every commit against (BDL-UX #244). After the fix the two layouts read
identically: 74 rows, 52 kept, 51 nodes, from one table or from five.

The section's body is therefore read twice, for the two different things it states. The
blockquote fields are prose the derivation wrote and are collected across every block; the
tables are its output and each is judged against its own header. Reading both in one pass is what
made the table boundary depend on where a field happened to stop.

### The table it reads is read by one reader

The row grammar and the table boundary are `doc_sync.tables`, not a parser of this module's own
(BDL-068 S1.5, S6). `/task-init`'s routing table is read for a different fact by the same
`table_cells`, and `doc-quality` finds its decision tables with the same `table_blocks`, so
"what a row is" and "where a table starts" cannot disagree with themselves between the readers.
The second of those two was added because they did: BDL-UX #213 and #244 are one sentence found
in two places, hours apart, in one slice.

## Public API

| Symbol | Kind |
|--------|------|
| `AXES_HEADING` / `SEED_FIELD` / `DERIVED_BY_FIELD` / `UNRESOLVED_FIELD` / `NO_SEED` / `COLUMNS` | constant |
| `AXES_WITHOUT_A_SEED` / `AXIS_WITHOUT_A_SCOPE_DECISION` / `CHECK_NAMES` | constant |
| `OWNS_UNREAD_COLUMN` / `OWNS_NOTHING_UNREAD` | constant |
| `Axis` / `AxesSection` | dataclass |
| `read_axes_section` | function |
| `refs_line` | function |
| `derived_targets` | function |
| `check_axes_section` | function |

## Dependencies

- Depends on: `doc_sync.doc_shape.read_sections` — the one fence-aware, depth-aware section
  reader, so a `## Axes` quoted inside a fenced block is not read as this document's own;
  `doc_sync.tables.table_blocks`, the one place that decides where a table starts; and
  `doc_sync.doc_quality.QualityFinding`, the shape every planning-document finding takes.
- Used by: `application.planning_report` (the one composition behind the Gate step and
  `beadloom docs quality`), `application.impact.section` (the renderer), the
  `beadloom axes` command, and `application.declared_scope` (BDL-068 S1.6), which resolves
  what `derived_targets` returns.

## The targets the derivation ran over

`derived_targets(section)` returns the paths the `Derived by` field names, over a SHAPE
rather than a spelling: any whitespace-separated word inside a code span of that field which
carries a path separator. That reads the rendered form, where the target and the sweep root
share one span, and a hand-written field naming three files in three spans, without either
being a special case. A target given as a SYMBOL carries no separator and is not returned,
because a symbol names no path and the caller has nothing to resolve — the gap is stated
rather than guessed at. Whether a returned word is a file, a directory or neither is the
caller's question: this domain has no filesystem and no index to ask.

## Parent

`doc-sync`

## Testing

`tests/test_the_axes_section_is_required_by_the_template.py` — the grammar in both directions,
the wrapped seed field, the offered-but-undecided cell, the stated absence of a seed, the
dedupe in `refs:`, and the round trip. The scenarios are
`tests/acceptance/features/axes_section.feature`.
