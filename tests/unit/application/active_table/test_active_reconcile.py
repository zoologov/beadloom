"""The reconcile's reading and the reconcile's staging (BDL-068 S5, #210 and #207).

Two defects that are entirely ours, fixed together because whoever holds
``active-sync`` in their head meets both: one reads the STAGE and decides for the
agent, the other reads the TABLE and cannot see what is plainly there.

MEASURED ON THIS REPOSITORY, before and after, with ``beadloom active-sync
--check --json`` at ``5846b20``, macOS 26.6.2 arm64 / CPython 3.13.7:

    rows read   329  ->  329
    resolved    211  ->  238
    unresolved  118  ->   91, as 38 bead-and-text, 50 no-bead-id, 3 range
    rewritten     0  ->    0

The 27 rows the fix gained are BDL-067's whole table, every id of which is
written as a Markdown code span. Nothing was rewritten in either run, which is
the honest outcome: those rows already said what the tracker says. What changed
is that the mechanism now knows it, and that the 91 it still cannot read are
named as three different faults instead of one.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from beadloom.application.active_table import (
    SHAPE_NO_ID,
    SHAPE_RANGE,
    SHAPE_UNKNOWN_TO_TRACKER,
    SHAPE_WITH_TEXT,
    SHAPES,
    decide_staging,
    reconcile_active_tables,
    resolve_row_bead_id,
    stageable,
    undecorate,
)
from beadloom.services.bd_seam import BdResult
from beadloom.services.cli import main
from beadloom.services.commands.docsync import pre_commit_hook_body

if TYPE_CHECKING:
    from pathlib import Path


# --------------------------------------------------------------------------- #
# #210 — the id a cell names, under whatever a document wrapped it in
# --------------------------------------------------------------------------- #


class TestDecorationIsNotAFactAboutTheBead:
    """A cell is text in a document before it is a key in a lookup."""

    @pytest.mark.parametrize(
        "cell",
        [
            "`beadloom-e8s4.1`",
            "``beadloom-e8s4.1``",
            "**beadloom-e8s4.1**",
            "*beadloom-e8s4.1*",
            "  `beadloom-e8s4.1`  ",
            "[beadloom-e8s4.1](https://example.test/x)",
            "`[beadloom-e8s4.1](https://example.test/x)`",
        ],
    )
    def test_every_way_a_markdown_table_writes_one_id_reads_as_that_id(
        self, cell: str
    ) -> None:
        assert undecorate(cell) == "beadloom-e8s4.1"

    def test_an_underscore_is_left_alone_because_a_tracker_id_can_contain_one(
        self,
    ) -> None:
        """The stripped set is two characters, and the reason is a false positive.

        Emphasis with underscores is real Markdown, and so is an underscore in a
        tracker id. Stripping ``_`` to read ``_.22_`` would silently corrupt
        ``proj_x.22``, which is the worse of the two failures.
        """
        assert undecorate("proj_x.22") == "proj_x.22"

    def test_a_code_spanned_full_id_resolves(self) -> None:
        row = resolve_row_bead_id("`proj-x.10`", {"proj-x.10": "closed"})

        assert (row.bead_id, row.shape) == ("proj-x.10", None)

    def test_a_code_spanned_short_id_resolves_against_its_epic(self) -> None:
        row = resolve_row_bead_id("`.10`", {"proj-x.10": "closed"}, prefix="proj-x")

        assert row.bead_id == "proj-x.10"


class TestARowThatDidNotResolveSaysWhichOfFourThingsItWas:
    """One sentence over four populations is the defect this epic keeps removing."""

    @pytest.mark.parametrize(
        ("cell", "shape"),
        [
            ("BEAD-01", SHAPE_NO_ID),
            ("01", SHAPE_NO_ID),
            ("b0xl", SHAPE_NO_ID),
            (".7 review", SHAPE_WITH_TEXT),
            (".1 Contract model + protocol-aware contract_key", SHAPE_WITH_TEXT),
            ("`.2` `.github/workflows/deploy-site.yml` (Pages deploy)", SHAPE_WITH_TEXT),
            (".73\u2013.76", SHAPE_RANGE),  # an en dash, spelled so ruff can tell
            (".81-.82", SHAPE_RANGE),
            ("proj-x.3..8", SHAPE_RANGE),
        ],
    )
    def test_the_shape_is_the_one_the_cell_actually_has(
        self, cell: str, shape: str
    ) -> None:
        row = resolve_row_bead_id(cell, {"proj-x.7": "closed"}, prefix="proj-x")

        assert row.bead_id is None
        assert row.shape == shape

    def test_a_range_is_judged_before_an_id_with_text_because_it_has_an_id_head(
        self,
    ) -> None:
        """``proj-x.3..8`` would match the id-and-text shape if the order flipped."""
        assert resolve_row_bead_id("proj-x.3..8", {}).shape == SHAPE_RANGE

    def test_the_id_with_text_reason_names_the_id_and_the_remedy(self) -> None:
        row = resolve_row_bead_id(".7 review", {"proj-x.7": "closed"}, prefix="proj-x")

        assert row.reason is not None
        assert "`.7`" in row.reason
        assert "column of its own" in row.reason

    def test_an_id_with_text_is_deliberately_not_resolved_to_its_head(self) -> None:
        """The whole cell is the row's id, and that decision is not overturned here.

        Reading ``.1 Contract model`` as the bead ``.1`` would resolve about fifty
        rows of this repository's finished epics and rewrite their status cells
        inside an unrelated commit. The shape is reported so the next decision is
        taken on a number rather than on a guess.
        """
        row = resolve_row_bead_id(".1 Contract model", {"proj-x.1": "closed"}, prefix="proj-x")

        assert row.bead_id is None

    def test_a_tracker_that_does_not_hold_the_id_is_not_the_cell_s_fault(self) -> None:
        row = resolve_row_bead_id("`.99`", {"proj-x.7": "closed"}, prefix="proj-x")

        assert row.shape == SHAPE_UNKNOWN_TO_TRACKER
        assert row.reason is not None
        assert "tracker" in row.reason

    def test_every_declared_shape_is_a_shape_the_resolver_can_produce(self) -> None:
        """A vocabulary with a member nothing emits is a list that reads as coverage."""
        produced = {
            resolve_row_bead_id(cell, statuses, prefix=prefix).shape
            for cell, statuses, prefix in [
                ("BEAD-01", {}, None),
                (".7 review", {}, None),
                (".73\u2013.76", {}, None),
                (".99", {"proj-x.7": "closed"}, "proj-x"),
                (".22", {"proj-x.22": "c", "proj-y.22": "c"}, None),
            ]
        }

        assert produced == set(SHAPES)


class TestTheCountsAreOfShapesAndNotOfATotal:
    def test_a_run_counts_each_shape_it_could_not_read(self, tmp_path: Path) -> None:
        directory = tmp_path / ".claude" / "development" / "docs" / "features" / "E"
        directory.mkdir(parents=True)
        (directory / "ACTIVE.md").write_text(
            "| Bead | Status |\n| --- | --- |\n"
            "| `.1` | ✓ done |\n| .2 the title | ✓ done |\n"
            "| BEAD-01 | ✓ done |\n| .3-.4 | ✓ done |\n",
            encoding="utf-8",
        )

        result = reconcile_active_tables(
            tmp_path,
            {f"proj-e.{n}": "closed" for n in (1, 2, 3, 4)},
            epic_prefixes={"E": "proj-e"},
        )

        assert result.rows_resolved == 1
        assert result.unresolved_by_shape == {
            SHAPE_WITH_TEXT: 1,
            SHAPE_NO_ID: 1,
            SHAPE_RANGE: 1,
        }


class TestABeadWithNoRowIsDriftTheReconcileCannotCorrect:
    """The other half of what `beadloom-viaj.8` reported: rows that are not there."""

    def _table(self, tmp_path: Path, cells: str) -> Path:
        directory = tmp_path / ".claude" / "development" / "docs" / "features" / "E"
        directory.mkdir(parents=True)
        path = directory / "ACTIVE.md"
        path.write_text(f"| Bead | Status |\n| --- | --- |\n{cells}", encoding="utf-8")
        return path

    def test_the_epic_s_missing_beads_are_named(self, tmp_path: Path) -> None:
        self._table(tmp_path, "| `.1` | ✓ done |\n")

        result = reconcile_active_tables(
            tmp_path,
            {"proj-e.1": "closed", "proj-e.2": "closed"},
            epic_prefixes={"E": "proj-e"},
        )

        expected = tmp_path / ".claude/development/docs/features/E/ACTIVE.md"
        assert result.unlisted_beads == [(expected, "proj-e.2")]

    def test_they_are_named_in_the_order_their_numbers_run(self, tmp_path: Path) -> None:
        """``.9`` before ``.10``: sorted as text they come out the other way."""
        self._table(tmp_path, "| .1 | ✓ done |\n")

        result = reconcile_active_tables(
            tmp_path,
            {"proj-e.1": "closed", "proj-e.9": "closed", "proj-e.10": "closed"},
            epic_prefixes={"E": "proj-e"},
        )

        assert [bead for _, bead in result.unlisted_beads] == ["proj-e.9", "proj-e.10"]

    def test_no_row_is_ever_written_into_the_table(self, tmp_path: Path) -> None:
        path = self._table(tmp_path, "| `.1` | ✓ done |\n")
        before = path.read_text(encoding="utf-8")

        reconcile_active_tables(
            tmp_path,
            {"proj-e.1": "closed", "proj-e.2": "closed"},
            epic_prefixes={"E": "proj-e"},
        )

        assert path.read_text(encoding="utf-8") == before

    def test_without_a_known_epic_nothing_is_called_unlisted(self, tmp_path: Path) -> None:
        """There is no population to subtract from, so a wall of names is not printed."""
        self._table(tmp_path, "| proj-e.1 | ✓ done |\n")

        result = reconcile_active_tables(
            tmp_path, {"proj-e.1": "closed", "proj-e.2": "closed"}
        )

        assert result.unlisted_beads == []


# --------------------------------------------------------------------------- #
# #207 — the staging decision
# --------------------------------------------------------------------------- #


class TestTheCommitsOwnScopeDecidesWhatIsStaged:
    def test_a_path_the_commit_carries_is_staged(self) -> None:
        decision = decide_staging(["a", "b"], frozenset({"a"}))

        assert decision.staged == ("a",)
        assert decision.withheld == ("b",)

    def test_an_unreadable_scope_stages_nothing_and_says_which_it_was(self) -> None:
        """A scope that could not be read is not an empty one."""
        unreadable = decide_staging(["a"], None)
        empty = decide_staging(["a"], frozenset())

        assert unreadable.staged == empty.staged == ()
        assert unreadable.scope_unreadable is True
        assert empty.scope_unreadable is False
        assert "could not be read" in unreadable.stated
        assert "could not be read" not in empty.stated

    def test_the_order_a_caller_gave_is_the_order_reported(self) -> None:
        decision = decide_staging(["z", "a", "m"], frozenset())

        assert decision.withheld == ("z", "a", "m")

    def test_nothing_withheld_reads_differently_from_something_withheld(self) -> None:
        assert "withheld" not in decide_staging(["a"], frozenset({"a"})).stated
        assert "withheld" in decide_staging(["a"], frozenset()).stated


class TestNothingIsSaidAboutAPathStagingWouldNotChange:
    """The noise question, answered before the hook shipped.

    `bd export` rewrites `.beads/issues.jsonl` on every commit whether the tracker
    moved or not, so a candidate list built from "what the reconcile touched"
    would name it every time. A hook that prints a line on every commit is a hook
    that is off within a day.
    """

    def test_a_candidate_the_index_already_matches_is_not_a_candidate(self) -> None:
        assert stageable([".beads/issues.jsonl"], frozenset()) == ()

    def test_a_candidate_the_index_has_not_taken_stays_one(self) -> None:
        assert stageable([".beads/issues.jsonl"], frozenset({".beads/issues.jsonl"})) == (
            ".beads/issues.jsonl",
        )

    def test_an_unknown_pending_set_keeps_every_candidate(self) -> None:
        """A set that could not be read is not an empty one."""
        assert stageable(["a", "b"], None) == ("a", "b")


class TestTheShippedHookTakesNoStagingDecision:
    @pytest.mark.parametrize("blocking", [True, False])
    def test_it_runs_no_git_add_of_its_own(self, blocking: bool) -> None:
        assert "git add" not in pre_commit_hook_body(blocking=blocking)

    @pytest.mark.parametrize("blocking", [True, False])
    def test_it_prints_what_the_reconcile_withheld(self, blocking: bool) -> None:
        body = pre_commit_hook_body(blocking=blocking)

        assert "grep '^  withheld: '" in body
        assert "were NOT added to it" in body

    @pytest.mark.parametrize("blocking", [True, False])
    def test_it_does_not_borrow_the_verdict_protocol_for_this(self, blocking: bool) -> None:
        """`sed -n 's/^# //p'` is the verdict/payload split and means something else.

        Two legs of this hook use it to take a porcelain verdict off a beadloom
        command. Spelling an unrelated extraction the same way gives one protocol
        a second meaning, which is how the two stop being checkable together.
        """
        body = pre_commit_hook_body(blocking=blocking)

        assert "sed -n 's/^  withheld: //p'" not in body


# --------------------------------------------------------------------------- #
# The report names files a reader can open
# --------------------------------------------------------------------------- #


def _bd_result(payload: list[dict[str, object]]) -> BdResult:
    return BdResult(returncode=0, stdout=json.dumps(payload), stderr="")


def test_check_mode_names_the_real_file_and_not_its_throwaway_copy(
    tmp_path: Path,
) -> None:
    """`--check` reconciles a temporary copy so it can never write.

    Every path it reported pointed inside a directory deleted before the report
    was printed, so a finding named a file the reader could not open.
    """
    directory = tmp_path / ".claude" / "development" / "docs" / "features" / "E"
    directory.mkdir(parents=True)
    (directory / "ACTIVE.md").write_text(
        "| Bead | Status |\n| --- | --- |\n| BEAD-01 | ✓ done |\n", encoding="utf-8"
    )

    with patch(
        "beadloom.services.bd_seam.run_bd",
        return_value=_bd_result([{"id": "proj-e.1", "status": "closed", "dependencies": []}]),
    ):
        result = CliRunner().invoke(
            main, ["active-sync", "--check", "--json", "--project", str(tmp_path)]
        )

    payload = json.loads(result.stdout)
    reported = payload["unresolved_rows"][0]["path"]
    assert reported == str(directory / "ACTIVE.md")
