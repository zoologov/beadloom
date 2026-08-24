"""Step implementations for the S6 review-independence suite (BDL-061 S6).

Thin by design: every step builds a real graph index and runs the real
assembler. The tracker and git arrive as data — :func:`assemble_brief` takes the
author's notes and the change inventory as arguments precisely so the brief can
be exercised without a ``bd`` binary and without a repository, and so the
application layer never reaches up into ``services``.

The module is named ``test_*`` so default pytest collection picks the scenarios
up — the acceptance suite runs inside ``uv run pytest``, not beside it.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from beadloom.application.review_brief import (
    AuthorNote,
    ReviewBrief,
    assemble_brief,
    release_notes,
)
from beadloom.application.waves import BeadRecord
from beadloom.graph.scenarios import Scenario
from beadloom.infrastructure.db import create_schema, open_db

if TYPE_CHECKING:
    from pathlib import Path

scenarios("../features/review_brief.feature")


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
            "INSERT INTO docs (ref_id, path, kind, hash) VALUES (?, ?, ?, ?)",
            (ref, f"docs/{ref}/SPEC.md", "feature", f"h-{ref}"),
        )
    conn.commit()
    return {
        "conn": conn,
        "record": None,
        "assignment": "",
        "notes": [],
        "changed": set(),
        "measured": True,
        "scenarios": [],
        "brief": None,
        "release": None,
    }


def _brief(world: dict[str, Any]) -> ReviewBrief:
    brief = world["brief"]
    assert isinstance(brief, ReviewBrief), "no brief was assembled"
    return brief


@given(parsers.parse('a bead "{bead}" declaring the node scope "{ref}"'))
def _declare(world: dict[str, Any], bead: str, ref: str) -> None:
    world["assignment"] = f"[{bead}] the assignment\n\nChange the {ref} feature."
    world["record"] = BeadRecord(
        bead_id=bead,
        declaration=f"{world['assignment']}\n\nrefs: {ref}",
        title=f"[{bead}] the assignment",
    )


@given(parsers.parse('the author recorded {count:d} comments on "{bead}"'))
def _comments(world: dict[str, Any], count: int, bead: str) -> None:
    world["notes"] = [
        AuthorNote(text=f"CHECKPOINT: note {index} on {bead}", author="dev")
        for index in range(count)
    ]


@given(parsers.parse('"{path}" changed since the base ref'))
def _changed(world: dict[str, Any], path: str) -> None:
    world["changed"].add(path)


@given("the change inventory could not be measured")
def _unmeasured(world: dict[str, Any]) -> None:
    world["measured"] = False


@given(parsers.parse('a verdict was recorded on "{bead}"'))
def _verdict(world: dict[str, Any], bead: str) -> None:
    world["notes"].append(
        AuthorNote(text=f"REVIEW PASSED: {bead} reads correct", author="review")
    )


@given(parsers.parse('a scenario bound to "{bead}"'))
def _bound_scenario(world: dict[str, Any], bead: str) -> None:
    world["scenarios"].append(
        Scenario(
            name="the billing total is rounded once",
            feature="billing",
            path="tests/acceptance/features/billing.feature",
            line=7,
            beads=(bead,),
            nodes=("billing",),
        )
    )


def _assemble(world: dict[str, Any]) -> ReviewBrief:
    return assemble_brief(
        world["conn"],
        world["record"],
        assignment=world["assignment"],
        changed_paths=frozenset(world["changed"]) if world["measured"] else None,
        notes=world["notes"],
        scenarios=world["scenarios"],
    )


@when("the reviewer's brief is assembled")
def _assemble_step(world: dict[str, Any]) -> None:
    world["brief"] = _assemble(world)


@when("the author's account is requested")
def _request_release(world: dict[str, Any]) -> None:
    world["brief"] = _assemble(world)
    world["release"] = release_notes(world["notes"])


@then(parsers.parse('the brief carries the changed file "{path}"'))
def _carries_change(world: dict[str, Any], path: str) -> None:
    assert path in {changed.path for changed in _brief(world).changed}


@then(parsers.parse('the brief carries the specification document of "{ref}"'))
def _carries_doc(world: dict[str, Any], ref: str) -> None:
    assert f"docs/{ref}/SPEC.md" in {doc.path for doc in _brief(world).docs}


@then("the brief carries no author comment")
def _no_author_text(world: dict[str, Any]) -> None:
    rendered = repr(_brief(world))
    for note in world["notes"]:
        assert note.text not in rendered, "the author's own words reached the brief"


@then(parsers.parse("the brief reports {count:d} author comments withheld"))
def _withheld_count(world: dict[str, Any], count: int) -> None:
    assert _brief(world).withheld.count == count


@then("the brief names the condition that releases them")
def _release_condition(world: dict[str, Any]) -> None:
    condition = _brief(world).withheld.release_condition
    assert condition.strip(), "the withholding named no way out"
    assert "verdict" in condition.lower()


@then("the author's account is released")
def _released(world: dict[str, Any]) -> None:
    outcome = world["release"]
    assert outcome is not None
    assert outcome.refused_reason is None
    assert [note.text for note in outcome.released] == [
        note.text for note in world["notes"]
    ]


@then("the release is refused")
def _refused(world: dict[str, Any]) -> None:
    outcome = world["release"]
    assert outcome is not None
    assert outcome.refused_reason is not None
    assert outcome.released == ()


@then(parsers.parse('the brief names "{path}" as outside the declared scope'))
def _outside_scope(world: dict[str, Any], path: str) -> None:
    outside = {
        changed.path for changed in _brief(world).changed if not changed.in_scope
    }
    assert path in outside


@then("the brief reports the change as unmeasured")
def _unmeasured_reported(world: dict[str, Any]) -> None:
    assert _brief(world).change_measured is False


@then(parsers.parse("the brief carries {count:d} bound scenario"))
def _scenario_count(world: dict[str, Any], count: int) -> None:
    assert len(_brief(world).scenarios) == count


@then("the brief is clean")
def _clean(world: dict[str, Any]) -> None:
    assert _brief(world).findings == ()


@then("the brief is not clean")
def _not_clean(world: dict[str, Any]) -> None:
    assert _brief(world).findings != ()
