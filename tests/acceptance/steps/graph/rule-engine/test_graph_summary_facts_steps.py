"""Steps for `graph/rule-engine/graph_summary_facts.feature` (BDL-062 `.1`, `.14`; BDL-074 E1).

The steps state summaries and facts; :class:`~tests.support.rule_engine_driver.SummaryClaims`
writes them into an index and runs the real ``summary_facts`` rule over it. What a
reader sees of a stand-down — that the rule checked nothing, and at what severity —
is the shared vocabulary (:mod:`tests.support.rule_engine_vocabulary`).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from beadloom.graph.rules import SUMMARY_FACTS_RULE_TYPE
from tests.support.rule_engine_driver import Outcome, SummaryClaims
from tests.support.rule_engine_vocabulary import use_findings_vocabulary

if TYPE_CHECKING:
    from pathlib import Path

    from beadloom.graph.rules import Violation

scenarios("../../../graph/rule-engine/graph_summary_facts.feature")
use_findings_vocabulary()


@pytest.fixture()
def claims(tmp_path: Path) -> SummaryClaims:
    return SummaryClaims(tmp_path)


@pytest.fixture()
def outcome() -> Outcome:
    return Outcome()


def _disagreements(outcome: Outcome) -> list[Violation]:
    return outcome.run.of_type(SUMMARY_FACTS_RULE_TYPE)


@given(parsers.parse("a project whose computed {fact_name} is {value}"))
def _computed(claims: SummaryClaims, fact_name: str, value: str) -> None:
    claims.computes(fact_name, value)


@given(parsers.parse('a project that declines to compute {fact_name} because "{reason}"'))
def _declined(claims: SummaryClaims, fact_name: str, reason: str) -> None:
    claims.declines(fact_name, reason)


@given(parsers.parse('the graph-summary-facts rule is declared with severity "{severity}"'))
def _declared_severity(claims: SummaryClaims, severity: str) -> None:
    claims.severity = severity


@given(parsers.parse('a node "{ref_id}" whose summary reads "{summary}"'))
def _summary(claims: SummaryClaims, ref_id: str, summary: str) -> None:
    claims.summary(ref_id, summary)


@when("the graph-summary-facts rule is evaluated")
def _evaluate(claims: SummaryClaims, outcome: Outcome) -> None:
    outcome.run = claims.evaluate()


@then(parsers.parse('the node "{ref_id}" is reported'))
def _reported(outcome: Outcome, ref_id: str) -> None:
    reported = {v.from_ref_id for v in _disagreements(outcome)}
    assert ref_id in reported, f"{ref_id} not among {reported}"


@then(parsers.parse('the node "{ref_id}" is not reported as disagreeing'))
def _not_disagreeing(outcome: Outcome, ref_id: str) -> None:
    reported = {v.from_ref_id for v in _disagreements(outcome)}
    assert ref_id not in reported, f"{ref_id} was reported as disagreeing"


@then(parsers.parse("the finding states both {claimed:d} and {computed:d}"))
def _both_values(outcome: Outcome, claimed: int, computed: int) -> None:
    messages = [v.message for v in _disagreements(outcome)]
    assert any(str(claimed) in m and str(computed) in m for m in messages), messages


@then("the finding carries the severity the rule was configured with")
def _configured_severity(outcome: Outcome, claims: SummaryClaims) -> None:
    findings = _disagreements(outcome)
    assert findings
    assert all(v.severity == claims.severity for v in findings)


@then("no node is reported")
def _no_node(outcome: Outcome) -> None:
    assert not _disagreements(outcome)


@then("the rule reports that it could not verify a claim")
def _unverifiable(outcome: Outcome) -> None:
    messages = outcome.run.liveness_messages()
    assert any("could not be verified" in m for m in messages), messages


@then(parsers.parse("""the report repeats the project's own reason "{reason}\""""))
def _repeats_reason(outcome: Outcome, reason: str) -> None:
    messages = outcome.run.liveness_messages()
    assert any(reason in m for m in messages), messages
