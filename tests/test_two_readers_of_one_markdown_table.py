"""BDL-068 S6 — one fact, two readers: what a markdown table row is.

``doc_sync/tables.py`` exists because two readers of that fact disagreed twice in
one slice. Its own docstring states the purpose: it is "that answer lifted to the
one place both readers spend, so a third reader cannot be wrong about it a third
time" (BDL-UX #213, #244, #259).

There is a third reader, and it is older than the component.
``application/active_table/table.py`` splits a row with its own body and carries
its own separator predicate, and every instrument that reads an ACTIVE document
spends one of the two. The ``focus-document`` medium ``beadloom-0mdo.75`` shipped
spends BOTH in one computation: it collects a document's rows with
``doc_sync.tables.cells_of`` and asks ``active_table``'s ``names_bead`` about the
cells it got, while ``active-sync`` reads the same document with
``active_table.split_table_row``. Two instruments, one document, two answers
about which rows it has.

**Measured before anything was written here**, which is why this is a module and
not an opinion. Over this repository's 259 planning documents (32 353 lines) the
two readers disagree on **0** lines; over its 610 markdown files (106 740 lines)
they disagree on **12**, every one of them a lone ``|`` inside a diagram. So the
divergence is invisible on this repository's own arrangement, which is the
condition BDL-UX #240 records and this slice's bead names.

Two findings are pinned as ``xfail(strict=True)`` with ``FINDING BDL-068.S6-N``
in the reason, the convention ``.18`` set and ``.22`` carried: a strict xfail
turns red the moment its defect is fixed, so a finding cannot be quietly closed.
Every other test here is a boundary guard written after the behaviour, and says
so where it matters.
"""

from __future__ import annotations

import ast
import inspect
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from beadloom.application.active_table.table import is_separator_cells, split_table_row
from beadloom.doc_sync import tables
from beadloom.doc_sync.axes_section import read_axes_section
from beadloom.doc_sync.tables import cells_of, is_separator

if TYPE_CHECKING:
    from collections.abc import Iterator

_SRC = Path(__file__).resolve().parent.parent / "src" / "beadloom"
_PLANNING = (
    Path(__file__).resolve().parent.parent / ".claude" / "development" / "docs" / "features"
)

#: Every place in the package that turns a line into cells by splitting on a
#: pipe, as ``(module path, enclosing function)``, with what each one is. The
#: derivation below finds these from the source; this list is what a reader has
#: DECIDED about them, so a fourth site fails the guard rather than joining a
#: population nobody looked at.
DECLARED_PIPE_SPLITS: dict[tuple[str, str], str] = {
    ("doc_sync/tables.py", "cells_of"): "row-reader",
    ("application/active_table/table.py", "split_table_row"): "row-reader",
    ("application/guards/surface.py", "named_but_not_granted"): "not-a-table",
    ("application/guards/surface.py", "_bound"): "not-a-table",
}

#: Rows the two readers answer differently. Each is a valid line a document can
#: hold, and each was measured rather than imagined.
DIVERGENT_ROWS: tuple[tuple[str, list[str] | None, list[str] | None], ...] = (
    ("|", None, [""]),
    ("||", None, [""]),
    ("|| a | b ||", ["", "a", "b", ""], ["a", "b"]),
)

#: Alignment rows the two separator predicates answer differently, each with the
#: answers ``tables.is_separator`` and ``active_table.is_separator_cells`` give.
#: The two rows have two different causes and only the first is a finding.
DIVERGENT_ALIGNMENTS: tuple[tuple[str, bool, bool], ...] = (
    ("|-|-|", False, True),
    ("| |", True, False),
)

#: The valid alignment row the lifted component refuses. GitHub Flavored Markdown
#: says a delimiter cell holds hyphens with optional colons, and one hyphen is a
#: well-formed cell.
SINGLE_HYPHEN_ROW = "|-|-|"

#: A row whose cells are all empty. ``tables.is_separator`` filters empty cells
#: out before deciding, so the ``all`` is vacuously true; ``is_separator_cells``
#: requires each cell to be non-empty and says no.
EMPTY_CELLED_ROW = "| |"


def _pipe_split_sites() -> list[tuple[str, str]]:
    """Every ``<expr>.split("|")`` in the package, with the function holding it.

    A SHAPE and not a spelling: the call is found in the parsed tree, so a body
    that writes ``line.split('|')``, ``stripped.strip('|').split("|")`` or
    ``match.group(1).split(SEP)`` where ``SEP`` is the literal is found the same
    way. What it cannot see is a split through a variable holding the pipe, which
    is stated here rather than left for a reader to discover.
    """
    sites: list[tuple[str, str]] = []
    for path in sorted(_SRC.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for holder, call in _calls_with_owner(tree):
            func = call.func
            if not isinstance(func, ast.Attribute) or func.attr != "split":
                continue
            if len(call.args) != 1:
                continue
            arg = call.args[0]
            if not (isinstance(arg, ast.Constant) and arg.value == "|"):
                continue
            sites.append((path.relative_to(_SRC).as_posix(), holder))
    return sites


def _calls_with_owner(tree: ast.AST) -> Iterator[tuple[str, ast.Call]]:
    """Every call in *tree*, paired with the name of the function holding it."""
    stack: list[tuple[str, ast.AST]] = [("<module>", tree)]
    while stack:
        owner, node = stack.pop()
        for child in ast.iter_child_nodes(node):
            name = owner
            if isinstance(child, ast.FunctionDef | ast.AsyncFunctionDef):
                name = child.name
            if isinstance(child, ast.Call):
                yield owner, child
            stack.append((name, child))


class TestThePackageHasTwoReadersOfOneRow:
    """The component was lifted so a third reader could not be wrong; there is one.

    Written after the behaviour, so it is a boundary guard rather than a red the
    code was built against. What it guards is the population: a FOURTH pipe-split
    arriving in the package must be classified by whoever adds it.
    """

    def test_every_pipe_split_in_the_package_is_declared(self) -> None:
        found = set(_pipe_split_sites())
        assert found == set(DECLARED_PIPE_SPLITS), (
            "a body splits a line on a pipe and no reader has classified it — "
            f"undeclared {sorted(found - set(DECLARED_PIPE_SPLITS))}, "
            f"gone {sorted(set(DECLARED_PIPE_SPLITS) - found)}"
        )

    def test_two_of_them_read_a_table_row_and_neither_calls_the_other(self) -> None:
        readers = [site for site, kind in DECLARED_PIPE_SPLITS.items() if kind == "row-reader"]
        assert len(readers) == 2, readers
        body = inspect.getsource(split_table_row)
        assert "cells_of" not in body, (
            "`split_table_row` now spends the lifted component — remove it from "
            "DECLARED_PIPE_SPLITS and close the findings this module pins"
        )

    def test_the_component_that_was_lifted_says_it_is_the_only_reader(self) -> None:
        """The claim under test is the module's own, quoted from its docstring."""
        claim = " ".join((tables.__doc__ or "").split())
        assert "a third reader cannot be wrong about it a third time" in claim


class TestTheTwoReadersOnThisRepositorysOwnDocuments:
    """The control: on this arrangement the two readers agree, which is the point.

    A divergence nobody can produce here is exactly the defect class BDL-UX #240
    records, so the measurement is kept as a test rather than as a sentence.
    """

    def test_they_agree_on_every_line_of_every_planning_document(self) -> None:
        documents = sorted(_PLANNING.glob("*/*.md"))
        assert len(documents) > 50, f"only {len(documents)} planning documents found"
        disagreements = [
            (path.name, number, line)
            for path in documents
            for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1)
            if cells_of(line) != split_table_row(line)
        ]
        assert disagreements == []

    def test_the_agreement_is_a_property_of_the_documents_and_not_of_the_readers(
        self,
    ) -> None:
        """The same two readers, given a row this repository does not write."""
        assert cells_of("|| a | b ||") != split_table_row("|| a | b ||")


class TestWhereTheTwoReadersDisagree:
    """The rows one reader calls a table row and the other does not.

    Both readers are reachable from one document. ``waves`` collects a focus
    document's rows with ``cells_of`` and ``active-sync`` reads the same file with
    ``split_table_row``, so a document holding one of these rows is two different
    tables depending on which instrument is asked.
    """

    @pytest.mark.xfail(
        strict=True,
        reason=(
            "FINDING BDL-068.S6-1 (BDL-UX #268): `doc_sync.tables.cells_of` and "
            "`active_table.table.split_table_row` are two readers of one fact and "
            "answer three measured rows differently"
        ),
    )
    @pytest.mark.parametrize(("row", "_lifted", "_older"), DIVERGENT_ROWS)
    def test_the_two_readers_return_the_same_cells(
        self, row: str, _lifted: list[str] | None, _older: list[str] | None
    ) -> None:
        assert cells_of(row) == split_table_row(row)

    @pytest.mark.parametrize(("row", "lifted", "older"), DIVERGENT_ROWS)
    def test_each_divergence_is_the_one_recorded(
        self, row: str, lifted: list[str] | None, older: list[str] | None
    ) -> None:
        """The red above is red for the reason claimed, cell by cell."""
        assert cells_of(row) == lifted
        assert split_table_row(row) == older

    def test_a_doubled_border_pipe_hides_the_bead_from_one_reader_only(self) -> None:
        """The consequence, in the one document both instruments read.

        A row an author wrapped in doubled pipes gives ``active-sync`` a bead id
        in its first cell and gives the ``focus-document`` medium an empty one, so
        one instrument updates the bead's status and the other reports that no
        row names it.
        """
        row = "|| beadloom-aaaa.1 | dev | done ||"
        assert (split_table_row(row) or [""])[0] == "beadloom-aaaa.1"
        assert (cells_of(row) or [""])[0] == ""


class TestWhereTheTwoSeparatorPredicatesDisagree:
    """An alignment row is a separator to one reader and data to the other.

    Two rows, two causes, and only one of them is a finding. The single-hyphen
    row is valid Markdown the lifted component refuses; the empty-celled row is a
    difference whose consequence is a row nobody wrote being dropped, which is
    what a reader would want anyway. Keeping them apart is the point — one
    finding covering two causes is the shape this epic removes everywhere else.
    """

    @pytest.mark.xfail(
        strict=True,
        reason=(
            "FINDING BDL-068.S6-2 (BDL-UX #269): `tables.is_separator` demands two hyphens and "
            "GitHub Flavored Markdown requires one, so a valid alignment row is "
            "read as data by the lifted component and as a separator by the older "
            "reader"
        ),
    )
    def test_a_single_hyphen_alignment_row_is_a_separator_to_both(self) -> None:
        cells = cells_of(SINGLE_HYPHEN_ROW)
        assert cells is not None
        assert is_separator(cells) == is_separator_cells(cells)

    @pytest.mark.parametrize(("row", "lifted", "older"), DIVERGENT_ALIGNMENTS)
    def test_each_separator_divergence_is_the_one_recorded(
        self, row: str, lifted: bool, older: bool
    ) -> None:
        cells = cells_of(row)
        assert cells is not None
        assert is_separator(cells) is lifted
        assert is_separator_cells(cells) is older

    def test_an_empty_celled_row_is_dropped_and_does_not_end_the_table(self) -> None:
        """The second divergence, with the consequence that makes it not a finding.

        ``table_blocks`` drops what ``is_separator`` accepts, so a row whose cells
        are all empty leaves the table without ending it. The row carried nothing,
        so nothing is lost — but the reason it is dropped is the empty-cell filter
        and not a decision about blank rows, and that is worth pinning.
        """
        lines = [
            "| Axis | Node |",
            "| ------ | ------ |",
            "| callers | alpha |",
            EMPTY_CELLED_ROW.replace("| |", "|  |  |"),
            "| writers | beta |",
        ]
        tables_found = tables.table_blocks(enumerate(lines, start=1))
        assert len(tables_found) == 1
        assert [cells for _, cells in tables_found[0]] == [
            ["Axis", "Node"],
            ["callers", "alpha"],
            ["writers", "beta"],
        ]

    def test_a_single_hyphen_alignment_row_is_valid_markdown(self) -> None:
        """Stated as a fact about the format, so the finding is not a matter of taste.

        A GitHub Flavored Markdown delimiter row's cells hold hyphens and an
        optional leading or trailing colon; one hyphen is a well-formed cell. Both
        predicates accept the long form this repository writes, so nothing here
        distinguishes them on our own documents.
        """
        long_cells = cells_of("| ------ | ------ |")
        assert long_cells is not None
        assert is_separator(long_cells) is True
        assert is_separator_cells(long_cells) is True


class TestTheAxesSectionUnderAValidAlignmentRow:
    """BDL-UX #244's own class, inside the component lifted to end it.

    ``axes-section`` reads the ``## Axes`` tables with ``table_blocks``, and the
    list it produces is what ``scope-check`` compares every commit against. #244
    was a second table's header row arriving in that list as an approved node
    named ``Node``. Under a one-hyphen alignment row the same list gains a row
    whose axis is ``-``, and ``doc-quality`` reports it as an axis nobody decided
    — a finding against a document that is correct.
    """

    SECTION = (
        "# BRIEF\n\n"
        "## Axes\n\n"
        "> **Derived by:** `beadloom impact` over `src/orders.py`\n"
        "> **Seed:** none\n"
        "> **Unresolved:** none\n\n"
        "| Axis | Node | Sites | In scope | Why |\n"
        "|-|-|-|-|-|\n"
        "| callers | orders | 3 | yes | the change ranges over it |\n"
    )

    LONG_SECTION = SECTION.replace("|-|-|-|-|-|", "|---|---|---|---|---|")

    @pytest.mark.xfail(
        strict=True,
        reason=(
            "FINDING BDL-068.S6-2 (BDL-UX #269): a one-hyphen alignment row reaches "
            "`read_axes_section` as an axis row, so the approved-node list "
            "`scope-check` compares commits against gains a row named `-`"
        ),
    )
    def test_a_section_states_one_axis_however_its_alignment_row_is_spelled(
        self,
    ) -> None:
        section = read_axes_section(self.SECTION)
        assert section is not None
        assert [axis.axis for axis in section.axes] == ["callers"]

    def test_the_long_alignment_row_this_repository_writes_reads_correctly(
        self,
    ) -> None:
        """The control that says the red above is the alignment row and nothing else."""
        section = read_axes_section(self.LONG_SECTION)
        assert section is not None
        assert [axis.axis for axis in section.axes] == ["callers"]

    def test_the_phantom_row_is_the_one_recorded(self) -> None:
        """What the section holds today, so the finding names a measured shape."""
        section = read_axes_section(self.SECTION)
        assert section is not None
        phantom = [axis for axis in section.axes if axis.axis == "-"]
        assert len(phantom) == 1
        assert phantom[0].node == ""
        assert phantom[0].in_scope is None


class TestEveryFindingHereIsStrictAndNamesItself:
    """The meta-check `.18` introduced and `.22` carried.

    A non-strict xfail can be an artefact of a broken fixture rather than a
    defect, and a finding stated only in prose is a finding nobody re-measures.
    """

    def test_every_xfail_in_this_module_is_strict_and_cites_a_finding(self) -> None:
        import sys

        module = sys.modules[__name__]
        for klass_name, klass in vars(module).items():
            if not (isinstance(klass, type) and klass_name.startswith("Test")):
                continue
            for name, function in vars(klass).items():
                for mark in getattr(function, "pytestmark", []):
                    if mark.name != "xfail":
                        continue
                    where = f"{klass_name}.{name}"
                    assert mark.kwargs.get("strict") is True, f"{where}: not strict"
                    assert "FINDING BDL-068.S6-" in mark.kwargs.get("reason", ""), where
