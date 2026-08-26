"""`doc-area-coherence` — the rule that holds a graph to its own docs placement.

BDL-062 `.2` (`beadloom-viaj.2`). The rule derives the convention from the graph
it is handed and reports the nodes that contradict it. Three standing rules from
BDL-061 shape this file, and they are cited by name:

**TESTS MUST BITE.** Every check below fails on its condition, not merely on a
crash: the contradiction test asserts *which* node is named, the unverifiable
tests assert the rule SAYS it checked nothing rather than returning an empty
list, and :func:`test_no_layout_literal_appears_in_the_rule` fails the moment a
directory name from any project is written into the rule.

**UNCHECKED IS NOT CLEAN, AND THE CHECKER MUST SAY WHICH.** ``unverifiable`` is
asserted as a state of its own — a distinct finding, a distinct gate line — never
as an empty violation list a reader would take for a pass.

**FAKES PROVE FAKES.** Every graph below is built with a source root and area
names this repository does not use (``app/billing``, ``platform/orders``), so a
rule that passed by knowing Beadloom's own tree would fail here.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from beadloom.graph.rules import (
    DOC_AREA_RULE_TYPE,
    LIVENESS_RULE_TYPE,
    DocAreaCoherenceRule,
    evaluate_all,
    evaluate_doc_area_coherence_rules,
    inert_rule_names,
    load_rules,
)
from beadloom.graph.rules.doc_area import derive_convention
from beadloom.infrastructure.db import create_schema, open_db

if TYPE_CHECKING:
    import sqlite3

    from beadloom.graph.rules import Violation

#: One placement: a node ref, the source it declares, the doc that documents it.
Placement = tuple[str, str, str]


def _graph(tmp_path: Path, placements: list[Placement]) -> sqlite3.Connection:
    """An index holding exactly *placements*, and nothing else."""
    conn = open_db(tmp_path / "graph.db")
    create_schema(conn)
    for ref_id, source, doc in placements:
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


def _rule(**kwargs: object) -> DocAreaCoherenceRule:
    defaults: dict[str, object] = {
        "name": "doc-area-coherence",
        "description": "a node documents itself where its graph says it should",
    }
    defaults.update(kwargs)
    return DocAreaCoherenceRule(**defaults)  # type: ignore[arg-type]


def _of_type(violations: list[Violation], rule_type: str) -> list[Violation]:
    return [v for v in violations if v.rule_type == rule_type]


def _coherent(area: str, count: int, docs_area: str | None = None) -> list[Placement]:
    """*count* nodes under *area*, each documented under *docs_area* (default *area*)."""
    target = docs_area if docs_area is not None else area
    return [
        (
            f"{area}-{index}",
            f"platform/{area}/{area}_{index}.py",
            f"reference/{target}/{area}-{index}/SPEC.md",
        )
        for index in range(count)
    ]


# --------------------------------------------------------------------------- #
# The convention is derived, and contradicting it is reported
# --------------------------------------------------------------------------- #


def test_a_node_documented_outside_its_area_is_named(tmp_path: Path) -> None:
    """The rule names the contradicting node, not merely "something is wrong"."""
    placements = (
        _coherent("orders", 5)
        + _coherent("billing", 4)
        + [("orders-stray", "platform/orders/stray.py", "reference/billing/stray/SPEC.md")]
    )
    conn = _graph(tmp_path, placements)
    violations = evaluate_doc_area_coherence_rules(conn, [_rule()])
    reported = _of_type(violations, DOC_AREA_RULE_TYPE)

    assert [v.from_ref_id for v in reported] == ["orders-stray"]
    assert reported[0].file_path == "reference/billing/stray/SPEC.md"


def test_a_coherent_graph_produces_no_finding(tmp_path: Path) -> None:
    """The other half of biting: the rule is silent when nothing contradicts it."""
    conn = _graph(tmp_path, _coherent("orders", 5) + _coherent("billing", 4))
    assert evaluate_doc_area_coherence_rules(conn, [_rule()]) == []


def test_the_convention_is_read_from_the_graph_not_from_a_layout(tmp_path: Path) -> None:
    """A graph that maps areas ACROSS names is enforced as the graph writes it.

    The strongest statement that nothing is hardcoded: here every ``orders`` node
    is documented under ``ledger`` and every ``billing`` node under ``orders``.
    The rule must enforce that crossed convention and report the one node that
    keeps the "obvious" arrangement instead.
    """
    placements = (
        _coherent("orders", 4, docs_area="ledger")
        + _coherent("billing", 4, docs_area="orders")
        + [("obvious", "platform/orders/obvious.py", "reference/orders/obvious/SPEC.md")]
    )
    conn = _graph(tmp_path, placements)
    reported = _of_type(
        evaluate_doc_area_coherence_rules(conn, [_rule()]), DOC_AREA_RULE_TYPE
    )

    assert [v.from_ref_id for v in reported] == ["obvious"]
    assert "under `ledger`" in reported[0].message


def test_a_doc_filed_where_no_area_is_named_is_still_compared(tmp_path: Path) -> None:
    """Drift into a directory that names no source area is the commonest shape.

    A first cut of this rule located the docs area by matching against the source
    areas alone, which made exactly this case invisible: ``scratch`` is nobody's
    source area, so no segment matched and the pair was skipped. The depth is
    derived from the population and then read for every path, so the stray is
    compared against ``orders`` like any other.
    """
    placements = (
        _coherent("orders", 5)
        + _coherent("billing", 4)
        + [("lost", "platform/orders/lost.py", "reference/scratch/lost/SPEC.md")]
    )
    conn = _graph(tmp_path, placements)
    reported = _of_type(
        evaluate_doc_area_coherence_rules(conn, [_rule()]), DOC_AREA_RULE_TYPE
    )

    assert [v.from_ref_id for v in reported] == ["lost"]
    assert "under `scratch`" in reported[0].message


def test_the_finding_states_the_sample_size_and_the_threshold(tmp_path: Path) -> None:
    """A verdict a reader cannot audit is a verdict they have to take on trust."""
    placements = (
        _coherent("orders", 5)
        + _coherent("billing", 4)
        + [("orders-stray", "platform/orders/stray.py", "reference/billing/stray/SPEC.md")]
    )
    conn = _graph(tmp_path, placements)
    message = _of_type(
        evaluate_doc_area_coherence_rules(conn, [_rule()]), DOC_AREA_RULE_TYPE
    )[0].message

    assert "10 node/doc pairs" in message
    assert "9 of those agree" in message
    assert "majority 0.60" in message
    assert "at least 2 observations" in message
    assert "5 of 6 `orders` nodes under `orders`" in message


# --------------------------------------------------------------------------- #
# Unverifiable is a state of its own
# --------------------------------------------------------------------------- #


def test_a_flat_docs_tree_reports_that_it_checked_nothing(tmp_path: Path) -> None:
    """No docs directories at all: nothing to compare, and the rule says so."""
    placements = [
        (f"{area}-{index}", f"platform/{area}/{area}_{index}.py", f"{area}-{index}.md")
        for area in ("orders", "billing")
        for index in range(4)
    ]
    conn = _graph(tmp_path, placements)
    violations = evaluate_doc_area_coherence_rules(conn, [_rule()])

    assert _of_type(violations, DOC_AREA_RULE_TYPE) == []
    liveness = _of_type(violations, LIVENESS_RULE_TYPE)
    assert len(liveness) == 1
    assert "checked nothing" in liveness[0].message
    assert "no node/doc pair yields a comparable area" in liveness[0].message
    assert liveness[0].severity == "warn"


def test_one_documented_node_per_area_reports_that_it_checked_nothing(
    tmp_path: Path,
) -> None:
    """A graph too small to hold a convention is unverifiable, not unanimous.

    Without the minimum support every area is "unanimous" at one observation, and
    a six-node graph reports a clean sweep having compared nothing that could
    disagree. This test fails the moment ``min_support`` stops being applied.
    """
    placements = [
        (area, f"platform/{area}/service.py", f"reference/{area}/service/SPEC.md")
        for area in ("orders", "billing", "catalogue", "search", "payments", "audit")
    ]
    conn = _graph(tmp_path, placements)
    violations = evaluate_doc_area_coherence_rules(conn, [_rule()])

    assert _of_type(violations, DOC_AREA_RULE_TYPE) == []
    liveness = _of_type(violations, LIVENESS_RULE_TYPE)
    assert len(liveness) == 1
    assert "checked nothing" in liveness[0].message
    assert "6 pairs across 6 source areas" in liveness[0].message


def test_an_area_split_evenly_is_left_unchecked_not_called_wrong(tmp_path: Path) -> None:
    """A migration in progress has no convention to be judged against.

    ``billing`` is documented half in one place and half in another, which no
    threshold above 0.5 can call dominant. Those pairs are neither cleared nor
    reported, and the count of what fell under a dominant mapping says so.
    """
    placements = [
        *_coherent("orders", 6),
        ("billing-a", "platform/billing/a.py", "reference/billing/a/SPEC.md"),
        ("billing-b", "platform/billing/b.py", "reference/billing/b/SPEC.md"),
        ("billing-c", "platform/billing/c.py", "reference/ledger/c/SPEC.md"),
        ("billing-d", "platform/billing/d.py", "reference/ledger/d/SPEC.md"),
    ]
    conn = _graph(tmp_path, placements)
    violations = evaluate_doc_area_coherence_rules(conn, [_rule()])
    assert _of_type(violations, DOC_AREA_RULE_TYPE) == []

    convention = derive_convention(conn, threshold=0.6, min_support=2)
    assert set(convention.dominant) == {"orders"}
    assert convention.sampled == 10
    assert len(convention.checked) == 6
    assert "6 fall under a dominant mapping" in convention.population()


def test_the_gate_line_says_the_rule_was_unable_to_check_anything(
    tmp_path: Path,
) -> None:
    """The unverifiable state reaches the summary a human reads, not just a list.

    NO CALLER NO CAPABILITY: a state reported only inside the module that
    computes it is not reported. This asserts the count ``lint`` prints.
    """
    placements = [
        (f"orders-{index}", f"platform/orders/x{index}.py", f"orders-{index}.md")
        for index in range(4)
    ]
    conn = _graph(tmp_path, placements)
    rule = _rule()

    assert inert_rule_names(conn, [rule], project_root=tmp_path) == {"doc-area-coherence"}

    findings = evaluate_all(conn, [rule], project_root=tmp_path)
    # Counted once, reported once: the generic liveness pass must not add a
    # second finding for the same fact.
    assert len(_of_type(findings, LIVENESS_RULE_TYPE)) == 1


def test_the_summary_a_human_reads_qualifies_the_rule_count(tmp_path: Path) -> None:
    """End to end: the unverifiable state reaches the line `lint` prints.

    The count and the sentence are computed in different modules, so asserting
    the count alone would leave "and the gate line says so" unproven.
    """
    from beadloom.graph.linter import format_rich, lint

    project = tmp_path / "project"
    (project / ".beadloom" / "_graph").mkdir(parents=True)
    (project / ".beadloom" / "_graph" / "rules.yml").write_text(
        "version: 3\nrules:\n"
        "  - name: doc-area-coherence\n"
        '    description: "a node documents itself where its graph says it should"\n'
        "    doc_area_coherence: {}\n",
        encoding="utf-8",
    )
    conn = _graph(
        project / ".beadloom",
        [
            (f"orders-{index}", f"platform/orders/x{index}.py", f"orders-{index}.md")
            for index in range(4)
        ],
    )
    conn.close()
    (project / ".beadloom" / "graph.db").rename(project / ".beadloom" / "beadloom.db")

    result = lint(project)
    assert result.rules_inert == 1
    assert "1 of them unable to check anything" in format_rich(result)


def test_a_derivable_graph_is_not_counted_as_inert(tmp_path: Path) -> None:
    """The other half: a rule that DID check is not reported as standing down."""
    conn = _graph(tmp_path, _coherent("orders", 5) + _coherent("billing", 4))
    assert inert_rule_names(conn, [_rule()], project_root=tmp_path) == set()


# --------------------------------------------------------------------------- #
# No layout literal, anywhere
# --------------------------------------------------------------------------- #


def test_no_layout_literal_appears_in_the_rule() -> None:
    """The rule must not name a directory from any project's tree.

    This is the bead's single most important constraint made executable: a
    literal such as ``docs/domains/`` ships this repository's layout as every
    adopter's and is wrong for a feature-sliced project on day one. The check
    scans the code of the module and its rule type, ignoring the prose, so a
    docstring may still discuss ``domains`` as an example while the code may not
    contain it.
    """
    import ast

    from beadloom.graph.rules import doc_area, types

    forbidden = {
        "docs",
        "domains",
        "services",
        "features",
        "components",
        "src",
        "app",
        "reference",
    }

    def _own_code(module: object, names: set[str] | None) -> list[ast.AST]:
        """The rule's own code: a whole module, or only the nodes *names* covers."""
        source = Path(module.__file__ or "").read_text(encoding="utf-8")  # type: ignore[attr-defined]
        tree = ast.parse(source)
        if names is None:
            return [tree]
        return [
            node
            for node in tree.body
            if (isinstance(node, ast.ClassDef) and node.name in names)
            or (
                isinstance(node, ast.Assign)
                and any(
                    isinstance(target, ast.Name) and target.id in names
                    for target in node.targets
                )
            )
        ]

    # `types` holds every rule's dataclass, and `ModuleCoverageRule` legitimately
    # carries a source root default; only this rule's own declaration is scanned.
    scanned = [
        ("doc_area", _own_code(doc_area, None)),
        (
            "types",
            _own_code(
                types,
                {
                    "DocAreaCoherenceRule",
                    "DEFAULT_DOC_AREA_THRESHOLD",
                    "DEFAULT_DOC_AREA_MIN_SUPPORT",
                },
            ),
        ),
    ]
    for where, roots in scanned:
        assert roots, f"nothing of {where} was scanned"
        for root in roots:
            prose = {
                id(node.body[0].value)
                for node in ast.walk(root)
                if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef))
                and node.body
                and isinstance(node.body[0], ast.Expr)
                and isinstance(node.body[0].value, ast.Constant)
                and isinstance(node.body[0].value.value, str)
            }
            for node in ast.walk(root):
                if not isinstance(node, ast.Constant) or not isinstance(node.value, str):
                    continue
                if id(node) in prose:
                    continue
                segments = {part.strip().casefold() for part in node.value.split("/")}
                assert not (segments & forbidden), (
                    f"{where} carries the layout literal {node.value!r} "
                    f"on line {node.lineno}"
                )


# --------------------------------------------------------------------------- #
# Configuration: the rule loads, defaults to warn, and refuses nonsense
# --------------------------------------------------------------------------- #


def _rules_yaml(tmp_path: Path, block: str) -> Path:
    path = tmp_path / "rules.yml"
    path.write_text(
        "version: 3\nrules:\n"
        "  - name: doc-area-coherence\n"
        '    description: "a node documents itself where its graph says it should"\n'
        f"{block}",
        encoding="utf-8",
    )
    return path


def test_the_rule_loads_and_defaults_to_warn(tmp_path: Path) -> None:
    """It ships advisory: an adopter's first run must not fail on house style."""
    rules = load_rules(_rules_yaml(tmp_path, "    doc_area_coherence: {}\n"))
    assert len(rules) == 1
    rule = rules[0]
    assert isinstance(rule, DocAreaCoherenceRule)
    assert rule.severity == "warn"
    assert rule.threshold == pytest.approx(0.6)
    assert rule.min_support == 2


def test_a_project_can_escalate_the_rule_to_error(tmp_path: Path) -> None:
    """A project whose layout has settled enforces it, which is what this one does."""
    rules = load_rules(
        _rules_yaml(
            tmp_path,
            "    severity: error\n"
            "    doc_area_coherence:\n"
            "      threshold: 0.75\n"
            "      min_support: 3\n",
        )
    )
    rule = rules[0]
    assert isinstance(rule, DocAreaCoherenceRule)
    assert rule.severity == "error"
    assert rule.threshold == pytest.approx(0.75)
    assert rule.min_support == 3


def test_the_declared_severity_reaches_the_finding(tmp_path: Path) -> None:
    """An escalation that never reaches a violation is a setting, not a rule."""
    placements = (
        _coherent("orders", 5)
        + _coherent("billing", 4)
        + [("orders-stray", "platform/orders/stray.py", "reference/billing/stray/SPEC.md")]
    )
    conn = _graph(tmp_path, placements)
    reported = _of_type(
        evaluate_doc_area_coherence_rules(conn, [_rule(severity="error")]),
        DOC_AREA_RULE_TYPE,
    )
    assert [v.severity for v in reported] == ["error"]


@pytest.mark.parametrize(
    ("block", "fragment"),
    [
        ("    doc_area_coherence:\n      threshold: 0.5\n", "greater than"),
        ("    doc_area_coherence:\n      threshold: 1.5\n", "at most 1.0"),
        ("    doc_area_coherence:\n      threshold: high\n", "must be a number"),
        ("    doc_area_coherence:\n      min_support: 1\n", "at least 2"),
        ("    doc_area_coherence:\n      min_support: two\n", "must be an integer"),
    ],
)
def test_a_setting_that_could_only_silence_the_rule_is_refused(
    tmp_path: Path, block: str, fragment: str
) -> None:
    """A threshold under a majority and a support of one are silences, not settings."""
    with pytest.raises(ValueError, match=fragment):
        load_rules(_rules_yaml(tmp_path, block))


def test_the_rule_survives_being_written_to_the_index(tmp_path: Path) -> None:
    """Reindex serializes every rule type or raises; an unregistered type breaks it."""
    from beadloom.application.reindex.rules_loader import _serialize_rule

    rule_type, payload = _serialize_rule(_rule(threshold=0.8, min_support=4))
    assert rule_type == "doc_area_coherence"
    assert payload == {"threshold": 0.8, "min_support": 4}
