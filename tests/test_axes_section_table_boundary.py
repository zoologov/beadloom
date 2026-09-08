"""BDL-068 S6 / BDL-UX #244 — a second table under ``## Axes`` is its own table.

The RFC's own rule for this section is that an epic's axes are the UNION of its
slices' and that each slice appends its rows under its own ``Derived by`` line.
Five ``Derived by`` blocks later, that is naturally five tables. The reader took
the first table's header row as the header for everything under the heading, so
a second table's rows were judged against the first table's column index and the
second table's HEADER ROW came back as data — an axis named ``Axis`` on a node
named ``Node``, decided ``In scope``, which the word ``in scope`` reads as YES.

Measured before the fix, over this repository's own RFC laid out in the shape its
own rule describes (74 rows in five per-slice tables): 78 rows read, 4 of them
header rows, all four approved, and ``Node`` in the generated ``refs:`` line and
therefore in the set ``scope-check`` judges every commit against.

The same root, one reader over, is BDL-UX #213, fixed by ``beadloom-0mdo.68``
hours earlier in this slice. Its answer is reused here rather than reproduced:
:func:`beadloom.doc_sync.tables.table_blocks` is the one place that decides where
a table starts, and both readers spend it.
"""

from __future__ import annotations

from beadloom.doc_sync.axes_section import read_axes_section, refs_line

_HEADER = "| Axis | Node | Sites | In scope | Why |"
_SEPARATOR = "|------|------|-------|----------|-----|"


def _section(*blocks: str) -> str:
    return "\n".join(["# RFC: KEY-1 — a work item", "", "## Axes", "", *blocks, ""])


def _block(derived: str, *rows: str) -> str:
    return "\n".join(
        [
            f"> **Derived by:** `beadloom impact` over `{derived}`",
            "> **Seed:** `none`, under the rule `reaches-an-effect-sink`",
            "",
            _HEADER,
            _SEPARATOR,
            *rows,
            "",
        ]
    )


class TestASecondTableIsASecondTable:
    """A section holding two tables is two tables, not one long one."""

    def test_the_second_table_header_is_not_read_as_a_row(self) -> None:
        text = _section(
            _block("alpha.py", "| callers | billing | 1, `a` (`a.py:1`) | yes | S1 writes it |"),
            _block("beta.py", "| callers | shipping | 2, `b` (`b.py:2`) | yes | S2 writes it |"),
        )

        section = read_axes_section(text)

        assert section is not None
        assert [axis.node for axis in section.axes] == ["billing", "shipping"]

    def test_no_row_is_approved_that_nobody_wrote(self) -> None:
        text = _section(
            _block("alpha.py", "| callers | billing | 1, `a` (`a.py:1`) | yes | S1 writes it |"),
            _block("beta.py", "| callers | shipping | 2, `b` (`b.py:2`) | yes | S2 writes it |"),
        )

        section = read_axes_section(text)

        assert section is not None
        assert refs_line(section) == "refs: billing, shipping"

    def test_five_blocks_read_back_the_rows_they_state_and_no_more(self) -> None:
        rows = [
            f"| callers | node-{index} | 1, `f` (`f.py:1`) | yes | slice {index} |"
            for index in range(5)
        ]
        text = _section(*(_block(f"s{index}.py", row) for index, row in enumerate(rows)))

        section = read_axes_section(text)

        assert section is not None
        assert len(section.axes) == 5

    def test_a_second_table_is_judged_against_its_own_columns(self) -> None:
        """The columns may be ordered differently, and the row still reads."""
        reordered = "\n".join(
            [
                "> **Derived by:** `beadloom impact` over `beta.py`",
                "",
                "| Node | Axis | In scope | Sites | Why |",
                "|------|------|----------|-------|-----|",
                "| shipping | co-writers | no | 2, `b` (`b.py:2`) | only read here |",
                "",
            ]
        )
        text = _section(
            _block("alpha.py", "| callers | billing | 1, `a` (`a.py:1`) | yes | S1 writes it |"),
            reordered,
        )

        section = read_axes_section(text)

        assert section is not None
        second = section.axes[1]
        assert (second.node, second.axis, second.in_scope) == (
            "shipping",
            "co-writers",
            False,
        )

    def test_a_separator_row_does_not_end_the_table_it_belongs_to(self) -> None:
        text = _section(
            _block(
                "alpha.py",
                "| callers | billing | 1, `a` (`a.py:1`) | yes | S1 writes it |",
                "| callers | invoicing | 3, `c` (`c.py:3`) | yes | S1 writes it too |",
            )
        )

        section = read_axes_section(text)

        assert section is not None
        assert [axis.node for axis in section.axes] == ["billing", "invoicing"]

    def test_the_fields_of_every_block_are_still_read(self) -> None:
        """Splitting the tables must not cost the blockquote fields above them."""
        text = _section(
            _block("alpha.py", "| callers | billing | 1, `a` (`a.py:1`) | yes | S1 writes it |"),
            _block("beta.py", "| callers | shipping | 2, `b` (`b.py:2`) | yes | S2 writes it |"),
        )

        section = read_axes_section(text)

        assert section is not None
        assert "alpha.py" in section.derived_by
        assert "beta.py" in section.derived_by
        assert section.names_a_seed
