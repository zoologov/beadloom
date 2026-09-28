"""The driver the rule engine's acceptance scenarios run through: HOW, so the steps say WHAT.

BDL-074 E1. A scenario states a shape of graph, one thing that happens to it, and
what a reader can see afterwards. Everything between those words and the product —
writing ``nodes.yml`` and ``rules.yml``, indexing the project, calling the linter,
the evaluators or the CLI, and picking findings out of the result — lives here, once,
so two features that say "the project is linted" mean the same call.

Five objects:

* :class:`RuleRun` — what one evaluation left behind: its findings, or the error
  that refused the rules, and the exit code when the CLI was the caller. Its query
  methods are the only way the steps read a finding, so "a liveness message" and
  "a population statement" are each read one way.
* :class:`LayeredProject` — a project declaring a layer rule over a tiered graph,
  built from :mod:`tests.support.tiered_project`'s shapes and judged by the real
  reindex and the real linter. Nothing is mocked: a scenario that passes against a
  double proves the double.
* :class:`SummaryClaims` — node summaries and the facts a project computes (or
  declines to), judged by the ``summary_facts`` rule over an index holding exactly
  those summaries.
* :class:`CoveragePopulation` — a graph of feature and component nodes and a suite
  that binds one of them, judged by the ``scenario_coverage`` rule for its
  population.
* :class:`DocPlacements` — nodes, each with a source and a document, judged by the
  ``doc_area_coherence`` rule, beside the convention the rule derived.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from click.testing import CliRunner

from beadloom.application.architecture_view import build_architecture_view_data
from beadloom.doc_sync import Fact, FactSet
from beadloom.graph.linter import LintError, lint
from beadloom.graph.rules import (
    DOC_AREA_RULE_TYPE,
    LIVENESS_RULE_TYPE,
    DocAreaCoherenceRule,
    NodeMatcher,
    ScenarioCoverageRule,
    SummaryFactsRule,
    evaluate_all,
    evaluate_doc_area_coherence_rules,
    evaluate_scenario_coverage_rules,
    evaluate_summary_facts_rules,
)
from beadloom.graph.rules.doc_area import Convention, derive_convention
from beadloom.graph.rules.layer_exemptions import excused_crossings
from beadloom.graph.rules.layer_reach import (
    LAYER_POPULATION_RULE_TYPE,
    LayerReach,
    layer_rule_reach,
    live_edges_of_kind,
    part_of_parents,
)
from beadloom.graph.rules.layers import layer_of, same_layer_crossings
from beadloom.graph.rules.loader import load_rules, validate_rules
from beadloom.graph.rules.node_tags import node_tags
from beadloom.graph.rules.types import LayerRule
from beadloom.infrastructure.db import create_schema, open_db
from beadloom.services.cli import main
from tests.support.tiered_project import (
    TIERS,
    Edge,
    Node,
    write_tiered_project,
    write_zoned_import_project,
)

if TYPE_CHECKING:
    from pathlib import Path

    from beadloom.graph.rules import Rule, Violation

#: ``rule_type`` of a layer rule's own decision.
LAYER_RULE_TYPE = "layer"

#: The reason every exemption this driver writes carries, unless told otherwise.
DEFAULT_EXEMPTION_REASON = "the two read one ledger, and the read seam is not built yet"


@dataclass
class RuleRun:
    """What one evaluation left behind, and the one way each finding is read."""

    violations: list[Violation] = field(default_factory=list)
    error: str | None = None
    exit_code: int | None = None
    output: str = ""

    def of_type(self, rule_type: str) -> list[Violation]:
        return [v for v in self.violations if v.rule_type == rule_type]

    def messages(self) -> list[str]:
        return [v.message for v in self.violations]

    def liveness(self) -> list[Violation]:
        """Every finding about a rule that could not do its job."""
        return self.of_type(LIVENESS_RULE_TYPE)

    def liveness_messages(self) -> list[str]:
        return [v.message for v in self.liveness()]

    def population_statements(self) -> list[Violation]:
        """Every statement of how much of its edge set a layer rule judged."""
        return self.of_type(LAYER_POPULATION_RULE_TYPE)

    def layer_findings(self) -> list[Violation]:
        return self.of_type(LAYER_RULE_TYPE)

    def layer_pairs(self) -> set[tuple[str | None, str | None]]:
        """``(from, to)`` of every edge the layer rule decided against."""
        return {(v.from_ref_id, v.to_ref_id) for v in self.layer_findings()}


class LayeredProject:
    """A project that declares a layer rule, over a graph the scenario describes.

    The Given steps set the tiers, the graph and the exemptions; the first When
    step writes the project and indexes it ONCE (:func:`write_tiered_project`), and
    every reader after that reads that one index.
    """

    def __init__(self, root: Path) -> None:
        self.root = root
        self.tiers: tuple[str, ...] = TIERS
        self.nodes: list[Node] = []
        self.edges: list[Edge] = []
        self.exempt = ""
        self.run = RuleRun()
        self._built: Path | None = None
        self._written_from_imports = False

    # -- the shape, as the Given steps state it -------------------------------

    def use_graph(self, nodes: list[Node], edges: list[Edge]) -> None:
        self.nodes, self.edges = list(nodes), list(edges)

    def declare_tiers(self, tiers: tuple[str, ...]) -> None:
        self.tiers = tiers

    def excuse(self, src: str, dst: str, *, until: str, reason: str | None) -> None:
        """One ``exempt`` entry on the layer rule; ``reason=None`` writes none."""
        reason_line = "" if reason is None else f'        reason: "{reason}"\n'
        self.exempt = (
            "    exempt:\n"
            f"      - from: {src}\n"
            f"        to: {dst}\n"
            f"{reason_line}"
            f'        until: "{until}"\n'
        )

    def derive_edges_from_imports(self) -> None:
        """The project whose ``depends_on`` edges come only from Python imports."""
        self._built = write_zoned_import_project(self.root)
        self._written_from_imports = True

    # -- building and reading ------------------------------------------------

    @property
    def path(self) -> Path:
        """The project on disk, written and indexed on first use."""
        if self._built is None:
            self._built = write_tiered_project(
                self.root,
                nodes=self.nodes,
                edges=self.edges,
                tiers=self.tiers,
                exempt=self.exempt,
            )
        return self._built

    def graph_file_text(self) -> str:
        return (self.path / ".beadloom" / "_graph" / "nodes.yml").read_text(encoding="utf-8")

    def graph_files_text(self) -> str:
        graph_dir = self.path / ".beadloom" / "_graph"
        return "".join(p.read_text(encoding="utf-8") for p in sorted(graph_dir.glob("*.yml")))

    def rules(self) -> list[Rule]:
        return load_rules(self.path / ".beadloom" / "_graph" / "rules.yml")

    def layer_rule(self) -> LayerRule:
        return next(rule for rule in self.rules() if isinstance(rule, LayerRule))

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path / ".beadloom" / "beadloom.db")
        conn.row_factory = sqlite3.Row
        return conn

    # -- the one thing that happens -------------------------------------------

    def lint(self) -> RuleRun:
        """``lint()`` over the index; a refused ``rules.yml`` is kept as the error."""
        try:
            self.run = RuleRun(violations=lint(self.path).violations)
        except LintError as exc:
            self.run = RuleRun(error=str(exc))
        return self.run

    def lint_cli(self, *flags: str) -> RuleRun:
        """``beadloom lint --no-reindex`` through the CLI, and the findings beside it."""
        result = CliRunner().invoke(
            main, ["lint", "--no-reindex", "--project", str(self.path), *flags]
        )
        self.run = RuleRun(
            violations=lint(self.path).violations,
            exit_code=result.exit_code,
            output=result.output,
        )
        return self.run

    def evaluate_without_lint(self) -> RuleRun:
        """``evaluate_all`` directly — the call the TUI panel and the debt report make."""
        conn = self._connect()
        try:
            self.run = RuleRun(violations=evaluate_all(conn, self.rules(), project_root=self.path))
        finally:
            conn.close()
        return self.run

    def reach(self) -> LayerReach:
        conn = self._connect()
        try:
            return layer_rule_reach(conn, self.layer_rule())
        finally:
            conn.close()

    def validate(self) -> list[str]:
        conn = self._connect()
        try:
            return validate_rules(self.rules(), conn)
        finally:
            conn.close()

    def same_layer_crossings(self) -> list[tuple[str, str]]:
        rule = self.layer_rule()
        conn = self._connect()
        try:
            return same_layer_crossings(
                live_edges_of_kind(conn, rule.edge_kind),
                rule.layers,
                part_of_parents(conn),
                node_tags(conn).as_mapping(),
            )
        finally:
            conn.close()

    def crossings_no_entry_excuses(self) -> list[tuple[str, str]]:
        reported, _ = excused_crossings(self.layer_rule(), self.same_layer_crossings())
        return list(reported)

    def layers_by_instrument(self) -> tuple[dict[str, int | None], dict[str, object]]:
        """What the rule engine and the architecture view each say every node is in."""
        rule = self.layer_rule()
        conn = self._connect()
        try:
            parents = part_of_parents(conn)
            tags = node_tags(conn).as_mapping()
            engine = {
                ref_id: layer_of(ref_id, rule.layers, parents, tags) for ref_id, *_ in self.nodes
            }
            rendered = build_architecture_view_data(conn)["nodes"]
        finally:
            conn.close()
        assert isinstance(rendered, list)
        view = {str(node["id"]): node["layer_rank"] for node in rendered}
        return engine, view


@dataclass
class Outcome:
    """The last run, for a feature whose When step is not a layered project's."""

    run: RuleRun = field(default_factory=RuleRun)


class SummaryClaims:
    """Node summaries, the project's computed facts, and the rule that compares them."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.summaries: list[tuple[str, str]] = []
        self.facts: dict[str, Fact] = {}
        self.declined: dict[str, str] = {}
        # What the PROJECT declared for this rule. `error` is the shipped default,
        # so a scenario that says nothing about severity measures what an adopter
        # who wrote no `severity:` key actually gets.
        self.severity = "error"

    def computes(self, fact_name: str, value: str) -> None:
        parsed: str | int = int(value) if value.isdigit() else value
        self.facts[fact_name] = Fact(name=fact_name, value=parsed, source="the fixture")

    def declines(self, fact_name: str, reason: str) -> None:
        self.declined[fact_name] = reason

    def summary(self, ref_id: str, text: str) -> None:
        self.summaries.append((ref_id, text))

    def evaluate(self) -> RuleRun:
        conn = open_db(self.root / "graph.db")
        try:
            create_schema(conn)
            for ref_id, text in self.summaries:
                conn.execute(
                    "INSERT INTO nodes (ref_id, kind, summary, source) VALUES (?, ?, ?, ?)",
                    (ref_id, "feature", text, f"app/{ref_id}.py"),
                )
            conn.commit()
            rule = SummaryFactsRule(
                name="graph-summary-facts",
                description="A number stated in a node summary agrees with the project",
                severity=self.severity,
            )
            fact_set = FactSet(facts=dict(self.facts), not_applicable=dict(self.declined))
            violations = evaluate_summary_facts_rules(conn, [rule], fact_set=fact_set)
        finally:
            conn.close()
        return RuleRun(violations=violations)


class CoveragePopulation:
    """Features and components, judged by ``scenario_coverage`` over ``kind: feature``."""

    #: Where the suite is written, relative to the project root.
    FEATURE_DIR = "tests/acceptance/features"

    def __init__(self, root: Path) -> None:
        self.root = root
        self.nodes: list[tuple[str, str]] = []

    def graph(self, *, features: int, components: int) -> None:
        """*features* feature nodes and *components* component nodes, and a suite.

        The suite exists and binds one node: an ABSENT suite stands the whole rule
        down, and a population scenario is about the population, not liveness.
        """
        self.nodes = [(f"feat-{i}", "feature") for i in range(features)]
        self.nodes += [(f"comp-{i}", "component") for i in range(components)]
        path = self.root / self.FEATURE_DIR / "one.feature"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            "@bead:beadloom-mr2l.63 @node:feat-0\nFeature: F\n"
            "  Scenario: the only one\n    Given a step\n",
            encoding="utf-8",
        )

    def reclassify(self, ref_id: str, kind: str) -> None:
        self.nodes = [(ref, kind if ref == ref_id else k) for ref, k in self.nodes]

    def evaluate(self) -> RuleRun:
        conn = open_db(self.root / "graph.db")
        try:
            create_schema(conn)
            for ref_id, kind in self.nodes:
                conn.execute(
                    "INSERT INTO nodes (ref_id, kind, summary) VALUES (?, ?, '')", (ref_id, kind)
                )
            conn.commit()
            rule = ScenarioCoverageRule(
                name="scenario-coverage",
                description="behaviour carries an executable claim",
                for_matcher=NodeMatcher(kind="feature"),
                features=f"{self.FEATURE_DIR}/**/*.feature",
            )
            violations = evaluate_scenario_coverage_rules(conn, [rule], project_root=self.root)
        finally:
            conn.close()
        return RuleRun(violations=violations)


class DocPlacements:
    """Nodes with a source and a document each, judged by ``doc_area_coherence``."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.pairs: list[tuple[str, str, str]] = []
        #: ``None`` leaves the rule at its shipped severity.
        self.severity: str | None = None
        self.convention: Convention | None = None

    def place(self, ref_id: str, source: str, doc: str) -> None:
        self.pairs.append((ref_id, source, doc))

    def evaluate(self) -> RuleRun:
        """Run the rule, and keep the convention it derived for the population."""
        conn = open_db(self.root / "graph.db")
        try:
            create_schema(conn)
            for ref_id, source, doc in self.pairs:
                conn.execute(
                    "INSERT INTO nodes (ref_id, kind, summary, source) VALUES (?, ?, ?, ?)",
                    (ref_id, "feature", "", source),
                )
                conn.execute(
                    "INSERT INTO docs (path, kind, ref_id, hash) VALUES (?, ?, ?, ?)",
                    (doc, "feature", ref_id, ""),
                )
            conn.commit()
            rule = DocAreaCoherenceRule(
                name="doc-area-coherence",
                description="a node documents itself where its graph says it should",
                **({} if self.severity is None else {"severity": self.severity}),
            )
            violations = evaluate_doc_area_coherence_rules(conn, [rule])
            self.convention = derive_convention(
                conn, threshold=rule.threshold, min_support=rule.min_support
            )
        finally:
            conn.close()
        return RuleRun(violations=violations)

    @staticmethod
    def reported(run: RuleRun) -> list[str | None]:
        """The nodes the rule reported as documented outside the convention."""
        return [v.from_ref_id for v in run.of_type(DOC_AREA_RULE_TYPE)]
