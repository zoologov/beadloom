"""Step implementations for the S6 wave-shape suite (BDL-061 S6).

Thin by design: every step builds a real graph index and runs the real planner.
The tracker is the one thing that arrives as data — :func:`plan_waves` takes
bead records as an argument precisely so the decision can be exercised without a
``bd`` binary, and so the application layer never reaches up into ``services``.

The module is named ``test_*`` so default pytest collection picks the scenarios
up — the acceptance suite runs inside ``uv run pytest``, not beside it.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from beadloom.application.waves import (
    GATE_COMMIT_SCOPED,
    MEDIUM_COMMIT_GATE,
    MEDIUM_DOC_BASELINE,
    MEDIUM_TRACKER_IDS,
    MEDIUM_WORKING_TREE,
    REASON_SHARED_NODE,
    REASON_UNRESOLVED_SCOPE,
    STATUS_FAILED,
    STATUS_NOT_APPLICABLE,
    STATUS_UNMEASURED,
    BeadRecord,
    WaveEnvironment,
    WaveOverride,
    plan_waves,
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
    for ref in ("billing", "shipping"):
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
    }


def _declare(world: dict[str, Any], bead: str, declaration: str) -> None:
    world["beads"].append(BeadRecord(bead_id=bead, declaration=declaration))


@given(parsers.parse('a bead "{bead}" declaring the node scope "{ref}"'))
def given_bead_with_scope(world: dict[str, Any], bead: str, ref: str) -> None:
    _declare(world, bead, f"Do the work. refs: {ref}")


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
            bead_id=bead, declaration=f"Do the work. refs: {ref}", title=title
        )
    )


@given("the shared media were measured and are clean")
def given_media_measured(world: dict[str, Any]) -> None:
    """Somebody looked at the tree, the hook and the doc baseline, and said so."""
    world["environment"] = WaveEnvironment(
        tree_changed_paths=(),
        commit_gate=GATE_COMMIT_SCOPED,
        doc_baseline_stale_pairs=0,
    )


@given(parsers.parse('a bead "{bead}" declaring no node scope at all'))
def given_bead_without_scope(world: dict[str, Any], bead: str) -> None:
    _declare(world, bead, "Do the work.")


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
    "the wave names the working tree, the commit gate, the doc baseline and the "
    "tracker id space"
)
def then_names_media(world: dict[str, Any]) -> None:
    named = {medium.name for medium in world["plan"].shared_media}
    assert named == {
        MEDIUM_WORKING_TREE,
        MEDIUM_COMMIT_GATE,
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
