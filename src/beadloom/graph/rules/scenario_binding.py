# beadloom:domain=graph
# beadloom:feature=rule-engine
"""``scenario_binding`` — a scenario's ``@node:`` tag names the folder it is written in.

**One responsibility:** compare each scenario's node tags with the folder its
feature file sits in, and state how much of the suite that comparison reached.
The suite is read by :mod:`beadloom.graph.scenarios`; nothing here parses Gherkin.

The layout judged is one folder per node, ``<suite>/<domain>/<node>/*.feature``
(BDL-074, owner ruling 2026-09-28). No folder name is configured: the folder that
holds a feature file must name a node, and every scenario in it must carry that
node's tag (a scenario may carry others beside it). A folder between the suite
root and the node folder that names a node must name a ``part_of`` container of
it; one that names no node — ``services/`` on a graph with no ``services`` node —
is not judged, and an adopter's layout is not assumed to have one.

**The half this rule does not judge.** The RFC asks that a scenario's tag also
name a node its steps EXECUTE. That needs a runtime trace, and a static stand-in
was measured and rejected on this repository on 2026-09-28: reading the imports
of the step module that loads each feature, and counting a tag as executed when
an import resolves to it or to a node inside it, found 59 of the 81 (tag, step
file) pairs the suite map's coverage run observed executing — and missed 22, six
of them in feature files already in their correct node folder, because a step
that drives the CLI executes far more than it imports. It never claimed a tag
the run did not execute (0 of 59), so it is sound and far from complete; as a
rule it would have reported 22 correct placements to find 4 real ones. Every
population statement says the execution half is not judged.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import PurePosixPath
from typing import TYPE_CHECKING

from beadloom.graph.rules.layer_reach import part_of_parents
from beadloom.graph.rules.layers import part_of_ancestors
from beadloom.graph.rules.listed_exemptions import ExemptionLedger
from beadloom.graph.rules.types import (
    Violation,
    liveness_finding,
    population_finding,
)
from beadloom.graph.scenarios import load_suite

if TYPE_CHECKING:
    import sqlite3
    from collections.abc import Collection, Mapping
    from pathlib import Path

    from beadloom.graph.rules.types import ScenarioBindingRule
    from beadloom.graph.scenarios import Scenario, ScenarioSuite

#: ``rule_type`` of every finding this module makes about a scenario or a file.
SCENARIO_BINDING_RULE_TYPE = "scenario_binding"

_GLOB_CHARACTERS = frozenset("*?[")

_NOT_JUDGED = (
    "not judged: whether a scenario's steps execute the node it names, which needs "
    "a runtime trace"
)


def suite_root(glob: str) -> str:
    """The folder a feature glob starts from — its segments before the first wildcard."""
    fixed: list[str] = []
    for segment in glob.split("/"):
        if _GLOB_CHARACTERS.intersection(segment):
            break
        fixed.append(segment)
    return "/".join(fixed)


@dataclass
class _Tally:
    """What the comparison reached, for the population statement."""

    scenarios: int = 0
    agree: int = 0
    excused_scenarios: int = 0
    excused_files: int = 0
    findings: list[Violation] = field(default_factory=list)


@dataclass(frozen=True)
class _Graph:
    """The two graph facts the comparison needs: which ids are nodes, and their containers."""

    nodes: Collection[str]
    parents: Mapping[str, Collection[str]]


def _finding(
    rule: ScenarioBindingRule,
    path: str,
    message: str,
    remediation: str,
    *,
    line: int | None = None,
    node: str | None = None,
) -> Violation:
    return Violation(
        rule_name=rule.name,
        rule_description=rule.description,
        rule_type=SCENARIO_BINDING_RULE_TYPE,
        severity=rule.severity,
        file_path=path,
        line_number=line,
        from_ref_id=node,
        to_ref_id=None,
        message=message,
        remediation=remediation,
    )


def _move_hint(root: str) -> str:
    return (
        f"move the file to the folder of the node its scenarios bind to, "
        f"`{root}/<domain>/<node>/`; a file whose tag cannot be settled yet is "
        f"exempted by path, with a reason and an exit condition"
    )


def _file_findings(
    rule: ScenarioBindingRule, path: str, count: int, root: str, graph: _Graph
) -> list[Violation]:
    """What is wrong with WHERE the file is, before any scenario in it is read."""
    folders = PurePosixPath(path).parent.parts[len(PurePosixPath(root).parts) :]
    if not folders:
        return [
            _finding(
                rule,
                path,
                f"this file sits in the suite root `{root}`, in no node folder, so its "
                f"{count} scenario(s) bind to no folder",
                _move_hint(root),
            )
        ]
    folder = folders[-1]
    if folder not in graph.nodes:
        return [
            _finding(
                rule,
                path,
                f"the {count} scenario(s) of this file sit in the folder `{folder}`, "
                f"which names no node",
                _move_hint(root),
            )
        ]
    containers = part_of_ancestors(folder, graph.parents)
    return [
        _finding(
            rule,
            path,
            f"the folder `{enclosing}` names a node that `{folder}` is not part_of, so "
            f"this file sits under the wrong container",
            _move_hint(root),
            node=folder,
        )
        for enclosing in folders[:-1]
        if enclosing in graph.nodes and enclosing not in containers
    ]


def _scenario_finding(rule: ScenarioBindingRule, scenario: Scenario, folder: str) -> Violation:
    named = ", ".join(f"`@node:{node}`" for node in scenario.nodes) or "no node"
    return _finding(
        rule,
        scenario.path,
        f"scenario `{scenario.name}` names {named}, but it is written in the folder of "
        f"`{folder}`",
        f"tag the scenario `@node:{folder}` if it binds there, or move it to the folder "
        f"of the node it binds to",
        line=scenario.line,
        node=folder,
    )


def _judge_file(
    rule: ScenarioBindingRule,
    path: str,
    scenarios: list[Scenario],
    root: str,
    graph: _Graph,
) -> tuple[list[Violation], int]:
    """The file's findings and how many of its scenarios agree with their folder."""
    placed = _file_findings(rule, path, len(scenarios), root, graph)
    if placed:
        return placed, 0
    folder = PurePosixPath(path).parent.name
    findings = [_scenario_finding(rule, s, folder) for s in scenarios if folder not in s.nodes]
    return findings, len(scenarios) - len(findings)


def _tally(rule: ScenarioBindingRule, suite: ScenarioSuite, graph: _Graph) -> _Tally:
    root = suite_root(rule.features)
    by_file: dict[str, list[Scenario]] = {}
    for scenario in suite.scenarios:
        by_file.setdefault(scenario.path, []).append(scenario)
    ledger = ExemptionLedger(rule.exempt, by_path=True)
    tally = _Tally()
    for path, scenarios in sorted(by_file.items()):
        tally.scenarios += len(scenarios)
        findings, agree = _judge_file(rule, path, scenarios, root, graph)
        tally.agree += agree
        if findings and ledger.excuse(path):
            tally.excused_scenarios += len(scenarios) - agree
            tally.excused_files += 1
            continue
        tally.findings.extend(findings)
    tally.findings.extend(
        ledger.stale_findings(
            rule_name=rule.name, rule_description=rule.description, subject="feature file"
        )
    )
    return tally


def scenario_binding_inert_reason(
    rule: ScenarioBindingRule, project_root: Path, *, suite: ScenarioSuite | None = None
) -> str | None:
    """Why this rule can judge nothing, or ``None`` — one predicate for finding and count."""
    loaded = suite if suite is not None else load_suite(project_root, rule.features)
    if loaded.is_empty:
        return f"its acceptance suite glob '{rule.features}' matches no feature file"
    return None


def _evaluate_one(
    conn: sqlite3.Connection, rule: ScenarioBindingRule, project_root: Path
) -> list[Violation]:
    suite = load_suite(project_root, rule.features)
    reason = scenario_binding_inert_reason(rule, project_root, suite=suite)
    if reason is not None:
        return [
            liveness_finding(
                rule_name=rule.name,
                rule_description=rule.description,
                message=f"Rule '{rule.name}' cannot fire: {reason}, so no scenario was judged",
                remediation=(
                    "point `features:` at the acceptance suite, or delete the rule — an "
                    "absent suite is not a correctly placed one"
                ),
            )
        ]
    graph = _Graph(
        nodes={str(row[0]) for row in conn.execute("SELECT ref_id FROM nodes")},
        parents=part_of_parents(conn),
    )
    tally = _tally(rule, suite, graph)
    disagree = tally.scenarios - tally.agree
    statement = (
        f"judged {tally.scenarios} scenario(s) in {len(suite.files)} file(s) under "
        f"`{suite_root(rule.features)}`: {tally.agree} agree with their folder, {disagree} "
        f"do not — {tally.excused_scenarios} in {tally.excused_files} file(s) excused by "
        f"an exemption, {disagree - tally.excused_scenarios} reported; "
        f"{len(suite.unreadable)} file(s) could not be read; {_NOT_JUDGED}"
    )
    return [
        *tally.findings,
        population_finding(
            rule_name=rule.name, rule_description=rule.description, message=statement
        ),
    ]


def evaluate_scenario_binding_rules(
    conn: sqlite3.Connection,
    rules: list[ScenarioBindingRule],
    *,
    project_root: Path | None = None,
) -> list[Violation]:
    """Evaluate every ``scenario_binding`` rule; *project_root* (default: cwd) roots the glob."""
    from pathlib import Path as _Path

    root = project_root if project_root is not None else _Path.cwd()
    findings: list[Violation] = []
    for rule in rules:
        findings.extend(_evaluate_one(conn, rule, root))
    return findings
