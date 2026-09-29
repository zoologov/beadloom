# beadloom:domain=graph
# beadloom:feature=rule-engine
"""``test_binding`` — a test file bound to no node, and a node bound to no test file.

**One responsibility:** judge the binding the reindex recorded (BDL-074 C1) in
both directions, and state how much of the suite and the graph it judged.

- The FILE leg judges every indexed test file the ``files`` glob matches, except
  the ones a kind folder places (placement ``other_kind``), and names those BY
  KIND and count, never under one phrase (BDL-074 F1): an acceptance step file
  runs scenarios that bind through their ``@node:`` tags, judged by the
  project's ``scenario_binding`` rules, and a self-check tests the project's own
  files and binds to no node by design. The two bind differently, so one phrase
  over both is true of neither. The kind is the one the index recorded. A judged
  file whose ``ref_id`` is empty is a finding, and the finding names the
  placement that left it empty.
- Each kind named that way states how it was recognised (review
  ``beadloom-b9ll`` m4): by the folder the test layout the index recorded gives
  it, and whether that folder was declared in ``.beadloom/config.yml`` or is the
  default. The folder is trusted, not verified — what a file holds is never
  checked against its kind, so a unit test dropped into ``tests/self_check/`` is
  counted as a self-check — and the line says so, rather than implying a check.
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

from collections import Counter
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
from beadloom.infrastructure.repository import (
    KIND_ACCEPTANCE,
    KIND_SELF_CHECK,
    KIND_UNRECORDED,
    PLACEMENT_OTHER_KIND,
    label_test_kind,
    read_test_layout,
)

if TYPE_CHECKING:
    import sqlite3
    from collections.abc import Sequence

    from beadloom.graph.rules.suite_tables import IndexedTestFile
    from beadloom.graph.rules.types import NodeMatcher, TestBindingRule
    from beadloom.infrastructure.repository import RecordedTestLayout

#: ``rule_type`` of every finding this module makes about a file or a node.
TEST_BINDING_RULE_TYPE = "test_binding"

#: The limit every kind recognised by its folder carries (review m4).
_FOLDER_TRUSTED = (
    "the folder is trusted, not verified: what a file holds is not checked against its kind"
)
#: Said of a kind when the index recorded no test layout to name its folder from.
_NO_LAYOUT = (
    "recognised by its folder alone (the index records no test layout, so where that "
    "folder was declared is not stated: reindex to record it)"
)

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


def _file_leg(
    rule: TestBindingRule,
    glob: str,
    files: list[IndexedTestFile],
    scenario_rules: Sequence[str],
    layout: RecordedTestLayout | None,
) -> _Leg:
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
        f"`{glob}` ({len(files) - len(matched)} outside the glob): "
        f"{len(judged) - len(unbound)} bound to a node, {len(unbound)} bound to none — "
        f"{ledger.excused} excused by {ledger.exemptions_used} exemption(s), "
        f"{len(unbound) - ledger.excused} reported"
        f"{_kinds_not_judged(other, scenario_rules, layout)}"
    )
    dead = None if judged else f"its `files` glob `{glob}` matches no indexed test file it judges"
    return _Leg(findings, statement, dead)


def _kinds_not_judged(
    other: list[IndexedTestFile],
    scenario_rules: Sequence[str],
    layout: RecordedTestLayout | None,
) -> str:
    """The files a kind folder places, by recorded kind and count, each with how it binds.

    Each is followed by how that kind was recognised, from the recorded *layout*.
    """
    counts = Counter(f.kind or KIND_UNRECORDED for f in other)
    if not counts:
        return ""
    judged_by = (
        f"judged by {', '.join(f'`{name}`' for name in scenario_rules)}"
        if scenario_rules
        else "judged by no `scenario_binding` rule of this project"
    )
    statements = {
        KIND_ACCEPTANCE: (
            f"the scenarios they run bind through their @node: tags, {judged_by}"
        ),
        KIND_SELF_CHECK: (
            "the project's checks of its own files and configuration, bound to no node "
            "by design: a sanctioned outcome, not a gap"
        ),
    }
    stated = [
        f"{count} {label_test_kind(kind)} file(s) — "
        f"{statements.get(kind, 'bound to no node, and not judged by this rule')}, "
        f"{_recognised(kind, layout)}"
        for kind, count in sorted(counts.items())
    ]
    return f"; not judged by their path, by kind: {'; '.join(stated)}"


def _recognised(kind: str, layout: RecordedTestLayout | None) -> str:
    """How files of *kind* were recognised as that kind, with the limit of it."""
    if layout is None:
        return _NO_LAYOUT
    prefixes = layout.kind_prefixes.get(kind)
    if not prefixes:
        return "a kind no folder of the recorded test layout names"
    folders = ", ".join(f"`{prefix}`" for prefix in prefixes)
    noun = "the folder" if len(prefixes) == 1 else "the folders"
    source = (
        " declared in .beadloom/config.yml (`tests.kinds`)"
        if kind in layout.declared_kinds
        else ", Beadloom's default, which no `tests.kinds` entry replaces"
    )
    return f"recognised by {noun} {folders}{source} ({_FOLDER_TRUSTED})"


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


def _legs(
    conn: sqlite3.Connection, rule: TestBindingRule, scenario_rules: Sequence[str] = ()
) -> list[_Leg] | None:
    files = read_test_files(conn)
    if files is None:
        return None
    legs: list[_Leg] = []
    if rule.files is not None:
        layout = read_test_layout(conn)
        legs.append(_file_leg(rule, rule.files, files, scenario_rules, layout))
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


def _evaluate_one(
    conn: sqlite3.Connection, rule: TestBindingRule, scenario_rules: Sequence[str]
) -> list[Violation]:
    legs = _legs(conn, rule, scenario_rules)
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
    conn: sqlite3.Connection,
    rules: list[TestBindingRule],
    *,
    scenario_rules: Sequence[str] = (),
) -> list[Violation]:
    """Evaluate every ``test_binding`` rule against the recorded binding.

    *scenario_rules* names the project's ``scenario_binding`` rules, which judge
    the tags an acceptance step file's scenarios bind through; the population
    line names them, or says that none is declared.
    """
    findings: list[Violation] = []
    for rule in rules:
        findings.extend(_evaluate_one(conn, rule, scenario_rules))
    return findings
