# beadloom:domain=graph
# beadloom:feature=rule-engine
"""``scenario-coverage`` — evaluate the binding between behaviour and its scenarios.

**One responsibility:** given the graph and the acceptance suite, say where the
binding between the two is missing. The suite is read by
:mod:`beadloom.graph.scenarios`; nothing here parses Gherkin.

Why it lives in its own module rather than in :mod:`.evaluators`: every other
evaluator answers a question about the *index*, in SQL. This one compares the
index against files on disk that no index holds, and it owns its own liveness
(the same boundary :mod:`.liveness` draws for ``forbid_import``, and for the same
reason — the dead-glob finding falls out of the scan the evaluation already did).

**Liveness is per LEG, not per rule — with one exception, named here because a
note that understates a silence is worse than no note at all.** Four legs run
(suite, declaration, coverage, reference) and two of the dead-input cases are
genuinely per-leg: a ``for`` matcher that selects nothing kills the coverage leg
while the scenario legs still work, and a ``references`` glob that matches no
document kills only the reference leg. Each reports itself and the others run.

**The exception: an ABSENT SUITE stands the WHOLE rule down — all four legs, not
the coverage leg alone.** When the ``features`` glob matches no file,
:func:`_evaluate_one` reports the glob and returns, so the suite, declaration,
coverage and reference legs are all skipped. Measured on this repository,
repointing ``features:`` at a directory that does not exist takes ``lint`` from
68 findings to exactly 1, and that 1 is the liveness finding naming the dead
glob; the 33 reference findings that an empty suite would make definitionally
true go with it. The reason is unchanged and still holds — one configuration
error printing as N architecture findings buries the finding that would fix it —
but the reach was understated for six review cycles, and so was what follows
from it: in that state the rule is **counted** as inert
(:func:`inert_reason`), which a per-leg silence would not have been.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from beadloom.graph.rules.types import (
    Violation,
    liveness_finding,
)
from beadloom.graph.scenarios import load_references, load_suite

if TYPE_CHECKING:
    import sqlite3
    from pathlib import Path

    from beadloom.graph.rules.types import NodeMatcher, ScenarioCoverageRule
    from beadloom.graph.scenarios import ScenarioSuite

#: ``rule_type`` of every non-liveness finding this module produces.
SCENARIO_COVERAGE_RULE_TYPE = "scenario_coverage"

#: What the rule does NOT check, carried on the findings that would otherwise
#: imply it did. The tracker is not readable from the rule engine — a domain may
#: not depend on the application layer — so a scenario is checked for NAMING a
#: bead and never for naming one that exists.
BEAD_NOT_VERIFIED = (
    "the bead id itself is not verified against the tracker — this check reads "
    "the suite and the graph only"
)


def _matcher_description(matcher: NodeMatcher) -> str:
    """How a matcher reads in a finding, so an author can see what selected nothing."""
    parts = [
        f"{field}={value}"
        for field, value in (
            ("ref_id", matcher.ref_id),
            ("kind", matcher.kind),
            ("tag", matcher.tag),
        )
        if value is not None
    ]
    return ", ".join(parts) if parts else "everything"


def _matched_nodes(conn: sqlite3.Connection, matcher: NodeMatcher) -> list[str]:
    """Ref ids the rule's ``for`` matcher selects, in stable order."""
    from beadloom.graph.loader import get_node_tags

    rows = conn.execute("SELECT ref_id, kind FROM nodes ORDER BY ref_id").fetchall()
    matched: list[str] = []
    for ref_id, kind in ((str(r[0]), str(r[1])) for r in rows):
        tags = get_node_tags(conn, ref_id) if matcher.tag is not None else None
        if matcher.matches(ref_id, kind, tags=tags):
            matched.append(ref_id)
    return matched


def _all_ref_ids(conn: sqlite3.Connection) -> set[str]:
    return {str(r[0]) for r in conn.execute("SELECT ref_id FROM nodes").fetchall()}


def _finding(
    rule: ScenarioCoverageRule,
    *,
    message: str,
    remediation: str,
    file_path: str | None = None,
    line_number: int | None = None,
    from_ref_id: str | None = None,
    to_ref_id: str | None = None,
) -> Violation:
    return Violation(
        rule_name=rule.name,
        rule_description=rule.description,
        rule_type=SCENARIO_COVERAGE_RULE_TYPE,
        severity=rule.severity,
        file_path=file_path,
        line_number=line_number,
        from_ref_id=from_ref_id,
        to_ref_id=to_ref_id,
        message=message,
        remediation=remediation,
    )


def _population(suite: ScenarioSuite) -> str:
    """The denominator every coverage statement is a fraction of."""
    scenarios = len(suite.scenarios)
    files = len(suite.files)
    return (
        f"{scenarios} scenario{'' if scenarios == 1 else 's'} "
        f"in {files} file{'' if files == 1 else 's'}"
    )


def inert_reason(
    rule: ScenarioCoverageRule,
    project_root: Path,
    *,
    suite: ScenarioSuite | None = None,
) -> str | None:
    """Why this rule can check NOTHING AT ALL, or ``None`` when it checks something.

    One predicate, two callers, so the count and the control flow it describes
    cannot drift apart (BDL-UX #171 is one fact with two sources of truth):
    :func:`_evaluate_one` reports it as a liveness finding naming the glob, and
    :func:`beadloom.graph.rules.liveness.inert_rules` COUNTS it into
    ``N rules evaluated, M of them unable to check anything``. Until review
    ``.15`` M3 the second caller did not exist, so ``lint`` printed
    ``13 rules, 0 inert`` over a rule that had stood all four legs down.

    Only an ABSENT SUITE stands the whole rule down, because
    :func:`_evaluate_one` returns as soon as it finds one. A dead ``for`` matcher
    or a dead ``references`` glob stands ONE leg down while the others still
    check, and counting that rule as unable to check anything would make the
    summary line over-claim in the other direction.

    *suite* is passed by the evaluator, which has already loaded it; the liveness
    caller loads it once more, which is what the counter being true costs.
    """
    loaded = suite if suite is not None else load_suite(project_root, rule.features)
    if loaded.is_empty:
        return (
            f"its acceptance suite glob '{rule.features}' matches no file, so no "
            f"node was checked for a scenario and no scenario for a binding"
        )
    return None


def _coverage_leg(
    rule: ScenarioCoverageRule,
    *,
    matched: list[str],
    suite: ScenarioSuite,
    covered: set[str],
    declared: dict[str, str],
) -> list[Violation]:
    """Nodes in the population that no scenario names and no declaration excuses."""
    findings: list[Violation] = []
    for ref_id in matched:
        if ref_id in covered or ref_id in declared:
            continue
        findings.append(
            _finding(
                rule,
                from_ref_id=ref_id,
                message=(
                    f"no scenario binds to `{ref_id}` — none of {_population(suite)} "
                    f"carries `@node:{ref_id}`"
                ),
                remediation=(
                    f"write the acceptance scenario in `{rule.features}` and tag it "
                    f"`@node:{ref_id} @bead:<id>`, or declare the node non-behavioural "
                    f"with a reason in the rule's `non_behavioural:` list"
                ),
            )
        )
    return findings


def _suite_leg(
    rule: ScenarioCoverageRule, *, suite: ScenarioSuite, known_refs: set[str]
) -> list[Violation]:
    """What the suite itself gets wrong: unread files, hollow files, loose bindings."""
    findings: list[Violation] = []
    for unreadable in suite.unreadable:
        findings.append(
            _finding(
                rule,
                file_path=unreadable.path,
                message=f"the scenarios of this file are UNKNOWN: {unreadable.reason}",
                remediation=(
                    "an unread file in the suite is not an empty one — every node it "
                    "would have covered is reported as uncovered until it can be read"
                ),
            )
        )
    for path in suite.empty_files:
        findings.append(
            _finding(
                rule,
                file_path=path,
                message="this file is in the acceptance suite and declares no scenario",
                remediation="write the scenario, or delete the file — an empty one covers nothing",
            )
        )
    for scenario in suite.scenarios:
        if not scenario.beads:
            findings.append(
                _finding(
                    rule,
                    file_path=scenario.path,
                    line_number=scenario.line,
                    message=(
                        f"scenario `{scenario.name}` names no bead — the work it was "
                        f"written for cannot be told from the suite"
                    ),
                    remediation=(
                        f"tag the scenario (or its Feature) `@bead:<id>`; note that "
                        f"{BEAD_NOT_VERIFIED}"
                    ),
                )
            )
        for node in scenario.nodes:
            if node in known_refs:
                continue
            findings.append(
                _finding(
                    rule,
                    file_path=scenario.path,
                    line_number=scenario.line,
                    to_ref_id=node,
                    message=(
                        f"scenario `{scenario.name}` names `@node:{node}`, which is "
                        f"not a node in the graph"
                    ),
                    remediation=(
                        "fix the ref_id (`beadloom graph` lists them) or add the node — "
                        "a binding to a node that does not exist covers nothing"
                    ),
                )
            )
    return findings


def _reference_leg(
    rule: ScenarioCoverageRule, *, project_root: Path, suite: ScenarioSuite
) -> list[Violation]:
    """Scenarios a TO-BE document claims exist, checked against the suite."""
    if not rule.references:
        return []
    found = load_references(project_root, rule.references)
    findings: list[Violation] = []
    names = {scenario.name for scenario in suite.scenarios}
    for unreadable in found.unreadable:
        findings.append(
            _finding(
                rule,
                file_path=unreadable.path,
                message=(
                    f"the scenarios this document references are UNKNOWN: "
                    f"{unreadable.reason}"
                ),
                remediation=(
                    "save the document as UTF-8, or drop it from `references:` — a "
                    "document that cannot be read states no intent, and reading that "
                    "as intent fully met is how a check gets quieter when a file "
                    "gets worse"
                ),
            )
        )
    for reference in found.references:
        if reference.name in names:
            continue
        findings.append(
            _finding(
                rule,
                file_path=reference.path,
                line_number=reference.line,
                message=(
                    f"this document references the scenario `{reference.name}`, which "
                    f"is not in the suite ({_population(suite)})"
                ),
                remediation=(
                    f"write the scenario in `{rule.features}` under exactly this name, "
                    f"or correct the reference — the `.feature` file is the source of "
                    f"truth and the document states intent"
                ),
            )
        )
    for glob in found.dead_globs:
        findings.append(
            liveness_finding(
                rule_name=rule.name,
                rule_description=rule.description,
                message=(
                    f"the reference glob `{glob}` matches no document, so no "
                    f"referenced scenario was checked by it"
                ),
                remediation=(
                    "point `references:` at the documents that state intent, or drop "
                    "the glob — a reference check with no documents reports nothing "
                    "and reads exactly like one that found no problem"
                ),
            )
        )
    return findings


def _excused_statement(
    rule: ScenarioCoverageRule, *, matched: set[str], covered: set[str]
) -> list[Violation]:
    """What the population lost to declarations, said out loud once per rule.

    PLAN's criterion is that a node MAY declare itself non-behavioural *with a
    named reason* and is accepted. Accepted in SILENCE is not that: the excused
    nodes leave the population, the coverage fraction improves, and nothing said
    the denominator had moved. So a run that excuses anything states how many of
    how many, and each reason — ``.63``'s option 2, the denominator printed
    beside the fraction.

    Silent when nothing is excused. A line about zero excused nodes on every lint
    of every project is noise, and noise is how a real one goes unread.

    Always ``warn``, whatever the rule declares, for the reason
    :func:`~beadloom.graph.rules.types.liveness_finding` is: this is a statement
    about the CONFIGURATION and not about the code, and doing the thing PLAN says
    is accepted must never redden a pipeline.
    """
    reasons = {d.node: d.reason for d in rule.non_behavioural}
    excused = sorted(node for node in reasons if node in matched and node not in covered)
    if not excused:
        return []
    named = ", ".join(f"`{node}` ({reasons[node]})" for node in excused)
    return [
        Violation(
            rule_name=rule.name,
            rule_description=rule.description,
            rule_type=SCENARIO_COVERAGE_RULE_TYPE,
            severity="warn",
            file_path=None,
            line_number=None,
            from_ref_id=None,
            to_ref_id=None,
            message=(
                f"{len(excused)} of {len(matched)} node(s) in this rule's population "
                f"are excused as non-behavioural, so every coverage figure below is "
                f"a fraction of {len(matched) - len(excused)}: {named}"
            ),
            remediation=(
                "keep each declaration only while its reason holds — an excused "
                "node is outside every count this rule reports, and a declaration "
                "that stops being true is how a population shrinks quietly"
            ),
        )
    ]


def _declaration_leg(
    rule: ScenarioCoverageRule, *, matched: set[str], covered: set[str]
) -> list[Violation]:
    """A non-behavioural declaration that excuses nothing is the exit condition firing."""
    findings: list[Violation] = []
    for declaration in rule.non_behavioural:
        if declaration.node not in matched:
            findings.append(
                _finding(
                    rule,
                    from_ref_id=declaration.node,
                    message=(
                        f"`{declaration.node}` is declared non-behavioural "
                        f"({declaration.reason!r}) but is not in this rule's "
                        f"population — the declaration excuses nothing"
                    ),
                    remediation=(
                        "delete the declaration, or fix the ref_id — a dead exclusion "
                        "hides how much of the population is really covered"
                    ),
                )
            )
        elif declaration.node in covered:
            findings.append(
                _finding(
                    rule,
                    from_ref_id=declaration.node,
                    message=(
                        f"`{declaration.node}` is declared non-behavioural "
                        f"({declaration.reason!r}) and a scenario binds to it anyway"
                    ),
                    remediation=(
                        "delete the declaration — the node has behaviour, and the "
                        "suite says so"
                    ),
                )
            )
    return findings


def _evaluate_one(
    conn: sqlite3.Connection, rule: ScenarioCoverageRule, project_root: Path
) -> list[Violation]:
    matched = _matched_nodes(conn, rule.for_matcher)
    findings: list[Violation] = []
    if not matched:
        findings.append(
            liveness_finding(
                rule_name=rule.name,
                rule_description=rule.description,
                message=(
                    f"the `for` matcher ({_matcher_description(rule.for_matcher)}) "
                    f"selects no node, so no behaviour-bearing node was checked for a "
                    f"scenario"
                ),
                remediation=(
                    "make the matcher name a kind or tag the graph actually has, or "
                    "delete the rule — it is counted in `N rules evaluated` and checks "
                    "nothing"
                ),
            )
        )

    suite = load_suite(project_root, rule.features)
    if inert_reason(rule, project_root, suite=suite) is not None:
        findings.append(
            liveness_finding(
                rule_name=rule.name,
                rule_description=rule.description,
                message=(
                    f"the acceptance suite glob `{rule.features}` matches no file, so "
                    f"no node was checked for a scenario and no scenario was checked "
                    f"for a binding"
                ),
                remediation=(
                    "point `features:` at the acceptance suite, or delete the rule — "
                    "an absent suite is not a covered one"
                ),
            )
        )
        return findings

    covered = {node for scenario in suite.scenarios for node in scenario.nodes}
    declared = {d.node: d.reason for d in rule.non_behavioural}
    findings.extend(_suite_leg(rule, suite=suite, known_refs=_all_ref_ids(conn)))
    findings.extend(
        _declaration_leg(rule, matched=set(matched), covered=covered)
    )
    findings.extend(
        _excused_statement(rule, matched=set(matched), covered=covered)
    )
    findings.extend(
        _coverage_leg(
            rule, matched=matched, suite=suite, covered=covered, declared=declared
        )
    )
    findings.extend(_reference_leg(rule, project_root=project_root, suite=suite))
    return findings


def evaluate_scenario_coverage_rules(
    conn: sqlite3.Connection,
    rules: list[ScenarioCoverageRule],
    *,
    project_root: Path | None = None,
) -> list[Violation]:
    """Evaluate every ``scenario_coverage`` rule against the graph and the suite.

    *project_root* (default: cwd) roots the ``features`` and ``references`` globs.
    """
    from pathlib import Path as _Path

    root = project_root if project_root is not None else _Path.cwd()
    findings: list[Violation] = []
    for rule in rules:
        findings.extend(_evaluate_one(conn, rule, root))
    return findings
