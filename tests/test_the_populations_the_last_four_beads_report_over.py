"""BDL-068 S6 — the four beads that landed after the test bead, re-asked.

`beadloom-0mdo.78`, `.83`, `beadloom-ec1a` and `beadloom-iur5` changed source
after `beadloom-0mdo.69` had measured S6's surface, so its four questions are put
to them here rather than assumed answered. `beadloom-l9ee` found a phantom
population inside `.66`'s allocator six hours after it shipped, and `.83`'s own
module names the shape it was watching for: what can fail is not the count but
the answer the count was taken from.

Three findings, each `xfail(strict=True)` citing its log entry, none of them
producible by reading the code alone — each was measured against this
repository's own tracker and its own gate.

* **BDL-UX #275**, `.83`: `_narrowest` searches every bead in the census for the
  work item to hold a plan against, and a bead qualifies by DEPENDING on what
  the plan asked about. Measured: `beadloom waves beadloom-0mdo.69` names
  `beadloom-0mdo.70` — the S6 review task, whose whole population is the one
  bead the plan was asked about — and reports a clean line over it.
* **BDL-UX #276**, `.78`: the GitHub annotation surface emits the ownership
  headline and drops the `unowned` count, the `unattributed` count, which beads
  were claimed, and the caveat that says `unowned` is not a proof. Measured on
  this tree: 31 unowned, 165 unattributed, 2 of 2 claimed beads declaring a
  scope the run could not read, one notice line.
* **BDL-UX #277**, `ec1a`: the orphan check's ROLE population is the manifest
  and its TOOL population is `TOOL_AGENT_DIRS`, and only the first is stated.

Everything else here is a boundary guard written after the behaviour, holding
the population each of the four states correctly today.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

from beadloom.application.gate import GateResult
from beadloom.application.gate_ownership import (
    UNATTRIBUTED,
    UNOWNED,
    GateOwnership,
    derive_gate_ownership,
    gate_ownership_lines,
)
from beadloom.application.guards.contract import ClaimedBead
from beadloom.application.waves.population import (
    POPULATION_NO_COMMON_ITEM,
    POPULATION_NOT_GATHERED,
    TrackerBead,
    TrackerCensus,
    beads_under,
    derive_population,
    population_findings,
    population_lines,
)
from beadloom.onboarding.flow_config import resolve_flow_config
from beadloom.onboarding.role_adapters import TOOL_AGENT_DIRS, orphaned_adapters
from beadloom.services.commands.federation import _gate_ownership_notices
from tests.adopter_flow import OURS, build_flow

if TYPE_CHECKING:
    from pathlib import Path

#: An epic, two children, and a third bead that BLOCKS one of the children
#: without being anybody's child — the shape BDL-UX #274 was filed about, where
#: the parent field alone finds only one of the lost beads.
CENSUS = (
    TrackerBead(bead_id="epic"),
    TrackerBead(bead_id="epic.1", parent="epic"),
    TrackerBead(bead_id="epic.2", parent="epic", depends_on=frozenset({"loose"})),
    TrackerBead(bead_id="loose"),
)


def _census(*, ready: tuple[str, ...] = (), **kwargs: object) -> TrackerCensus:
    return TrackerCensus(beads=CENSUS, ready=ready, **kwargs)  # type: ignore[arg-type]


class _Tracker:
    """A `WorkTracker` that answers with whatever the row hands it."""

    def __init__(self, beads: tuple[ClaimedBead, ...] | None) -> None:
        self._beads = beads

    def claimed_beads(self) -> tuple[ClaimedBead, ...] | None:
        return self._beads


class TestTheMembershipRuleTheLostBeadsNeeded:
    """The parent-child closure plus one dependency step, and not one step more.

    Boundary guards. `.83` measured that `parent` alone finds one of the three
    lost beads and the unbounded walk reaches another epic entirely; these hold
    the bounded rule where it sits.
    """

    def test_a_child_belongs_to_its_parent(self) -> None:
        assert "epic.1" in beads_under("epic", CENSUS)

    def test_a_blocker_of_a_child_belongs_too(self) -> None:
        """`loose` has no parent and belongs to the epic because it blocks it."""
        assert "loose" in beads_under("epic", CENSUS)

    def test_a_work_item_is_not_a_member_of_its_own_population(self) -> None:
        assert "epic" not in beads_under("epic", CENSUS)

    def test_the_step_out_of_the_tree_is_not_taken_twice(self) -> None:
        """A blocker's own blockers belong to that blocker's work item."""
        census: tuple[TrackerBead, ...] = (
            *[bead for bead in CENSUS if bead.bead_id != "loose"],
            TrackerBead(bead_id="loose", depends_on=frozenset({"far"})),
            TrackerBead(bead_id="far"),
        )
        found = beads_under("epic", census)
        assert "loose" in found
        assert "far" not in found

    def test_an_item_the_census_does_not_hold_has_an_empty_population(self) -> None:
        assert beads_under("absent", CENSUS) == frozenset()


class TestThePopulationAPlanIsHeldAgainst:
    """What `derive_population` states, and what it declines to guess."""

    def test_a_plan_over_a_subset_names_what_it_left_out(self) -> None:
        population = derive_population(["epic.1"], _census(ready=("epic.1", "epic.2", "loose")))
        assert population.derived is True
        assert population.work_item == "epic"
        assert population.unasked == ("epic.2", "loose")

    def test_a_plan_holding_every_ready_bead_says_so(self) -> None:
        population = derive_population(
            ["epic.1", "epic.2", "loose"], _census(ready=("epic.1", "epic.2", "loose"))
        )
        assert population.unasked == ()
        assert "every ready bead under epic is in this plan" in "\n".join(
            population_lines(population)
        )

    def test_no_census_is_a_stated_reason_and_never_a_count_of_zero(self) -> None:
        population = derive_population(["epic.1"], None)
        assert population.derived is False
        assert population.reason == POPULATION_NOT_GATHERED
        assert POPULATION_NOT_GATHERED in "\n".join(population_lines(population))

    def test_an_absent_ready_list_is_the_same_refusal(self) -> None:
        """`bd` answered about beads and not about readiness; neither is a zero."""
        population = derive_population(["epic.1"], TrackerCensus(beads=CENSUS, ready=None))
        assert population.reason == POPULATION_NOT_GATHERED

    def test_an_empty_ready_list_is_an_observation_rather_than_an_absence(self) -> None:
        population = derive_population(["epic.1"], _census(ready=()))
        assert population.derived is True
        assert population.ready_under == ()

    def test_beads_spanning_no_one_item_are_refused_by_name(self) -> None:
        census = TrackerCensus(
            beads=(TrackerBead(bead_id="a"), TrackerBead(bead_id="b")),
            ready=("a", "b"),
        )
        population = derive_population(["a", "b"], census)
        assert population.reason == POPULATION_NO_COMMON_ITEM

    def test_a_named_parent_stops_the_search(self) -> None:
        """A caller that said which item it meant is answered about that item."""
        population = derive_population(["epic.1"], _census(ready=("epic.1",)), work_item="epic")
        assert population.work_item == "epic"

    def test_a_capped_ready_answer_is_a_finding_about_this_report(self) -> None:
        population = derive_population(
            ["epic.1"],
            _census(ready=("epic.1",), ready_whole=False, ready_note="capped at 100"),
        )
        findings = population_findings(population)
        assert len(findings) == 1
        assert "capped at 100" in findings[0]

    def test_an_uncapped_ready_answer_produces_no_finding(self) -> None:
        assert population_findings(derive_population(["epic.1"], _census(ready=()))) == ()


class TestWhichBeadIsTakenForAWorkItem:
    """A candidate qualifies by DEPENDING on the plan, which a work item does not.

    `beads_under(item)` is `item`'s children plus what those children depend on,
    so for a childless bead it is exactly that bead's own blockers. A plan about
    one bead is therefore a subset of every bead that blocks on it, and
    `_narrowest` prefers the smallest — which is the blocker, never the epic.
    """

    #: An epic with two children, where `epic.2` blocks on `epic.1` — the shape
    #: a dev bead and the review bead after it have.
    BLOCKED = (
        TrackerBead(bead_id="epic"),
        TrackerBead(bead_id="epic.1", parent="epic"),
        TrackerBead(bead_id="epic.2", parent="epic", depends_on=frozenset({"epic.1"})),
    )

    @pytest.mark.xfail(
        strict=True,
        reason=(
            "FINDING BDL-068.S6-7 (BDL-UX #275): a bead qualifies as a work item "
            "by depending on the plan's beads, so a one-bead plan is attributed "
            "to the bead that blocks on it and reported clean over a population "
            "of one. Measured: `beadloom waves beadloom-0mdo.69` names "
            "`beadloom-0mdo.70`, the S6 review task"
        ),
    )
    def test_a_plan_of_one_bead_is_held_against_its_epic(self) -> None:
        census = TrackerCensus(beads=self.BLOCKED, ready=("epic.1",))
        assert derive_population(["epic.1"], census).work_item == "epic"

    def test_the_attribution_is_the_one_recorded(self) -> None:
        """The red above is red for the reason claimed, and the line it produces."""
        census = TrackerCensus(beads=self.BLOCKED, ready=("epic.1",))
        population = derive_population(["epic.1"], census)
        assert population.work_item == "epic.2"
        assert population.under == ("epic.1",)
        assert population.unasked == ()
        assert "every ready bead under epic.2 is in this plan" in "\n".join(
            population_lines(population)
        )

    def test_the_epic_is_a_candidate_and_loses_on_size(self) -> None:
        """Both answers are available; the tie-break is what chooses wrongly."""
        assert beads_under("epic", self.BLOCKED) == frozenset({"epic.1", "epic.2"})
        assert beads_under("epic.2", self.BLOCKED) == frozenset({"epic.1"})

    def test_having_a_child_separates_the_two_candidates(self) -> None:
        """The discriminator the module already holds and does not spend.

        A work item has children; a blocker does not have to. Stated as a test so
        the remedy the finding proposes is the one that was measured.
        """
        with_children = {bead.parent for bead in self.BLOCKED if bead.parent}
        assert "epic" in with_children
        assert "epic.2" not in with_children

    def test_naming_the_parent_reaches_the_right_answer_today(self) -> None:
        """The workaround in force, so the finding is a default and not a wall."""
        census = TrackerCensus(beads=self.BLOCKED, ready=("epic.1",))
        population = derive_population(["epic.1"], census, work_item="epic")
        assert population.work_item == "epic"
        assert population.unasked == ()
        assert population.under == ("epic.1", "epic.2")


class TestWhatTheOwnershipReportSaysOnEachSurface:
    """One run, three formats, and the claim they are supposed to share.

    `gate_ownership_lines` exists, in its own words, because "three formats and
    one MCP tool quote it, and a second wording is how two surfaces of one run
    come to disagree". The GitHub emitter does not quote it.
    """

    FINDINGS: tuple[dict[str, object], ...] = (
        {"rule": "scenario-coverage", "node": "cache"},
        {"rule": "scenario-coverage", "node": "watcher"},
        {"rule": "doc-fact-stale", "locations": [{"file": "nowhere.md"}]},
    )

    def test_a_tracker_that_cannot_answer_is_a_reason_and_not_a_page_of_unowned(
        self, tmp_path: Path
    ) -> None:
        report = derive_gate_ownership(
            tmp_path, findings=list(self.FINDINGS), tracker=_Tracker(None)
        )
        assert report.reason is not None
        assert report.owners == ()

    def test_a_green_run_asks_the_tracker_nothing(self, tmp_path: Path) -> None:
        report = derive_gate_ownership(tmp_path, findings=[], tracker=_Tracker(None))
        assert report.reason is None
        assert report.owners == ()

    def test_a_project_with_no_index_names_the_claims_it_could_not_use(
        self, tmp_path: Path
    ) -> None:
        report = derive_gate_ownership(
            tmp_path,
            findings=list(self.FINDINGS),
            tracker=_Tracker((ClaimedBead(id="bead-a"),)),
        )
        assert report.claimed == ("bead-a",)
        assert report.reason is not None

    @pytest.mark.xfail(
        strict=True,
        reason=(
            "FINDING BDL-068.S6-8 (BDL-UX #276): the GitHub emitter calls itself "
            "`the same claim, one line each` and drops the unowned count, the "
            "unattributed count, which beads were claimed, and the caveat that "
            "says `unowned` is not a proof. Measured on this tree: 31 unowned, "
            "165 unattributed, 2 of 2 claimed beads with an unreadable scope, one "
            "notice line"
        ),
    )
    def test_the_annotation_surface_carries_the_unread_caveat(self) -> None:
        notices = "\n".join(_gate_ownership_notices(_result(_ownership_with_unread())))
        assert "not a proof" in notices

    def test_the_two_surfaces_differ_in_the_way_recorded(self) -> None:
        """The red above is red for the reason claimed, clause by clause."""
        ownership = _ownership_with_unread()
        human = "\n".join(gate_ownership_lines(ownership))
        notices = "\n".join(_gate_ownership_notices(_result(ownership)))

        assert UNOWNED in human
        assert UNATTRIBUTED in human
        assert "not a proof" in human
        assert "claimed: bead-a, bead-b" in human

        assert notices.count("\n") == 0
        assert UNOWNED not in notices
        assert UNATTRIBUTED not in notices
        assert "not a proof" not in notices
        assert "bead-a" not in notices

    def test_the_headline_itself_reaches_both_surfaces(self) -> None:
        """What the emitter does carry, held so the finding is a gap and not a denial."""
        ownership = _ownership_with_unread()
        headline = "no finding of this run is owned by a bead claimed now"
        assert headline in "\n".join(gate_ownership_lines(ownership))
        assert headline in "\n".join(_gate_ownership_notices(_result(ownership)))

    def test_none_owned_is_false_when_there_was_nothing_to_attribute(self) -> None:
        """A green run must not print the sentence a red one needs."""
        assert GateOwnership().none_owned is False


class TestWhichAdaptersCanBeReportedOrphaned:
    """The orphan check's two populations, and only one of them is stated."""

    def test_an_adapter_of_a_dropped_tool_is_reported(self, tmp_path: Path) -> None:
        root = _scaffolded(tmp_path, ".cursor/agents/dev.md")
        orphans = orphaned_adapters(root, resolve_flow_config(root))
        assert [orphan.file for orphan in orphans] == [".cursor/agents/dev.md"]
        assert orphans[0].tool == "cursor"

    def test_an_adapter_of_a_declared_tool_is_not(self, tmp_path: Path) -> None:
        root = _scaffolded(tmp_path, ".claude/agents/dev.md")
        assert orphaned_adapters(root, resolve_flow_config(root)) == ()

    def test_a_recorded_file_the_adopter_deleted_is_not_reported(self, tmp_path: Path) -> None:
        """One of the two remedies was taken, and reporting a repair is noise."""
        root = _scaffolded(tmp_path, ".cursor/agents/dev.md", on_disk=False)
        assert orphaned_adapters(root, resolve_flow_config(root)) == ()

    def test_a_file_beadloom_never_recorded_writing_is_somebody_elses(
        self, tmp_path: Path
    ) -> None:
        root = _scaffolded(tmp_path, ".claude/agents/dev.md")
        (root / ".cursor" / "agents").mkdir(parents=True)
        (root / ".cursor" / "agents" / "dev.md").write_text("mine\n", encoding="utf-8")
        assert orphaned_adapters(root, resolve_flow_config(root)) == ()

    @pytest.mark.xfail(
        strict=True,
        reason=(
            "FINDING BDL-068.S6-9 (BDL-UX #277): the ROLE population is the "
            "manifest and the TOOL population is TOOL_AGENT_DIRS, so an adapter "
            "this release recorded writing under a tool this release no longer "
            "ships is invisible — the case the docstring argues it handles, one "
            "axis over"
        ),
    )
    def test_an_adapter_under_a_tool_this_release_does_not_ship_is_reported(
        self, tmp_path: Path
    ) -> None:
        root = _scaffolded(tmp_path, ".windsurf/agents/dev.md")
        assert orphaned_adapters(root, resolve_flow_config(root)) != ()

    def test_the_silence_is_the_one_recorded(self, tmp_path: Path) -> None:
        """The file is on disk, the manifest records it, and nothing is said."""
        root = _scaffolded(tmp_path, ".windsurf/agents/dev.md")
        assert (root / ".windsurf" / "agents" / "dev.md").is_file()
        assert "windsurf" not in TOOL_AGENT_DIRS
        assert orphaned_adapters(root, resolve_flow_config(root)) == ()


class TestEveryFindingHereIsStrictAndNamesItself:
    """The meta-check `.18` introduced and `.22` carried."""

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


def _ownership_with_unread() -> GateOwnership:
    """A report shaped like this tree's: unowned, unattributed, nothing owned.

    Both claimed beads declare no scope this run could read, which is the state
    the tree was in when the finding was measured — so `unowned` there is a
    statement about what could be asked, not about who owns the nodes.
    """
    from beadloom.application.gate_ownership import FindingOwner, UnreadClaim

    return GateOwnership(
        owners=(
            FindingOwner(rule="scenario-coverage", verdict=UNOWNED, node="cache"),
            FindingOwner(rule="scenario-coverage", verdict=UNOWNED, node="watcher"),
            FindingOwner(rule="doc-fact-stale", verdict=UNATTRIBUTED),
        ),
        claimed=("bead-a", "bead-b"),
        unread=(
            UnreadClaim(bead_id="bead-a", why="no_declared_refs"),
            UnreadClaim(bead_id="bead-b", why="no_declared_refs"),
        ),
    )


def _result(ownership: GateOwnership) -> GateResult:
    """The real `GateResult`, carrying nothing but the ownership under test.

    The product's own type rather than a stand-in: the emitter reads one field,
    and a double that also has one field would prove only that the double has
    one field.
    """
    return GateResult(ownership=ownership)


def _scaffolded(tmp_path: Path, relpath: str, *, on_disk: bool = True) -> Path:
    """A `tools: [claude]` project whose manifest records *relpath* as written."""
    root = tmp_path / "proj"
    build_flow(root, OURS)
    target = root / relpath
    target.parent.mkdir(parents=True, exist_ok=True)
    if on_disk:
        target.write_text("# adapter\n", encoding="utf-8")
    (root / ".beadloom" / "flow-manifest.json").write_text(
        json.dumps({"version": 1, "written": {relpath: "deadbeef"}}, indent=2),
        encoding="utf-8",
    )
    return root
