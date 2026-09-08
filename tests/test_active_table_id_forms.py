"""The ACTIVE reconcile against the two forms a bead id is written in (BDL-061.84).

MEASURED on this repository, 2026-08-24: ``beadloom active-sync --check`` printed
``ACTIVE tables already coherent.`` and ``--json`` returned empty lists while
BDL-061's own ACTIVE.md carried ``| .22 | In progress |`` for a bead ``bd``
reported CLOSED. The table writes the SHORT id (``.22``); the injected keys are
full ids (``beadloom-mr2l.22``); the lookup compared them as whole strings and so
matched nothing at all. The mechanism built (BDL-053) so the table would not need
manual discipline had been inert on the repository that authored it.

Two properties are pinned here, because fixing only the first would leave the
second failure available: a short row id RESOLVES, and a run that resolved
nothing SAYS SO instead of reading like a clean one.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING
from unittest.mock import patch

from click.testing import CliRunner

from beadloom.application.active_table import (
    SHAPE_AMBIGUOUS,
    SHAPE_UNKNOWN_TO_TRACKER,
    SHAPE_WITH_TEXT,
    reconcile_active_tables,
    resolve_row_bead_id,
    set_active_table_status,
)
from beadloom.services.bd_seam import BdResult
from beadloom.services.cli import main

if TYPE_CHECKING:
    from pathlib import Path


def _features_dir(root: Path, epic: str) -> Path:
    directory = root / ".claude" / "development" / "docs" / "features" / epic
    directory.mkdir(parents=True, exist_ok=True)
    return directory


# --------------------------------------------------------------------------- #
# The resolver: one row cell, one bead id or one stated reason
# --------------------------------------------------------------------------- #


class TestResolvingTheFormTheTableIsWrittenIn:
    """``.22`` and ``beadloom-mr2l.22`` are the same bead written two ways."""

    def test_a_full_id_resolves_to_itself(self) -> None:
        row = resolve_row_bead_id("proj-x.22", {"proj-x.22": "closed"})

        assert (row.bead_id, row.reason) == ("proj-x.22", None)

    def test_a_short_id_resolves_against_the_only_prefix_the_tracker_uses(self) -> None:
        row = resolve_row_bead_id(".22", {"proj-x.22": "closed"})

        assert (row.bead_id, row.reason) == ("proj-x.22", None)

    def test_a_short_id_matches_its_whole_number_and_not_a_longer_one(self) -> None:
        """``.2`` is not ``.22``. A suffix compared as text is the same defect again."""
        row = resolve_row_bead_id(".2", {"proj-x.22": "closed"})

        assert row.bead_id is None
        assert row.reason is not None
        assert ".2" in row.reason
        assert row.shape == SHAPE_UNKNOWN_TO_TRACKER

    def test_two_prefixes_carrying_the_same_number_are_ambiguous_not_guessed(self) -> None:
        row = resolve_row_bead_id(".22", {"proj-x.22": "closed", "proj-y.22": "open"})

        assert row.bead_id is None
        assert row.reason is not None
        assert "proj-x.22" in row.reason
        assert "proj-y.22" in row.reason
        assert row.shape == SHAPE_AMBIGUOUS

    def test_a_cell_that_is_not_a_bead_id_says_that_rather_than_nothing(self) -> None:
        """A first cell carrying a title (``.1 Contract model``) is a real shape here."""
        row = resolve_row_bead_id(".1 Contract model", {"proj-x.1": "closed"})

        assert row.bead_id is None
        assert row.reason is not None
        assert row.shape == SHAPE_WITH_TEXT


# --------------------------------------------------------------------------- #
# The reconcile itself
# --------------------------------------------------------------------------- #


class TestTheReconcileReadsTheTableThisProjectWrites:
    def test_a_short_row_id_is_reconciled_against_a_full_bd_id(self, tmp_path: Path) -> None:
        """The measured defect, in the shape it was measured in."""
        active = _features_dir(tmp_path, "BDL-061") / "ACTIVE.md"
        active.write_text(
            "| Bead | Status | Details |\n"
            "| --- | --- | --- |\n"
            "| .22 | In progress | the guide |\n",
            encoding="utf-8",
        )

        result = reconcile_active_tables(
            tmp_path, {"beadloom-mr2l.22": "closed"}, epic="BDL-061"
        )

        assert active in result.changed_files
        assert "| .22 | ✓ done | the guide |" in active.read_text(encoding="utf-8")
        assert [row[1] for row in result.drifted_rows] == ["beadloom-mr2l.22"]

    def test_a_state_written_without_its_decoration_is_not_drift(self, tmp_path: Path) -> None:
        """``Done`` and ``✓ done`` are one state in two spellings.

        Measured on BDL-061's own ACTIVE.md: 78 of its 79 rows read ``Done`` for a
        closed bead. A reconcile whose first working run rewrites 78 rows to add a
        checkmark is a reconcile that gets switched off, and the module's stated
        contract is already that a richer cell is preserved when the STATE agrees.
        """
        active = _features_dir(tmp_path, "BDL-007") / "ACTIVE.md"
        active.write_text(
            "| Bead | Status |\n| --- | --- |\n| .1 | Done |\n| .2 | **DONE** (a1b2c3d) |\n",
            encoding="utf-8",
        )

        result = reconcile_active_tables(
            tmp_path, {"proj.1": "closed", "proj.2": "closed"}, epic="BDL-007"
        )

        assert result.drifted_rows == []
        assert result.changed_files == []

    def test_an_unresolvable_row_is_recorded_with_its_reason(self, tmp_path: Path) -> None:
        active = _features_dir(tmp_path, "BDL-008") / "ACTIVE.md"
        active.write_text(
            "| Bead | Status |\n| --- | --- |\n| .1 Contract model | open |\n",
            encoding="utf-8",
        )

        result = reconcile_active_tables(tmp_path, {"proj.1": "closed"}, epic="BDL-008")

        assert result.rows_read == 1
        assert result.rows_resolved == 0
        assert [row.cell for row in result.unresolved_rows] == [".1 Contract model"]

    def test_the_counts_are_of_rows_read_not_of_rows_that_drifted(self, tmp_path: Path) -> None:
        active = _features_dir(tmp_path, "BDL-009") / "ACTIVE.md"
        active.write_text(
            "| Bead | Status |\n| --- | --- |\n| .1 | ready |\n| .2 | ✓ done |\n",
            encoding="utf-8",
        )

        result = reconcile_active_tables(
            tmp_path, {"proj.1": "closed", "proj.2": "closed"}, epic="BDL-009"
        )

        assert (result.rows_read, result.rows_resolved) == (2, 2)
        assert len(result.drifted_rows) == 1


class TestAShortIdIsReadAgainstItsOwnEpic:
    """A number alone is not a bead: this repository holds eight beads ``.17``.

    Measured while fixing the id-form defect. With the lookup repaired but the
    scope left global, BDL-061's ``.17`` to ``.24`` rows resolved to
    ``beadloom-8qqp.17`` to ``.24`` — another epic entirely — and eight rows of one
    epic's table would have been rewritten from another's tracker state.
    """

    def test_the_epic_prefix_decides_which_of_two_beads_a_row_names(self) -> None:
        statuses = {"proj-a.17": "closed", "proj-b.17": "open"}

        row = resolve_row_bead_id(".17", statuses, prefix="proj-a")

        assert (row.bead_id, row.reason) == ("proj-a.17", None)

    def test_a_number_the_epic_does_not_have_is_not_borrowed_from_another(self) -> None:
        statuses = {"proj-b.17": "open"}

        row = resolve_row_bead_id(".17", statuses, prefix="proj-a")

        assert row.bead_id is None
        assert row.reason is not None
        assert "proj-a.17" in row.reason

    def test_the_reconcile_scopes_each_file_to_its_own_epic(self, tmp_path: Path) -> None:
        active = _features_dir(tmp_path, "BDL-061") / "ACTIVE.md"
        active.write_text(
            "| Bead | Status |\n| --- | --- |\n| .17 | Pending |\n", encoding="utf-8"
        )

        result = reconcile_active_tables(
            tmp_path,
            {"beadloom-mr2l.17": "closed", "beadloom-8qqp.17": "open"},
            epic="BDL-061",
            epic_prefixes={"BDL-061": "beadloom-mr2l"},
        )

        assert [row[1] for row in result.drifted_rows] == ["beadloom-mr2l.17"]
        assert "| .17 | ✓ done |" in active.read_text(encoding="utf-8")


class TestTheTrackerViewTheReconcileReads:
    """``bd list --json`` is not the tracker: it is 41 of this repository's 709 beads.

    Measured 2026-08-25. The default view excludes closed beads and caps the
    result at 50 rows, so the reconcile could never write ``✓ done`` — the exact
    correction BDL-061.84 was filed for — and every short id it resolved was
    resolved against a view with most of the tracker missing from it.
    """

    def test_the_query_asks_for_the_whole_tracker(self, tmp_path: Path) -> None:
        from beadloom.services.commands.docsync import _query_bd_beads

        with patch(
            "beadloom.services.bd_seam.run_bd", return_value=_bd_ok([])
        ) as run_bd:
            _query_bd_beads(tmp_path)

        argv = run_bd.call_args.args[0]
        assert "--all" in argv, "closed beads are missing, so ✓ done can never be written"
        assert argv[argv.index("-n") + 1] == "0", "the default 50-row cap truncates the tracker"

    def test_an_epic_bead_maps_its_directory_key_onto_its_tracker_id(self) -> None:
        from beadloom.services.commands.docsync import _bd_epic_prefixes

        beads: list[dict[str, object]] = [
            {"id": "beadloom-mr2l", "issue_type": "epic", "title": "[BDL-061] Enforced flow"},
            {"id": "beadloom-mr2l.1", "issue_type": "task", "title": "[BDL-061] a bead"},
        ]

        assert _bd_epic_prefixes(beads) == {"BDL-061": "beadloom-mr2l"}


class TestTheScanReachesTheBeadStatusTable:
    """A ``Bead``-headed table with no Status column is not the end of the file.

    Measured on BDL-061's own ACTIVE.md while fixing the id-form defect: the
    document carries a ``| Bead | What it is | Why it was not done here |`` table
    at line 203 and the real bead-status table at line 683, and the scan gave up
    at the first one — so ``_find_status_column`` returned ``None`` and the file
    was skipped whole. Fixing the lookup alone would have left the mechanism just
    as inert on the repository that authored it.
    """

    def test_a_second_bead_headed_table_is_still_searched(self, tmp_path: Path) -> None:
        active = _features_dir(tmp_path, "BDL-013") / "ACTIVE.md"
        active.write_text(
            "| Bead | What it is | Why not |\n"
            "| --- | --- | --- |\n"
            "| .9 | a deferral | scoped out |\n"
            "\n"
            "| Bead | Status | Details |\n"
            "| --- | --- | --- |\n"
            "| .1 | In progress | the guide |\n",
            encoding="utf-8",
        )

        result = reconcile_active_tables(tmp_path, {"proj.1": "closed"}, epic="BDL-013")

        assert active in result.changed_files
        assert "| .1 | ✓ done | the guide |" in active.read_text(encoding="utf-8")
        assert "| .9 | a deferral | scoped out |" in active.read_text(encoding="utf-8")


class TestTheOtherLookupWithTheSameBlindSpot:
    """``set_active_table_status`` compares the same two forms the same way.

    The sweep BDL-061.84 asks for: the id-form mismatch appears once more, in this
    module, and reaches the MCP ``checkpoint`` / ``complete_bead`` tools, which
    pass the full id ``bd`` gave them into a table written in short form.
    """

    def test_a_full_bead_id_finds_the_short_row_it_names(self, tmp_path: Path) -> None:
        active = tmp_path / "ACTIVE.md"
        active.write_text(
            "| Bead | Status |\n| --- | --- |\n| .22 | ready |\n", encoding="utf-8"
        )

        assert set_active_table_status(active, "beadloom-mr2l.22", "in progress") is True
        assert "| .22 | in progress |" in active.read_text(encoding="utf-8")

    def test_a_short_row_is_still_not_matched_by_a_different_number(self, tmp_path: Path) -> None:
        active = tmp_path / "ACTIVE.md"
        active.write_text(
            "| Bead | Status |\n| --- | --- |\n| .2 | ready |\n", encoding="utf-8"
        )

        assert set_active_table_status(active, "beadloom-mr2l.22", "in progress") is False
        assert "| .2 | ready |" in active.read_text(encoding="utf-8")


# --------------------------------------------------------------------------- #
# What the command says about a run that compared nothing
# --------------------------------------------------------------------------- #


def _bd_ok(payload: list[dict[str, object]]) -> BdResult:
    return BdResult(returncode=0, stdout=json.dumps(payload), stderr="")


class TestAnInertRunDoesNotReadLikeACleanOne:
    """'already coherent' over zero compared rows is the defect, not the report."""

    def test_check_reports_the_fraction_it_resolved(self, tmp_path: Path) -> None:
        _features_dir(tmp_path, "BDL-010").joinpath("ACTIVE.md").write_text(
            "| Bead | Status |\n| --- | --- |\n| .1 | ✓ done |\n| .2 | ✓ done |\n",
            encoding="utf-8",
        )
        beads: list[dict[str, object]] = [
            {"id": "proj.1", "status": "closed"},
            {"id": "proj.2", "status": "closed"},
        ]

        with patch("beadloom.services.bd_seam.run_bd", return_value=_bd_ok(beads)):
            result = CliRunner().invoke(
                main, ["active-sync", "--check", "--project", str(tmp_path)]
            )

        assert result.exit_code == 0
        assert "2 of 2" in result.output

    def test_a_run_that_resolved_no_row_exits_nonzero(self, tmp_path: Path) -> None:
        _features_dir(tmp_path, "BDL-011").joinpath("ACTIVE.md").write_text(
            "| Bead | Status |\n| --- | --- |\n| .1 Contract model | open |\n",
            encoding="utf-8",
        )
        beads: list[dict[str, object]] = [{"id": "proj.1", "status": "closed"}]

        with patch("beadloom.services.bd_seam.run_bd", return_value=_bd_ok(beads)):
            result = CliRunner().invoke(
                main, ["active-sync", "--check", "--project", str(tmp_path)]
            )

        assert result.exit_code == 1
        assert "already coherent" not in result.output

    def test_the_json_carries_the_denominator(self, tmp_path: Path) -> None:
        _features_dir(tmp_path, "BDL-012").joinpath("ACTIVE.md").write_text(
            "| Bead | Status |\n| --- | --- |\n| .1 | ✓ done |\n| .9 Something | open |\n",
            encoding="utf-8",
        )
        beads: list[dict[str, object]] = [{"id": "proj.1", "status": "closed"}]

        with patch("beadloom.services.bd_seam.run_bd", return_value=_bd_ok(beads)):
            result = CliRunner().invoke(
                main, ["active-sync", "--check", "--json", "--project", str(tmp_path)]
            )

        payload = json.loads(result.stdout)
        assert payload["rows_read"] == 2
        assert payload["rows_resolved"] == 1
        assert payload["unresolved_rows"][0]["cell"] == ".9 Something"
        assert payload["unresolved_rows"][0]["reason"]
