"""Boundary guards for the duty check (BDL-068 S4, `beadloom-0mdo.27`).

The two directions and the limit are stated as scenarios in
`tests/acceptance/features/role_duties.feature`. What is here is the edge each
scenario would make unreadable if it were written as one: a marker that declares
nothing, a duty text living outside a role file, the population the report must
name on a clean run, and this repository's own duties.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from beadloom.onboarding.agentic_flow_setup import COMMAND_FILES
from beadloom.onboarding.role_composer import ROLE_NAMES
from beadloom.onboarding.role_duties import duty_report

_FLOW_YML = "tools:\n- claude\narchitecture:\n- ddd\nstack:\n- python\n"

_REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture()
def project(tmp_path: Path) -> Path:
    """A project with a flow configured and an empty project layer."""
    (tmp_path / ".beadloom").mkdir()
    (tmp_path / ".beadloom" / "flow.yml").write_text(_FLOW_YML, encoding="utf-8")
    return tmp_path


def _fragment(project: Path, kind: str, name: str, body: str) -> None:
    directory = project / ".beadloom" / "flow" / kind
    directory.mkdir(parents=True, exist_ok=True)
    (directory / f"{name}.md").write_text(body, encoding="utf-8")


def test_a_duty_marker_naming_no_performer_declares_nothing(project: Path) -> None:
    """A `duty=` with no `roles=` is reported, never read as a carriage marker.

    The two markers differ by one attribute, so a typo would otherwise turn a
    declaration into a silent claim that the duty is already delivered — the
    check satisfying itself.
    """
    _fragment(project, "commands", "coordinator", "<!-- beadloom:duty=example-duty -->")

    report = duty_report(project)

    malformed = [f for f in report.findings if f.kind == "malformed"]
    assert [f.duty for f in malformed] == ["example-duty"]
    assert "example-duty" not in {d.duty for d in report.declarations}
    assert not [pair for pair in report.carried if pair[1] == "example-duty"]


def test_a_duty_text_outside_a_role_file_is_still_read(project: Path) -> None:
    """A `carries` marker in a slash command is a duty somebody wrote.

    Recording carriage only for role files would drop it, and a check that
    silently drops a duty because of where it sits is the class this check
    exists to report.
    """
    _fragment(
        project, "commands", "checkpoint", "<!-- beadloom:carries=example-duty -->"
    )

    report = duty_report(project)

    undeclared = [f for f in report.findings if f.kind == "undeclared"]
    assert [(f.duty, f.role) for f in undeclared] == [
        ("example-duty", "commands/checkpoint")
    ]


def test_a_role_is_not_satisfied_by_another_roles_carriage(project: Path) -> None:
    """Delivery is judged per role, not per project."""
    _fragment(
        project,
        "commands",
        "coordinator",
        "<!-- beadloom:duty=example-duty roles=dev,review -->",
    )
    _fragment(project, "roles", "dev", "<!-- beadloom:carries=example-duty -->")

    report = duty_report(project)

    assert [(f.kind, f.role) for f in report.findings] == [
        ("undelivered", "review")
    ]


def test_the_report_names_its_limit_on_a_clean_run(project: Path) -> None:
    """The launch prompt is named on a clean run too.

    A check that speaks only when it finds something hands the reader a clean
    list, and a clean list is trusted and stopped at.

    The project declares nothing of its own here. It is no longer a project that
    declares NOTHING: since BDL-UX #228 the shipped coordinator declares the
    `clean-room` duty for all five roles, so every project running this flow
    inherits one declaration and one carriage per role.
    """
    report = duty_report(project)

    assert report.findings == ()
    assert {d.duty for d in report.declarations} == {"clean-room"}
    prompts = [e for e in report.not_inspected if "prompt" in e.source]
    assert len(prompts) == 1
    assert "not an artifact" in prompts[0].why


def test_the_inspected_corpus_is_every_agent_addressed_artifact(project: Path) -> None:
    """Roles, slash commands and CLAUDE.md — derived, never listed."""
    report = duty_report(project)

    assert len(report.inspected) == len(ROLE_NAMES) + len(COMMAND_FILES) + 1
    assert set(report.inspected) >= {f"roles/{role}" for role in ROLE_NAMES}


def test_every_duty_this_repository_declares_reaches_the_roles_it_names() -> None:
    """Beadloom's own flow, checked against itself.

    A self-fact rather than a fixture: it holds today because this repository
    declares no duty yet, and it goes on holding when `beadloom-67t1` declares
    the example-duty duty and writes it into the role cores. A regression there is
    exactly the finding this check exists to make.
    """
    report = duty_report(_REPO_ROOT)

    assert report.findings == ()


def test_the_vendored_role_snapshot_is_not_reported_as_unreachable(
    project: Path,
) -> None:
    """A byte-identical copy of a composed role is not a place a duty can hide.

    `templates/agentic_flow/agents/*.md.txt` is the vendored snapshot of the
    live `.claude/agents/*.md`, held byte-identical by
    `tests/test_core_roles.py::TestVendoringDriftGuard` and dropped verbatim into
    an adopter's `.claude/agents/` by the plain scaffold path. It carries every
    marker the composed role carries, so subtraction listed all five the moment
    a role core first declared a duty (`beadloom-67t1`) — under a `why` that says
    the duties in it reach no role, which is false on both counts: the marker is
    inspected in its composed form, and the file itself reaches an adopter's
    roles directory.
    """
    report = duty_report(project)

    vendored = [
        entry
        for entry in report.not_inspected
        if "agentic_flow/agents/" in entry.source
    ]
    assert vendored == [], [entry.source for entry in vendored]
