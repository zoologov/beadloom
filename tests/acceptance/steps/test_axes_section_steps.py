"""Step implementations for BDL-068 S1.4 — the ``## Axes`` section.

Thin by design: each step arranges a real document or a real
:class:`~beadloom.application.impact.ImpactAnswer` and runs the real check or
the real renderer. Nothing is doubled, because a scenario that passes against a
double proves the double.

The module is named ``test_*`` so default pytest collection picks the scenarios
up — the acceptance suite runs inside ``uv run pytest``, not beside it.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from beadloom.application.impact.answer import (
    Boundary,
    ImpactAnswer,
    Population,
    Site,
)
from beadloom.application.impact.section import render_axes_section
from beadloom.application.impact.unresolved import Unresolved
from beadloom.doc_sync.axes_section import (
    AXES_WITHOUT_A_SEED,
    AXIS_WITHOUT_A_SCOPE_DECISION,
    check_axes_section,
    read_axes_section,
    refs_line,
)
from beadloom.doc_sync.doc_shape import (
    EMPTY_SECTION,
    MISSING_SECTION,
    check_planning_sections,
)
from beadloom.onboarding.doc_templates import (
    DEFAULT_DOC_CONFIG,
    required_sections_by_document_kind,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

scenarios("../features/planning_document_shape.feature")
scenarios("../features/axes_section.feature")


@pytest.fixture()
def world() -> dict[str, Any]:
    """The one mutable bag the steps share, kept explicit rather than global."""
    return {}


# ---------------------------------------------------------------------------
# The requirement, derived from the shipped templates rather than declared here
# ---------------------------------------------------------------------------


def _requirements() -> dict[str, tuple[str, ...]]:
    return required_sections_by_document_kind(config=DEFAULT_DOC_CONFIG)


def _brief(*, carrying: Sequence[str], empty: Sequence[str] = ()) -> str:
    """A BRIEF carrying exactly the named sections, each with a body."""
    lines = ["# BRIEF: KEY-1 — a brief", "", "> **Status:** Draft", ""]
    for section in carrying:
        lines.append(f"## {section}")
        lines.append("")
        if section not in empty:
            lines.append("something an observer can read.")
            lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Given — planning document shape
# ---------------------------------------------------------------------------


@given(parsers.parse('three briefs of which two carry an "{section}" section'))
def _three_briefs_two_carrying(world: dict[str, Any], section: str) -> None:
    required = _requirements()["BRIEF"]
    without = tuple(s for s in required if s != section)
    world["documents"] = [
        ("one/BRIEF.md", _brief(carrying=required)),
        ("two/BRIEF.md", _brief(carrying=required)),
        ("three/BRIEF.md", _brief(carrying=without)),
    ]


@given(parsers.parse('three briefs of which one carries an "{section}" section'))
def _three_briefs_one_carrying(world: dict[str, Any], section: str) -> None:
    required = _requirements()["BRIEF"]
    without = tuple(s for s in required if s != section)
    world["documents"] = [
        ("one/BRIEF.md", _brief(carrying=required)),
        ("two/BRIEF.md", _brief(carrying=without)),
        ("three/BRIEF.md", _brief(carrying=without)),
    ]


@given(parsers.parse('a brief whose "{section}" heading has nothing under it'))
def _brief_with_an_empty_section(world: dict[str, Any], section: str) -> None:
    required = _requirements()["BRIEF"]
    world["documents"] = [("one/BRIEF.md", _brief(carrying=required, empty=(section,)))]


@given(parsers.parse('a document named "{name}" carrying no section at all'))
def _a_document_of_an_unknown_kind(world: dict[str, Any], name: str) -> None:
    world["documents"] = [(f"one/{name}", "# notes\n\njust prose.\n")]


# ---------------------------------------------------------------------------
# Given — the Axes section itself
# ---------------------------------------------------------------------------


def _answer(
    *,
    seeds: tuple[Any, ...] = (),
    co_writers: Population,
    unresolved: tuple[Unresolved, ...] = (),
) -> ImpactAnswer:
    return ImpactAnswer(
        target="src/pkg/writer.py",
        root="src/pkg",
        seed_rule="reaches-an-effect-sink",
        seed_rule_statement="a name the target reaches whose own body performs a declared effect",
        effect_rules=(("serialises-yaml", "the body calls a YAML serialiser itself"),),
        seeds=seeds,
        co_writers=co_writers,
        callers=Population(resolved=True),
        commands=(),
        boundary=Boundary(
            resolved=True,
            target_node="writer",
            target_domain="pkg",
            nodes_touched=("writer",),
            domains_touched=("pkg",),
            leaves_the_target_node=False,
            leaves_the_target_domain=False,
        ),
        unresolved=unresolved,
    )


@given("an impact answer whose derivation could not resolve two call sites")
def _an_answer_with_gaps(world: dict[str, Any]) -> None:
    count = 2
    from beadloom.application.impact.seeds import Seed

    world["answer"] = _answer(
        seeds=(
            Seed(
                name="write_yaml",
                path=Path("src/pkg/writer.py"),
                lineno=10,
                effect="serialises-yaml",
            ),
        ),
        co_writers=Population(
            resolved=True,
            sites=(
                Site(
                    name="save",
                    path="src/pkg/save.py",
                    lineno=3,
                    node="writer",
                    domain="pkg",
                ),
            ),
        ),
        unresolved=tuple(
            Unresolved(kind="unnameable-callee", detail=f"call {n}", where="src/pkg/save.py")
            for n in range(count)
        ),
    )


@given("an impact answer for which the seed rule found no seed")
def _an_answer_without_a_seed(world: dict[str, Any]) -> None:
    world["answer"] = _answer(
        co_writers=Population(
            resolved=False,
            reason="no seed was derived, so no writer population could be computed",
        ),
        unresolved=(
            Unresolved(
                kind="no-seed",
                detail="no name the target reaches performs a declared effect",
                where="src/pkg/writer.py",
            ),
        ),
    )


_AXES_WITH_A_SEED = """## Axes

> **Derived by:** `beadloom impact src/pkg/writer.py`
> **Seed:** `write_yaml` (rule `reaches-an-effect-sink`, effect `serialises-yaml`)
> **Unresolved:** none

| Axis | Node | Sites | In scope | Why |
|------|------|-------|----------|-----|
| co-writers | writer | 1 — `src/pkg/save.py:3` | yes | the invariant is written here |
"""


@given(parsers.parse('a brief whose "Axes" section lists an axis and names no seed'))
def _axes_without_a_seed(world: dict[str, Any]) -> None:
    world["text"] = (
        "# BRIEF: KEY-1 — a brief\n\n"
        + "\n".join(
            line
            for line in _AXES_WITH_A_SEED.splitlines()
            if not line.startswith("> **Seed:**")
        )
        + "\n"
    )


@given(parsers.parse('a brief whose "Axes" section lists an axis with an undecided scope cell'))
def _axis_without_a_scope_decision(world: dict[str, Any]) -> None:
    world["text"] = "# BRIEF: KEY-1 — a brief\n\n" + _AXES_WITH_A_SEED.replace(
        "| yes | the invariant is written here |", "| ? |  |"
    )


@given(parsers.parse('a brief whose "Axes" section keeps two nodes in scope and one out'))
def _axes_with_a_scope_decision(world: dict[str, Any]) -> None:
    world["text"] = (
        "# BRIEF: KEY-1 — a brief\n\n"
        + _AXES_WITH_A_SEED
        + "| callers | flow-composer | 2 — `src/pkg/read.py:8` | yes "
        + "| the caller changes shape |\n"
        + "| callers | doc-templates | 1 — `src/pkg/other.py:4` | no | reads the result only |\n"
    )


# ---------------------------------------------------------------------------
# When
# ---------------------------------------------------------------------------


@when("the planning documents are checked against their templates")
def _check_planning(world: dict[str, Any]) -> None:
    world["report"] = check_planning_sections(world["documents"], _requirements())


@when("the Axes section is rendered from it")
def _render(world: dict[str, Any]) -> None:
    world["section"] = render_axes_section(world["answer"])


@when("the Axes section is checked")
def _check_axes(world: dict[str, Any]) -> None:
    world["findings"] = check_axes_section("one/BRIEF.md", world["text"])


@when("the refs line is generated from the document")
def _generate_refs(world: dict[str, Any]) -> None:
    section = read_axes_section(world["text"])
    assert section is not None
    world["refs"] = refs_line(section)


# ---------------------------------------------------------------------------
# Then
# ---------------------------------------------------------------------------


@then(parsers.parse('the third brief is reported as missing "{section}"'))
def _third_is_missing(world: dict[str, Any], section: str) -> None:
    reported = [
        finding
        for finding in world["report"].findings
        if finding.check == MISSING_SECTION and section in finding.excerpt
    ]
    assert [finding.path for finding in reported] == ["three/BRIEF.md"]


@then(parsers.parse('that brief is reported as carrying an empty "{section}" section'))
def _reported_as_empty(world: dict[str, Any], section: str) -> None:
    reported = [
        finding
        for finding in world["report"].findings
        if finding.check == EMPTY_SECTION and section in finding.excerpt
    ]
    assert [finding.path for finding in reported] == ["one/BRIEF.md"]


@then(parsers.parse('no document is reported for "{section}"'))
def _no_document_reported(world: dict[str, Any], section: str) -> None:
    assert not [
        finding
        for finding in world["report"].findings
        if finding.check == MISSING_SECTION and section in finding.excerpt
    ]


@then(parsers.parse('the kind is reported once with the ratio "{ratio}"'))
def _kind_reported_once(world: dict[str, Any], ratio: str) -> None:
    carried, _, total = ratio.partition("/")
    matching = [
        convention
        for convention in world["report"].conventions
        if convention.carried == int(carried) and convention.total == int(total)
    ]
    assert len(matching) == 1


@then(parsers.parse('the kinds judged do not include "{kind}"'))
def _kinds_judged_exclude(world: dict[str, Any], kind: str) -> None:
    assert kind not in world["report"].kinds_judged


@then("the section names the unresolved population")
def _names_the_unresolved(world: dict[str, Any]) -> None:
    assert "unnameable-callee" in world["section"]
    assert "2" in world["section"]


@then("the section states that the seed is none")
def _states_no_seed(world: dict[str, Any]) -> None:
    assert "**Seed:** none" in world["section"]


@then("the section does not state that there are zero co-writers")
def _no_zero_co_writers(world: dict[str, Any]) -> None:
    assert "0" not in world["section"].split("| co-writers |", 1)[1].split("\n", 1)[0]
    assert "unresolved" in world["section"]


@then("the brief is reported as stating axes without a seed")
def _reported_without_a_seed(world: dict[str, Any]) -> None:
    assert [finding.check for finding in world["findings"]] == [AXES_WITHOUT_A_SEED]


@then("the brief is reported as stating an axis with no scope decision")
def _reported_without_a_scope_decision(world: dict[str, Any]) -> None:
    assert AXIS_WITHOUT_A_SCOPE_DECISION in {
        finding.check for finding in world["findings"]
    }


@then("it names the two nodes kept in scope and not the third")
def _refs_names_the_kept(world: dict[str, Any]) -> None:
    assert world["refs"] == "refs: writer, flow-composer"
