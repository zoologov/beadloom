"""`graph-summary-facts` — the rule that checks a number stated in a node summary.

BDL-062 `.1` (`beadloom-viaj.1`). The rule reads the numeric and version claims
out of every node ``summary`` and compares each one against the same fact the
project computes about itself. Three standing rules from BDL-061 shape this file
and are cited by name:

**TESTS MUST BITE.** Every check below fails on its condition, not merely on a
crash. The disagreement tests assert *which* node is named and that BOTH values
appear; :func:`test_the_rule_owns_no_second_notion_of_a_version` fails the moment
a version pattern or a fact-keyword table is written into the rule module, which
is the neutering that would let the two extractors drift apart.

**UNCHECKED IS NOT CLEAN, AND THE CHECKER MUST SAY WHICH.** ``unverifiable`` is
asserted as a state of its own — a distinct finding carrying the project's own
decline reason — never as an empty violation list a reader would take for a pass.

**FAKES PROVE FAKES.** Every graph below is built with node names and facts this
repository does not have (``gateway``, ``atlas``, ``ledger``; a version of
``4.2.0``), so a rule that passed by knowing Beadloom's own numbers would fail
here. The one test that DOES read this repository says so in its name.
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from beadloom.doc_sync import Fact, FactSet
from beadloom.graph.rules import (
    LIVENESS_RULE_TYPE,
    SUMMARY_FACTS_RULE_TYPE,
    SummaryFactsRule,
    evaluate_all,
    evaluate_summary_facts_rules,
    inert_rule_names,
    load_rules,
)
from beadloom.graph.rules.summary_facts import collect_claims, summary_facts_inert_reason
from beadloom.infrastructure.db import create_schema, open_db

if TYPE_CHECKING:
    import sqlite3

    from beadloom.graph.rules import Violation

#: The rule module, read as text by the "no second notion" guard.
RULE_MODULE = Path("src/beadloom/graph/rules/summary_facts.py")


def _graph(tmp_path: Path, summaries: dict[str, str]) -> sqlite3.Connection:
    """An index holding exactly these node summaries, and nothing else."""
    conn = open_db(tmp_path / "graph.db")
    create_schema(conn)
    for ref_id, summary in summaries.items():
        conn.execute(
            "INSERT INTO nodes (ref_id, kind, summary, source) VALUES (?, ?, ?, ?)",
            (ref_id, "feature", summary, f"platform/{ref_id}.py"),
        )
    conn.commit()
    return conn


def _facts(**values: str | int) -> FactSet:
    """A project that computed exactly these facts and declined nothing."""
    return FactSet(
        facts={
            name: Fact(name=name, value=value, source="the fixture")
            for name, value in values.items()
        }
    )


def _declining(**reasons: str) -> FactSet:
    """A project that computed nothing and stated why for each fact."""
    return FactSet(facts={}, not_applicable=dict(reasons))


def _rule(**kwargs: object) -> SummaryFactsRule:
    defaults: dict[str, object] = {
        "name": "graph-summary-facts",
        "description": "a number in a node summary agrees with the project",
    }
    defaults.update(kwargs)
    return SummaryFactsRule(**defaults)  # type: ignore[arg-type]


def _findings(violations: list[Violation], rule_type: str) -> list[Violation]:
    return [v for v in violations if v.rule_type == rule_type]


# --------------------------------------------------------------------------- #
# disagrees — the state that fails the gate
# --------------------------------------------------------------------------- #


class TestDisagreement:
    """A claim that differs from the computed fact is named, with both values."""

    def test_a_stale_count_names_the_node_and_both_values(self, tmp_path: Path) -> None:
        conn = _graph(tmp_path, {"gateway": "MCP stdio server with 14 tools for agents"})
        found = _findings(
            evaluate_summary_facts_rules(
                conn, [_rule()], fact_set=_facts(mcp_tool_count=18)
            ),
            SUMMARY_FACTS_RULE_TYPE,
        )
        assert [v.from_ref_id for v in found] == ["gateway"]
        assert "14" in found[0].message
        assert "18" in found[0].message

    def test_a_stale_version_is_reported_though_the_claim_carries_a_v(
        self, tmp_path: Path
    ) -> None:
        conn = _graph(tmp_path, {"platform": "The platform, release v1.5.0"})
        found = _findings(
            evaluate_summary_facts_rules(
                conn, [_rule()], fact_set=_facts(version="4.2.0")
            ),
            SUMMARY_FACTS_RULE_TYPE,
        )
        assert [v.from_ref_id for v in found] == ["platform"]
        assert "1.5.0" in found[0].message
        assert "4.2.0" in found[0].message

    def test_a_matching_version_is_not_reported_though_it_is_spelled_with_a_v(
        self, tmp_path: Path
    ) -> None:
        """``v4.2.0`` and ``4.2.0`` are the same version.

        The comparison is the audit's, which strips the leading ``v`` on both
        sides. A rule that compared the two strings raw would report every
        correct version in every graph — a false positive on the commonest
        spelling there is.
        """
        conn = _graph(tmp_path, {"platform": "The platform, release v4.2.0"})
        assert not _findings(
            evaluate_summary_facts_rules(
                conn, [_rule()], fact_set=_facts(version="4.2.0")
            ),
            SUMMARY_FACTS_RULE_TYPE,
        )

    def test_the_finding_carries_the_rule_s_own_severity(self, tmp_path: Path) -> None:
        conn = _graph(tmp_path, {"gateway": "MCP stdio server with 14 tools for agents"})
        found = _findings(
            evaluate_summary_facts_rules(
                conn, [_rule(severity="warn")], fact_set=_facts(mcp_tool_count=18)
            ),
            SUMMARY_FACTS_RULE_TYPE,
        )
        assert [v.severity for v in found] == ["warn"]

    def test_every_finding_states_the_population_it_is_a_fraction_of(
        self, tmp_path: Path
    ) -> None:
        """A GREEN COUNT IS NOT A CHECKED COUNT, applied to the red one too."""
        conn = _graph(
            tmp_path,
            {
                "gateway": "MCP stdio server with 14 tools for agents",
                "ledger": "Double-entry ledger",
                "atlas": "The atlas of everything",
            },
        )
        found = _findings(
            evaluate_summary_facts_rules(
                conn, [_rule()], fact_set=_facts(mcp_tool_count=18)
            ),
            SUMMARY_FACTS_RULE_TYPE,
        )
        assert "read from 3 node summaries" in found[0].message
        assert "1 state a checkable fact" in found[0].message
        assert "2 state none" in found[0].message

    def test_a_finding_carries_an_actionable_remediation(self, tmp_path: Path) -> None:
        conn = _graph(tmp_path, {"gateway": "MCP stdio server with 14 tools for agents"})
        found = _findings(
            evaluate_summary_facts_rules(
                conn, [_rule()], fact_set=_facts(mcp_tool_count=18)
            ),
            SUMMARY_FACTS_RULE_TYPE,
        )
        assert found[0].remediation is not None
        assert "summary" in found[0].remediation


# --------------------------------------------------------------------------- #
# agrees / no claim — the two states that pass, kept apart
# --------------------------------------------------------------------------- #


class TestAgreementAndSilence:
    """A summary that agrees passes; a summary that says nothing is not the same."""

    def test_an_agreeing_count_is_reported_by_nobody(self, tmp_path: Path) -> None:
        conn = _graph(tmp_path, {"gateway": "MCP stdio server with 18 tools for agents"})
        violations = evaluate_summary_facts_rules(
            conn, [_rule()], fact_set=_facts(mcp_tool_count=18)
        )
        assert not violations

    def test_a_graph_stating_no_number_reports_that_it_checked_nothing(
        self, tmp_path: Path
    ) -> None:
        """UNCHECKED IS NOT CLEAN — the empty list would read as a pass."""
        conn = _graph(tmp_path, {"widgets": "Widgets, and the handling thereof"})
        found = _findings(
            evaluate_summary_facts_rules(
                conn, [_rule()], fact_set=_facts(node_count=30)
            ),
            LIVENESS_RULE_TYPE,
        )
        assert len(found) == 1
        assert "checked nothing" in found[0].message
        assert found[0].severity == "warn"

    def test_a_live_rule_does_not_also_claim_it_checked_nothing(
        self, tmp_path: Path
    ) -> None:
        conn = _graph(tmp_path, {"gateway": "MCP stdio server with 18 tools for agents"})
        assert summary_facts_inert_reason(conn, tmp_path) is None

    def test_the_liveness_count_and_the_rule_agree_about_standing_down(
        self, tmp_path: Path
    ) -> None:
        """One predicate, so the count `lint` prints cannot contradict the finding."""
        conn = _graph(tmp_path, {"widgets": "Widgets, and the handling thereof"})
        assert summary_facts_inert_reason(conn, tmp_path) is not None
        assert inert_rule_names(conn, [_rule()], project_root=tmp_path) == {
            "graph-summary-facts"
        }


# --------------------------------------------------------------------------- #
# unverifiable — the state the whole feature exists to keep separate
# --------------------------------------------------------------------------- #


class TestUnverifiable:
    """A claim about a fact the project declined to compute is reported, not passed."""

    def test_a_claim_on_a_declined_fact_is_not_a_disagreement(
        self, tmp_path: Path
    ) -> None:
        conn = _graph(tmp_path, {"atlas": "The atlas, indexing 42 nodes"})
        violations = evaluate_summary_facts_rules(
            conn,
            [_rule()],
            fact_set=_declining(node_count="the nodes table could not be read"),
        )
        assert not _findings(violations, SUMMARY_FACTS_RULE_TYPE)

    def test_a_claim_on_a_declined_fact_is_reported_with_the_project_s_own_reason(
        self, tmp_path: Path
    ) -> None:
        """The reason belongs to the registry that declined, not to this rule.

        Rewording it here would be a second account of the same refusal, and the
        two would diverge the first time the registry learned a better one.
        """
        conn = _graph(tmp_path, {"atlas": "The atlas, indexing 42 nodes"})
        found = _findings(
            evaluate_summary_facts_rules(
                conn,
                [_rule()],
                fact_set=_declining(node_count="the nodes table could not be read"),
            ),
            LIVENESS_RULE_TYPE,
        )
        assert len(found) == 1
        assert "atlas" in found[0].message
        assert "could not be verified" in found[0].message
        assert "the nodes table could not be read" in found[0].message

    def test_an_unverifiable_claim_does_not_stand_the_whole_rule_down(
        self, tmp_path: Path
    ) -> None:
        """A rule that found a claim it could not check is live, not inert.

        The two are different reports, and collapsing them would hide either the
        one node nobody can check or the whole graph nobody checked.
        """
        conn = _graph(tmp_path, {"atlas": "The atlas, indexing 42 nodes"})
        assert summary_facts_inert_reason(conn, tmp_path) is None

    def test_unverifiable_is_counted_apart_from_agreement(self, tmp_path: Path) -> None:
        conn = _graph(
            tmp_path,
            {
                "gateway": "MCP stdio server with 18 tools for agents",
                "atlas": "The atlas, indexing 42 nodes",
            },
        )
        claims = collect_claims(
            conn,
            FactSet(
                facts={
                    "mcp_tool_count": Fact(
                        name="mcp_tool_count", value=18, source="the fixture"
                    )
                },
                not_applicable={"node_count": "the nodes table could not be read"},
            ),
        )
        assert [c.ref_id for c in claims.agreeing] == ["gateway"]
        assert [c.ref_id for c in claims.unverifiable] == ["atlas"]
        assert claims.disagreeing == ()
        assert claims.silent == 0

    def test_a_claim_naming_a_fact_the_project_never_declared_says_so(
        self, tmp_path: Path
    ) -> None:
        """Neither computed nor declined is still not verified.

        A registry that simply does not know a fact leaves it out of both dicts.
        Reading that as agreement is the exact silent pass this rule refuses.
        """
        conn = _graph(tmp_path, {"atlas": "The atlas, indexing 42 nodes"})
        found = _findings(
            evaluate_summary_facts_rules(conn, [_rule()], fact_set=_facts()),
            LIVENESS_RULE_TYPE,
        )
        assert len(found) == 1
        assert "not a fact this project declares" in found[0].message


# --------------------------------------------------------------------------- #
# false positives — a number in prose is not a claim about the project
# --------------------------------------------------------------------------- #


class TestProseIsNotAClaim:
    """A bare integer near a noun is not a count of anything the project holds."""

    @pytest.mark.parametrize(
        "summary",
        [
            "Routing across 3 kinds of node",
            "Interactive 3-screen architecture workstation",
            "Graph traversal to a maximum depth of 30 nodes",
            "A node is indexed at most 30 times",
        ],
    )
    def test_a_small_or_modified_number_is_not_read_as_a_count(
        self, tmp_path: Path, summary: str
    ) -> None:
        """The computed count is 84, so a matcher that read any integer as a
        count would report every one of these as a disagreement."""
        conn = _graph(tmp_path, {"router": summary})
        assert not _findings(
            evaluate_summary_facts_rules(
                conn, [_rule()], fact_set=_facts(node_count=84)
            ),
            SUMMARY_FACTS_RULE_TYPE,
        )

    def test_a_number_with_no_keyword_beside_it_is_not_read_as_a_count(
        self, tmp_path: Path
    ) -> None:
        conn = _graph(tmp_path, {"ledger": "Double-entry ledger, 42 currencies"})
        assert not _findings(
            evaluate_summary_facts_rules(
                conn, [_rule()], fact_set=_facts(node_count=84)
            ),
            SUMMARY_FACTS_RULE_TYPE,
        )

    def test_a_dotted_identifier_is_not_read_as_a_version(self, tmp_path: Path) -> None:
        """``BDL-061.33`` and ``cli.py:645`` end in digits that mean nothing alone."""
        conn = _graph(tmp_path, {"ledger": "Ledger, tracked as BDL-061.33 in cli.py:645"})
        assert not _findings(
            evaluate_summary_facts_rules(
                conn, [_rule()], fact_set=_facts(version="4.2.0")
            ),
            SUMMARY_FACTS_RULE_TYPE,
        )


# --------------------------------------------------------------------------- #
# the neutering guards
# --------------------------------------------------------------------------- #


class TestOneNotionOfAVersion:
    """The rule must not grow its own extractor beside the audit's."""

    def test_the_rule_owns_no_second_notion_of_a_version(self) -> None:
        """No version pattern and no fact-keyword table appears in the rule module.

        THE NEUTERING THIS BITES ON: pasting ``re.compile(r"\\bv?\\d+\\.\\d+\\.\\d+\\b")``
        or a ``{"node_count": ["node", ...]}`` table into the rule. Both would
        pass every behavioural test above on the day they were written and
        diverge from the audit on the first token-boundary or clause-scope repair
        that landed on only one of the two.
        """
        module = ast.parse(RULE_MODULE.read_text(encoding="utf-8"))
        literals = [
            node.value
            for node in ast.walk(module)
            if isinstance(node, ast.Constant) and isinstance(node.value, str)
        ]
        docstrings = {
            ast.get_docstring(node, clean=False)
            for node in ast.walk(module)
            if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef))
        }
        code_literals = [text for text in literals if text not in docstrings]

        assert not [text for text in code_literals if "\\d" in text or "\\b" in text], (
            "a regular expression in the rule module is a second notion of a "
            "version — the extraction belongs to DocScanner"
        )
        keywords = {"language", "framework", "subcommand", "rule kind", "assertion"}
        assert not [
            text for text in code_literals if text.casefold() in keywords
        ], "a fact keyword in the rule module is a second keyword table"

    def test_the_extraction_is_the_scanner_s_own_seam(self, tmp_path: Path) -> None:
        """NO CALLER NO CAPABILITY, in the other direction.

        THE NEUTERING THIS BITES ON: reimplementing ``scan_line`` inside the
        rule. Patching the scanner's seam must silence the rule, which it can
        only do if the rule genuinely goes through it.
        """
        import beadloom.doc_sync.scanner as scanner_module

        conn = _graph(tmp_path, {"gateway": "MCP stdio server with 14 tools for agents"})
        original = scanner_module.DocScanner.scan_line
        try:
            scanner_module.DocScanner.scan_line = (  # type: ignore[method-assign]
                lambda self, line, *, origin, line_number=1: []
            )
            silenced = evaluate_summary_facts_rules(
                conn, [_rule()], fact_set=_facts(mcp_tool_count=18)
            )
        finally:
            scanner_module.DocScanner.scan_line = original  # type: ignore[method-assign]
        assert not _findings(silenced, SUMMARY_FACTS_RULE_TYPE)


# --------------------------------------------------------------------------- #
# wiring
# --------------------------------------------------------------------------- #


class TestWiring:
    """The rule is reachable from the YAML an adopter writes, and from `lint`."""

    def test_the_loader_parses_the_rule_and_defaults_it_to_error(
        self, tmp_path: Path
    ) -> None:
        rules_path = tmp_path / "rules.yml"
        rules_path.write_text(
            "version: 3\n"
            "rules:\n"
            "  - name: graph-summary-facts\n"
            '    description: "a number in a summary agrees with the project"\n'
            "    summary_facts: {}\n",
            encoding="utf-8",
        )
        rules = load_rules(rules_path)
        assert rules == [
            SummaryFactsRule(
                name="graph-summary-facts",
                description="a number in a summary agrees with the project",
                severity="error",
            )
        ]

    def test_the_loader_rejects_a_key_that_would_do_nothing(
        self, tmp_path: Path
    ) -> None:
        """A setting that looks configured and is ignored is the defect, not a nicety."""
        rules_path = tmp_path / "rules.yml"
        rules_path.write_text(
            "version: 3\n"
            "rules:\n"
            "  - name: graph-summary-facts\n"
            '    description: "a number in a summary agrees with the project"\n'
            "    summary_facts:\n"
            "      threshold: 0.9\n",
            encoding="utf-8",
        )
        with pytest.raises(ValueError, match="takes no keys"):
            load_rules(rules_path)

    def test_evaluate_all_dispatches_to_the_rule(self, tmp_path: Path) -> None:
        """NO CALLER NO CAPABILITY: the rule fires through the engine, not only direct."""
        conn = _graph(tmp_path, {"gateway": "MCP stdio server with 14 tools for agents"})
        found = _findings(
            evaluate_all(conn, [_rule()], project_root=tmp_path),
            SUMMARY_FACTS_RULE_TYPE,
        )
        # `tmp_path` is not a Beadloom checkout, so the registry declines the
        # surface facts — but `mcp_tool_count` is claimed here, and a declined
        # fact must be REPORTED rather than compared against Beadloom's own 18.
        assert not found
        assert any(
            "could not be verified" in v.message
            for v in _findings(
                evaluate_all(conn, [_rule()], project_root=tmp_path), LIVENESS_RULE_TYPE
            )
        )


# --------------------------------------------------------------------------- #
# this repository
# --------------------------------------------------------------------------- #


class TestThisRepositoryIsChecked:
    """The rule is live on Beadloom's own graph, whatever it currently reports."""

    def test_this_repository_s_summaries_state_checkable_facts(self) -> None:
        """A rule that stood down here would prove nothing about the corrections.

        This asserts liveness, not cleanliness: the four findings this repository
        currently carries are BDL-062 `.4`'s to correct, and pinning their number
        here would make this test fail on the commit that fixes them.
        """
        from beadloom.infrastructure.db import open_db as open_index

        index = Path(".beadloom/beadloom.db")
        if not index.exists():  # pragma: no cover - a clone before its first reindex
            pytest.skip("no index; run `beadloom reindex`")
        conn = open_index(index)
        try:
            assert summary_facts_inert_reason(conn, Path.cwd()) is None
        finally:
            conn.close()
