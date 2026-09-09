# Markdown Tables (component)

Internal building block of the doc-sync domain.

**Source:** `src/beadloom/doc_sync/tables.py`

---

## Overview

What a markdown table row is, and where one table ends and the next begins. One
module, because three readers of that answer needed it and the first two
disagreed twice in one slice.

BDL-UX #213 and BDL-UX #244 are one sentence found in two places: a section
holding two tables was read as one, so the second table's rows were judged
against the FIRST table's column index and the second table's header row came
back as data. In `doc-quality` that reported a measurement table's header as a
decision row with a missing reason cell — four findings on BDL-067's `ACTIVE.md`,
all false. In `axes-section` it produced an approved node literally named `Node`.
Measured on this repository's own RFC laid out in the shape its own rule
describes — 74 rows in five per-slice tables — the axes reader returned 78 rows,
four of them header rows, all four approved.

Both second tables exist because this project's own document rules ask for them.
The RFC says each slice appends its axis rows under its own `Derived by` line,
and the `/coordinator` playbook asks for a verification table beside the decision
table it verifies. Neither reader was wrong about one table; both were wrong that
there is one.

BDL-UX #259 is the THIRD reader, `work-item-routing`, converted by
`beadloom-0mdo.77`. It matched the first ROW that spelled the routing header and
read every table row below it as a route, and it fired no instance because it
discarded a row whose second cell named neither `simplified` nor `full`. That is
the shape this component exists to remove: a vocabulary guard standing in for a
boundary, in the reader whose sibling had already measured that vocabulary cannot
decide this. Measured over this repository, the guard admits 27 of 5 122 table
rows in 456 markdown files, and 17 of the 27 belong to other tables in other
documents.

## Public surface

- `cells_of(line)` — the cells of a table line, alignment row included, or
  `None` when the line is not a table row. The raw reading, for a caller that
  asks whether a line is a row at all.
- `is_separator(cells)` — whether those cells are an alignment row rather than
  content.
- `table_cells(line)` — the cells of a table row that says something, or `None`.
  Re-exported from `doc_sync.doc_shape`, where it used to live, so no caller
  moved.
- `table_blocks(lines)` — the contiguous tables in numbered *lines*, each
  leading with its own header row. A separator row is dropped and does not end a
  table; everything that is not a table row does.
- `Table` — one table, as `(line number, cells)` rows.

## Collaborators

`doc-quality` spends `table_blocks` for `decision-reason`, `risk-mitigation` and
`pending-in-approved`, and `cells_of` for `unfilled-placeholder`. `axes-section`
spends it to read the `## Axes` section's per-slice tables. `work-item-routing`
spends it to find the `/task-init` routing tables — every block whose own header
row leads with `Type` and `Flow` — and reads their union, each table's rows
judged against its own header. `wave-plan` spends `cells_of`.

`doc-shape` still re-exports `table_cells`, and since `beadloom-0mdo.77` moved
`work-item-routing` onto `table_blocks` that re-export has **no caller in this
repository**. It is kept as the documented alias its comment describes rather
than removed here, because removing a public name is a surface change and not
this bead's subject.

The boundary rule reads no header vocabulary at all. The residual class that a
boundary cannot decide — a measurement table carrying a reason column of its own
— is `doc-quality`'s, and is answered there by asking what the DOCUMENT declares.

> Component doc (BDL-068 S6, `beadloom-0mdo.46`; third reader added by
> `beadloom-0mdo.77`). Public surface verified against `tables.py`.
