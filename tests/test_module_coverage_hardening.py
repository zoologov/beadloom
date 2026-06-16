# beadloom:domain=graph
"""Hardening tests for the `component` node kind + `module-coverage` coverage-lint.

BDL-051 Slice 3a / BEAD-08 (test). These tests harden the dev's S3a work
(`tests/test_rule_engine.py`) without duplicating its passing cases. Focus:

* component-kind round-trip through serialize / `ctx` / `lint --strict`
* coverage classification matrix gaps (annotation precedence, zero-symbol edge)
* exempt-glob nuances (nested ``__init__``, partial-name no over-match, sibling)
* the ``module_coverage`` rule type serialize round-trip + Unknown-type guard
* the retired ``unregistered-feature-candidate`` is not an active rule
* a real-repo regression guard: coverage stays enforced over the live tree

All tests are deterministic and do no network I/O.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from click.testing import CliRunner

from beadloom.graph.rule_engine import (
    ModuleCoverageRule,
    evaluate_all,
    evaluate_module_coverage_rules,
    load_rules,
)
from beadloom.infrastructure.db import create_schema
from beadloom.services.cli import main

if TYPE_CHECKING:
    from collections.abc import Iterator

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _insert_symbol(
    conn: sqlite3.Connection,
    file_path: str,
    symbol_name: str,
    annotations: dict[str, str],
) -> None:
    """Insert a single code_symbols row with the given annotations JSON."""
    conn.execute(
        "INSERT INTO code_symbols"
        " (file_path, symbol_name, kind, line_start, line_end, annotations, file_hash)"
        " VALUES (?, ?, ?, ?, ?, ?, ?)",
        (file_path, symbol_name, "function", 1, 10, json.dumps(annotations), "h"),
    )


def _mc_rule(
    *,
    source_root: str = "src/beadloom/",
    min_symbols: int = 1,
    exempt: tuple[str, ...] = (),
    severity: str = "warn",
) -> ModuleCoverageRule:
    return ModuleCoverageRule(
        name="module-coverage",
        description="every src module must be a node or exempt",
        source_root=source_root,
        min_symbols=min_symbols,
        exempt=exempt,
        severity=severity,
    )


@pytest.fixture()
def mem_db() -> Iterator[sqlite3.Connection]:
    """Empty in-memory DB with the full schema."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    create_schema(conn)
    yield conn
    conn.close()


# ---------------------------------------------------------------------------
# component kind — full round-trip (reindex / ctx / lint --strict)
# ---------------------------------------------------------------------------


class TestComponentKindRoundTrip:
    """A `kind: component` node survives loader, ctx resolution, and lint --strict."""

    def _make_project(self, tmp_path: Path) -> Path:
        project = tmp_path / "proj"
        graph_dir = project / ".beadloom" / "_graph"
        graph_dir.mkdir(parents=True)
        (project / "docs").mkdir()
        (graph_dir / "services.yml").write_text(
            "version: 1\n"
            "nodes:\n"
            "  - ref_id: beadloom\n"
            "    kind: service\n"
            "    summary: root service\n"
            "  - ref_id: graph\n"
            "    kind: domain\n"
            "    summary: graph domain\n"
            "    source: src/beadloom/graph/\n"
            "  - ref_id: graph-loader\n"
            "    kind: component\n"
            "    summary: the loader building block\n"
            "    source: src/beadloom/graph/loader.py\n"
            "edges:\n"
            "  - src: graph\n"
            "    dst: beadloom\n"
            "    kind: part_of\n"
            "  - src: graph-loader\n"
            "    dst: graph\n"
            "    kind: part_of\n"
        )
        # rules.yml: require components to be part_of a domain (mirrors real rules).
        (graph_dir / "rules.yml").write_text(
            "version: 3\n"
            "rules:\n"
            "  - name: component-needs-domain\n"
            "    description: components need a parent domain\n"
            "    require:\n"
            "      for: { kind: component }\n"
            "      has_edge_to: { kind: domain }\n"
            "      edge_kind: part_of\n"
        )
        src = project / "src" / "beadloom" / "graph"
        src.mkdir(parents=True)
        (src / "loader.py").write_text("# beadloom:component=graph-loader\ndef load(): pass\n")
        return project

    def test_reindex_accepts_component_kind(self, tmp_path: Path) -> None:
        """`beadloom reindex` ingests a component node with no 'Unknown kind' error."""
        project = self._make_project(tmp_path)
        runner = CliRunner()
        result = runner.invoke(main, ["reindex", "--project", str(project)])
        assert result.exit_code == 0, result.output
        assert "unknown kind" not in result.output.lower()
        assert "invalid kind" not in result.output.lower()

    def test_ctx_resolves_component_node(self, tmp_path: Path) -> None:
        """`beadloom ctx <component-id>` resolves a component node to a bundle."""
        project = self._make_project(tmp_path)
        runner = CliRunner()
        runner.invoke(main, ["reindex", "--project", str(project)])
        result = runner.invoke(main, ["ctx", "graph-loader", "--project", str(project), "--json"])
        assert result.exit_code == 0, result.output
        bundle = json.loads(result.output)
        # Public behavior: the bundle is for the component we asked for.
        blob = json.dumps(bundle)
        assert "graph-loader" in blob
        assert "component" in blob

    def test_lint_strict_does_not_reject_component(self, tmp_path: Path) -> None:
        """A well-formed component node passes `lint --strict` (exit 0)."""
        project = self._make_project(tmp_path)
        runner = CliRunner()
        runner.invoke(main, ["reindex", "--project", str(project)])
        result = runner.invoke(main, ["lint", "--strict", "--project", str(project)])
        assert result.exit_code == 0, result.output


# ---------------------------------------------------------------------------
# Coverage classification matrix — gaps the dev's tests don't cover
# ---------------------------------------------------------------------------


class TestCoverageClassificationMatrix:
    """Each coverage path + the precedence/edge cases, asserting actual behavior."""

    def test_zero_symbol_module_on_disk_is_flagged(
        self, mem_db: sqlite3.Connection, tmp_path: Path
    ) -> None:
        """A real zero-top-level-symbol module on disk (no annotation, not exempt) IS flagged.

        BDL-051 S3a / BEAD-17 (review .9 MAJOR fix): the coverage lint enumerates
        candidate modules from DISK, not from ``code_symbols``. A ``.py`` file with
        no indexed ``def``/``class`` symbols used to slip through silently (no row ->
        nothing to flag). This flips the prior accepted false-negative: it must now
        be flagged. (Was ``test_zero_symbol_module_not_flagged``.)
        """
        root = tmp_path / "src" / "beadloom"
        (root / "graph").mkdir(parents=True)
        # A real module on disk with NO top-level def/class -> zero indexed symbols.
        (root / "graph" / "shadow.py").write_text('"""Docstring-only glue."""\nX = 1\n')
        violations = evaluate_module_coverage_rules(mem_db, [_mc_rule()], project_root=tmp_path)
        assert "src/beadloom/graph/shadow.py" in {v.file_path for v in violations}

    def test_domain_only_with_one_public_symbol_flagged(
        self, mem_db: sqlite3.Connection, tmp_path: Path
    ) -> None:
        """domain= only + >=1 symbol (>= min_symbols) -> flagged (the whole point)."""
        _insert_symbol(mem_db, "src/beadloom/graph/shadow.py", "fn", {"domain": "graph"})
        violations = evaluate_module_coverage_rules(
            mem_db, [_mc_rule(min_symbols=1)], project_root=tmp_path
        )
        assert {v.file_path for v in violations} == {"src/beadloom/graph/shadow.py"}

    def test_component_wins_over_domain_when_both_present(
        self, mem_db: sqlite3.Connection, tmp_path: Path
    ) -> None:
        """A symbol carrying BOTH domain= and component= is covered (component counts)."""
        _insert_symbol(
            mem_db,
            "src/beadloom/graph/dual.py",
            "fn",
            {"domain": "graph", "component": "graph-dual"},
        )
        violations = evaluate_module_coverage_rules(mem_db, [_mc_rule()], project_root=tmp_path)
        assert "src/beadloom/graph/dual.py" not in {v.file_path for v in violations}

    def test_feature_wins_over_domain_when_both_present(
        self, mem_db: sqlite3.Connection, tmp_path: Path
    ) -> None:
        """A symbol carrying BOTH domain= and feature= is covered (feature counts)."""
        _insert_symbol(
            mem_db,
            "src/beadloom/graph/feat.py",
            "fn",
            {"domain": "graph", "feature": "graph-feat"},
        )
        violations = evaluate_module_coverage_rules(mem_db, [_mc_rule()], project_root=tmp_path)
        assert "src/beadloom/graph/feat.py" not in {v.file_path for v in violations}

    def test_node_source_covers_even_with_no_annotation(
        self, mem_db: sqlite3.Connection, tmp_path: Path
    ) -> None:
        """A module that IS a node's `source` is covered even with no annotation at all."""
        mem_db.execute(
            "INSERT INTO nodes (ref_id, kind, summary, source) VALUES (?, ?, ?, ?)",
            ("graph-db", "component", "db file", "src/beadloom/graph/db.py"),
        )
        # Symbols carry NO annotations dict key for feature/component.
        _insert_symbol(mem_db, "src/beadloom/graph/db.py", "open_db", {})
        violations = evaluate_module_coverage_rules(mem_db, [_mc_rule()], project_root=tmp_path)
        assert "src/beadloom/graph/db.py" not in {v.file_path for v in violations}

    def test_directory_source_does_not_cover_modules_under_it(
        self, mem_db: sqlite3.Connection, tmp_path: Path
    ) -> None:
        """A domain's directory `source` (trailing /) does NOT cover modules beneath it."""
        mem_db.execute(
            "INSERT INTO nodes (ref_id, kind, summary, source) VALUES (?, ?, ?, ?)",
            ("graph", "domain", "graph", "src/beadloom/graph/"),
        )
        _insert_symbol(mem_db, "src/beadloom/graph/under_dir.py", "fn", {"domain": "graph"})
        violations = evaluate_module_coverage_rules(mem_db, [_mc_rule()], project_root=tmp_path)
        # The module is NOT covered just by living under the domain directory.
        assert "src/beadloom/graph/under_dir.py" in {v.file_path for v in violations}

    def test_service_directory_source_covers_modules_under_it(
        self, mem_db: sqlite3.Connection, tmp_path: Path
    ) -> None:
        """A *service* node whose `source` is a directory covers every module under it.

        Owner choice (BDL-051 / BEAD-14): the `tui` service node covers the whole
        `src/beadloom/tui/` tree as one node (no per-widget nodes). A directory
        `source` on a service therefore covers contained modules, while a *domain*
        directory source does NOT (coarse ownership is not coverage).
        """
        mem_db.execute(
            "INSERT INTO nodes (ref_id, kind, summary, source) VALUES (?, ?, ?, ?)",
            ("tui", "service", "tui", "src/beadloom/tui/"),
        )
        _insert_symbol(mem_db, "src/beadloom/tui/widgets/status_bar.py", "fn", {})
        violations = evaluate_module_coverage_rules(mem_db, [_mc_rule()], project_root=tmp_path)
        assert "src/beadloom/tui/widgets/status_bar.py" not in {v.file_path for v in violations}

    def test_root_service_directory_source_does_not_cover_everything(
        self, mem_db: sqlite3.Connection, tmp_path: Path
    ) -> None:
        """The root `beadloom` service (source == source_root) must NOT cover the tree.

        Otherwise the whole lint is trivially satisfied. Only sub-tree service /
        feature / component directory sources count as coverage.
        """
        mem_db.execute(
            "INSERT INTO nodes (ref_id, kind, summary, source) VALUES (?, ?, ?, ?)",
            ("beadloom", "service", "root", "src/beadloom/"),
        )
        _insert_symbol(mem_db, "src/beadloom/graph/orphan.py", "fn", {"domain": "graph"})
        violations = evaluate_module_coverage_rules(mem_db, [_mc_rule()], project_root=tmp_path)
        assert "src/beadloom/graph/orphan.py" in {v.file_path for v in violations}

    def test_source_root_scopes_evaluation(
        self, mem_db: sqlite3.Connection, tmp_path: Path
    ) -> None:
        """Modules outside source_root are not evaluated at all."""
        _insert_symbol(mem_db, "tests/test_thing.py", "fn", {})
        _insert_symbol(mem_db, "src/beadloom/graph/inside.py", "fn", {})
        violations = evaluate_module_coverage_rules(mem_db, [_mc_rule()], project_root=tmp_path)
        flagged = {v.file_path for v in violations}
        assert "tests/test_thing.py" not in flagged
        assert "src/beadloom/graph/inside.py" in flagged

    @pytest.mark.parametrize(
        ("symbol_count", "min_symbols", "expect_flagged"),
        [
            (1, 1, True),  # exactly at threshold -> flagged
            (2, 3, False),  # below threshold -> skipped
            (3, 3, True),  # exactly at threshold -> flagged
            (5, 3, True),  # above threshold -> flagged
        ],
    )
    def test_min_symbols_boundary(
        self,
        mem_db: sqlite3.Connection,
        tmp_path: Path,
        symbol_count: int,
        min_symbols: int,
        expect_flagged: bool,
    ) -> None:
        """min_symbols is an inclusive lower bound (>=) for symbol-indexed modules.

        (Disk-only zero-symbol modules bypass this threshold by design — they are
        always candidates; here the module has indexed symbols on the DB side and
        is NOT present on disk, so the threshold applies.)
        """
        for i in range(symbol_count):
            _insert_symbol(
                mem_db, "src/beadloom/graph/threshold.py", f"fn_{i}", {"domain": "graph"}
            )
        violations = evaluate_module_coverage_rules(
            mem_db, [_mc_rule(min_symbols=min_symbols)], project_root=tmp_path
        )
        flagged = "src/beadloom/graph/threshold.py" in {v.file_path for v in violations}
        assert flagged is expect_flagged


# ---------------------------------------------------------------------------
# Disk-walk enumeration (BDL-051 S3a / BEAD-17, review .9 MAJOR fix)
# ---------------------------------------------------------------------------


class TestDiskWalkEnumeration:
    """The candidate set is enumerated from DISK, closing the zero-symbol hole."""

    def _make_tree(self, tmp_path: Path) -> Path:
        """A synthetic src/ tree: a shadow module, an exempt __main__, a covered module."""
        root = tmp_path / "src" / "beadloom"
        (root / "ai_agents" / "tw").mkdir(parents=True)
        # zero-top-level-symbol shadow module (no annotation, not exempt) -> flagged
        (root / "graph" / "shadow.py").parent.mkdir(parents=True)
        (root / "graph" / "shadow.py").write_text('"""glue."""\nX = 1\n')
        # an exempt python -m entrypoint -> NOT flagged
        (root / "ai_agents" / "tw" / "__main__.py").write_text(
            '"""entrypoint."""\nfrom x import main\n\nif __name__ == "__main__":\n    main()\n'
        )
        # a covered module (it IS a node's source) -> NOT flagged
        (root / "graph" / "loader.py").write_text("def load():\n    pass\n")
        return tmp_path

    def test_disk_walk_flags_shadow_exempts_main_and_skips_covered(
        self, mem_db: sqlite3.Connection, tmp_path: Path
    ) -> None:
        """Shadow flagged; __main__.py exempt; node-source module covered."""
        self._make_tree(tmp_path)
        # loader.py is covered by being a node's source (no symbol/annotation needed).
        mem_db.execute(
            "INSERT INTO nodes (ref_id, kind, summary, source) VALUES (?, ?, ?, ?)",
            ("graph-loader", "component", "loader", "src/beadloom/graph/loader.py"),
        )
        rule = _mc_rule(exempt=("**/__init__.py", "**/__main__.py"))
        flagged = {
            v.file_path
            for v in evaluate_module_coverage_rules(mem_db, [rule], project_root=tmp_path)
        }
        assert "src/beadloom/graph/shadow.py" in flagged
        assert "src/beadloom/ai_agents/tw/__main__.py" not in flagged
        assert "src/beadloom/graph/loader.py" not in flagged

    def test_disk_walk_is_deterministic_and_sorted(
        self, mem_db: sqlite3.Connection, tmp_path: Path
    ) -> None:
        """Repeated evaluation yields findings in a stable, sorted (by file_path) order."""
        root = tmp_path / "src" / "beadloom" / "graph"
        root.mkdir(parents=True)
        for name in ("zeta.py", "alpha.py", "mid.py"):
            (root / name).write_text('"""glue."""\nX = 1\n')
        rule = _mc_rule()
        runs = [
            [
                v.file_path
                for v in evaluate_module_coverage_rules(mem_db, [rule], project_root=tmp_path)
            ]
            for _ in range(3)
        ]
        assert runs[0] == runs[1] == runs[2]
        assert runs[0] == sorted(runs[0])

    def test_disk_module_with_feature_annotation_is_covered(
        self, mem_db: sqlite3.Connection, tmp_path: Path
    ) -> None:
        """A disk module whose symbols carry a feature annotation is covered."""
        root = tmp_path / "src" / "beadloom" / "graph"
        root.mkdir(parents=True)
        (root / "feat.py").write_text("# beadloom:feature=graph-feat\ndef f():\n    pass\n")
        _insert_symbol(mem_db, "src/beadloom/graph/feat.py", "f", {"feature": "graph-feat"})
        flagged = {
            v.file_path
            for v in evaluate_module_coverage_rules(mem_db, [_mc_rule()], project_root=tmp_path)
        }
        assert "src/beadloom/graph/feat.py" not in flagged


# ---------------------------------------------------------------------------
# Exempt-glob nuances
# ---------------------------------------------------------------------------


class TestExemptGlobNuances:
    def test_nested_init_matched_by_recursive_glob(
        self, mem_db: sqlite3.Connection, tmp_path: Path
    ) -> None:
        """`**/__init__.py` exempts a deeply nested __init__.py."""
        _insert_symbol(mem_db, "src/beadloom/tui/widgets/__init__.py", "x", {"domain": "graph"})
        violations = evaluate_module_coverage_rules(
            mem_db, [_mc_rule(exempt=("**/__init__.py",))], project_root=tmp_path
        )
        assert "src/beadloom/tui/widgets/__init__.py" not in {v.file_path for v in violations}

    def test_config_reader_and_presets_exempted_by_real_globs(
        self, mem_db: sqlite3.Connection, tmp_path: Path
    ) -> None:
        """The real seeded globs exempt config_reader.py and presets.py."""
        _insert_symbol(
            mem_db,
            "src/beadloom/onboarding/config_reader.py",
            "read",
            {"domain": "onboarding"},
        )
        _insert_symbol(
            mem_db,
            "src/beadloom/onboarding/presets.py",
            "preset",
            {"domain": "onboarding"},
        )
        exempt = (
            "**/__init__.py",
            "**/onboarding/config_reader.py",
            "**/onboarding/presets.py",
        )
        violations = evaluate_module_coverage_rules(
            mem_db, [_mc_rule(exempt=exempt)], project_root=tmp_path
        )
        flagged = {v.file_path for v in violations}
        assert "src/beadloom/onboarding/config_reader.py" not in flagged
        assert "src/beadloom/onboarding/presets.py" not in flagged

    def test_non_exempt_sibling_still_flagged(
        self, mem_db: sqlite3.Connection, tmp_path: Path
    ) -> None:
        """A sibling of an exempt file is NOT swept up by the exempt glob."""
        _insert_symbol(mem_db, "src/beadloom/onboarding/presets.py", "p", {"domain": "onboarding"})
        _insert_symbol(mem_db, "src/beadloom/onboarding/scanner.py", "s", {"domain": "onboarding"})
        violations = evaluate_module_coverage_rules(
            mem_db, [_mc_rule(exempt=("**/onboarding/presets.py",))], project_root=tmp_path
        )
        flagged = {v.file_path for v in violations}
        assert "src/beadloom/onboarding/presets.py" not in flagged
        assert "src/beadloom/onboarding/scanner.py" in flagged

    def test_partial_name_glob_does_not_over_match(
        self, mem_db: sqlite3.Connection, tmp_path: Path
    ) -> None:
        """`**/presets.py` must not exempt `presets_extra.py` (no partial-name over-match)."""
        _insert_symbol(
            mem_db,
            "src/beadloom/onboarding/presets_extra.py",
            "e",
            {"domain": "onboarding"},
        )
        violations = evaluate_module_coverage_rules(
            mem_db, [_mc_rule(exempt=("**/presets.py",))], project_root=tmp_path
        )
        assert "src/beadloom/onboarding/presets_extra.py" in {v.file_path for v in violations}


# ---------------------------------------------------------------------------
# warn-not-fail (S3b will promote to error — pin the CURRENT behavior)
# ---------------------------------------------------------------------------


class TestSeverityIsHonored:
    @pytest.mark.parametrize("severity", ["warn", "error"])
    def test_findings_carry_the_rule_severity(
        self, mem_db: sqlite3.Connection, tmp_path: Path, severity: str
    ) -> None:
        """Every finding carries the rule's configured severity (warn OR error)."""
        for n in range(20):
            _insert_symbol(mem_db, f"src/beadloom/graph/mod_{n}.py", "fn", {"domain": "graph"})
        violations = evaluate_all(mem_db, [_mc_rule(severity=severity)], project_root=tmp_path)
        mc = [v for v in violations if v.rule_type == "module_coverage"]
        assert len(mc) == 20
        assert all(v.severity == severity for v in mc)


class TestRealRepoCoveragePromoted:
    """BDL-051 S3b / BEAD-14: every module is classified, so the rule is `error`."""

    def test_live_repo_module_coverage_rule_is_error(self) -> None:
        """The repo's `module-coverage` rule has been PROMOTED from warn to error."""
        rules = load_rules(Path.cwd() / ".beadloom" / "_graph" / "rules.yml")
        mc = [r for r in rules if isinstance(r, ModuleCoverageRule)]
        assert len(mc) == 1
        assert mc[0].severity == "error"

    def test_live_repo_has_zero_module_coverage_findings(
        self, live_repo_reindexed: Path
    ) -> None:
        """`module-coverage` reports ZERO findings over the live src tree (no shadow code)."""
        runner = CliRunner()
        # The `live_repo_reindexed` fixture guarantees the shared on-disk DB
        # reflects current source, so we read it (--no-reindex) without
        # re-mutating it for other tests. This keeps the assertion
        # order-independent (surfaced by pytest-randomly in S1).
        result = runner.invoke(
            main,
            ["lint", "--format", "json", "--project", str(live_repo_reindexed), "--no-reindex"],
        )
        assert result.exit_code in (0, 1), result.output
        payload = json.loads(result.output)
        findings = payload["violations"]
        coverage = [f for f in findings if f.get("rule_name") == "module-coverage"]
        assert coverage == [], coverage

    def test_real_repo_lint_strict_exits_zero(self, live_repo_reindexed: Path) -> None:
        """`lint --strict` over the live repo exits 0 — coverage clean despite error severity."""
        runner = CliRunner()
        # Reads the fixture-reindexed shared DB (see the note above).
        result = runner.invoke(
            main, ["lint", "--strict", "--project", str(live_repo_reindexed), "--no-reindex"]
        )
        assert result.exit_code == 0, result.output


# ---------------------------------------------------------------------------
# Serialize / reindex round-trip + Unknown-rule-type guard
# ---------------------------------------------------------------------------


class TestModuleCoverageParseEdges:
    """Parser edge branches not exercised by the dev's happy-path parsing tests."""

    def test_exempt_null_normalizes_to_empty(self, tmp_path: Path) -> None:
        """`exempt: null` (YAML null) normalizes to an empty exempt tuple, not a crash."""
        rules_path = tmp_path / "rules.yml"
        rules_path.write_text(
            "version: 3\nrules:\n"
            "  - name: module-coverage\n"
            "    description: coverage\n"
            "    module_coverage:\n"
            "      exempt: null\n"
        )
        rules = load_rules(rules_path)
        assert isinstance(rules[0], ModuleCoverageRule)
        assert rules[0].exempt == ()

    def test_exempt_not_a_list_rejected(self, tmp_path: Path) -> None:
        """A non-list `exempt` value is a schema error."""
        rules_path = tmp_path / "rules.yml"
        rules_path.write_text(
            "version: 3\nrules:\n"
            "  - name: module-coverage\n"
            "    description: coverage\n"
            "    module_coverage:\n"
            "      exempt: '**/__init__.py'\n"
        )
        with pytest.raises(ValueError, match="exempt must be a list"):
            load_rules(rules_path)

    def test_custom_source_root_parsed(self, tmp_path: Path) -> None:
        """A non-default source_root round-trips through the parser."""
        rules_path = tmp_path / "rules.yml"
        rules_path.write_text(
            "version: 3\nrules:\n"
            "  - name: module-coverage\n"
            "    description: coverage\n"
            "    module_coverage:\n"
            "      source_root: src/other/\n"
        )
        rules = load_rules(rules_path)
        assert isinstance(rules[0], ModuleCoverageRule)
        assert rules[0].source_root == "src/other/"


class TestSerializeRoundTrip:
    def test_module_coverage_round_trips_through_serialize(self) -> None:
        """A parsed module_coverage rule serializes back to the same rule_type+fields."""
        from beadloom.application.reindex import _serialize_rule

        rule = _mc_rule(exempt=("**/__init__.py", "**/presets.py"), min_symbols=2)
        rule_type, rule_def = _serialize_rule(rule)
        assert rule_type == "module_coverage"
        assert rule_def["source_root"] == "src/beadloom/"
        assert rule_def["min_symbols"] == 2
        assert rule_def["exempt"] == ["**/__init__.py", "**/presets.py"]

    def test_empty_exempt_omitted_from_serialization(self) -> None:
        """An empty exempt tuple is omitted from the serialized def (compact form)."""
        from beadloom.application.reindex import _serialize_rule

        _rule_type, rule_def = _serialize_rule(_mc_rule(exempt=()))
        assert "exempt" not in rule_def

    def test_serialize_rejects_unknown_rule_type(self) -> None:
        """An object that is not a known Rule type raises 'Unknown rule type'."""
        from beadloom.application.reindex import _serialize_rule

        class _NotARule:
            pass

        with pytest.raises(TypeError, match="Unknown rule type"):
            _serialize_rule(_NotARule())

    def test_real_rules_yml_module_coverage_loads_into_db(
        self, mem_db: sqlite3.Connection
    ) -> None:
        """The repo's real rules.yml round-trips: module-coverage lands as module_coverage."""
        from beadloom.application.reindex import ReindexResult, _load_rules_into_db

        rules_path = Path.cwd() / ".beadloom" / "_graph" / "rules.yml"
        result = ReindexResult()
        _load_rules_into_db(rules_path, mem_db, result)
        mem_db.commit()
        assert result.errors == []
        row = mem_db.execute(
            "SELECT rule_type FROM rules WHERE name = ?", ("module-coverage",)
        ).fetchone()
        assert row is not None
        assert row["rule_type"] == "module_coverage"


# ---------------------------------------------------------------------------
# Retired unregistered-feature-candidate is fully superseded
# ---------------------------------------------------------------------------


class TestUnregisteredFeatureCandidateRetired:
    def test_no_active_unregistered_rule_in_real_rules_yml(self) -> None:
        """The repo's rules.yml carries NO active unregistered_feature_candidate rule."""
        rules_path = Path.cwd() / ".beadloom" / "_graph" / "rules.yml"
        rules = load_rules(rules_path)
        type_names = {type(r).__name__ for r in rules}
        assert "UnregisteredFeatureCandidateRule" not in type_names

    def test_real_rules_yml_has_module_coverage_rule(self) -> None:
        """The successor module-coverage rule IS present in the real rules.yml.

        Post-S3b (BEAD-14): every module is classified, so the rule has been
        PROMOTED from warn to error (any future shadow module fails CI).
        """
        rules_path = Path.cwd() / ".beadloom" / "_graph" / "rules.yml"
        rules = load_rules(rules_path)
        mc = [r for r in rules if isinstance(r, ModuleCoverageRule)]
        assert len(mc) == 1
        assert mc[0].name == "module-coverage"
        assert mc[0].severity == "error"
        # The minimally-seeded exempt list is visible (not a silent escape hatch).
        assert "**/__init__.py" in mc[0].exempt


# ---------------------------------------------------------------------------
# Real-repo regression guard: coverage stays enforced over the live tree
# ---------------------------------------------------------------------------


class TestRealRepoCoverageGuard:
    """Post-S3b (BEAD-14): every module is classified, so the live tree has ZERO
    coverage findings. The formerly-shadow modules are now covered by a node."""

    def _real_coverage_findings(self, repo_root: Path) -> set[str]:
        runner = CliRunner()
        # --no-reindex: the `live_repo_reindexed` fixture has already brought the
        # shared on-disk DB up to date, so we read it without re-mutating it.
        result = runner.invoke(
            main,
            ["lint", "--format", "porcelain", "--project", str(repo_root), "--no-reindex"],
        )
        assert result.exit_code == 0, result.output
        flagged: set[str] = set()
        for line in result.output.splitlines():
            parts = line.split(":")
            if len(parts) >= 4 and parts[0] == "module-coverage":
                flagged.add(parts[3])
        return flagged

    def test_formerly_shadow_modules_now_covered(self, live_repo_reindexed: Path) -> None:
        """The modules classified in S3b are no longer flagged (they have nodes now)."""
        flagged = self._real_coverage_findings(live_repo_reindexed)
        for covered in (
            "src/beadloom/graph/loader.py",
            "src/beadloom/infrastructure/db.py",
            "src/beadloom/doc_sync/engine.py",
        ):
            assert covered not in flagged, f"{covered} should be covered post-S3b"

    def test_coverage_lint_reports_no_findings(self, live_repo_reindexed: Path) -> None:
        """Every src module is classified — the coverage lint reports zero findings."""
        flagged = self._real_coverage_findings(live_repo_reindexed)
        assert flagged == set(), flagged
