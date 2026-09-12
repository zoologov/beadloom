"""BDL-UX #283 — a wave plan is compared against the beads already running beside it.

`beadloom waves --parent <work-item>` takes its bead list from `bd ready`, and a
bead in progress is not ready. Measured in BDL-069 on 2026-09-11: `--parent`
answered `1 wave(s) for 1 bead(s), 0 serialisation(s)` for `beadloom-8lmj` while
`beadloom-h7b3` ran under the same epic, and the pair named explicitly serialised
over `cli-commands -> agent-prime`. The answer was right about its population and
silent about the running bead, and `0 serialisation(s)` reads as "nothing
conflicts".

Reproduced red on a bd 1.0.4 rig before this change: an epic with one bead in
progress and one ready, both declaring `billing`.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest

from beadloom.application.waves import (
    FINDING_RUNNING_NOT_COMPARED,
    REASON_BLOCKED_BY_BEAD,
    REASON_SHARED_NODE,
    REASON_UNRESOLVED_SCOPE,
    RUNNING_NO_WORK_ITEM,
    RUNNING_STATUS_UNOBSERVED,
    TRACKER_IN_PROGRESS,
    BeadRecord,
    RunningConflict,
    RunningWork,
    TrackerBead,
    TrackerCensus,
    conflicts_with_running,
    derive_population,
    plan_waves,
    resolve_scopes,
    running_findings,
    running_lines,
    running_population,
    running_summary,
)
from beadloom.infrastructure.db import create_schema, open_db
from beadloom.services.bd_seam import BdResult

_PROJECT_ROOT = Path(__file__).resolve().parents[1]

#: An epic holding one bead in progress, one ready, and one closed.
CENSUS = TrackerCensus(
    beads=(
        TrackerBead(bead_id="epic", status="open"),
        TrackerBead(bead_id="running", parent="epic", status=TRACKER_IN_PROGRESS),
        TrackerBead(bead_id="new", parent="epic", status="open"),
        TrackerBead(bead_id="done", parent="epic", status="closed"),
        TrackerBead(bead_id="elsewhere", status=TRACKER_IN_PROGRESS),
    ),
    ready=("epic", "new"),
)


@pytest.fixture()
def conn(tmp_path: Path) -> Any:
    connection = open_db(tmp_path / "beadloom.db")
    create_schema(connection)
    for ref in ("billing", "shipping"):
        connection.execute(
            "INSERT INTO nodes (ref_id, kind, summary, source) VALUES (?, ?, ?, ?)",
            (ref, "feature", ref, f"src/{ref}/"),
        )
    connection.commit()
    yield connection
    connection.close()


def _record(bead: str, refs: str = "", blocked_by: tuple[str, ...] = ()) -> BeadRecord:
    declaration = f"do the work.\nrefs: {refs}" if refs else "do the work."
    return BeadRecord(
        bead_id=bead, declaration=declaration, blocked_by=frozenset(blocked_by)
    )


class TestWhichBeadsAreRunningBesideAPlan:
    def test_an_in_progress_bead_under_the_work_item_is_running(self) -> None:
        population = derive_population(("new",), CENSUS, work_item="epic")
        work = running_population(population, CENSUS)
        assert work.derived
        assert work.work_item == "epic"
        assert work.in_progress == ("running",)

    def test_an_in_progress_bead_under_another_item_is_not(self) -> None:
        population = derive_population(("new",), CENSUS, work_item="epic")
        assert "elsewhere" not in running_population(population, CENSUS).in_progress

    def test_a_bead_the_plan_holds_is_planned_rather_than_running(self) -> None:
        population = derive_population(("new", "running"), CENSUS, work_item="epic")
        assert running_population(population, CENSUS).in_progress == ()

    def test_a_plan_with_no_work_item_compares_nothing_and_says_why(self) -> None:
        population = derive_population(("new",), None)
        work = running_population(population, None)
        assert not work.derived
        assert work.reason == RUNNING_NO_WORK_ITEM

    def test_a_census_carrying_no_status_is_unobserved_rather_than_idle(self) -> None:
        """A row without a status is not a bead known to be idle."""
        census = TrackerCensus(
            beads=(TrackerBead(bead_id="epic"), TrackerBead(bead_id="a", parent="epic")),
            ready=("a",),
        )
        population = derive_population(("a",), census, work_item="epic")
        work = running_population(population, census)
        assert not work.derived
        assert work.reason == RUNNING_STATUS_UNOBSERVED


class TestThePairsAgainstRunningWork:
    def test_a_shared_node_serialises_the_planned_bead_behind_the_running_one(
        self, conn: Any
    ) -> None:
        planned = resolve_scopes(conn, [_record("new", "billing")])
        running = resolve_scopes(conn, [_record("running", "billing")])
        found = conflicts_with_running(conn, planned, running, [])
        assert found == (
            RunningConflict("new", "running", REASON_SHARED_NODE, "billing"),
        )

    def test_the_orientation_is_kept_whatever_the_ids_sort_as(self, conn: Any) -> None:
        planned = resolve_scopes(conn, [_record("z-new", "billing")])
        running = resolve_scopes(conn, [_record("a-running", "billing")])
        (conflict,) = conflicts_with_running(conn, planned, running, [])
        assert (conflict.planned, conflict.running) == ("z-new", "a-running")

    def test_disjoint_scopes_compare_independent(self, conn: Any) -> None:
        planned = resolve_scopes(conn, [_record("new", "billing")])
        running = resolve_scopes(conn, [_record("running", "shipping")])
        assert conflicts_with_running(conn, planned, running, []) == ()

    def test_a_running_bead_with_no_declaration_serialises_as_unknown(
        self, conn: Any
    ) -> None:
        """Unknown is not independent, for running work as for planned work."""
        planned = resolve_scopes(conn, [_record("new", "billing")])
        running = resolve_scopes(conn, [_record("running")])
        (conflict,) = conflicts_with_running(conn, planned, running, [])
        assert conflict.reason == REASON_UNRESOLVED_SCOPE

    def test_a_planned_bead_blocked_by_running_work_names_the_blocker(
        self, conn: Any
    ) -> None:
        records = [_record("new", "billing", ("running",)), _record("running", "shipping")]
        planned = resolve_scopes(conn, records[:1])
        running = resolve_scopes(conn, records[1:])
        (conflict,) = conflicts_with_running(conn, planned, running, records)
        assert conflict == RunningConflict(
            "new", "running", REASON_BLOCKED_BY_BEAD, "running"
        )


class TestThePlanCarriesTheComparison:
    def test_a_conflict_with_running_work_is_not_a_serialisation_within_the_plan(
        self, conn: Any
    ) -> None:
        plan = plan_waves(
            [_record("new", "billing")],
            conn=conn,
            census=CENSUS,
            work_item="epic",
            running=[_record("running", "billing")],
        )
        assert plan.conflicts == ()
        assert [wave.beads for wave in plan.waves] == [("new",)]
        assert plan.running.conflicts == (
            RunningConflict("new", "running", REASON_SHARED_NODE, "billing"),
        )
        assert plan.running.compared == ("running",)

    def test_it_is_not_a_finding(self, conn: Any) -> None:
        """A serialisation is a decision the shape makes, not a defect of it."""
        plan = plan_waves(
            [_record("new", "billing")],
            conn=conn,
            census=CENSUS,
            work_item="epic",
            running=[_record("running", "billing")],
        )
        assert not any(FINDING_RUNNING_NOT_COMPARED in f for f in plan.findings)

    def test_a_running_bead_with_no_record_is_a_finding(self, conn: Any) -> None:
        plan = plan_waves(
            [_record("new", "billing")], conn=conn, census=CENSUS, work_item="epic"
        )
        assert plan.running.not_compared == ("running",)
        assert any(
            f.startswith(FINDING_RUNNING_NOT_COMPARED) and "running" in f
            for f in plan.findings
        )

    def test_a_record_for_a_bead_outside_the_work_item_is_not_compared(
        self, conn: Any
    ) -> None:
        plan = plan_waves(
            [_record("new", "billing")],
            conn=conn,
            census=CENSUS,
            work_item="epic",
            running=[_record("running", "shipping"), _record("elsewhere", "billing")],
        )
        assert plan.running.compared == ("running",)
        assert plan.running.conflicts == ()

    def test_a_plan_with_no_census_states_it_compared_no_running_work(
        self, conn: Any
    ) -> None:
        plan = plan_waves([_record("new", "billing")], conn=conn)
        assert not plan.running.derived
        assert running_findings(plan.running) == ()


class TestWhatTheComparisonSays:
    def test_the_summary_counts_conflicts_over_the_running_beads_compared(self) -> None:
        work = RunningWork(
            work_item="epic",
            in_progress=("r1", "r2"),
            compared=("r1", "r2"),
            conflicts=(RunningConflict("new", "r1", REASON_SHARED_NODE, "billing"),),
            reason="",
        )
        assert running_summary(work) == "1 against 2 running bead(s)"

    def test_the_summary_names_what_it_did_not_compare(self) -> None:
        work = RunningWork(
            work_item="epic", in_progress=("r1", "r2"), compared=("r1",), reason=""
        )
        assert running_summary(work) == "0 against 1 running bead(s) (1 not compared)"

    def test_an_underived_comparison_never_prints_a_count(self) -> None:
        assert running_summary(RunningWork()) == "running work not compared"

    def test_the_block_names_each_conflict_planned_bead_first(self) -> None:
        work = RunningWork(
            work_item="epic",
            in_progress=("running",),
            compared=("running",),
            conflicts=(RunningConflict("new", "running", REASON_SHARED_NODE, "billing"),),
            reason="",
        )
        block = "\n".join(running_lines(work))
        assert "1 in-progress bead(s) under epic and not in this plan: running" in block
        assert "Serialised against running work:" in block
        assert "new waits for running — shared_node: billing" in block

    def test_the_block_says_when_nothing_is_running(self) -> None:
        work = RunningWork(work_item="epic", reason="")
        block = "\n".join(running_lines(work))
        assert "no bead under epic is in progress outside this plan" in block

    def test_the_block_says_when_running_work_shares_nothing(self) -> None:
        work = RunningWork(
            work_item="epic", in_progress=("r",), compared=("r",), reason=""
        )
        assert "no bead of this plan conflicts with them" in "\n".join(
            running_lines(work)
        )

    def test_the_block_states_the_reason_nothing_was_compared(self) -> None:
        block = "\n".join(running_lines(RunningWork()))
        assert "NOT COMPARED" in block
        assert RUNNING_NO_WORK_ITEM in block

    def test_waits_for_names_the_running_beads_one_planned_bead_is_behind(self) -> None:
        work = RunningWork(
            work_item="epic",
            in_progress=("r1", "r2"),
            compared=("r1", "r2"),
            conflicts=(
                RunningConflict("new", "r2", REASON_SHARED_NODE, "billing"),
                RunningConflict("new", "r1", REASON_SHARED_NODE, "billing"),
            ),
            reason="",
        )
        assert work.waits_for("new") == ("r1", "r2")
        assert work.waits_for("other") == ()


class TestTheTrackerAnswerItIsReadFrom:
    def test_the_census_reader_keeps_bds_status(self) -> None:
        from beadloom.services.commands.waves import _census_beads

        rows = [
            {"id": "a", "status": "in_progress", "dependencies": []},
            {"id": "b", "dependencies": []},
        ]
        beads = _census_beads(json.dumps(rows))
        assert beads is not None
        assert [bead.status for bead in beads] == ["in_progress", None]

    def test_only_in_progress_beads_outside_the_plan_are_shown(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        from beadloom.services.commands.waves import _running_records

        shown: list[str] = []

        def fake(args: list[str], *, cwd: str | None = None) -> BdResult:
            shown.append(args[1])
            record = {"id": args[1], "title": "t", "description": "refs: billing"}
            return BdResult(returncode=0, stdout=json.dumps([record]), stderr="")

        monkeypatch.setattr("beadloom.services.bd_seam.run_bd", fake, raising=True)
        census = TrackerCensus(
            beads=(
                TrackerBead(bead_id="a", status=TRACKER_IN_PROGRESS),
                TrackerBead(bead_id="b", status=TRACKER_IN_PROGRESS),
                TrackerBead(bead_id="c", status="open"),
            ),
            ready=("c",),
        )
        records = _running_records(census, ("b",), tmp_path)
        assert shown == ["a"]
        assert [record.bead_id for record in records] == ["a"]

    def test_a_bead_the_tracker_cannot_show_is_left_out_rather_than_raised(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        from beadloom.services.commands.waves import _running_records

        def fake(args: list[str], *, cwd: str | None = None) -> BdResult:
            return BdResult(returncode=1, stdout="", stderr="no issue found")

        monkeypatch.setattr("beadloom.services.bd_seam.run_bd", fake, raising=True)
        census = TrackerCensus(
            beads=(TrackerBead(bead_id="a", status=TRACKER_IN_PROGRESS),), ready=()
        )
        assert _running_records(census, (), tmp_path) == []

    def test_bd_spells_the_status_the_way_this_comparison_reads_it(self) -> None:
        """The premise of the defect, read off the real tracker: a bead in
        progress carries `in_progress` in `bd list` and is absent from `bd ready`."""
        if shutil.which("bd") is None or not (_PROJECT_ROOT / ".beads").is_dir():
            pytest.skip("bd is not installed here; its answer cannot be observed")
        listed = subprocess.run(
            ["bd", "list", "--all", "--json"],  # noqa: S607
            cwd=_PROJECT_ROOT,
            capture_output=True,
            encoding="utf-8",
            check=False,
        )
        ready = subprocess.run(
            ["bd", "ready", "--json", "--limit", "0"],  # noqa: S607
            cwd=_PROJECT_ROOT,
            capture_output=True,
            encoding="utf-8",
            check=False,
        )
        if listed.returncode != 0 or ready.returncode != 0:
            pytest.skip("the tracker here did not answer")
        rows = json.loads(listed.stdout)
        assert all("status" in row for row in rows)
        running = {row["id"] for row in rows if row["status"] == TRACKER_IN_PROGRESS}
        ready_ids = {row["id"] for row in json.loads(ready.stdout)}
        assert not running & ready_ids
