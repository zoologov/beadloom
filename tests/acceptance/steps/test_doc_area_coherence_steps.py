"""Step implementations for `features/doc_area_coherence.feature` (BDL-062 `.2`).

The steps build a real index — real ``nodes`` and ``docs`` rows — and run the
real rule against it. Nothing is doubled: the whole claim of this rule is that it
reads a convention out of a graph it has never seen, and a double would be a
graph written by the person asserting the answer (FAKES PROVE FAKES).

Every tree below is deliberately NOT this repository's: the source root is
``app/`` and the areas are ``billing``/``shipping``, so a rule that passed by
knowing Beadloom's own layout would fail here.

The module is named ``test_*`` so default pytest collection picks the scenarios
up — the acceptance suite runs inside ``uv run pytest``, not beside it.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from beadloom.graph.rules import (
    LIVENESS_RULE_TYPE,
    DocAreaCoherenceRule,
    evaluate_doc_area_coherence_rules,
)
from beadloom.infrastructure.db import create_schema, open_db

if TYPE_CHECKING:
    import sqlite3
    from pathlib import Path

    from beadloom.graph.rules import Violation

scenarios("../features/doc_area_coherence.feature")

DOC_AREA_RULE_TYPE = "doc_area_coherence"


@pytest.fixture()
def world(tmp_path: Path) -> dict[str, Any]:
    """The one mutable bag the steps share, kept explicit rather than global."""
    return {"root": tmp_path, "placements": [], "violations": []}


def _place(world: dict[str, Any], ref_id: str, source: str, doc: str) -> None:
    world["placements"].append((ref_id, source, doc))


def _index(world: dict[str, Any]) -> sqlite3.Connection:
    conn = open_db(world["root"] / "graph.db")
    create_schema(conn)
    for ref_id, source, doc in world["placements"]:
        conn.execute(
            "INSERT INTO nodes (ref_id, kind, summary, source) VALUES (?, ?, ?, ?)",
            (ref_id, "feature", "", source),
        )
        conn.execute(
            "INSERT INTO docs (path, kind, ref_id, hash) VALUES (?, ?, ?, ?)",
            (doc, "feature", ref_id, ""),
        )
    conn.commit()
    return conn


def _findings(violations: list[Violation], rule_type: str) -> list[Violation]:
    return [v for v in violations if v.rule_type == rule_type]


# --------------------------------------------------------------------------- #
# Given
# --------------------------------------------------------------------------- #


@given(
    parsers.parse(
        'a graph where {count:d} nodes under source area "{area}" '
        'are documented under "{docs_area}"'
    )
)
def _agreeing_nodes(world: dict[str, Any], count: int, area: str, docs_area: str) -> None:
    for index in range(count):
        ref_id = f"{area}-{index}"
        _place(
            world,
            ref_id,
            f"app/{area}/{ref_id}.py",
            f"reference/{docs_area}/{ref_id}/SPEC.md",
        )


@given(
    parsers.parse(
        '{count:d} stray node under source area "{area}" is documented under "{docs_area}"',
    )
)
def _dissenting_nodes(
    world: dict[str, Any], count: int, area: str, docs_area: str
) -> None:
    for index in range(count):
        ref_id = f"{area}-stray-{index}"
        _place(
            world,
            ref_id,
            f"app/{area}/{ref_id}.py",
            f"reference/{docs_area}/{ref_id}/SPEC.md",
        )


@given("a graph whose documents all sit at the root of the docs tree")
def _flat_docs(world: dict[str, Any]) -> None:
    for area in ("billing", "shipping"):
        for index in range(4):
            ref_id = f"{area}-{index}"
            _place(world, ref_id, f"app/{area}/{ref_id}.py", f"{ref_id}.md")


@given("a graph where every source area holds exactly one documented node")
def _one_node_per_area(world: dict[str, Any]) -> None:
    for area in ("billing", "shipping", "catalogue", "search", "payments", "audit"):
        _place(
            world,
            area,
            f"app/{area}/service.py",
            f"reference/{area}/service/SPEC.md",
        )


# --------------------------------------------------------------------------- #
# When
# --------------------------------------------------------------------------- #


@when("the doc-area-coherence rule is evaluated")
def _evaluate(world: dict[str, Any]) -> None:
    conn = _index(world)
    try:
        world["violations"] = evaluate_doc_area_coherence_rules(
            conn,
            [
                DocAreaCoherenceRule(
                    name="doc-area-coherence",
                    description="a node documents itself where its graph says it should",
                )
            ],
        )
    finally:
        conn.close()


# --------------------------------------------------------------------------- #
# Then
# --------------------------------------------------------------------------- #


@then("the stray node is reported")
def _stray_reported(world: dict[str, Any]) -> None:
    reported = _findings(world["violations"], DOC_AREA_RULE_TYPE)
    assert [v.from_ref_id for v in reported] == ["billing-stray-0"], (
        f"expected exactly the stray node, got {[v.from_ref_id for v in reported]}"
    )


@then("the finding states the sample size and the threshold")
def _finding_states_population(world: dict[str, Any]) -> None:
    reported = _findings(world["violations"], DOC_AREA_RULE_TYPE)
    assert reported, "no doc-area finding to inspect"
    message = reported[0].message
    assert "8 node/doc pairs" in message, message
    assert "0.60" in message, message


@then("the rule does not report that it checked nothing")
def _not_inert(world: dict[str, Any]) -> None:
    assert not _findings(world["violations"], LIVENESS_RULE_TYPE), (
        "the rule stood down on a graph whose convention is derivable"
    )


@then("the rule reports that it checked nothing")
def _inert(world: dict[str, Any]) -> None:
    findings = _findings(world["violations"], LIVENESS_RULE_TYPE)
    assert len(findings) == 1, f"expected one liveness finding, got {findings}"
    assert "checked nothing" in findings[0].message, findings[0].message


@then("no node is reported as misplaced")
def _no_misplacement(world: dict[str, Any]) -> None:
    assert not _findings(world["violations"], DOC_AREA_RULE_TYPE)
