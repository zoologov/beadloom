"""Step implementations for the S6 wave-shape suite (BDL-061 S6).

Thin by design: every step builds a real graph index and runs the real planner.
The tracker is the one thing that arrives as data — :func:`plan_waves` takes
bead records as an argument precisely so the decision can be exercised without a
``bd`` binary, and so the application layer never reaches up into ``services``.

The module is named ``test_*`` so default pytest collection picks the scenarios
up — the acceptance suite runs inside ``uv run pytest``, not beside it.
"""

from __future__ import annotations

import re
from dataclasses import replace
from typing import TYPE_CHECKING, Any

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from beadloom.application.waves import (
    AXIS_NOT_ATTRIBUTED,
    AXIS_NOT_DERIVED,
    AXIS_RULED_OUT,
    AXIS_SWEPT_UNDECIDED,
    FINDING_DECLARED_OUTSIDE,
    FINDING_NOT_COMPARED,
    FINDING_UNGUARDED_AXIS,
    GATE_COMMIT_SCOPED,
    MEDIUM_COMMIT_GATE,
    MEDIUM_DOC_BASELINE,
    MEDIUM_FOCUS_DOCUMENT,
    MEDIUM_GRAPH_FILES,
    MEDIUM_LANDING_ORDER,
    MEDIUM_TRACKER_IDS,
    MEDIUM_WORKING_TREE,
    REASON_SHARED_NODE,
    REASON_UNRESOLVED_SCOPE,
    STATUS_FAILED,
    STATUS_NOT_APPLICABLE,
    STATUS_PASSED,
    STATUS_UNMEASURED,
    BeadRecord,
    FocusDocument,
    GraphFile,
    GraphInput,
    WaveEnvironment,
    WaveOverride,
    WorkItemAxes,
    plan_waves,
    remedy_for,
    room_for,
)
from beadloom.infrastructure.db import create_schema, open_db

if TYPE_CHECKING:
    from pathlib import Path

scenarios("../features/wave_plan.feature")


@pytest.fixture()
def world(tmp_path: Path) -> dict[str, Any]:
    """One mutable bag the steps share, kept explicit rather than global."""
    db_path = tmp_path / "beadloom.db"
    conn = open_db(db_path)
    create_schema(conn)
    for ref in ("billing", "shipping", "invoicing"):
        conn.execute(
            "INSERT INTO nodes (ref_id, kind, summary, source) VALUES (?, ?, ?, ?)",
            (ref, "feature", ref, f"src/{ref}/"),
        )
        conn.execute(
            "INSERT INTO file_index (path, hash, kind, indexed_at) VALUES (?, ?, ?, ?)",
            (f"src/{ref}/core.py", f"h-{ref}", "code", "2026-08-24T00:00:00Z"),
        )
    conn.commit()
    return {
        "conn": conn,
        "beads": [],
        "overrides": [],
        "plan": None,
        "environment": None,
        "axes": None,
    }


def _declare(world: dict[str, Any], bead: str, declaration: str) -> None:
    world["beads"].append(BeadRecord(bead_id=bead, declaration=declaration))


@given(parsers.parse('a bead "{bead}" declaring the node scope "{ref}"'))
def given_bead_with_scope(world: dict[str, Any], bead: str, ref: str) -> None:
    _declare(world, bead, f"Do the work.\nrefs: {ref}")


@given(
    parsers.parse(
        'a bead "{bead}" declaring the node scope "{ref}" titled "{title}"'
    )
)
def given_bead_with_scope_and_title(
    world: dict[str, Any], bead: str, ref: str, title: str
) -> None:
    world["beads"].append(
        BeadRecord(
            bead_id=bead, declaration=f"Do the work.\nrefs: {ref}", title=title
        )
    )


#: The graph of the fixture project, in the two homes it has: the files declare
#: what the index the scopes were resolved from holds.
_AGREEING_GRAPH = GraphInput(
    files=(
        GraphFile(
            path=".beadloom/_graph/services.yml", nodes=("billing", "shipping")
        ),
    ),
    indexed=frozenset({"billing", "shipping"}),
)


@given("the shared media were measured and are clean")
def given_media_measured(world: dict[str, Any]) -> None:
    """Somebody read the tree, the hook, the doc baseline and the flow, and said so."""
    world["environment"] = WaveEnvironment(
        tree_changed_paths=(),
        commit_gate=GATE_COMMIT_SCOPED,
        doc_baseline_stale_pairs=0,
        landing_lock_sites=(),
        focus_documents=(),
        graph_input=_AGREEING_GRAPH,
    )


@given(parsers.parse('a bead "{bead}" declaring no node scope at all'))
def given_bead_without_scope(world: dict[str, Any], bead: str) -> None:
    _declare(world, bead, "Do the work.")


@given(
    parsers.parse(
        'a bead "{bead}" that mentions "{ref}" in a sentence about declarations'
    )
)
def given_bead_that_only_mentions_a_ref(
    world: dict[str, Any], bead: str, ref: str
) -> None:
    """Bead `.80` wrote exactly this while describing the parser, and was scoped."""
    _declare(
        world,
        bead,
        f"It is serialised until it declares `refs: <ref_id>`, {ref} being "
        "the example.",
    )


@given(
    parsers.parse(
        'a bead "{bead}" declaring the node scopes "{first} {second}" without a comma'
    )
)
def given_bead_declaring_two_refs_without_a_comma(
    world: dict[str, Any], bead: str, first: str, second: str
) -> None:
    _declare(world, bead, f"Do the work.\nrefs: {first} {second}")


@given(
    parsers.parse(
        'an override placing "{left}" and "{right}" in parallel with a reason '
        "and an exit condition"
    )
)
def given_parallel_override(world: dict[str, Any], left: str, right: str) -> None:
    world["overrides"].append(
        WaveOverride(
            beads=(left, right),
            decision="parallel",
            reason="the owner accepts the collision risk for one wave",
            until="BDL-061 S6 closes",
        )
    )


@when("the wave shape is decided")
def when_decided(world: dict[str, Any]) -> None:
    world["plan"] = plan_waves(
        world["beads"],
        conn=world["conn"],
        overrides=world["overrides"],
        environment=world["environment"],
        axes=world["axes"],
    )


def _wave_of(world: dict[str, Any], bead: str) -> int:
    for wave in world["plan"].waves:
        if bead in wave.beads:
            return wave.index
    msg = f"bead {bead!r} was placed in no wave at all"
    raise AssertionError(msg)


@then(parsers.parse('"{left}" and "{right}" are in the same wave'))
def then_same_wave(world: dict[str, Any], left: str, right: str) -> None:
    assert _wave_of(world, left) == _wave_of(world, right)


@then(parsers.parse('"{left}" and "{right}" are in different waves'))
def then_different_waves(world: dict[str, Any], left: str, right: str) -> None:
    assert _wave_of(world, left) != _wave_of(world, right)


@then(parsers.parse('the decision names "{reason}" over "{detail}"'))
def then_names_reason_over(world: dict[str, Any], reason: str, detail: str) -> None:
    assert reason == REASON_SHARED_NODE
    assert any(
        c.reason == reason and c.detail == detail for c in world["plan"].conflicts
    )


@then(parsers.parse('the decision names "{reason}" for "{bead}"'))
def then_names_reason_for(world: dict[str, Any], reason: str, bead: str) -> None:
    assert reason == REASON_UNRESOLVED_SCOPE
    assert any(
        c.reason == reason and bead in (c.left, c.right)
        for c in world["plan"].conflicts
    )
    assert any(f"{bead}" in finding for finding in world["plan"].findings)


@then(parsers.parse("the override reports that it changed {count:d} decision"))
def then_override_changed(world: dict[str, Any], count: int) -> None:
    outcomes = world["plan"].overrides
    assert len(outcomes) == 1
    assert outcomes[0].changed == count
    assert not outcomes[0].inert


@then("the override is reported as inert")
def then_override_inert(world: dict[str, Any]) -> None:
    outcomes = world["plan"].overrides
    assert len(outcomes) == 1
    assert outcomes[0].inert
    assert outcomes[0].changed == 0
    assert any("inert" in finding for finding in world["plan"].findings)


@then(
    "the wave names the graph files, the working tree, the commit gate, the "
    "landing order, the focus document, the doc baseline and the tracker id space"
)
def then_names_media(world: dict[str, Any]) -> None:
    named = {medium.name for medium in world["plan"].shared_media}
    assert named == {
        MEDIUM_GRAPH_FILES,
        MEDIUM_WORKING_TREE,
        MEDIUM_COMMIT_GATE,
        MEDIUM_LANDING_ORDER,
        MEDIUM_FOCUS_DOCUMENT,
        MEDIUM_DOC_BASELINE,
        MEDIUM_TRACKER_IDS,
    }
    for medium in world["plan"].shared_media:
        assert medium.evidence
        assert medium.statement


@then("exactly one bead of the wave owns the combined-tree result")
def then_one_gate_owner(world: dict[str, Any]) -> None:
    for wave in world["plan"].waves:
        assert wave.gate_owner in wave.beads


@then("every medium the wave names carries a verdict of its own")
def then_every_medium_checked(world: dict[str, Any]) -> None:
    """A medium stated and not checked is the defect BDL-061.80 closed."""
    plan = world["plan"]
    stated = {medium.name for medium in plan.shared_media}
    checked = {check.medium for check in plan.media_checks}
    assert stated
    assert stated <= checked
    for check in plan.media_checks:
        assert check.status != STATUS_NOT_APPLICABLE
        assert check.detail


@then(parsers.parse('the wave reports "{medium}" as unmeasured'))
def then_medium_unmeasured(world: dict[str, Any], medium: str) -> None:
    check = next(c for c in world["plan"].media_checks if c.medium == medium)
    assert check.status == STATUS_UNMEASURED
    assert any(f"medium_unmeasured: {medium}" in f for f in world["plan"].findings)


@then(parsers.parse('the wave reports "{medium}" as failed'))
def then_medium_failed(world: dict[str, Any], medium: str) -> None:
    check = next(c for c in world["plan"].media_checks if c.medium == medium)
    assert check.status == STATUS_FAILED
    assert any(f"medium_failed: {medium}" in f for f in world["plan"].findings)


@then("the plan is clean")
def then_plan_clean(world: dict[str, Any]) -> None:
    assert world["plan"].findings == ()
    assert world["plan"].exit_code == 0


@then("the plan is not clean")
def then_plan_not_clean(world: dict[str, Any]) -> None:
    assert world["plan"].findings
    assert world["plan"].exit_code == 1


@then("no wave holds more than one bead")
def then_no_concurrent_wave(world: dict[str, Any]) -> None:
    assert max(len(wave.beads) for wave in world["plan"].waves) == 1


@then("every bead is told the clean room it owes, named after its own id")
def then_every_bead_owes_a_room(world: dict[str, Any]) -> None:
    """One room per bead, and no two beads sharing a path.

    BDL-UX #235: two concurrent agents each built a clean room at the same path
    and one measurement was taken over its neighbour's untracked files. A room
    whose name cannot say whose it is is a shared directory with a reassuring
    name.
    """
    beads = [bead for wave in world["plan"].waves for bead in wave.beads]
    rooms = [room_for(bead) for bead in beads]
    assert len(set(rooms)) == len(beads)
    for bead, room in zip(beads, rooms, strict=True):
        assert bead in room


# --- BDL-UX #232 / #234: the declaration held against the recorded derivation ---


#: The names a Given spells inside double quotes.
_QUOTED = re.compile(r'"([^"]+)"')


def _axes(world: dict[str, Any], **changes: Any) -> None:
    """Replace the work item's recorded axes, keeping what was already given."""
    current = world["axes"] or WorkItemAxes(
        work_item="BDL-000", document="docs/BDL-000/RFC.md", seed="none"
    )
    world["axes"] = replace(current, reason=None, **changes)


@given(parsers.re(r'the work item keeps (?P<nodes>[^:]+) in scope$'))
def given_work_item_keeps(world: dict[str, Any], nodes: str) -> None:
    """One step for every length of list, so no two parsers race for one line."""
    _axes(world, kept=frozenset(_QUOTED.findall(nodes)))


@given(parsers.parse('the work item keeps "{kept}" in scope and rules "{out}" out'))
def given_work_item_rules_one_out(world: dict[str, Any], kept: str, out: str) -> None:
    _axes(world, kept=frozenset({kept}), ruled_out=frozenset({out}))


@given(parsers.parse('the work item records an axis "{axis}" that names no node'))
def given_unattributed_axis(world: dict[str, Any], axis: str) -> None:
    _axes(world, unattributed=(axis,))


@then(parsers.parse('the plan reports "{node}" as declared by no bead of that wave'))
def then_unguarded(world: dict[str, Any], node: str) -> None:
    plan = world["plan"]
    assert any(node in gap.nodes for gap in plan.unguarded_axes)
    assert any(
        finding.startswith(FINDING_UNGUARDED_AXIS) and node in finding
        for finding in plan.findings
    )


@then(
    parsers.parse('the plan reports "{bead}" declaring "{ref}" outside the approved axes')
)
def then_declared_outside(world: dict[str, Any], bead: str, ref: str) -> None:
    plan = world["plan"]
    assert any(
        a.bead_id == bead and a.ref == ref and a.verdict == AXIS_RULED_OUT
        for a in plan.agreements
    )
    assert any(
        finding.startswith(FINDING_DECLARED_OUTSIDE) and bead in finding
        for finding in plan.findings
    )


@then(parsers.parse('the plan states "{ref}" as a node the derivation did not reach'))
def then_not_derived(world: dict[str, Any], ref: str) -> None:
    assert any(
        a.ref == ref and a.verdict == AXIS_NOT_DERIVED
        for a in world["plan"].agreements
    )


@then(parsers.parse('the plan reports no finding against "{bead}" for declaring it'))
def then_no_finding_for_bead(world: dict[str, Any], bead: str) -> None:
    """`impact` under-reports (BDL-UX #225), so an absent row accuses nobody."""
    assert not any(
        finding.startswith(FINDING_DECLARED_OUTSIDE) and bead in finding
        for finding in world["plan"].findings
    )


@then(parsers.parse('the plan states the axis "{axis}" as compared against nothing'))
def then_axis_not_compared(world: dict[str, Any], axis: str) -> None:
    assert any(
        a.ref == axis and a.verdict == AXIS_NOT_ATTRIBUTED
        for a in world["plan"].agreements
    )


@then("the plan states that it compared the declarations against no derivation")
def then_nothing_compared(world: dict[str, Any]) -> None:
    plan = world["plan"]
    assert plan.axes.reason
    assert any(
        finding.startswith(FINDING_NOT_COMPARED) and plan.axes.reason in finding
        for finding in plan.findings
    )


def _remedy(world: dict[str, Any], bead: str) -> str:
    scope = next(s for s in world["plan"].scopes if s.bead_id == bead)
    return remedy_for(scope.unresolved, axes=world["plan"].axes)


@then(parsers.parse('the remedy for "{bead}" says this check cannot tell the two apart'))
def then_remedy_admits_ambiguity(world: dict[str, Any], bead: str) -> None:
    remedy = _remedy(world, bead)
    assert "cannot tell" in remedy
    assert any(remedy in finding for finding in world["plan"].findings)


@then(
    parsers.parse(
        'the remedy for "{bead}" states the prose case as well as the declaration case'
    )
)
def then_remedy_states_both(world: dict[str, Any], bead: str) -> None:
    """#234: the printed remedy told nn4c to promote a sentence it wrote on purpose."""
    remedy = _remedy(world, bead)
    assert "prose" in remedy
    assert "start of its own line" in remedy


@then(parsers.parse('the remedy for "{bead}" names the document the axes were read from'))
def then_remedy_names_document(world: dict[str, Any], bead: str) -> None:
    assert world["plan"].axes.document in _remedy(world, bead)


# ---------------------------------------------------------------------------
# BDL-UX #250 and #245 — what the approval list is, and what its remedy asks for
# ---------------------------------------------------------------------------


@given(parsers.parse('the work item derived over "{node}" and rules on it nowhere'))
def given_swept_target(world: dict[str, Any], node: str) -> None:
    """Provenance: the `Derived by` field ran over a file this node owns."""
    _axes(world, targets=frozenset({node}))


@given("three beads each declaring the work item's whole approved set")
def given_three_beads_with_the_union(world: dict[str, Any]) -> None:
    """The old remedy, performed exactly: `axes --refs` renders one line."""
    union = "billing, shipping, invoicing"
    _axes(world, kept=frozenset({"billing", "shipping", "invoicing"}))
    for bead in ("alpha", "beta", "gamma"):
        _declare(world, bead, f"Do the work.\nrefs: {union}")


@then(parsers.parse('the plan does not approve "{node}"'))
def then_not_approved(world: dict[str, Any], node: str) -> None:
    assert node not in world["plan"].axes.approved


@then(
    parsers.parse('the plan does not report "{node}" as declared by no bead of that wave')
)
def then_no_gap_for(world: dict[str, Any], node: str) -> None:
    assert not any(node in gap.nodes for gap in world["plan"].unguarded_axes)


@then(parsers.parse('the plan states "{ref}" as swept and not ruled on'))
def then_swept_undecided(world: dict[str, Any], ref: str) -> None:
    """Different from `not_derived`, which would say it was never reached."""
    assert any(
        agreement.ref == ref and agreement.verdict == AXIS_SWEPT_UNDECIDED
        for agreement in world["plan"].agreements
    )


def _gap_finding(world: dict[str, Any]) -> str:
    return next(
        finding
        for finding in world["plan"].findings
        if finding.startswith(FINDING_UNGUARDED_AXIS)
    )


@then("the remedy for the unguarded axis derives each bead's own scope")
def then_gap_remedy_is_per_bead(world: dict[str, Any]) -> None:
    finding = _gap_finding(world)
    assert "beadloom impact" in finding
    assert "the files that bead changes" in finding


@then("the remedy for the unguarded axis does not prescribe the work item's whole set")
def then_gap_remedy_is_not_the_union(world: dict[str, Any]) -> None:
    """#245: performed exactly, that sentence collapses the plan it is printed on."""
    finding = _gap_finding(world)
    assert "generate each bead's `refs:` from the `## Axes` section" not in finding
    assert "collapses every wave to a wave of one" in finding


@given(parsers.parse('the focus document carries a row for "{first}" only'))
def given_focus_document_names_one(world: dict[str, Any], first: str) -> None:
    """One row, and the other bead of the wave writes into the prose beside it."""
    world["environment"] = replace(
        world["environment"],
        focus_documents=(
            FocusDocument(
                path=".claude/development/docs/features/KEY/ACTIVE.md",
                kind="ACTIVE",
                row_cells=("Bead", first),
            ),
        ),
    )


@given(parsers.parse('the focus document carries a row for "{first}" and "{second}"'))
def given_focus_document_names_both(
    world: dict[str, Any], first: str, second: str
) -> None:
    world["environment"] = replace(
        world["environment"],
        focus_documents=(
            FocusDocument(
                path=".claude/development/docs/features/KEY/ACTIVE.md",
                kind="ACTIVE",
                row_cells=("Bead", first, second),
            ),
        ),
    )


@given("the routes of this flow write no document in common")
def given_no_shared_document(world: dict[str, Any]) -> None:
    """An empty population is a real observation, the way an empty lock site is."""
    world["environment"] = replace(world["environment"], focus_documents=())


@then("the wave names the focus document among the media it did not decide")
def then_names_focus_document(world: dict[str, Any]) -> None:
    named = {medium.name for medium in world["plan"].shared_media}
    assert MEDIUM_FOCUS_DOCUMENT in named
    medium = next(
        m for m in world["plan"].shared_media if m.name == MEDIUM_FOCUS_DOCUMENT
    )
    assert medium.statement
    assert medium.evidence


@then(parsers.parse('the wave reports "{medium}" as passed'))
def then_medium_passed(world: dict[str, Any], medium: str) -> None:
    check = next(c for c in world["plan"].media_checks if c.medium == medium)
    assert check.status == STATUS_PASSED
    assert check.detail


@then(
    parsers.parse(
        'the failure names "{bead}" as writing into a document it has no row in'
    )
)
def then_failure_names_bead(world: dict[str, Any], bead: str) -> None:
    check = next(
        c for c in world["plan"].media_checks if c.medium == MEDIUM_FOCUS_DOCUMENT
    )
    assert bead in check.detail
    assert "ACTIVE.md" in check.detail


@given("a neighbour added a node to the graph file and nobody reindexed")
def given_graph_ahead_of_index(world: dict[str, Any]) -> None:
    """The self-reference, as a wave meets it: the plan's own input has moved."""
    world["environment"] = replace(
        world["environment"],
        graph_input=GraphInput(
            files=(
                GraphFile(
                    path=".beadloom/_graph/services.yml",
                    nodes=("billing", "reporting", "shipping"),
                ),
            ),
            indexed=frozenset({"billing", "shipping"}),
        ),
    )


@given("the graph directory of this project declares no node")
def given_graph_declares_nothing(world: dict[str, Any]) -> None:
    """A real observation of an empty population, the way an empty lock site is."""
    world["environment"] = replace(world["environment"], graph_input=GraphInput())


@then("the wave names the graph files among the media it did not decide")
def then_names_graph_files(world: dict[str, Any]) -> None:
    medium = next(
        m for m in world["plan"].shared_media if m.name == MEDIUM_GRAPH_FILES
    )
    assert medium.statement
    assert medium.evidence


@then("the failure names the node the plan could not have compared")
def then_failure_names_the_node(world: dict[str, Any]) -> None:
    check = next(
        c for c in world["plan"].media_checks if c.medium == MEDIUM_GRAPH_FILES
    )
    assert "reporting" in check.detail
    assert "reindex" in check.detail


@given("this project declares each of its nodes in a file of its own")
def given_one_file_per_node(world: dict[str, Any]) -> None:
    """The layout BDL-UX #265 moved this repository to."""
    world["environment"] = replace(
        world["environment"],
        graph_input=GraphInput(
            files=(
                GraphFile(path=".beadloom/_graph/billing.yml", nodes=("billing",)),
                GraphFile(path=".beadloom/_graph/shipping.yml", nodes=("shipping",)),
            ),
            indexed=frozenset({"billing", "shipping"}),
        ),
    )


@then("the pass says two node-adding beads write two files")
def then_pass_says_the_collision_cannot_be_attempted(world: dict[str, Any]) -> None:
    """The sharing is gone, so the pass says so rather than naming a shared file."""
    check = next(
        c for c in world["plan"].media_checks if c.medium == MEDIUM_GRAPH_FILES
    )
    assert "a file of its own" in check.detail
    assert "cannot be attempted" in check.detail


@then("the pass still names the file it could not read")
def then_pass_still_names_what_it_cannot_reach(world: dict[str, Any]) -> None:
    """The half no plan can reach moved rather than disappearing."""
    check = next(
        c for c in world["plan"].media_checks if c.medium == MEDIUM_GRAPH_FILES
    )
    assert "no graph this plan could read" in check.detail


@then("the pass names the file a bead that adds a node writes")
def then_pass_names_the_file(world: dict[str, Any]) -> None:
    """The half no plan can observe is stated rather than left out of the pass."""
    check = next(
        c for c in world["plan"].media_checks if c.medium == MEDIUM_GRAPH_FILES
    )
    assert ".beadloom/_graph/services.yml" in check.detail
    assert "adds" in check.detail
