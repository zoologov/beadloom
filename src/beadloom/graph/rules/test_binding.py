# beadloom:domain=graph
# beadloom:feature=rule-engine
"""``test_binding`` — a test file bound to no node, and a node bound to no test file.

**One responsibility:** judge the binding the reindex recorded (BDL-074 C1) in
both directions, and state how much of the suite and the graph it judged.

- The FILE leg judges every indexed test file the ``files`` glob matches, except
  the ones bound by other means (placement ``other_kind``: an acceptance step
  file, whose scenarios bind by tag, and a self-check, which tests the
  repository). A judged file whose ``ref_id`` is empty is a finding, and the
  finding names the placement that left it empty.
- The NODE leg judges every node the ``for`` matcher selects. A node is bound
  when a test file is bound to it or to one of its ``part_of`` descendants — the
  union ``ctx`` counts. Acceptance scenarios are not counted here; that binding
  is ``scenario_coverage``'s population.

**A node with no bound test file is not an untested node** while any test file
binds to no node, because the unbound file may test it. Every node finding says
how many files bind to no node, so the reader weighs it; the rule does not
withhold the finding the way the debt report withholds its count, because a
finding names ONE node a person can check and a score does not.

Liveness is reported here, per leg: a ``for`` matcher selecting no node, a
``files`` glob matching no test file the leg judges, and an index written before
the test tables existed.
"""

from __future__ import annotations

from dataclasses import dataclass
from fnmatch import fnmatchcase
from typing import TYPE_CHECKING

from beadloom.graph.rules.listed_exemptions import ExemptionLedger
from beadloom.graph.rules.suite_tables import NodeSelection, read_test_files
from beadloom.graph.rules.types import (
    Violation,
    liveness_finding,
    population_finding,
)
from beadloom.infrastructure.repository import PLACEMENT_OTHER_KIND

if TYPE_CHECKING:
    import sqlite3

    from beadloom.graph.rules.suite_tables import IndexedTestFile
    from beadloom.graph.rules.types import NodeMatcher, TestBindingRule

#: ``rule_type`` of every finding this module makes about a file or a node.
TEST_BINDING_RULE_TYPE = "test_binding"

_NO_TEST_TABLE = (
    "the index holds no test-file table — it was written before test files were "
    "indexed, so no binding was judged"
)


@dataclass(frozen=True)
class _Leg:
    """What one leg judged: its findings, its population sentence, and whether it could look."""

    findings: list[Violation]
    statement: str
    dead_reason: str | None = None


def _finding(rule: TestBindingRule, message: str, remediation: str, **where: str) -> Violation:
    return Violation(
        rule_name=rule.name,
        rule_description=rule.description,
        rule_type=TEST_BINDING_RULE_TYPE,
        severity=rule.severity,
        file_path=where.get("file_path"),
        line_number=None,
        from_ref_id=where.get("from_ref_id"),
        to_ref_id=None,
        message=message,
        remediation=remediation,
    )


def _file_leg(rule: TestBindingRule, glob: str, files: list[IndexedTestFile]) -> _Leg:
    matched = [f for f in files if fnmatchcase(f.path, glob)]
    other = [f for f in matched if f.placement == PLACEMENT_OTHER_KIND]
    judged = [f for f in matched if f.placement != PLACEMENT_OTHER_KIND]
    ledger = ExemptionLedger(rule.exempt_files, by_path=True)
    unbound = [f for f in judged if f.ref_id is None]
    findings = [
        _finding(
            rule,
            f"test file `{f.path}` binds to no node (placement `{f.placement}`) — its path "
            f"mirrors no node's code and no node's `tests:` list names it",
            "place it where its path mirrors the code it tests, or name it in the "
            "`tests:` list of the node it belongs to; a file that cannot be placed yet "
            "is exempted by path, with a reason and an exit condition",
            file_path=f.path,
        )
        for f in unbound
        if not ledger.excuse(f.path)
    ]
    findings.extend(
        ledger.stale_findings(
            rule_name=rule.name, rule_description=rule.description, subject="test file"
        )
    )
    statement = (
        f"test files: judged {len(judged)} of {len(files)} indexed test file(s) matching "
        f"`{glob}` ({len(other)} bind by other means, "
        f"{len(files) - len(matched)} outside the glob): {len(judged) - len(unbound)} bound "
        f"to a node, {len(unbound)} bound to none — {ledger.excused} excused by an "
        f"exemption, {len(unbound) - ledger.excused} reported"
    )
    dead = None if judged else f"its `files` glob `{glob}` matches no indexed test file it judges"
    return _Leg(findings, statement, dead)


def _node_leg(
    conn: sqlite3.Connection,
    rule: TestBindingRule,
    matcher: NodeMatcher,
    files: list[IndexedTestFile],
) -> _Leg:
    selection = NodeSelection(conn, matcher)
    bound = selection.covered_by({f.ref_id for f in files if f.ref_id is not None})
    unbound_files = sum(
        1 for f in files if f.ref_id is None and f.placement != PLACEMENT_OTHER_KIND
    )
    ledger = ExemptionLedger(rule.exempt_nodes, by_path=False)
    without = [node for node in selection.nodes if node not in bound]
    findings = [
        _finding(
            rule,
            f"no test file is bound to `{node}` or to a node part_of it; "
            f"{unbound_files} test file(s) bind to no node, so one of them may test it",
            f"place a test of `{node}` where its path mirrors the node's code, or name "
            f"the file in the node's `tests:` list; a node that is not tested yet is "
            f"exempted by name, with a reason and an exit condition",
            from_ref_id=node,
        )
        for node in without
        if not ledger.excuse(node)
    ]
    findings.extend(
        ledger.stale_findings(
            rule_name=rule.name, rule_description=rule.description, subject="node"
        )
    )
    statement = (
        f"nodes: judged {len(selection.nodes)} node(s) ({matcher.describe()}): "
        f"{len(selection.nodes) - len(without)} with a bound test file, {len(without)} "
        f"without — {ledger.excused} excused by an exemption, "
        f"{len(without) - ledger.excused} reported; acceptance scenarios are not counted "
        f"here"
    )
    dead = None if selection.nodes else f"its `for` matcher ({matcher.describe()}) selects no node"
    return _Leg(findings, statement, dead)


def _legs(conn: sqlite3.Connection, rule: TestBindingRule) -> list[_Leg] | None:
    files = read_test_files(conn)
    if files is None:
        return None
    legs: list[_Leg] = []
    if rule.files is not None:
        legs.append(_file_leg(rule, rule.files, files))
    if rule.for_matcher is not None:
        legs.append(_node_leg(conn, rule, rule.for_matcher, files))
    return legs


def test_binding_inert_reason(conn: sqlite3.Connection, rule: TestBindingRule) -> str | None:
    """Why this rule can judge NOTHING AT ALL, or ``None`` when one leg can.

    One predicate for the evaluator and for the ``N rules, M inert`` count, so
    the two cannot drift (BDL-UX #171).
    """
    legs = _legs(conn, rule)
    if legs is None:
        return _NO_TEST_TABLE
    reasons = [leg.dead_reason for leg in legs]
    if legs and all(reason is not None for reason in reasons):
        return "; ".join(reason for reason in reasons if reason is not None)
    return None


def _evaluate_one(conn: sqlite3.Connection, rule: TestBindingRule) -> list[Violation]:
    legs = _legs(conn, rule)
    if legs is None:
        return [_liveness(rule, _NO_TEST_TABLE)]
    findings: list[Violation] = []
    for leg in legs:
        if leg.dead_reason is not None:
            findings.append(_liveness(rule, leg.dead_reason))
        findings.extend(leg.findings)
    findings.append(
        population_finding(
            rule_name=rule.name,
            rule_description=rule.description,
            message="; ".join(leg.statement for leg in legs),
        )
    )
    return findings


def _liveness(rule: TestBindingRule, reason: str) -> Violation:
    return liveness_finding(
        rule_name=rule.name,
        rule_description=rule.description,
        message=f"Rule '{rule.name}' cannot judge a leg: {reason}",
        remediation=(
            "reindex so the test files are recorded, or point `files:` / `for:` at "
            "what the project has — a leg that judges nothing reads exactly like one "
            "that found nothing wrong"
        ),
    )


def evaluate_test_binding_rules(
    conn: sqlite3.Connection, rules: list[TestBindingRule]
) -> list[Violation]:
    """Evaluate every ``test_binding`` rule against the recorded binding."""
    findings: list[Violation] = []
    for rule in rules:
        findings.extend(_evaluate_one(conn, rule))
    return findings
