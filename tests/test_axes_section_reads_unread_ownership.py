"""The reader of the `## Axes` section parses the unread-ownership column (BDL-UX #284).

`beadloom axes <doc> --refs` is what `beadloom waves` and `scope-check` are fed
from, and every axes table this project wrote before the column existed carries
five columns. Two things therefore have to hold together, and this module holds
both: a table carrying the column is read into a count per row, and a table
without it reads exactly as it did — every field it had, and `None` for the one
it never stated, because "nobody measured this" is not "this node owns nothing
unread".
"""

from __future__ import annotations

from beadloom.doc_sync.axes_section import (
    COLUMNS,
    OWNS_UNREAD_COLUMN,
    Axis,
    read_axes_section,
    refs_line,
)

_FIELDS = """\
## Axes

> **Derived by:** `beadloom impact src/pkg/manifest.py` over `src/pkg`
> **Seed:** none
> **Unresolved:** 1 no-seed

"""

_OLD_TABLE = """\
| Axis | Node | Sites | In scope | Why |
|------|------|-------|----------|-----|
| callers | skel | 1 — `src/pkg/skel/generator.py:8` | no | reads the manifest |
| branches | manifest | `read_manifest`: 1 branch(es) | yes | the change |
"""

_NEW_TABLE = """\
| Axis | Node | Sites | Owns unread | In scope | Why |
|---|---|---|---|---|---|
| callers | skel | 1 — `src/pkg/gen.py:8` | 3 — `src/pkg/t/a.md.txt` | yes | owns them |
| branches | manifest | `read_manifest`: 1 branch(es) | none | yes | the change |
| co-writers | — | unresolved — no seed | — | no | nothing to rule |
"""


def _read(text: str) -> tuple[Axis, ...]:
    section = read_axes_section(text)
    assert section is not None
    return section.axes


class TestATableWrittenBeforeTheColumnReadsAsItDid:
    def test_every_field_it_stated_is_read_as_before(self) -> None:
        assert _read(_FIELDS + _OLD_TABLE) == (
            Axis(
                axis="callers",
                node="skel",
                sites="1 — `src/pkg/skel/generator.py:8`",
                in_scope=False,
                why="reads the manifest",
                line=9,
            ),
            Axis(
                axis="branches",
                node="manifest",
                sites="`read_manifest`: 1 branch(es)",
                in_scope=True,
                why="the change",
                line=10,
            ),
        )

    def test_the_column_it_never_stated_reads_as_not_stated_rather_than_none(self) -> None:
        for axis in _read(_FIELDS + _OLD_TABLE):
            assert axis.owns_unread is None
            assert axis.unread_count is None


class TestATableCarryingTheColumn:
    def test_a_count_is_read_from_the_cell(self) -> None:
        by_node = {axis.node: axis for axis in _read(_FIELDS + _NEW_TABLE)}
        assert by_node["skel"].owns_unread == "3 — `src/pkg/t/a.md.txt`"
        assert by_node["skel"].unread_count == 3

    def test_a_stated_none_is_zero(self) -> None:
        by_node = {axis.node: axis for axis in _read(_FIELDS + _NEW_TABLE)}
        assert by_node["manifest"].unread_count == 0

    def test_a_row_naming_no_node_carries_no_count(self) -> None:
        unowned = [axis for axis in _read(_FIELDS + _NEW_TABLE) if not axis.node]
        assert [axis.unread_count for axis in unowned] == [None]

    def test_the_decision_columns_after_it_are_read_from_their_own_positions(self) -> None:
        by_node = {axis.node: axis for axis in _read(_FIELDS + _NEW_TABLE)}
        assert by_node["skel"].in_scope is True
        assert by_node["skel"].why == "owns them"

    def test_a_cell_that_is_not_a_count_is_kept_and_not_guessed_at(self) -> None:
        text = _FIELDS + _NEW_TABLE.replace("3 — `src/pkg/t/a.md.txt`", "the templates")
        by_node = {axis.node: axis for axis in _read(text)}
        assert by_node["skel"].owns_unread == "the templates"
        assert by_node["skel"].unread_count is None


class TestOneSectionHoldingBothShapes:
    """A slice appends its rows under its own table, so the two shapes meet in one section."""

    def test_each_table_is_read_by_its_own_header(self) -> None:
        axes = _read(_FIELDS + _OLD_TABLE + "\n" + _NEW_TABLE)
        assert [axis.unread_count for axis in axes] == [None, None, 3, 0, None]
        assert [axis.in_scope for axis in axes] == [False, True, True, True, False]

    def test_the_refs_line_is_generated_from_the_decisions_alone(self) -> None:
        section = read_axes_section(_FIELDS + _OLD_TABLE + "\n" + _NEW_TABLE)
        assert section is not None
        assert refs_line(section) == "refs: manifest, skel"


def test_the_column_sits_in_the_derivation_half_of_the_grammar() -> None:
    """The last two columns stay the person's decision; the new one is derived."""
    assert COLUMNS[-2:] == ("In scope", "Why")
    assert OWNS_UNREAD_COLUMN in COLUMNS[:-2]
