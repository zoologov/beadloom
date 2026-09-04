"""The declaration held against the derivation its work item recorded.

BDL-UX #232 and #234. The acceptance suite states the behaviour a reader is
promised; this file covers the branches that behaviour is assembled from, and
two of them are the ones the defect actually lived in: the verdict for a ref the
table never names, and the remedy for a cause with two sub-cases.
"""

from __future__ import annotations

from beadloom.application.waves import (
    AXES_NOT_GATHERED,
    AXIS_AGREES,
    AXIS_NOT_ATTRIBUTED,
    AXIS_NOT_DERIVED,
    AXIS_RULED_OUT,
    AXIS_UNDECIDED,
    FINDING_DECLARED_OUTSIDE,
    FINDING_NOT_COMPARED,
    FINDING_UNGUARDED_AXIS,
    UNKNOWN_REMEDY,
    UNRESOLVED_NO_DECLARATION,
    UNRESOLVED_UNANCHORED,
    UNRESOLVED_UNKNOWN_REF,
    BeadScope,
    Wave,
    WorkItemAxes,
    compare_declarations,
    derivation_findings,
    remedy_for,
    unguarded_axes,
)

#: A work item that approves two nodes by a kept row, one by having derived over
#: it, rules one out, decides nothing about one, and could attribute no node to
#: one axis. Every verdict has a subject here, so a test asking for one never
#: passes because the table happened to be empty.
AXES = WorkItemAxes(
    work_item="BDL-000",
    document="docs/BDL-000/RFC.md",
    seed="none",
    unresolved="co-writers, on all three targets",
    kept=frozenset({"billing", "shipping"}),
    targets=frozenset({"invoicing"}),
    ruled_out=frozenset({"legacy"}),
    undecided=frozenset({"pending"}),
    unattributed=("co-writers",),
)


def _scope(bead: str, *declared: str, refs: tuple[str, ...] | None = None) -> BeadScope:
    """A bead whose declaration named *declared* and whose closure is *refs*."""
    return BeadScope(
        bead_id=bead,
        refs=frozenset(refs if refs is not None else declared),
        files=frozenset(),
        declared=declared,
    )


def _verdicts(scopes: list[BeadScope], axes: WorkItemAxes) -> dict[str, str]:
    return {a.ref: a.verdict for a in compare_declarations(scopes, axes)}


class TestOneRefAgainstTheTable:
    """Four verdicts, and the reason only one of them accuses anybody."""

    def test_a_kept_row_agrees(self) -> None:
        assert _verdicts([_scope("a", "billing")], AXES)["billing"] == AXIS_AGREES

    def test_a_derived_by_target_agrees_as_well_as_a_kept_row(self) -> None:
        """A work item changes the surfaces it derived its answer from.

        The same rule `scope_check.DeclaredScope.inside` applies, spent here
        rather than restated: two readings of one approval are two things that
        can disagree.
        """
        assert _verdicts([_scope("a", "invoicing")], AXES)["invoicing"] == AXIS_AGREES

    def test_a_row_that_rules_the_node_out_is_the_sharpest_half(self) -> None:
        assert _verdicts([_scope("a", "legacy")], AXES)["legacy"] == AXIS_RULED_OUT

    def test_a_row_nobody_ruled_on_neither_authorises_nor_condemns(self) -> None:
        assert _verdicts([_scope("a", "pending")], AXES)["pending"] == AXIS_UNDECIDED

    def test_a_ref_no_row_names_is_the_derivation_not_reaching(self) -> None:
        """BDL-UX #225: `impact` attributed no node to any of 148 caller sites.

        So the absence of a row says nothing about the declaration, and calling
        it a disagreement would send an author to correct a line already right.
        """
        assert _verdicts([_scope("a", "elsewhere")], AXES)["elsewhere"] == (
            AXIS_NOT_DERIVED
        )

    def test_an_axis_row_naming_no_node_is_compared_against_nothing(self) -> None:
        verdicts = _verdicts([_scope("a", "billing")], AXES)
        assert verdicts["co-writers"] == AXIS_NOT_ATTRIBUTED

    def test_an_unattributed_row_belongs_to_the_work_item_and_to_no_bead(self) -> None:
        row = next(
            a
            for a in compare_declarations([_scope("a", "billing")], AXES)
            if a.verdict == AXIS_NOT_ATTRIBUTED
        )
        assert row.bead_id == ""

    def test_the_closure_is_not_compared_only_the_declaration(self) -> None:
        """A component a `part_of` expansion reached is not a ref anybody wrote.

        Comparing the closure would report every component of a domain a bead
        named as a declaration its author never made.
        """
        scope = _scope("a", "billing", refs=("billing", "billing-core"))
        assert set(_verdicts([scope], AXES)) == {"billing", "co-writers"}

    def test_nothing_is_compared_when_there_is_no_derivation(self) -> None:
        """An empty list beside a stated reason, never a list of agreements."""
        assert compare_declarations(
            [_scope("a", "billing")], WorkItemAxes(reason="no work item")
        ) == ()


class TestTheGapAWaveLeaves:
    """The finding that would have caught BDL-UX #232's measured collision."""

    def test_a_wave_of_two_reports_the_approved_nodes_neither_declares(self) -> None:
        gaps = unguarded_axes(
            [Wave(index=1, beads=("a", "b"), gate_owner="b")],
            [_scope("a", "billing"), _scope("b", "shipping")],
            AXES,
        )
        assert [gap.nodes for gap in gaps] == [("invoicing",)]

    def test_a_wave_whose_beads_together_declare_everything_reports_no_gap(self) -> None:
        assert unguarded_axes(
            [Wave(index=1, beads=("a", "b"), gate_owner="b")],
            [_scope("a", "billing", "invoicing"), _scope("b", "shipping")],
            AXES,
        ) == ()

    def test_containment_through_part_of_is_real_coverage(self) -> None:
        """A bead declaring a domain does occupy its components.

        The gap is measured against the closure for exactly this reason, while
        the per-ref verdict is measured against the declaration. The two
        questions differ, so the two populations differ.
        """
        covering = _scope("a", "billing", refs=("billing", "invoicing"))
        assert unguarded_axes(
            [Wave(index=1, beads=("a", "b"), gate_owner="b")],
            [covering, _scope("b", "shipping")],
            AXES,
        ) == ()

    def test_a_wave_of_one_bead_makes_no_pair_and_claims_nothing(self) -> None:
        """Not suppression: the sentence is about a PAIRWISE verdict.

        Reported per plan instead, an epic approving ten nodes would print a
        finding for every undeclared one on every single-bead plan, and an
        always-red check is an ignored check.
        """
        assert unguarded_axes(
            [Wave(index=1, beads=("a",), gate_owner="a")], [_scope("a", "billing")], AXES
        ) == ()

    def test_a_work_item_approving_nothing_leaves_no_gap_to_report(self) -> None:
        empty = WorkItemAxes(work_item="BDL-000", document="d.md")
        assert unguarded_axes(
            [Wave(index=1, beads=("a", "b"), gate_owner="b")],
            [_scope("a", "billing"), _scope("b", "shipping")],
            empty,
        ) == ()


class TestWhatReachesTheReader:
    """Which of the five verdicts becomes a finding, and which stays a statement."""

    def _findings(self, waves: list[Wave], axes: WorkItemAxes) -> tuple[str, ...]:
        scopes = [_scope("a", "billing", "legacy", "elsewhere"), _scope("b", "shipping")]
        return derivation_findings(
            waves,
            compare_declarations(scopes, axes),
            unguarded_axes(waves, scopes, axes),
            axes,
        )

    def test_a_ruled_out_declaration_is_a_finding(self) -> None:
        found = self._findings([Wave(index=1, beads=("a", "b"), gate_owner="b")], AXES)
        assert any(line.startswith(FINDING_DECLARED_OUTSIDE) for line in found)

    def test_a_ref_the_derivation_did_not_reach_is_not(self) -> None:
        found = self._findings([Wave(index=1, beads=("a", "b"), gate_owner="b")], AXES)
        assert not any("elsewhere" in line for line in found)

    def test_an_unattributed_row_is_not(self) -> None:
        found = self._findings([Wave(index=1, beads=("a", "b"), gate_owner="b")], AXES)
        assert not any("co-writers" in line for line in found)

    def test_the_gap_names_its_wave_its_beads_and_the_document(self) -> None:
        found = self._findings([Wave(index=1, beads=("a", "b"), gate_owner="b")], AXES)
        line = next(f for f in found if f.startswith(FINDING_UNGUARDED_AXIS))
        assert "wave 1" in line
        assert "a, b" in line
        assert AXES.document in line

    def test_an_ungathered_derivation_is_reported_where_a_pair_exists(self) -> None:
        found = self._findings(
            [Wave(index=1, beads=("a", "b"), gate_owner="b")],
            WorkItemAxes(reason=AXES_NOT_GATHERED),
        )
        assert [line for line in found if line.startswith(FINDING_NOT_COMPARED)]

    def test_and_is_silent_where_none_does(self) -> None:
        """A plan run off a work-item branch legitimately compares nothing.

        Exiting 1 on every such run is how a reader learns to discount the
        command — the rule this project already applies to a suppressed check.
        """
        assert self._findings(
            [Wave(index=1, beads=("a",), gate_owner="a")],
            WorkItemAxes(reason=AXES_NOT_GATHERED),
        ) == ()


class TestTheRemedyFollowsTheCause:
    """BDL-UX #234: a printed remedy that outran what its reason could tell."""

    def test_a_refs_inside_prose_states_both_cases_and_the_ambiguity(self) -> None:
        remedy = remedy_for(UNRESOLVED_UNANCHORED)
        assert "cannot tell" in remedy
        assert "start of its own line" in remedy
        assert "prose" in remedy

    def test_it_never_tells_the_reader_to_promote_the_sentence_outright(self) -> None:
        """The instruction that would have authored a scope on `beadloom-nn4c`."""
        assert "If it is a declaration" in remedy_for(UNRESOLVED_UNANCHORED)

    def test_an_absent_declaration_is_sent_to_the_document_when_there_is_one(
        self,
    ) -> None:
        remedy = remedy_for(UNRESOLVED_NO_DECLARATION, axes=AXES)
        assert AXES.document in remedy
        assert "billing" in remedy

    def test_and_is_asked_for_a_line_when_there_is_not(self) -> None:
        remedy = remedy_for(
            UNRESOLVED_NO_DECLARATION, axes=WorkItemAxes(reason="no work item")
        )
        assert "on a line of its own" in remedy
        assert "## Axes" not in remedy

    def test_an_approval_longer_than_the_limit_is_counted_rather_than_transcribed(
        self,
    ) -> None:
        wide = WorkItemAxes(
            work_item="BDL-000",
            document="d.md",
            kept=frozenset({f"n{index}" for index in range(9)}),
        )
        remedy = remedy_for(UNRESOLVED_NO_DECLARATION, axes=wide)
        assert "and 3 more" in remedy

    def test_a_reason_this_module_does_not_know_still_gets_an_instruction(self) -> None:
        assert remedy_for("something_new") == UNKNOWN_REMEDY
        assert remedy_for(None) == UNKNOWN_REMEDY

    def test_the_two_single_sentence_causes_are_unchanged_by_the_axes(self) -> None:
        """A cause whose answer does not depend on the document must not move."""
        assert remedy_for(UNRESOLVED_UNKNOWN_REF) == remedy_for(
            UNRESOLVED_UNKNOWN_REF, axes=AXES
        )
