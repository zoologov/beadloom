"""Step implementations for the reachability report (BDL-068 S2).

Thin by design, like the S6 steps beside them: every step builds a real project
on disk — a real planning corpus, a real project flow fragment — and runs the
real assembler. What arrives as data is what the application layer must not
reach up for: the tracker's comments and git's answer about the commit range.

The document population is NOT stated by any step. A step puts documents in a
work item's folder and, in one scenario, a project role fragment that names one
of them; whether the report mentions them is the derivation's business. That is
the property the whole change turns on, so no step may assert it into existence.

The module is named ``test_*`` so default pytest collection picks the scenarios
up — the acceptance suite runs inside ``uv run pytest``, not beside it.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from beadloom.application.review_brief import (
    AuthorNote,
    Commit,
    ReviewBrief,
    assemble_brief,
)
from beadloom.application.waves import BeadRecord
from beadloom.infrastructure.db import create_schema, open_db

if TYPE_CHECKING:
    from pathlib import Path

    from beadloom.application.review_brief import Channel

scenarios("../features/review_brief_reachability.feature")

#: The work item folder layout the shipped planning globs find.
_PLANNING_ROOT = (".claude", "development", "docs", "features")


@pytest.fixture()
def world(tmp_path: Path) -> dict[str, Any]:
    """One project on disk, and the bag the steps share."""
    project = tmp_path / "proj"
    (project / ".beadloom").mkdir(parents=True)
    conn = open_db(project / ".beadloom" / "beadloom.db")
    create_schema(conn)
    conn.execute(
        "INSERT INTO nodes (ref_id, kind, summary, source) VALUES (?, ?, ?, ?)",
        ("billing", "feature", "billing", "src/billing/"),
    )
    conn.commit()
    return {
        "conn": conn,
        "project": project,
        "record": BeadRecord(
            bead_id="alpha", declaration="the assignment\n\nrefs: billing", title="alpha"
        ),
        "assignment": "the assignment",
        "notes": [],
        "branch": None,
        "commits": None,
        "since": "",
        "brief": None,
    }


def _brief(world: dict[str, Any]) -> ReviewBrief:
    brief = world["brief"]
    assert isinstance(brief, ReviewBrief), "no brief was assembled"
    return brief


def _channel(world: dict[str, Any], name: str) -> Channel:
    found = _brief(world).reachability.named(name)
    assert found is not None, (
        f"the report names no channel {name!r} — it carries "
        f"{[c.name for c in _brief(world).reachability.channels]}"
    )
    return found


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


@given(parsers.parse('a work item "{key}" carrying the documents "{documents}"'))
def _work_item(world: dict[str, Any], key: str, documents: str) -> None:
    folder = world["project"].joinpath(*_PLANNING_ROOT, key)
    folder.mkdir(parents=True, exist_ok=True)
    for name in (part.strip() for part in documents.split(",")):
        (folder / name).write_text(f"# {name}\n\nThe work item's own text.\n", encoding="utf-8")


@given(parsers.parse('the project\'s own "{role}" role fragment names "{document}"'))
def _project_fragment(world: dict[str, Any], role: str, document: str) -> None:
    fragment = world["project"] / ".beadloom" / "flow" / "roles" / f"{role}.md"
    fragment.parent.mkdir(parents=True, exist_ok=True)
    fragment.write_text(
        f"## This project's standing practice\n\nRead `{document}` before you judge.\n",
        encoding="utf-8",
    )


@given(parsers.parse('the review runs on the branch "{branch}"'))
def _branch(world: dict[str, Any], branch: str) -> None:
    world["branch"] = branch


@given(
    parsers.parse(
        'the reviewed range since "{since}" holds a commit whose body carries {lines:d} line(s)'
    )
)
def _range_with_a_body(world: dict[str, Any], since: str, lines: int) -> None:
    world["since"] = since
    world["commits"] = [
        Commit(sha="0f1e2d3", subject="the fix, and why it is shaped this way", body_lines=lines)
    ]


@given(parsers.parse('the reviewed range since "{since}" holds no commits'))
def _empty_range(world: dict[str, Any], since: str) -> None:
    world["since"] = since
    world["commits"] = []


@given("git gave no answer for the reviewed range")
def _no_git_answer(world: dict[str, Any]) -> None:
    world["commits"] = None


@when("the reviewer's brief is assembled")
def _assemble(world: dict[str, Any]) -> None:
    world["brief"] = assemble_brief(
        world["conn"],
        world["record"],
        assignment=world["assignment"],
        changed_paths=frozenset(),
        measured_since=world["since"],
        notes=world["notes"],
        project_root=world["project"],
        branch=world["branch"],
        commits=world["commits"],
    )


@then(
    parsers.parse('the "{name}" channel was inspected and carries {count:d} item(s)')
)
def _inspected_with(world: dict[str, Any], name: str, count: int) -> None:
    channel = _channel(world, name)
    assert channel.inspected, f"{name!r} reported itself uninspected: {channel.reason}"
    assert channel.carries == count, f"{name!r} carries {list(channel.items)}"


@then(parsers.parse('the "{name}" channel was not inspected'))
def _not_inspected(world: dict[str, Any], name: str) -> None:
    assert not _channel(world, name).inspected


@then(parsers.parse('the "{name}" channel gives its reason'))
def _gives_a_reason(world: dict[str, Any], name: str) -> None:
    assert _channel(world, name).reason.strip(), f"{name!r} stated no reason"


@then(parsers.parse('the "{name}" channel says this command withholds them'))
def _says_withheld(world: dict[str, Any], name: str) -> None:
    reason = _channel(world, name).reason.lower()
    assert "withh" in reason, reason


@then(parsers.parse('the "{name}" channel names "{document}" and the prompt that names it'))
def _names_document_and_prompt(world: dict[str, Any], name: str, document: str) -> None:
    matching = [item for item in _channel(world, name).items if document in item]
    assert matching, f"{name!r} carries {list(_channel(world, name).items)}"
    entry = matching[0]
    _, _, attribution = entry.partition("—")
    assert attribution.strip(), f"{entry!r} names no prompt"


@then(parsers.parse('the "{name}" channel names the range it was read over'))
def _names_the_range(world: dict[str, Any], name: str) -> None:
    assert world["since"] in _channel(world, name).reason


@then(parsers.parse('the "{name}" channel says only the reviewer can see it'))
def _only_the_reviewer(world: dict[str, Any], name: str) -> None:
    assert "you" in _channel(world, name).reason.lower()


@then("the two channels state themselves differently")
def _distinct_statements(world: dict[str, Any]) -> None:
    channels = _brief(world).reachability.channels
    empty = [c for c in channels if c.inspected and c.carries == 0]
    unseen = [c for c in channels if not c.inspected]
    assert empty and unseen, "the scenario built no such pair"
    assert {c.statement() for c in empty}.isdisjoint({c.statement() for c in unseen})
