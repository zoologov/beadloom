"""A bead a row NAMES is not a bead the table has no row for (BDL-068 S5, Major 1).

The reconcile filled ``seen`` only from rows that RESOLVED, so every row it could
not read handed its bead to the "no row in their epic's table" report. One run
then made two statements about the same row: it printed the cell under
``bead-and-text`` or ``more-than-one-bead``, and printed the bead the cell names
as having no row at all. A reader acting on the second adds a row that is there.

MEASURED ON THIS REPOSITORY with ``uv run beadloom active-sync --check --json``,
Darwin 25.6.0 arm64 / CPython 3.13.7, in the foreground:

    at 27db92b (before)   79 beads reported as carried by no row
    of those 79           38 have a row whose first cell's head is that bead's id
                          (36 ``bead-and-text``, 2 ``more-than-one-bead``),
                          derived by running the two shape regexes over the
                          unresolved rows of the same file
    after                 41 carried by no row, 38 named by a row this run
                          could not read

The 38 do not vanish into ``seen``. Folding them there would leave 38 beads in no
number the run prints, and a population that stops being stated is the defect one
level up from the one being fixed. They are stated as their own population, with
the remedy their shape already carries.

A RANGE IS NOT EXPANDED. ``proj-e.3..8`` names ``proj-e.3``, which is the id the
shape itself extracted; the beads between the endpoints are ids the table does
not write, and inferring them would be a guess. They stay in "carried by no row",
which is what the range's own remedy — give each bead its own row — asks for.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING
from unittest.mock import patch

from click.testing import CliRunner

from beadloom.application.active_table import (
    SHAPE_NO_ID,
    SHAPE_RANGE,
    SHAPE_WITH_TEXT,
    reconcile_active_tables,
    resolve_row_bead_id,
)
from beadloom.services.bd_seam import BdResult
from beadloom.services.cli import main

if TYPE_CHECKING:
    from pathlib import Path

_STATUSES = {"proj-e.1": "closed", "proj-e.3": "closed", "proj-e.8": "closed"}


def _table(tmp_path: Path, cells: str, *, epic: str = "E") -> Path:
    """An ACTIVE.md under *epic*'s document directory carrying *cells* as rows."""
    directory = tmp_path / ".claude" / "development" / "docs" / "features" / epic
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "ACTIVE.md"
    path.write_text(f"| Bead | Status |\n| --- | --- |\n{cells}", encoding="utf-8")
    return path


# --------------------------------------------------------------------------- #
# The id the shape already found, kept instead of thrown away
# --------------------------------------------------------------------------- #


class TestAnUnresolvedRowStillSaysWhichBeadItNames:
    """Both offending shapes extract an id for their message and discarded it."""

    def test_an_id_followed_by_a_title_names_its_bead(self) -> None:
        row = resolve_row_bead_id(".1 Contract model", _STATUSES, prefix="proj-e")

        assert row.bead_id is None
        assert row.shape == SHAPE_WITH_TEXT
        assert row.names == "proj-e.1"

    def test_a_range_names_the_bead_its_first_id_is(self) -> None:
        row = resolve_row_bead_id(".3-.8", _STATUSES, prefix="proj-e")

        assert row.bead_id is None
        assert row.shape == SHAPE_RANGE
        assert row.names == "proj-e.3"

    def test_a_full_id_at_the_head_of_a_range_names_its_bead(self) -> None:
        row = resolve_row_bead_id("proj-e.3..8", _STATUSES, prefix="proj-e")

        assert row.names == "proj-e.3"

    def test_a_head_the_tracker_never_reported_names_nothing(self) -> None:
        """There is no bead to subtract, so claiming one would invent a population."""
        row = resolve_row_bead_id(".99 something", _STATUSES, prefix="proj-e")

        assert row.names is None

    def test_a_cell_with_no_id_in_it_names_nothing(self) -> None:
        row = resolve_row_bead_id("BEAD-01", _STATUSES, prefix="proj-e")

        assert row.shape == SHAPE_NO_ID
        assert row.names is None

    def test_a_head_read_against_the_whole_tracker_names_its_bead(self) -> None:
        """Without an epic the number must be unique in the tracker, as everywhere."""
        row = resolve_row_bead_id(".1 Contract model", _STATUSES)

        assert row.names == "proj-e.1"

    def test_an_ambiguous_head_names_nothing(self) -> None:
        row = resolve_row_bead_id(
            ".1 Contract model", {"proj-e.1": "closed", "proj-f.1": "closed"}
        )

        assert row.names is None

    def test_a_row_that_resolves_names_the_bead_it_resolved_to(self) -> None:
        row = resolve_row_bead_id("`.1`", _STATUSES, prefix="proj-e")

        assert row.bead_id == "proj-e.1"
        assert row.names is None


# --------------------------------------------------------------------------- #
# Two populations, and no bead in both
# --------------------------------------------------------------------------- #


class TestTheTwoPopulationsAreReportedSeparately:
    def test_a_bead_a_row_names_is_not_reported_as_having_no_row(
        self, tmp_path: Path
    ) -> None:
        _table(tmp_path, "| .1 Contract model | ✓ done |\n")

        result = reconcile_active_tables(
            tmp_path, dict(_STATUSES), epic_prefixes={"E": "proj-e"}
        )

        assert [bead for _, bead in result.unlisted_beads] == ["proj-e.3", "proj-e.8"]

    def test_it_is_reported_as_a_row_this_run_could_not_read(
        self, tmp_path: Path
    ) -> None:
        path = _table(tmp_path, "| .1 Contract model | ✓ done |\n")

        result = reconcile_active_tables(
            tmp_path, dict(_STATUSES), epic_prefixes={"E": "proj-e"}
        )

        assert result.beads_named_by_an_unresolved_row == [
            (path, "proj-e.1", ".1 Contract model")
        ]

    def test_no_bead_is_in_both_populations(self, tmp_path: Path) -> None:
        _table(tmp_path, "| .1 Contract model | ✓ done |\n| .3-.8 | ✓ done |\n")

        result = reconcile_active_tables(
            tmp_path, dict(_STATUSES), epic_prefixes={"E": "proj-e"}
        )

        unlisted = {bead for _, bead in result.unlisted_beads}
        named = {bead for _, bead, _ in result.beads_named_by_an_unresolved_row}
        assert unlisted & named == set()
        assert unlisted == {"proj-e.8"}
        assert named == {"proj-e.1", "proj-e.3"}

    def test_a_bead_whose_row_resolved_is_in_neither(self, tmp_path: Path) -> None:
        _table(tmp_path, "| `.1` | ✓ done |\n")

        result = reconcile_active_tables(
            tmp_path, {"proj-e.1": "closed"}, epic_prefixes={"E": "proj-e"}
        )

        assert result.unlisted_beads == []
        assert result.beads_named_by_an_unresolved_row == []

    def test_a_bead_one_row_resolves_and_another_names_is_in_neither(
        self, tmp_path: Path
    ) -> None:
        """The reconcile compared it, so neither report has anything to say."""
        _table(tmp_path, "| `.1` | ✓ done |\n| .1 Contract model | ✓ done |\n")

        result = reconcile_active_tables(
            tmp_path, {"proj-e.1": "closed"}, epic_prefixes={"E": "proj-e"}
        )

        assert result.unlisted_beads == []
        assert result.beads_named_by_an_unresolved_row == []
        assert result.unresolved_by_shape == {SHAPE_WITH_TEXT: 1}

    def test_the_named_beads_run_in_the_order_their_numbers_do(
        self, tmp_path: Path
    ) -> None:
        """``.9`` before ``.10``, like every other bead-keyed list here."""
        _table(
            tmp_path,
            "| .10 the title | ✓ done |\n| .9 the title | ✓ done |\n",
        )

        result = reconcile_active_tables(
            tmp_path,
            {"proj-e.9": "closed", "proj-e.10": "closed"},
            epic_prefixes={"E": "proj-e"},
        )

        assert [bead for _, bead, _ in result.beads_named_by_an_unresolved_row] == [
            "proj-e.9",
            "proj-e.10",
        ]

    def test_without_a_known_epic_neither_population_is_computed(
        self, tmp_path: Path
    ) -> None:
        """There is no population to subtract from, so neither report is a wall."""
        _table(tmp_path, "| .1 Contract model | ✓ done |\n")

        result = reconcile_active_tables(tmp_path, dict(_STATUSES))

        assert result.unlisted_beads == []
        assert result.beads_named_by_an_unresolved_row == []

    def test_the_unresolved_row_is_still_reported_with_its_own_remedy(
        self, tmp_path: Path
    ) -> None:
        """The row keeps its shape and its reason: nothing stopped being reported."""
        _table(tmp_path, "| .1 Contract model | ✓ done |\n")

        result = reconcile_active_tables(
            tmp_path, dict(_STATUSES), epic_prefixes={"E": "proj-e"}
        )

        assert result.unresolved_by_shape == {SHAPE_WITH_TEXT: 1}
        assert "move the title into a column of its own" in (
            result.unresolved_rows[0].reason
        )

    def test_no_row_is_written_into_the_table(self, tmp_path: Path) -> None:
        path = _table(tmp_path, "| .1 Contract model | ✓ done |\n")
        before = path.read_text(encoding="utf-8")

        reconcile_active_tables(
            tmp_path, dict(_STATUSES), epic_prefixes={"E": "proj-e"}
        )

        assert path.read_text(encoding="utf-8") == before


# --------------------------------------------------------------------------- #
# The report a reader sees
# --------------------------------------------------------------------------- #


def _bd_result(payload: list[dict[str, object]]) -> BdResult:
    return BdResult(returncode=0, stdout=json.dumps(payload), stderr="")


_BEADS: list[dict[str, object]] = [
    {"id": "proj-e", "title": "[E] the epic", "issue_type": "epic", "dependencies": []},
    {"id": "proj-e.1", "title": "one", "status": "closed", "dependencies": []},
    {"id": "proj-e.2", "title": "two", "status": "closed", "dependencies": []},
    {"id": "proj-e.3", "title": "three", "status": "closed", "dependencies": []},
]

#: A table with one row that resolves and one that names a bead without resolving.
#: The resolving row matters: a run that resolves NOTHING is `is_inert` and takes a
#: branch of its own, so a table of only unreadable rows would test that branch
#: instead of this one.
_ONE_OF_EACH = "| `.1` | ✓ done |\n| .2 the title | ✓ done |\n"


def _run(tmp_path: Path, *args: str) -> str:
    with patch(
        "beadloom.services.bd_seam.run_bd", return_value=_bd_result(_BEADS)
    ):
        result = CliRunner().invoke(
            main, ["active-sync", "--check", "--project", str(tmp_path), *args]
        )
    return result.stdout


class TestTheCommandStatesBothPopulations:
    def test_the_json_carries_the_beads_a_row_names(self, tmp_path: Path) -> None:
        _table(tmp_path, _ONE_OF_EACH)

        payload = json.loads(_run(tmp_path, "--json"))

        active = str(tmp_path / ".claude/development/docs/features/E/ACTIVE.md")
        assert payload["beads_named_by_an_unresolved_row"] == [
            {"path": active, "bead_id": "proj-e.2", "cell": ".2 the title"}
        ]
        assert payload["unlisted_beads"] == [{"path": active, "bead_id": "proj-e.3"}]

    def test_check_mode_names_the_real_file_and_not_its_throwaway_copy(
        self, tmp_path: Path
    ) -> None:
        """`--check` reconciles a temporary copy, and a population it forgets to
        rebase names a path inside a directory deleted before the report prints."""
        _table(tmp_path, "| .1 Contract model | ✓ done |\n")

        payload = json.loads(_run(tmp_path, "--json"))

        reported = payload["beads_named_by_an_unresolved_row"][0]["path"]
        assert reported == str(
            tmp_path / ".claude/development/docs/features/E/ACTIVE.md"
        )

    def test_the_human_report_says_which_of_the_two_it_is(self, tmp_path: Path) -> None:
        _table(tmp_path, _ONE_OF_EACH)

        output = _run(tmp_path)

        assert "1 bead(s) the tracker holds have a row this run could not read" in output
        assert "1 bead(s) the tracker holds have no row in their epic's table" in output
        assert "proj-e.2: the row '.2 the title' names it" in output
        assert "proj-e.3" in output

    def test_an_inert_run_prints_neither_of_them(self, tmp_path: Path) -> None:
        """A run that resolved NO row compared nothing, and says that instead.

        Both lists are computed and both are in `--json`; the human inert branch
        prints the rows it could not read and stops, because on a table it read
        none of, a per-bead list is a restatement of the same fact once per bead.
        This is BDL-061.84's branch and this bead does not move it.
        """
        _table(tmp_path, "| .2 the title | ✓ done |\n")

        output = _run(tmp_path)

        assert "resolved NONE against bd" in output
        assert "could not read:" not in output
        assert "no row in their epic's table" not in output

    def test_neither_sentence_is_printed_when_it_has_no_population(
        self, tmp_path: Path
    ) -> None:
        _table(tmp_path, "| `.1` | ✓ done |\n| `.2` | ✓ done |\n| `.3` | ✓ done |\n")

        output = _run(tmp_path)

        assert "resolved 3 of 3 row(s) read." in output
        assert "could not read" not in output
        assert "no row in their epic's table" not in output
