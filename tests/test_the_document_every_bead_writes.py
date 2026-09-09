"""BDL-UX #257 — the document every bead of a work item writes, and no bead owns.

`beadloom waves` resolves a bead to the nodes and files its CODE occupies, so two
beads holding disjoint code scopes and one shared DOCUMENT read as independent
and the plan reports `0 serialisations` truthfully about the wrong population.

Three claims are pinned here, and the third is the one that decides the shape of
the fix rather than verifying it:

1. WHICH document every bead writes into is DERIVED from the composed
   `/task-init` routing table, never authored. `Routing.shared_kinds` is the
   intersection over every route, beside the two difference properties that
   already existed.
2. The check over it fails on a bead the document carries no row for, passes when
   every bead has one, and reads a row through the reader `active-sync` already
   spends.
3. A `shared_document` SERIALISATION derived from document ownership would be a
   check that cannot fail. `docs.ref_id` holds at most one node per document and
   `conflict_between` already fires `shared_node` on any ref intersection, so two
   beads that reach a document comparison have disjoint refs and therefore
   disjoint owned documents. `TestDocumentOwnershipCannotSerialiseAnything` is
   that claim as an executable, so a later schema change that makes it false is
   found by a red test rather than by a wave.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from beadloom.application.waves import (
    MEDIUM_FOCUS_DOCUMENT,
    STATUS_FAILED,
    STATUS_PASSED,
    STATUS_UNMEASURED,
    BeadRecord,
    FocusDocument,
    WaveEnvironment,
    check_media,
)
from beadloom.application.work_item_routing import read_routing
from beadloom.infrastructure.db import create_schema, open_db
from beadloom.infrastructure.repository import get_docs_for_ref

if TYPE_CHECKING:
    from pathlib import Path

    from beadloom.application.waves import MediumCheck

#: A `/task-init` command as the composer writes one, reduced to the table the
#: routing is read from. Both flows write ACTIVE; only one writes each of the
#: rest, which is the shape every route table of this flow has had.
_A_TASK_INIT = """# /task-init

## Step 2: Decide the type

| Type | Flow | Docs created |
|------|------|--------------|
| epic | Full: PRD, RFC, CONTEXT, PLAN, ACTIVE | PRD, RFC, CONTEXT, PLAN, ACTIVE |
| bug | Simplified: BRIEF, ACTIVE | BRIEF, ACTIVE |
"""

#: The same command with no document written by both routes.
_ROUTES_SHARING_NOTHING = """# /task-init

## Step 2: Decide the type

| Type | Flow | Docs created |
|------|------|--------------|
| epic | Full: PRD, RFC | PRD, RFC |
| bug | Simplified: BRIEF | BRIEF |
"""


def _check(
    records: list[BeadRecord], environment: WaveEnvironment
) -> MediumCheck:
    """The focus-document verdict for *records* under *environment*."""
    checks = check_media(records, environment=environment)
    return next(check for check in checks if check.medium == MEDIUM_FOCUS_DOCUMENT)


def _document(*cells: str) -> FocusDocument:
    return FocusDocument(
        path=".claude/development/docs/features/KEY/ACTIVE.md",
        kind="ACTIVE",
        row_cells=cells,
    )


class TestTheSharedDocumentIsDerivedFromTheRoutingTable:
    """Which document every work item writes is read off the composed command.

    Not a constant and not a `refs:` line. An authored population is the defect
    BDL-UX #232 was filed against and `beadloom-en0x` closed, and
    `beadloom-0mdo.51`'s report measured why one rots. A project that adds a type
    or moves a document between flows changes this answer by the same act.
    """

    def test_the_kind_both_routes_write_is_the_shared_one(self) -> None:
        routing = read_routing(_A_TASK_INIT)

        assert routing.shared_kinds == frozenset({"ACTIVE"})

    def test_a_kind_only_one_route_writes_is_not_shared(self) -> None:
        """The complement of the two properties that already existed."""
        routing = read_routing(_A_TASK_INIT)

        assert "BRIEF" not in routing.shared_kinds
        assert "PRD" not in routing.shared_kinds
        assert routing.simplified_kinds == frozenset({"BRIEF"})

    def test_routes_writing_no_document_in_common_share_none(self) -> None:
        assert read_routing(_ROUTES_SHARING_NOTHING).shared_kinds == frozenset()

    def test_a_command_with_no_routing_table_shares_nothing_and_says_so(self) -> None:
        """An empty answer over an unread table is not the same as an empty table."""
        routing = read_routing("# /task-init\n\nNo table here.\n")

        assert routing.shared_kinds == frozenset()
        assert routing.notes


class TestTheCheckOverTheDocumentEveryBeadWrites:
    """The precondition: does the shared document give each bead a row of its own?

    Not *do these beads share it* — they do, by construction, which is why it is
    a medium. A bead with no row has only the prose around the table, and that is
    where one bead's hunk lands inside another bead's commit.
    """

    def test_a_bead_with_no_row_fails_the_check_and_is_named(self) -> None:
        check = _check(
            [BeadRecord(bead_id="proj.1"), BeadRecord(bead_id="proj.2")],
            WaveEnvironment(focus_documents=(_document("Bead", "proj.1"),)),
        )

        assert check.status == STATUS_FAILED
        assert "proj.2" in check.detail
        assert "proj.1" not in check.detail.replace("proj.1`", "")

    def test_a_document_naming_every_bead_passes(self) -> None:
        check = _check(
            [BeadRecord(bead_id="proj.1"), BeadRecord(bead_id="proj.2")],
            WaveEnvironment(focus_documents=(_document("Bead", "proj.1", "proj.2"),)),
        )

        assert check.status == STATUS_PASSED

    def test_nothing_read_is_unmeasured_rather_than_a_lenient_pass(self) -> None:
        check = _check([BeadRecord(bead_id="proj.1")], WaveEnvironment())

        assert check.status == STATUS_UNMEASURED

    def test_an_empty_population_is_an_observation_and_passes(self) -> None:
        """The landing-order precedent: nobody's flow is failed for not having one."""
        check = _check(
            [BeadRecord(bead_id="proj.1")],
            WaveEnvironment(focus_documents=()),
        )

        assert check.status == STATUS_PASSED
        assert "no work item" in check.detail

    @pytest.mark.parametrize(
        "cell",
        [".2", "`.2`", "**.2**", "[.2](#anchor)", "`proj.2`"],
        ids=["short", "code-span", "bold", "link", "decorated-full"],
    )
    def test_a_row_is_read_the_way_active_sync_reads_one(self, cell: str) -> None:
        """No second reader. BDL-UX #210 measured what a third one costs.

        An ACTIVE table abbreviates the tracker's id to its number and wraps it in
        whatever Markdown the author writes identifiers in. A check that only
        matched the full bare id would report every row of every table in this
        repository as naming no bead.
        """
        check = _check(
            [BeadRecord(bead_id="proj.2")],
            WaveEnvironment(focus_documents=(_document("Bead", cell),)),
        )

        assert check.status == STATUS_PASSED

    def test_the_check_judges_exactly_the_documents_it_was_handed(self) -> None:
        """The POPULATION is chosen at the services edge, and this is why it matters.

        The first version of the gathering read every focus document in the
        project. Run on this repository it reported `passed` for all three beads
        of BDL-068's S6 wave over 58 documents, not one of which carries a row
        for any of them: a table abbreviates `beadloom-0mdo.75` to `.75`, and
        BDL-061's own table has a `.75` row. `_focus_documents` now keeps the
        work item's folder only, and the check trusts what it is handed — which
        is why a wrong population is a wrong verdict and is pinned here.
        """
        a_neighbours_table = FocusDocument(
            path=".claude/development/docs/features/OTHER/ACTIVE.md",
            kind="ACTIVE",
            row_cells=(".2",),
        )

        assert (
            _check(
                [BeadRecord(bead_id="proj.2")],
                WaveEnvironment(focus_documents=(a_neighbours_table,)),
            ).status
            == STATUS_PASSED
        )
        assert (
            _check(
                [BeadRecord(bead_id="proj.2")],
                WaveEnvironment(focus_documents=(_document("Bead", ".1"),)),
            ).status
            == STATUS_FAILED
        )

    def test_the_failure_says_where_to_add_the_row(self) -> None:
        """A verdict a reader cannot act on is the class this epic removes."""
        check = _check(
            [BeadRecord(bead_id="proj.9")],
            WaveEnvironment(focus_documents=(_document("Bead", ".1"),)),
        )

        assert check.status == STATUS_FAILED
        assert "ACTIVE.md" in check.detail
        assert "#257" in check.detail


class TestDocumentOwnershipCannotSerialiseAnything:
    """Why the other half of #257's fix is not a serialisation, as an executable.

    The bead asked for a derivation of a bead's document scope. Derived from
    OWNERSHIP it is worth exactly zero, and this is the measurement rather than
    the opinion: `docs.ref_id` is a single column, so a document belongs to at
    most one node, and `conflict_between` serialises on `shared_node` before any
    document could be compared. Two beads that reach a document comparison
    therefore hold disjoint refs, and disjoint refs hold disjoint documents.

    If a later schema gives a document more than one owner this class goes red,
    which is when the serialisation becomes worth building.
    """

    def test_a_document_belongs_to_at_most_one_node(self, tmp_path: Path) -> None:
        conn = open_db(tmp_path / "beadloom.db")
        try:
            create_schema(conn)
            for ref in ("billing", "shipping"):
                conn.execute(
                    "INSERT INTO nodes (ref_id, kind, summary) VALUES (?, ?, ?)",
                    (ref, "feature", ref.title()),
                )
            conn.execute(
                "INSERT INTO docs (path, kind, ref_id, hash) VALUES (?, ?, ?, ?)",
                ("docs/shared.md", "feature", "billing", "h"),
            )
            conn.commit()

            assert [path for path, _ in get_docs_for_ref(conn, "billing")] == [
                "docs/shared.md"
            ]
            assert get_docs_for_ref(conn, "shipping") == []
        finally:
            conn.close()

    def test_the_same_path_cannot_be_owned_twice(self, tmp_path: Path) -> None:
        """`docs.path` is UNIQUE, so the row that would share a document cannot exist."""
        import sqlite3

        conn = open_db(tmp_path / "beadloom.db")
        try:
            create_schema(conn)
            for ref in ("billing", "shipping"):
                conn.execute(
                    "INSERT INTO nodes (ref_id, kind, summary) VALUES (?, ?, ?)",
                    (ref, "feature", ref.title()),
                )
            conn.execute(
                "INSERT INTO docs (path, kind, ref_id, hash) VALUES (?, ?, ?, ?)",
                ("docs/shared.md", "feature", "billing", "h"),
            )
            with pytest.raises(sqlite3.IntegrityError):
                conn.execute(
                    "INSERT INTO docs (path, kind, ref_id, hash) VALUES (?, ?, ?, ?)",
                    ("docs/shared.md", "feature", "shipping", "h"),
                )
        finally:
            conn.close()
