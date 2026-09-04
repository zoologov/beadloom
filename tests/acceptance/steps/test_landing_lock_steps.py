"""Step implementations for the landing-lock suite (BDL-068 S5, BDL-UX #194, #237).

Thin, like every other acceptance module here: the derivation runs for real over
text the steps build, and the planner runs for real over bead records. Nothing
invokes ``bd`` — the point of the check is what an agent is TOLD about the lock,
which is a property of the artifacts and not of the tracker.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from beadloom.application.waves import (
    GATE_COMMIT_SCOPED,
    MEDIUM_LANDING_ORDER,
    SHARED_MEDIA,
    STATUS_FAILED,
    STATUS_PASSED,
    STATUS_UNMEASURED,
    BeadRecord,
    WaveEnvironment,
    lock_sites,
    plan_waves,
)
from beadloom.infrastructure.db import create_schema, open_db

if TYPE_CHECKING:
    from pathlib import Path

scenarios("../features/landing_lock.feature")


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
        "artifacts": [],
        "sites": None,
        "plan": None,
        "environment": None,
    }


@given(parsers.parse('a bead "{bead}" declaring the node scope "{ref}"'))
def given_bead_with_scope(world: dict[str, Any], bead: str, ref: str) -> None:
    world["beads"].append(
        BeadRecord(bead_id=bead, declaration=f"Do the work.\nrefs: {ref}")
    )


@given("the shared media were measured and are clean")
def given_media_measured(world: dict[str, Any]) -> None:
    world["environment"] = WaveEnvironment(
        tree_changed_paths=(),
        commit_gate=GATE_COMMIT_SCOPED,
        doc_baseline_stale_pairs=0,
        landing_lock_sites=(),
    )


@given(parsers.parse('a flow artifact instructing "{command}" before a commit'))
def given_artifact_instructing_before(world: dict[str, Any], command: str) -> None:
    world["artifacts"].append(
        (
            f".claude/agents/dev-{len(world['artifacts'])}.md",
            f"Before you commit, run `{command}`.\n",
        )
    )


@given(parsers.parse('a flow artifact instructing "{command}" after a commit'))
def given_artifact_instructing_after(world: dict[str, Any], command: str) -> None:
    world["artifacts"].append(
        (
            f".claude/agents/dev-{len(world['artifacts'])}.md",
            f"After you commit, run `{command}`.\n",
        )
    )


@given("no flow artifact instructs the landing lock at all")
def given_no_artifact(world: dict[str, Any]) -> None:
    world["artifacts"] = []


@when("the landing lock sites are derived")
def when_sites_derived(world: dict[str, Any]) -> None:
    world["sites"] = lock_sites(world["artifacts"])


@when("the wave shape is decided")
def when_decided(world: dict[str, Any]) -> None:
    environment = world["environment"]
    if environment is not None:
        environment = WaveEnvironment(
            tree_changed_paths=environment.tree_changed_paths,
            commit_gate=environment.commit_gate,
            doc_baseline_stale_pairs=environment.doc_baseline_stale_pairs,
            landing_lock_sites=lock_sites(world["artifacts"]),
        )
    world["plan"] = plan_waves(
        world["beads"], conn=world["conn"], environment=environment
    )


@then("the wave names the landing order among its shared media")
def then_names_landing_order(world: dict[str, Any]) -> None:
    assert MEDIUM_LANDING_ORDER in {medium.name for medium in SHARED_MEDIA}


@then("the landing-order statement says the exclusion rests on the derived scopes")
def then_statement_names_the_scopes(world: dict[str, Any]) -> None:
    statement = next(
        medium.statement
        for medium in SHARED_MEDIA
        if medium.name == MEDIUM_LANDING_ORDER
    )
    assert "scope" in statement
    assert "--holder" in statement


@then(parsers.parse('the site is reported as "{defect}"'))
def then_site_reported_as(world: dict[str, Any], defect: str) -> None:
    assert any(defect in site.defects for site in world["sites"]), world["sites"]


@then("no site is reported as defective")
def then_no_defective_site(world: dict[str, Any]) -> None:
    assert world["sites"], "the derivation found no site at all"
    assert all(not site.defects for site in world["sites"]), world["sites"]


def _landing_check(world: dict[str, Any]) -> Any:
    for check in world["plan"].media_checks:
        if check.medium == MEDIUM_LANDING_ORDER:
            return check
    msg = "the plan carried no landing-order check"
    raise AssertionError(msg)


@then(parsers.parse('the wave reports "{medium}" as failed'))
def then_medium_failed(world: dict[str, Any], medium: str) -> None:
    assert medium == MEDIUM_LANDING_ORDER
    assert _landing_check(world).status == STATUS_FAILED


@then(parsers.parse('the wave reports "{medium}" as unmeasured'))
def then_medium_unmeasured(world: dict[str, Any], medium: str) -> None:
    assert medium == MEDIUM_LANDING_ORDER
    assert _landing_check(world).status == STATUS_UNMEASURED


@then(parsers.parse('the wave reports "{medium}" as passed'))
def then_medium_passed(world: dict[str, Any], medium: str) -> None:
    assert medium == MEDIUM_LANDING_ORDER
    assert _landing_check(world).status == STATUS_PASSED


@then("the landing-order verdict states that it read no instruction")
def then_verdict_states_empty_population(world: dict[str, Any]) -> None:
    assert "no flow artifact" in _landing_check(world).detail


@then("the plan is not clean")
def then_plan_not_clean(world: dict[str, Any]) -> None:
    assert world["plan"].findings
