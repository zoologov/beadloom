"""Step implementations for the running-work comparison of a wave plan (BDL-UX #283).

The command is run for real, over a real graph index, and only the ``bd`` binary is
replaced — by a tracker that answers in bd's own JSON spelling: ``bd list`` writes a
row's dependencies as ``type`` and ``depends_on_id`` and carries ``status``, ``bd
ready`` excludes a bead in progress, and ``bd show`` returns the words a bead
declares its scope in. The defect lived in exactly that difference between the two
lists, so a double that did not reproduce it would test nothing.

The module is named ``test_*`` so default pytest collection picks the scenarios up.
"""

from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING, Any

import pytest
from click.testing import CliRunner
from pytest_bdd import given, parsers, scenarios, then, when

from beadloom.infrastructure.db import create_schema, open_db
from beadloom.services.bd_seam import BdResult
from beadloom.services.cli import main

if TYPE_CHECKING:
    from pathlib import Path

scenarios("../features/wave_running_work.feature")

#: bd's own words for the two states this comparison distinguishes.
_OPEN = "open"
_IN_PROGRESS = "in_progress"


class _Tracker:
    """A tracker answering the three call forms `beadloom waves` makes."""

    def __init__(self) -> None:
        self.beads: dict[str, dict[str, Any]] = {}
        self.unshowable: set[str] = set()
        self.readable = True

    def add(self, bead: str, *, status: str, parent: str = "", refs: str = "") -> None:
        self.beads[bead] = {"status": status, "parent": parent, "refs": refs}

    def __call__(self, args: list[str], *, cwd: str | None = None) -> BdResult:
        if args[0] in ("list", "ready") and not self.readable:
            return BdResult(returncode=1, stdout="", stderr="no tracker")
        if args[0] == "list":
            return BdResult(returncode=0, stdout=json.dumps(self._rows()), stderr="")
        if args[0] == "ready":
            ready = [
                {"id": bead}
                for bead, row in sorted(self.beads.items())
                if row["status"] == _OPEN
            ]
            return BdResult(returncode=0, stdout=json.dumps(ready), stderr="")
        return self._show(args[1])

    def _rows(self) -> list[dict[str, Any]]:
        return [
            {
                "id": bead,
                "status": row["status"],
                "parent": row["parent"] or None,
                "dependencies": (
                    [
                        {
                            "issue_id": bead,
                            "depends_on_id": row["parent"],
                            "type": "parent-child",
                        }
                    ]
                    if row["parent"]
                    else []
                ),
            }
            for bead, row in sorted(self.beads.items())
        ]

    def _show(self, bead: str) -> BdResult:
        if bead not in self.beads or bead in self.unshowable:
            return BdResult(returncode=1, stdout="", stderr=f"no issue found: {bead}")
        row = self.beads[bead]
        record = {
            "id": bead,
            "title": f"[{bead}] work",
            "status": row["status"],
            "description": f"do the work.\nrefs: {row['refs']}" if row["refs"] else "",
            "dependencies": [],
        }
        return BdResult(returncode=0, stdout=json.dumps([record]), stderr="")


@pytest.fixture()
def world(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    tracker = _Tracker()
    monkeypatch.setattr("beadloom.services.bd_seam.run_bd", tracker, raising=True)
    return {"tracker": tracker, "project": tmp_path / "proj"}


@given(parsers.parse('a project whose graph holds the nodes "{first}" and "{second}"'))
def given_project(world: dict[str, Any], first: str, second: str) -> None:
    project: Path = world["project"]
    graph = project / ".beadloom" / "_graph"
    graph.mkdir(parents=True)
    refs = (first, second)
    (graph / "services.yml").write_text(
        "nodes:\n"
        + "".join(
            f"  - ref_id: {ref}\n    kind: feature\n    source: src/{ref}/\n"
            for ref in refs
        ),
        encoding="utf-8",
    )
    conn = open_db(project / ".beadloom" / "beadloom.db")
    create_schema(conn)
    for ref in refs:
        conn.execute(
            "INSERT INTO nodes (ref_id, kind, summary, source) VALUES (?, ?, ?, ?)",
            (ref, "feature", ref, f"src/{ref}/"),
        )
    conn.commit()
    conn.close()


@given(
    parsers.parse(
        'a work item "{item}" holding a bead "{bead}" in progress declaring "{ref}"'
    )
)
def given_running_bead(world: dict[str, Any], item: str, bead: str, ref: str) -> None:
    tracker: _Tracker = world["tracker"]
    tracker.add(item, status=_OPEN)
    tracker.add(bead, status=_IN_PROGRESS, parent=item, refs=ref)


@given(
    parsers.parse('the work item "{item}" holds a ready bead "{bead}" declaring "{ref}"')
)
def given_ready_bead(world: dict[str, Any], item: str, bead: str, ref: str) -> None:
    world["tracker"].add(bead, status=_OPEN, parent=item, refs=ref)


@given(parsers.parse('the tracker cannot show the bead "{bead}"'))
def given_unshowable(world: dict[str, Any], bead: str) -> None:
    world["tracker"].unshowable.add(bead)


@given(
    parsers.parse('a bead "{bead}" declaring "{ref}" and a tracker that lists nothing')
)
def given_unlisted_tracker(world: dict[str, Any], bead: str, ref: str) -> None:
    tracker: _Tracker = world["tracker"]
    tracker.add(bead, status=_OPEN, refs=ref)
    tracker.readable = False


def _run(world: dict[str, Any], args: list[str]) -> None:
    project = str(world["project"])
    human = CliRunner().invoke(main, ["waves", *args, "--project", project])
    as_json = CliRunner().invoke(main, ["waves", *args, "--json", "--project", project])
    assert human.exit_code in (0, 1), human.output
    world["human"] = human
    world["payload"] = json.loads(as_json.stdout)


@when(parsers.parse('the plan is derived from the work item "{item}"'))
def when_derived_from(world: dict[str, Any], item: str) -> None:
    _run(world, ["--parent", item])


@when(parsers.re(r"the plan is asked about the beads (?P<beads>.+)"))
def when_asked_about(world: dict[str, Any], beads: str) -> None:
    _run(world, re.findall(r'"([^"]+)"', beads))


def _summary(world: dict[str, Any]) -> str:
    return str(world["human"].stdout.splitlines()[0])


@then(
    parsers.parse(
        '"{planned}" is serialised against the running bead "{running}" over "{detail}"'
    )
)
def then_serialised_against_running(
    world: dict[str, Any], planned: str, running: str, detail: str
) -> None:
    conflicts = world["payload"]["running"]["conflicts"]
    assert {
        "planned": planned,
        "running": running,
        "reason": "shared_node",
        "detail": detail,
    } in conflicts
    assert f"{planned} waits for {running} — shared_node: {detail}" in world["human"].stdout


@then("that serialisation is reported apart from the plan's own serialisations")
def then_apart(world: dict[str, Any]) -> None:
    assert world["payload"]["conflicts"] == []
    assert "Serialised because:" not in world["human"].stdout
    assert "Serialised against running work:" in world["human"].stdout


@then(
    parsers.re(
        r"the summary line states (?P<count>\d+) serialisations? against "
        r"(?P<running>\d+) running beads?"
    )
)
def then_summary_counts(world: dict[str, Any], count: str, running: str) -> None:
    assert f"{count} against {running} running bead(s)" in _summary(world)


@then("the serialisation against running work is not a finding")
def then_not_a_finding(world: dict[str, Any]) -> None:
    assert not any("running" in finding for finding in world["payload"]["findings"])


@then("the plan says no bead of it conflicts with the running work")
def then_no_conflict_with_running(world: dict[str, Any]) -> None:
    assert world["payload"]["running"]["compared"] == ["running"]
    assert "no bead of this plan conflicts with them" in world["human"].stdout


@then(
    parsers.re(
        r"the summary line states (?P<count>\d+) running beads? it did not compare "
        r"against"
    )
)
def then_summary_not_compared(world: dict[str, Any], count: str) -> None:
    assert f"({count} not compared)" in _summary(world)


@then(parsers.parse('the plan carries a finding naming "{bead}" as not compared'))
def then_not_compared_finding(world: dict[str, Any], bead: str) -> None:
    findings = world["payload"]["findings"]
    assert any(
        finding.startswith("running_not_compared") and bead in finding
        for finding in findings
    ), findings
    assert world["payload"]["running"]["not_compared"] == [bead]
    assert world["human"].exit_code == 1


@then(
    parsers.parse(
        '"{left}" and "{right}" are serialised within the plan over "{detail}"'
    )
)
def then_serialised_within(
    world: dict[str, Any], left: str, right: str, detail: str
) -> None:
    pairs = {
        (c["left"], c["right"], c["reason"], c["detail"])
        for c in world["payload"]["conflicts"]
    }
    first, second = sorted((left, right))
    assert (first, second, "shared_node", detail) in pairs


@then("the summary line says running work was not compared")
def then_summary_not_gathered(world: dict[str, Any]) -> None:
    assert "running work not compared" in _summary(world)
