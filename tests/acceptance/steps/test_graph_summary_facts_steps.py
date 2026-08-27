"""Step implementations for `features/graph_summary_facts.feature` (BDL-062 `.1`).

The steps build a real index — real ``nodes`` rows — and run the real rule
against a real :class:`~beadloom.doc_sync.FactSet`. Nothing is doubled: the
claim of this rule is that it reads a number out of prose it has never seen and
compares it against a fact the project computed, and a double on either side
would be an answer written by the person asserting it (FAKES PROVE FAKES).

Every graph below is deliberately NOT this repository's — the nodes are
``gateway``/``atlas``/``widgets`` and the facts are supplied directly — so a rule
that passed by knowing Beadloom's own numbers would fail here.

The module is named ``test_*`` so default pytest collection picks the scenarios
up: the acceptance suite runs inside ``uv run pytest``, not beside it.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from beadloom.doc_sync import Fact, FactSet
from beadloom.graph.rules import (
    LIVENESS_RULE_TYPE,
    SUMMARY_FACTS_RULE_TYPE,
    SummaryFactsRule,
    evaluate_summary_facts_rules,
)
from beadloom.infrastructure.db import create_schema, open_db

if TYPE_CHECKING:
    import sqlite3
    from pathlib import Path

    from beadloom.graph.rules import Violation

scenarios("../features/graph_summary_facts.feature")


@pytest.fixture()
def world(tmp_path: Path) -> dict[str, Any]:
    """The one mutable bag the steps share, kept explicit rather than global."""
    return {
        "root": tmp_path,
        "nodes": [],
        "facts": {},
        "not_applicable": {},
        "violations": [],
        # What the PROJECT declared for this rule. `error` is the shipped
        # default, so a scenario that says nothing about severity is measuring
        # what an adopter who wrote no `severity:` key actually gets.
        "severity": "error",
    }


def _index(world: dict[str, Any]) -> sqlite3.Connection:
    conn = open_db(world["root"] / "graph.db")
    create_schema(conn)
    for ref_id, summary in world["nodes"]:
        conn.execute(
            "INSERT INTO nodes (ref_id, kind, summary, source) VALUES (?, ?, ?, ?)",
            (ref_id, "feature", summary, f"app/{ref_id}.py"),
        )
    conn.commit()
    return conn


def _findings(violations: list[Violation], rule_type: str) -> list[Violation]:
    return [v for v in violations if v.rule_type == rule_type]


# --------------------------------------------------------------------------- #
# Given
# --------------------------------------------------------------------------- #


@given(parsers.parse("a project whose computed {fact_name} is {value}"))
def _computed_fact(world: dict[str, Any], fact_name: str, value: str) -> None:
    parsed: str | int = int(value) if value.isdigit() else value
    world["facts"][fact_name] = Fact(name=fact_name, value=parsed, source="the fixture")


@given(
    parsers.parse('a project that declines to compute {fact_name} because "{reason}"')
)
def _declined_fact(world: dict[str, Any], fact_name: str, reason: str) -> None:
    world["not_applicable"][fact_name] = reason


@given(
    parsers.parse(
        'the graph-summary-facts rule is declared with severity "{severity}"'
    )
)
def _declared_severity(world: dict[str, Any], severity: str) -> None:
    world["severity"] = severity


@given(parsers.parse('a node "{ref_id}" whose summary reads "{summary}"'))
def _node(world: dict[str, Any], ref_id: str, summary: str) -> None:
    world["nodes"].append((ref_id, summary))


# --------------------------------------------------------------------------- #
# When
# --------------------------------------------------------------------------- #


@when("the graph-summary-facts rule is evaluated")
def _evaluate(world: dict[str, Any]) -> None:
    conn = _index(world)
    fact_set = FactSet(
        facts=dict(world["facts"]), not_applicable=dict(world["not_applicable"])
    )
    rule = SummaryFactsRule(
        name="graph-summary-facts",
        description="A number stated in a node summary agrees with the project",
        severity=world["severity"],
    )
    world["violations"] = evaluate_summary_facts_rules(conn, [rule], fact_set=fact_set)
    conn.close()


# --------------------------------------------------------------------------- #
# Then
# --------------------------------------------------------------------------- #


@then(parsers.parse('the node "{ref_id}" is reported'))
def _node_reported(world: dict[str, Any], ref_id: str) -> None:
    reported = {
        v.from_ref_id for v in _findings(world["violations"], SUMMARY_FACTS_RULE_TYPE)
    }
    assert ref_id in reported, f"{ref_id} not among {reported}"


@then(parsers.parse('the node "{ref_id}" is not reported as disagreeing'))
def _node_not_disagreeing(world: dict[str, Any], ref_id: str) -> None:
    reported = {
        v.from_ref_id for v in _findings(world["violations"], SUMMARY_FACTS_RULE_TYPE)
    }
    assert ref_id not in reported, f"{ref_id} was reported as disagreeing"


@then(parsers.parse("the finding states both {claimed:d} and {computed:d}"))
def _both_values(world: dict[str, Any], claimed: int, computed: int) -> None:
    messages = [v.message for v in _findings(world["violations"], SUMMARY_FACTS_RULE_TYPE)]
    assert any(
        str(claimed) in message and str(computed) in message for message in messages
    ), messages


@then("the finding carries the severity the rule was configured with")
def _severity(world: dict[str, Any]) -> None:
    findings = _findings(world["violations"], SUMMARY_FACTS_RULE_TYPE)
    assert findings
    assert all(v.severity == "error" for v in findings)


@then(parsers.parse('that report carries the severity "{severity}"'))
def _liveness_severity(world: dict[str, Any], severity: str) -> None:
    findings = _findings(world["violations"], LIVENESS_RULE_TYPE)
    assert findings, "no liveness finding to carry a severity"
    assert [v.severity for v in findings] == [severity] * len(findings)


@then("no node is reported")
def _no_node_reported(world: dict[str, Any]) -> None:
    assert not _findings(world["violations"], SUMMARY_FACTS_RULE_TYPE)


@then("the rule does not report that it checked nothing")
def _no_liveness(world: dict[str, Any]) -> None:
    assert not _findings(world["violations"], LIVENESS_RULE_TYPE)


@then("the rule reports that it checked nothing")
def _checked_nothing(world: dict[str, Any]) -> None:
    messages = [v.message for v in _findings(world["violations"], LIVENESS_RULE_TYPE)]
    assert any("checked nothing" in message for message in messages), messages


@then("the rule reports that it could not verify a claim")
def _reports_unverifiable(world: dict[str, Any]) -> None:
    messages = [v.message for v in _findings(world["violations"], LIVENESS_RULE_TYPE)]
    assert any("could not be verified" in message for message in messages), messages


@then(parsers.parse("""the report repeats the project's own reason "{reason}\""""))
def _repeats_reason(world: dict[str, Any], reason: str) -> None:
    messages = [v.message for v in _findings(world["violations"], LIVENESS_RULE_TYPE)]
    assert any(reason in message for message in messages), messages
