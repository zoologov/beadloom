# beadloom:domain=graph
"""A rule that cannot match is reported — for EVERY rule type, not one of them.

BDL-061.48 / BDL-UX #172. ``beadloom-mr2l.43`` shipped ``rule_liveness`` for
``forbid_import`` only, so the other eight rule types still counted clean when
their candidate set was empty: a ``require`` rule naming a node that does not
exist contributed 0 violations to ``lint --strict`` and 1 to ``N rules
evaluated``, at exit 0.

Each rule type gets a PAIR of tests:

* an **inert** rule of that type must be reported (RED before the fix), and
* a **live** rule of the same type on the same fixture must NOT be reported
  (the non-vacuity guard — otherwise "everything is inert" would pass every
  assertion above it; TESTS MUST BITE).

The severity question is asserted too, because it is the decision the bead had
to make: a liveness finding is a statement about the *configuration*, never
about the code, so it is ``warn`` whatever the rule declares — an adopter whose
project is green today must not go red on upgrade (BDL-061 CONTEXT).
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest
from click.testing import CliRunner

from beadloom.application.reindex import reindex
from beadloom.graph.linter import format_json
from beadloom.graph.linter import lint as run_lint
from beadloom.graph.rule_engine import (
    CardinalityRule,
    CycleRule,
    DenyRule,
    ForbidEdgeRule,
    ImportBoundaryRule,
    LayerDef,
    LayerRule,
    ModuleCoverageRule,
    NodeMatcher,
    RequireRule,
    UnregisteredFeatureCandidateRule,
    Violation,
    evaluate_all,
)
from beadloom.infrastructure.db import create_schema, open_db
from beadloom.services.cli import main

if TYPE_CHECKING:
    import sqlite3
    from pathlib import Path

    from beadloom.graph.rules import Rule

LIVENESS = "rule_liveness"


# ---------------------------------------------------------------------------
# Fixture — a small but genuinely populated graph
# ---------------------------------------------------------------------------


@pytest.fixture()
def graph_db(tmp_path: Path) -> sqlite3.Connection:
    """A graph with nodes, tags, live edges, imports and annotated symbols.

    Everything a rule could want to look at exists here, so an empty candidate
    set in the tests below is a property of the RULE and never of the index.
    """
    conn = open_db(tmp_path / "test.db")
    create_schema(conn)

    for ref_id, kind, source, tags in (
        ("app", "service", "src/app/", ["layer-svc"]),
        ("alpha", "domain", "src/app/alpha/", ["layer-top"]),
        ("beta", "domain", "src/app/beta/", ["layer-bottom"]),
    ):
        conn.execute(
            "INSERT INTO nodes (ref_id, kind, summary, source, extra) VALUES (?, ?, ?, ?, ?)",
            (ref_id, kind, f"{ref_id} node", source, json.dumps({"tags": tags})),
        )

    for src, dst, edge_kind in (
        ("app", "alpha", "depends_on"),
        ("alpha", "beta", "depends_on"),
        ("alpha", "app", "part_of"),
    ):
        conn.execute(
            "INSERT INTO edges (src_ref_id, dst_ref_id, kind) VALUES (?, ?, ?)",
            (src, dst, edge_kind),
        )

    conn.execute(
        "INSERT INTO code_imports"
        " (file_path, line_number, import_path, resolved_ref_id, file_hash)"
        " VALUES (?, ?, ?, ?, ?)",
        ("src/app/alpha/service.py", 3, "app.beta.tokens", "beta", "h1"),
    )
    conn.execute(
        "INSERT INTO code_symbols"
        " (file_path, symbol_name, kind, line_start, line_end, annotations, file_hash)"
        " VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            "src/app/alpha/service.py",
            "run",
            "function",
            1,
            9,
            json.dumps({"domain": "alpha", "feature": "svc"}),
            "h1",
        ),
    )
    conn.commit()
    yield conn  # type: ignore[misc]
    conn.close()


@pytest.fixture()
def empty_db(tmp_path: Path) -> sqlite3.Connection:
    """A schema with nothing in it — a fresh clone before the first reindex."""
    conn = open_db(tmp_path / "empty.db")
    create_schema(conn)
    yield conn  # type: ignore[misc]
    conn.close()


def _liveness(conn: sqlite3.Connection, rules: list[Rule], **kw: object) -> list[Violation]:
    """Every liveness finding ``lint`` would report for *rules*."""
    project_root = kw.get("project_root")
    violations = evaluate_all(
        conn,
        rules,
        project_root=project_root,  # type: ignore[arg-type]
    )
    return [v for v in violations if v.rule_type == LIVENESS]


def _named(conn: sqlite3.Connection, rules: list[Rule], **kw: object) -> set[str]:
    """The names of the rules reported as unable to do their job."""
    return {v.rule_name for v in _liveness(conn, rules, **kw)}


# ---------------------------------------------------------------------------
# The nine rule types, one inert/live pair each
# ---------------------------------------------------------------------------


class TestDenyLiveness:
    """A ``deny`` rule whose matchers select no node checks nothing."""

    def test_a_deny_between_tags_nobody_carries_is_reported(
        self, graph_db: sqlite3.Connection
    ) -> None:
        # Arrange
        rule = DenyRule(
            name="dead-deny",
            description="tags nobody carries",
            from_matcher=NodeMatcher(tag="layer-nonexistent"),
            to_matcher=NodeMatcher(tag="layer-also-not"),
            unless_edge=(),
        )

        # Act
        findings = _liveness(graph_db, [rule])

        # Assert
        assert [v.rule_name for v in findings] == ["dead-deny"]
        assert "layer-nonexistent" in findings[0].message

    def test_a_deny_naming_an_unknown_ref_id_names_that_ref_id(
        self, graph_db: sqlite3.Connection
    ) -> None:
        """The diagnosis ``validate_rules`` already computed, no longer discarded."""
        # Arrange
        rule = DenyRule(
            name="ghost-deny",
            description="about a node that does not exist",
            from_matcher=NodeMatcher(ref_id="no-such-node-at-all"),
            to_matcher=NodeMatcher(ref_id="alpha"),
            unless_edge=(),
        )

        # Act
        findings = _liveness(graph_db, [rule])

        # Assert
        assert len(findings) == 1
        assert "no-such-node-at-all" in findings[0].message

    def test_a_live_deny_rule_is_not_reported(self, graph_db: sqlite3.Connection) -> None:
        # Arrange
        rule = DenyRule(
            name="live-deny",
            description="domain must not import domain",
            from_matcher=NodeMatcher(kind="domain"),
            to_matcher=NodeMatcher(kind="domain"),
            unless_edge=(),
        )

        # Act / Assert
        assert _named(graph_db, [rule]) == set()


class TestRequireLiveness:
    """A ``require`` rule iterates its ``for`` matcher; an empty one is vacuous."""

    def test_a_require_about_a_node_that_does_not_exist_is_reported(
        self, graph_db: sqlite3.Connection
    ) -> None:
        # Arrange
        rule = RequireRule(
            name="dead-require",
            description="require about a node that does not exist",
            for_matcher=NodeMatcher(ref_id="no-such-node"),
            has_edge_to=NodeMatcher(ref_id="alpha"),
            edge_kind="part_of",
        )

        # Act
        findings = _liveness(graph_db, [rule])

        # Assert
        assert [v.rule_name for v in findings] == ["dead-require"]
        assert "no-such-node" in findings[0].message

    def test_a_require_whose_target_does_not_exist_is_reported(
        self, graph_db: sqlite3.Connection
    ) -> None:
        """The other direction: the rule can only ever fail, which is equally broken."""
        # Arrange
        rule = RequireRule(
            name="unsatisfiable-require",
            description="every domain must be part_of a node that is not in the graph",
            for_matcher=NodeMatcher(kind="domain"),
            has_edge_to=NodeMatcher(ref_id="ghost-parent"),
            edge_kind="part_of",
        )

        # Act
        findings = _liveness(graph_db, [rule])

        # Assert
        assert [v.rule_name for v in findings] == ["unsatisfiable-require"]
        assert "ghost-parent" in findings[0].message

    def test_a_live_require_rule_is_not_reported(self, graph_db: sqlite3.Connection) -> None:
        # Arrange
        rule = RequireRule(
            name="live-require",
            description="every domain must be part_of something",
            for_matcher=NodeMatcher(kind="domain"),
            has_edge_to=NodeMatcher(kind="service"),
            edge_kind="part_of",
        )

        # Act / Assert
        assert _named(graph_db, [rule]) == set()


class TestCycleLiveness:
    """``forbid_cycles`` over an edge kind the graph does not have finds nothing."""

    def test_a_cycle_rule_over_an_absent_edge_kind_is_reported(
        self, graph_db: sqlite3.Connection
    ) -> None:
        # Arrange
        rule = CycleRule(
            name="dead-cycles",
            description="no cycles along an edge kind nobody uses",
            edge_kind="implements",
            severity="error",
        )

        # Act
        findings = _liveness(graph_db, [rule])

        # Assert
        assert [v.rule_name for v in findings] == ["dead-cycles"]
        assert "implements" in findings[0].message

    def test_a_live_cycle_rule_is_not_reported(self, graph_db: sqlite3.Connection) -> None:
        # Arrange
        rule = CycleRule(
            name="live-cycles",
            description="no depends_on cycles",
            edge_kind="depends_on",
            severity="error",
        )

        # Act / Assert
        assert _named(graph_db, [rule]) == set()


class TestForbidEdgeLiveness:
    """``forbid`` needs matched nodes AND edges of the kind it names."""

    def test_a_forbid_edge_between_tags_nobody_carries_is_reported(
        self, graph_db: sqlite3.Connection
    ) -> None:
        # Arrange
        rule = ForbidEdgeRule(
            name="dead-forbid",
            description="edges between tags nobody carries",
            from_matcher=NodeMatcher(tag="ghost-a"),
            to_matcher=NodeMatcher(tag="ghost-b"),
        )

        # Act / Assert
        assert _named(graph_db, [rule]) == {"dead-forbid"}

    def test_a_forbid_edge_over_an_absent_edge_kind_is_reported(
        self, graph_db: sqlite3.Connection
    ) -> None:
        # Arrange
        rule = ForbidEdgeRule(
            name="dead-forbid-kind",
            description="matchers are fine, the edge kind does not occur",
            from_matcher=NodeMatcher(kind="service"),
            to_matcher=NodeMatcher(kind="domain"),
            edge_kind="touches_entity",
        )

        # Act
        findings = _liveness(graph_db, [rule])

        # Assert
        assert [v.rule_name for v in findings] == ["dead-forbid-kind"]
        assert "touches_entity" in findings[0].message

    def test_a_live_forbid_edge_rule_is_not_reported(self, graph_db: sqlite3.Connection) -> None:
        # Arrange
        rule = ForbidEdgeRule(
            name="live-forbid",
            description="no service depends_on domain",
            from_matcher=NodeMatcher(kind="service"),
            to_matcher=NodeMatcher(kind="domain"),
            edge_kind="depends_on",
        )

        # Act / Assert
        assert _named(graph_db, [rule]) == set()


class TestLayerLiveness:
    """A layered rule needs at least two POPULATED layers and edges to judge."""

    def test_a_layer_rule_whose_tags_nobody_carries_is_reported(
        self, graph_db: sqlite3.Connection
    ) -> None:
        # Arrange
        rule = LayerRule(
            name="dead-layers",
            description="layers nobody is tagged with",
            layers=(LayerDef(name="ui", tag="tier-ui"), LayerDef(name="core", tag="tier-core")),
            enforce="top-down",
            edge_kind="depends_on",
            severity="error",
        )

        # Act
        findings = _liveness(graph_db, [rule])

        # Assert
        assert [v.rule_name for v in findings] == ["dead-layers"]
        assert "tier-ui" in findings[0].message

    def test_a_layer_rule_with_only_one_populated_layer_is_reported(
        self, graph_db: sqlite3.Connection
    ) -> None:
        """One layer cannot be above or below anything — direction is undefined."""
        # Arrange
        rule = LayerRule(
            name="single-layer",
            description="one real layer, one empty",
            layers=(
                LayerDef(name="svc", tag="layer-svc"),
                LayerDef(name="nobody", tag="tier-empty"),
            ),
            enforce="top-down",
            edge_kind="depends_on",
            severity="error",
        )

        # Act / Assert
        assert _named(graph_db, [rule]) == {"single-layer"}

    def test_a_layer_rule_over_an_absent_edge_kind_is_reported(
        self, graph_db: sqlite3.Connection
    ) -> None:
        # Arrange
        rule = LayerRule(
            name="layers-no-edges",
            description="layers are populated, the edge kind does not occur",
            layers=(
                LayerDef(name="svc", tag="layer-svc"),
                LayerDef(name="top", tag="layer-top"),
            ),
            enforce="top-down",
            edge_kind="uses",
            severity="error",
        )

        # Act / Assert
        assert _named(graph_db, [rule]) == {"layers-no-edges"}

    def test_a_live_layer_rule_is_not_reported(self, graph_db: sqlite3.Connection) -> None:
        # Arrange
        rule = LayerRule(
            name="live-layers",
            description="svc above top above bottom",
            layers=(
                LayerDef(name="svc", tag="layer-svc"),
                LayerDef(name="top", tag="layer-top"),
                LayerDef(name="bottom", tag="layer-bottom"),
            ),
            enforce="top-down",
            edge_kind="depends_on",
            severity="error",
        )

        # Act / Assert
        assert _named(graph_db, [rule]) == set()


class TestCardinalityLiveness:
    """A ``check`` needs a matched node AND a threshold to compare it against."""

    def test_a_check_on_a_node_that_does_not_exist_is_reported(
        self, graph_db: sqlite3.Connection
    ) -> None:
        # Arrange
        rule = CardinalityRule(
            name="dead-check",
            description="size limit on a node that is not in the graph",
            for_matcher=NodeMatcher(ref_id="no-such-node"),
            max_symbols=10,
        )

        # Act
        findings = _liveness(graph_db, [rule])

        # Assert
        assert [v.rule_name for v in findings] == ["dead-check"]
        assert "no-such-node" in findings[0].message

    def test_a_check_with_no_threshold_at_all_is_reported(
        self, graph_db: sqlite3.Connection
    ) -> None:
        """Matching every domain and comparing it to nothing is still nothing checked."""
        # Arrange
        rule = CardinalityRule(
            name="thresholdless-check",
            description="a check with no limit set",
            for_matcher=NodeMatcher(kind="domain"),
        )

        # Act
        findings = _liveness(graph_db, [rule])

        # Assert
        assert [v.rule_name for v in findings] == ["thresholdless-check"]
        assert "threshold" in findings[0].message

    def test_a_live_check_is_not_reported(self, graph_db: sqlite3.Connection) -> None:
        # Arrange
        rule = CardinalityRule(
            name="live-check",
            description="domains stay small",
            for_matcher=NodeMatcher(kind="domain"),
            max_symbols=500,
        )

        # Act / Assert
        assert _named(graph_db, [rule]) == set()


class TestUnregisteredFeatureCandidateLiveness:
    """The modelling advisory is vacuous when it matches no domain."""

    def test_an_unregistered_candidate_rule_matching_no_node_is_reported(
        self, graph_db: sqlite3.Connection
    ) -> None:
        # Arrange
        rule = UnregisteredFeatureCandidateRule(
            name="dead-unregistered",
            description="candidates inside a node that does not exist",
            for_matcher=NodeMatcher(ref_id="no-such-domain"),
        )

        # Act / Assert
        assert _named(graph_db, [rule]) == {"dead-unregistered"}

    def test_a_live_unregistered_candidate_rule_is_not_reported(
        self, graph_db: sqlite3.Connection
    ) -> None:
        # Arrange
        rule = UnregisteredFeatureCandidateRule(
            name="live-unregistered",
            description="candidates in every domain",
            for_matcher=NodeMatcher(kind="domain"),
        )

        # Act / Assert
        assert _named(graph_db, [rule]) == set()


class TestModuleCoverageLiveness:
    """"No shadow code" over a source root with no modules covers nothing."""

    def test_coverage_over_a_source_root_with_no_modules_is_reported(
        self, graph_db: sqlite3.Connection, tmp_path: Path
    ) -> None:
        # Arrange
        rule = ModuleCoverageRule(
            name="dead-coverage",
            description="coverage over a source root that does not exist",
            source_root="src/nowhere/",
            severity="error",
        )

        # Act
        findings = _liveness(graph_db, [rule], project_root=tmp_path)

        # Assert
        assert [v.rule_name for v in findings] == ["dead-coverage"]
        assert "src/nowhere/" in findings[0].message

    def test_a_live_coverage_rule_is_not_reported(
        self, graph_db: sqlite3.Connection, tmp_path: Path
    ) -> None:
        # Arrange — the indexed symbol under src/app/ is the candidate module
        rule = ModuleCoverageRule(
            name="live-coverage",
            description="every module under src/app is classified",
            source_root="src/app/",
            severity="error",
        )

        # Act / Assert
        assert _named(graph_db, [rule], project_root=tmp_path) == set()


class TestImportBoundaryLivenessStillWorks:
    """BDL-061.43's channel is the one that already existed — it must not regress."""

    def test_a_dead_import_glob_is_still_reported(self, graph_db: sqlite3.Connection) -> None:
        # Arrange
        rule = ImportBoundaryRule(
            name="dead-import-glob",
            description="the src/-prefixed to-glob that can never match",
            from_glob="src/app/alpha/*",
            to_glob="src/app/beta/**",
            severity="error",
        )

        # Act / Assert
        assert _named(graph_db, [rule]) == {"dead-import-glob"}

    def test_a_live_import_rule_is_not_reported_as_inert(
        self, graph_db: sqlite3.Connection
    ) -> None:
        # Arrange
        rule = ImportBoundaryRule(
            name="live-import",
            description="alpha must not import beta",
            from_glob="src/app/alpha/*",
            to_glob="app/beta*",
            severity="error",
        )

        # Act / Assert
        assert _named(graph_db, [rule]) == set()


# ---------------------------------------------------------------------------
# Cross-cutting invariants — severity, non-duplication, and the empty index
# ---------------------------------------------------------------------------

_ONE_OF_EACH: list[Rule] = [
    DenyRule(
        name="x-deny",
        description="d",
        from_matcher=NodeMatcher(ref_id="ghost1"),
        to_matcher=NodeMatcher(ref_id="ghost2"),
        unless_edge=(),
        severity="error",
    ),
    RequireRule(
        name="x-require",
        description="r",
        for_matcher=NodeMatcher(ref_id="ghost3"),
        has_edge_to=NodeMatcher(),
        severity="error",
    ),
    CycleRule(name="x-cycle", description="c", edge_kind="implements", severity="error"),
    ImportBoundaryRule(
        name="x-import",
        description="i",
        from_glob="src/nowhere/*",
        to_glob="nowhere/**",
        severity="error",
    ),
    ForbidEdgeRule(
        name="x-forbid",
        description="f",
        from_matcher=NodeMatcher(tag="ghost-tag"),
        to_matcher=NodeMatcher(tag="ghost-tag"),
        severity="error",
    ),
    LayerRule(
        name="x-layers",
        description="l",
        layers=(LayerDef(name="a", tag="ghost-a"), LayerDef(name="b", tag="ghost-b")),
        enforce="top-down",
        severity="error",
    ),
    CardinalityRule(
        name="x-check",
        description="k",
        for_matcher=NodeMatcher(ref_id="ghost4"),
        max_symbols=1,
        severity="error",
    ),
    UnregisteredFeatureCandidateRule(
        name="x-unregistered",
        description="u",
        for_matcher=NodeMatcher(ref_id="ghost5"),
        severity="error",
    ),
    ModuleCoverageRule(
        name="x-coverage",
        description="m",
        source_root="src/nowhere/",
        severity="error",
    ),
]


class TestEveryRuleTypeIsCovered:
    """The scope check: nine rule types exist and nine can report their own inertness."""

    def test_every_rule_type_reports_its_own_inertness(
        self, graph_db: sqlite3.Connection, tmp_path: Path
    ) -> None:
        # Act
        reported = _named(graph_db, _ONE_OF_EACH, project_root=tmp_path)

        # Assert — named individually so a gap says WHICH type is missing
        assert reported == {r.name for r in _ONE_OF_EACH}

    def test_each_inert_rule_is_reported_exactly_once(
        self, graph_db: sqlite3.Connection, tmp_path: Path
    ) -> None:
        """One rule, one finding: the audit that affirms one fact twice is #173."""
        # Act
        findings = _liveness(graph_db, _ONE_OF_EACH, project_root=tmp_path)

        # Assert
        names = [v.rule_name for v in findings]
        assert sorted(names) == sorted({r.name for r in _ONE_OF_EACH})

    def test_liveness_is_always_warn_even_for_error_rules(
        self, graph_db: sqlite3.Connection, tmp_path: Path
    ) -> None:
        """CONTEXT's constraint: no adopter's green project turns red on upgrade."""
        # Act
        findings = _liveness(graph_db, _ONE_OF_EACH, project_root=tmp_path)

        # Assert
        assert {v.severity for v in findings} == {"warn"}

    def test_every_liveness_finding_carries_a_remediation(
        self, graph_db: sqlite3.Connection, tmp_path: Path
    ) -> None:
        # Act
        findings = _liveness(graph_db, _ONE_OF_EACH, project_root=tmp_path)

        # Assert
        assert all(v.remediation for v in findings)

    def test_liveness_is_silent_on_an_empty_index(
        self, empty_db: sqlite3.Connection, tmp_path: Path
    ) -> None:
        """A fresh clone has nothing indexed; that is a header, not nine warnings."""
        # Act / Assert
        assert _liveness(empty_db, _ONE_OF_EACH, project_root=tmp_path) == []


# ---------------------------------------------------------------------------
# End to end, through the real CLI — exit codes and --json, never line counts
# ---------------------------------------------------------------------------

_NODES_YML = """\
nodes:
  - ref_id: alpha
    kind: component
    summary: Alpha component
    source: src/app/alpha/
    docs:
      - components/alpha.md
edges: []
"""

_RULES_YML = """\
version: 1
rules:
  - name: dead-require
    description: require about a node that does not exist
    severity: error
    require:
      for: { ref_id: no-such-node-at-all }
      has_edge_to: { ref_id: also-not-a-node }
"""


def _make_project(root: Path) -> Path:
    """A minimal indexable project carrying one inert ``require`` rule."""
    project = root / "proj"
    (project / ".beadloom" / "_graph").mkdir(parents=True)
    (project / "docs" / "components").mkdir(parents=True)
    (project / ".beadloom" / "config.yml").write_text(
        "scan_paths:\n  - src\ndocs_dir: docs\n", encoding="utf-8"
    )
    (project / ".beadloom" / "_graph" / "services.yml").write_text(_NODES_YML, encoding="utf-8")
    (project / ".beadloom" / "_graph" / "rules.yml").write_text(_RULES_YML, encoding="utf-8")
    (project / "docs" / "components" / "alpha.md").write_text(
        "# Alpha\n\nThe `service` module runs alpha.\n", encoding="utf-8"
    )
    (project / "src" / "app" / "alpha").mkdir(parents=True)
    (project / "src" / "app" / "__init__.py").write_text("", encoding="utf-8")
    (project / "src" / "app" / "alpha" / "__init__.py").write_text("", encoding="utf-8")
    (project / "src" / "app" / "alpha" / "service.py").write_text(
        "# beadloom:component=alpha\n'''Alpha.'''\n\nimport os\n\n\n"
        "def run() -> int:\n    return len(os.sep)\n",
        encoding="utf-8",
    )
    reindex(project)
    return project


class TestThroughTheRealCli:
    """The reproduction from ``beadloom-mr2l.7`` MAJOR 1, asserted end to end."""

    def test_the_reproduction_case_is_no_longer_silent(self, tmp_path: Path) -> None:
        # Arrange
        project = _make_project(tmp_path)

        # Act
        result = run_lint(project)

        # Assert
        messages = [v.message for v in result.violations if v.rule_type == LIVENESS]
        assert any("no-such-node-at-all" in m for m in messages), (
            f"the unknown ref_id must be named; got {messages}"
        )

    def test_lint_strict_stays_green_over_a_liveness_finding(self, tmp_path: Path) -> None:
        """Exit code, not line counts (#148) — and warn must not fail the Gate."""
        # Arrange
        project = _make_project(tmp_path)

        # Act
        invocation = CliRunner().invoke(
            main,
            ["lint", "--strict", "--no-reindex", "--format", "json", "--project", str(project)],
        )

        # Assert
        assert invocation.exit_code == 0, invocation.output
        payload = json.loads(invocation.output)
        assert any(f["kind"] == LIVENESS for f in payload["findings"]), invocation.output

    def test_the_json_payload_names_the_inert_rule_and_counts_it(self, tmp_path: Path) -> None:
        # Arrange
        project = _make_project(tmp_path)
        result = run_lint(project)

        # Act
        payload = json.loads(format_json(result))

        # Assert
        kinds = {f["kind"] for f in payload["findings"]}
        assert LIVENESS in kinds
        assert payload["summary"]["rules_inert"] == 1, (
            "the advertised rule count must say how many of those rules checked "
            f"nothing; got {payload['summary']}"
        )
