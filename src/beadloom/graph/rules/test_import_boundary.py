# beadloom:domain=graph
# beadloom:feature=rule-engine
"""``test_import_boundary`` — ``forbid_import``, run over the imports of test files.

**One responsibility:** choose which recorded TEST imports a boundary judges, and
state how many test files that choice left out. The judging itself is
``forbid_import``'s — :func:`~beadloom.graph.rules.evaluators.evaluate_one_import_rule` — so a
crossing, an exemption that excuses nothing and an exemption past its date mean
here exactly what they mean for source code.

Which files are judged: the ones the ``from`` glob matches and, when ``of`` is
set, whose bound node is selected by it or is ``part_of`` a node it selects.
"A unit test of a domain node" is ``from: tests/unit/**`` with ``of: {tag:
layer-domain}``. A file bound to no node cannot be the test of a domain node, so
under ``of`` it is not judged, and it is counted as such.

**What this reads differently from ``forbid_import``.** The test imports come
from ``test_imports`` (C1), whose reader keeps an aliased ``import a as b`` that
the code-import extractor drops. The population statement says so, because the
same boundary could otherwise report a crossing in a test that it would not
report in the source file it tests.

Liveness is decided before the crossings: a ``from`` glob no test file matches,
an ``of`` matcher that leaves no file, or a ``to`` glob no recorded test import
reaches stands the rule down, in the test-file vocabulary.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from fnmatch import fnmatch
from typing import TYPE_CHECKING

from beadloom.graph.rules.evaluators import evaluate_one_import_rule
from beadloom.graph.rules.exemptions import exemption_index_for, stale_exemption_findings
from beadloom.graph.rules.suite_tables import (
    NodeSelection,
    read_test_files,
    read_test_imports,
)
from beadloom.graph.rules.types import (
    Violation,
    import_path_as_path,
    liveness_finding,
    matches_import_target,
    population_finding,
)

if TYPE_CHECKING:
    import sqlite3

    from beadloom.graph.rules.suite_tables import TestImport
    from beadloom.graph.rules.types import TestImportBoundaryRule

#: ``rule_type`` of a crossing this rule reports.
TEST_IMPORT_BOUNDARY_RULE_TYPE = "test_import_boundary"

#: The rule type ``forbid_import``'s evaluator stamps on a crossing, replaced here.
_FORBID_IMPORT = "forbid_import"

#: What each side is matched against, in this rule's vocabulary: the two forms
#: ``forbid_import`` states in ``MATCHING_FORM_HINT``, with a test file on the left.
_MATCHING_FORM = (
    "`from:` is matched against the repo-relative test file path as indexed (e.g. "
    "`tests/unit/pkg/test_app.py`); `to:` against the dotted import path with dots "
    "replaced by slashes (e.g. `pkg/infrastructure/db`); `of:` against the node the "
    "test file is bound to and that node's `part_of` containers"
)


@dataclass(frozen=True)
class _Selection:
    """The imports a rule judges, the counts that explain the rest, and why it cannot look."""

    imports: list[tuple[str, int, str]]
    judged_files: int
    files_with_imports: int
    outside_from: int
    unbound: int
    outside_of: int
    dead_reason: str | None


def _select(conn: sqlite3.Connection, rule: TestImportBoundaryRule) -> _Selection:
    recorded = read_test_imports(conn) or []
    by_file: dict[str, list[TestImport]] = {}
    for test_import in recorded:
        by_file.setdefault(test_import.file_path, []).append(test_import)
    bound = {f.path: f.ref_id for f in read_test_files(conn) or []}
    selection = NodeSelection(conn, rule.of_matcher) if rule.of_matcher is not None else None

    judged: list[str] = []
    outside_from = unbound = outside_of = 0
    for path in sorted(by_file):
        if not fnmatch(path, rule.from_glob):
            outside_from += 1
        elif selection is None:
            judged.append(path)
        elif bound.get(path) is None:
            unbound += 1
        elif selection.holds_or_contains(str(bound[path])):
            judged.append(path)
        else:
            outside_of += 1

    imports = [(i.file_path, i.line_number, i.import_path) for p in judged for i in by_file[p]]
    return _Selection(
        imports=imports,
        judged_files=len(judged),
        files_with_imports=len(by_file),
        outside_from=outside_from,
        unbound=unbound,
        outside_of=outside_of,
        dead_reason=_dead_reason(rule, recorded, len(by_file) - outside_from, judged),
    )


def _dead_reason(
    rule: TestImportBoundaryRule,
    recorded: list[TestImport],
    from_matches: int,
    judged: list[str],
) -> str | None:
    files = len({i.file_path for i in recorded})
    if not recorded:
        return "the index records no test import — no test file was read, or none imports"
    if from_matches == 0:
        return f"its `from` glob '{rule.from_glob}' matches 0 of {files} test file(s) with imports"
    if not judged and rule.of_matcher is not None:
        return (
            f"its `of` matcher ({rule.of_matcher.describe()}) selects no node that one of "
            f"the {from_matches} test file(s) matching `from` is bound to"
        )
    targets = {import_path_as_path(i.import_path) for i in recorded}
    if not any(matches_import_target(target, rule.to_glob) for target in targets):
        return (
            f"its `to` glob '{rule.to_glob}' matches 0 of {len(targets)} import path(s) "
            f"recorded for test files"
        )
    return None


def test_import_boundary_inert_reason(
    conn: sqlite3.Connection, rule: TestImportBoundaryRule
) -> str | None:
    """Why this rule can judge nothing, or ``None``: one predicate for finding and count."""
    return _select(conn, rule).dead_reason


def _excused_crossings(rule: TestImportBoundaryRule, chosen: _Selection) -> int:
    """How many judged imports cross the boundary and are excused by an exemption.

    Counted here because ``lint``'s ``N crossings suppressed`` reads
    ``code_imports`` only: without this clause an excused test crossing would
    appear nowhere in the output.
    """
    import_rule = rule.as_import_rule()
    return sum(
        1
        for path, _line, import_path in chosen.imports
        if matches_import_target(import_path_as_path(import_path), rule.to_glob)
        and exemption_index_for(import_rule, path, import_path_as_path(import_path)) is not None
    )


def _population(rule: TestImportBoundaryRule, chosen: _Selection) -> Violation:
    return population_finding(
        rule_name=rule.name,
        rule_description=rule.description,
        message=(
            f"judged {chosen.judged_files} of {chosen.files_with_imports} test file(s) with "
            f"recorded imports ({len(chosen.imports)} import(s), "
            f"{_excused_crossings(rule, chosen)} crossing(s) excused by an exemption); "
            f"not judged: "
            f"{chosen.outside_from} outside the `from` glob, {chosen.unbound} bound to no "
            f"node, {chosen.outside_of} bound to a node outside `of`. Test imports keep an "
            f"aliased `import a as b`, which the code-import index drops"
        ),
    )


def _evaluate_one(conn: sqlite3.Connection, rule: TestImportBoundaryRule) -> list[Violation]:
    chosen = _select(conn, rule)
    if chosen.dead_reason is not None:
        return [
            liveness_finding(
                rule_name=rule.name,
                rule_description=rule.description,
                message=(
                    f"Rule '{rule.name}' cannot fire: {chosen.dead_reason}. It is counted "
                    f"as evaluated but checks nothing"
                ),
                remediation=_MATCHING_FORM,
            ),
            _population(rule, chosen),
        ]
    import_rule = rule.as_import_rule()
    if any(
        matches_import_target(import_path_as_path(imp[2]), rule.to_glob) for imp in chosen.imports
    ):
        found = evaluate_one_import_rule(
            import_rule,
            chosen.imports,
            file_count=chosen.judged_files,
            target_count=len({imp[2] for imp in chosen.imports}),
        )
    else:
        # No judged file imports the target: the boundary holds, and the only thing
        # left to say is which exemptions excuse nothing. `forbid_import`'s evaluator
        # would read the same fact as a dead `to` glob, because it is handed only the
        # judged imports — liveness was decided above over every recorded one.
        found = stale_exemption_findings(import_rule, {})
    renamed = [
        replace(v, rule_type=TEST_IMPORT_BOUNDARY_RULE_TYPE)
        if v.rule_type == _FORBID_IMPORT
        else v
        for v in found
    ]
    return [*renamed, _population(rule, chosen)]


def evaluate_test_import_boundary_rules(
    conn: sqlite3.Connection, rules: list[TestImportBoundaryRule]
) -> list[Violation]:
    """Evaluate every ``test_import_boundary`` rule over the recorded test imports."""
    findings: list[Violation] = []
    for rule in rules:
        findings.extend(_evaluate_one(conn, rule))
    return findings
