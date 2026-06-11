# beadloom:domain=graph
"""S3b verify/harden: full module classification + the PROMOTED (error) coverage-lint.

BDL-051 Slice 3b / BEAD-15 (test). These tests harden the dev's S3b work
(`tests/test_module_coverage_hardening.py`, `tests/test_rule_engine.py`) WITHOUT
duplicating its passing cases. The dev's tests already pin: rule-is-error, the
live repo has zero coverage findings, dir-source-covers (tui), serialize
round-trips, exempt-glob nuances. This file adds the gaps the bead calls out:

* **error-level regression guard** — the whole point: an `error`-severity
  coverage rule + a NEW uncovered module must FAIL ``lint --strict`` (rc 1).
  The dev only proves the *clean* tree exits 0; this proves the gate actually
  bites (no future shadow code can slip in unnoticed).
* **dir-source coverage depth** — a dir source covers nested subtrees
  (``tui/screens/*``, ``tui/widgets/*``), does NOT over-cover siblings outside
  the dir, and nested/overlapping dir sources both count.
* **site-generation cluster** — all 9 ``application/site*.py`` are covered by the
  single ``site-generation`` node; none flagged; the node round-trips reindex.
* **every new node resolves** — ``ctx`` returns for a sample of new features +
  components; ``component``-kind nodes load/validate/serialize.
* **annotation <-> node consistency** — bidirectional: every annotation value
  names a declared node, and every new file-source node's file carries the
  matching annotation (or is the node's source).
* **sync-check** — the new SPEC/DOC pairs are tracked + currently fresh.
* **exempt still minimal** — exactly the 4 seeded globs, nothing newly hidden.

All deterministic, no network. Real-repo assertions use the live graph as-is.
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
    evaluate_module_coverage_rules,
    load_rules,
)
from beadloom.infrastructure.db import create_schema
from beadloom.services.cli import main

if TYPE_CHECKING:
    from collections.abc import Iterator

REPO_ROOT = Path(__file__).resolve().parent.parent
RULES_PATH = REPO_ROOT / ".beadloom" / "_graph" / "rules.yml"


@pytest.fixture(scope="module", autouse=True)
def _built_repo_graph() -> None:
    """Build the live repo graph DB once before the tests that query it.

    The tests below run ``ctx``/``lint --project REPO_ROOT`` against the real
    repo. A fresh CI checkout has no graph DB (it's gitignored and the ``tests``
    job doesn't reindex), so those assertions fail with "node not found" unless
    we build it here. ``reindex`` is deterministic + idempotent.
    """
    CliRunner().invoke(main, ["reindex", "--project", str(REPO_ROOT)])
SERVICES_PATH = REPO_ROOT / ".beadloom" / "_graph" / "services.yml"


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def mem_db() -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    create_schema(conn)
    yield conn
    conn.close()


def _insert_symbol(
    conn: sqlite3.Connection,
    file_path: str,
    symbol_name: str,
    annotations: dict[str, str],
) -> None:
    conn.execute(
        "INSERT INTO code_symbols"
        " (file_path, symbol_name, kind, line_start, line_end, annotations, file_hash)"
        " VALUES (?, ?, ?, ?, ?, ?, ?)",
        (file_path, symbol_name, "function", 1, 10, json.dumps(annotations), "h"),
    )


def _mc_rule(
    *,
    exempt: tuple[str, ...] = (),
    severity: str = "error",
) -> ModuleCoverageRule:
    return ModuleCoverageRule(
        name="module-coverage",
        description="every src module must be a node or exempt",
        source_root="src/beadloom/",
        min_symbols=1,
        exempt=exempt,
        severity=severity,
    )


def _load_real_nodes() -> dict[str, dict[str, object]]:
    """Load the live services.yml nodes into ``{ref_id: node_dict}`` (no DB)."""
    import yaml

    data = yaml.safe_load(SERVICES_PATH.read_text())
    nodes: dict[str, dict[str, object]] = {}
    for node in data.get("nodes", []):
        nodes[str(node["ref_id"])] = node
    return nodes


# ---------------------------------------------------------------------------
# THE REGRESSION GUARD: error severity actually FAILS lint --strict
# ---------------------------------------------------------------------------


class TestErrorLevelRegressionGuard:
    """The promoted (error) coverage-lint must FAIL the gate on a new shadow module.

    This is the entire point of S3b: once every module is classified, the rule is
    promoted warn -> error so any *future* uncovered module breaks CI. The dev's
    tests prove the clean tree exits 0; these prove the gate bites otherwise.
    """

    def _make_project(self, tmp_path: Path, *, severity: str) -> Path:
        """A synthetic project mirroring the real rule: one covered + one shadow module."""
        project = tmp_path / "proj"
        graph_dir = project / ".beadloom" / "_graph"
        graph_dir.mkdir(parents=True)
        (project / "docs").mkdir()
        (graph_dir / "services.yml").write_text(
            "version: 1\n"
            "nodes:\n"
            "  - ref_id: beadloom\n"
            "    kind: service\n"
            "    summary: root\n"
            "  - ref_id: graph\n"
            "    kind: domain\n"
            "    summary: graph domain\n"
            "    source: src/beadloom/graph/\n"
            "  - ref_id: graph-loader\n"
            "    kind: component\n"
            "    summary: loader\n"
            "    source: src/beadloom/graph/loader.py\n"
            "edges:\n"
            "  - src: graph\n"
            "    dst: beadloom\n"
            "    kind: part_of\n"
            "  - src: graph-loader\n"
            "    dst: graph\n"
            "    kind: part_of\n"
        )
        (graph_dir / "rules.yml").write_text(
            "version: 3\n"
            "rules:\n"
            "  - name: module-coverage\n"
            "    description: every module must be a node or exempt\n"
            f"    severity: {severity}\n"
            "    module_coverage:\n"
            "      source_root: src/beadloom/\n"
            "      min_symbols: 1\n"
            "      exempt:\n"
            "        - '**/__init__.py'\n"
        )
        src = project / "src" / "beadloom" / "graph"
        src.mkdir(parents=True)
        (src / "loader.py").write_text(
            "# beadloom:component=graph-loader\ndef load():\n    pass\n"
        )
        # The SHADOW module: real code, no annotation, not a node source, not exempt.
        (src / "shadow.py").write_text("def secret():\n    return 1\n")
        return project

    def test_new_uncovered_module_fails_lint_strict_at_error(self, tmp_path: Path) -> None:
        """error severity + a new shadow module -> ``lint --strict`` exits NON-zero."""
        project = self._make_project(tmp_path, severity="error")
        runner = CliRunner()
        result = runner.invoke(main, ["lint", "--strict", "--project", str(project)])
        assert result.exit_code == 1, result.output
        assert "shadow.py" in result.output

    def test_same_shadow_module_at_warn_does_not_fail_strict(self, tmp_path: Path) -> None:
        """Control: the IDENTICAL shadow at warn severity does NOT fail --strict (rc 0).

        Proves it is the *error* promotion — not merely the finding's presence —
        that fails the gate. This is the warn->error contrast the bead asks for.
        """
        project = self._make_project(tmp_path, severity="warn")
        runner = CliRunner()
        result = runner.invoke(main, ["lint", "--strict", "--project", str(project)])
        assert result.exit_code == 0, result.output

    def test_finding_carries_error_severity_in_json(self, tmp_path: Path) -> None:
        """The shadow finding is emitted with severity ``error`` (not silently demoted)."""
        project = self._make_project(tmp_path, severity="error")
        runner = CliRunner()
        result = runner.invoke(main, ["lint", "--format", "json", "--project", str(project)])
        payload = json.loads(result.output)
        coverage = [
            v for v in payload["violations"] if v["rule_name"] == "module-coverage"
        ]
        assert coverage, payload
        assert all(v["severity"] == "error" for v in coverage)
        assert any("shadow.py" in str(v["file_path"]) for v in coverage)

    def test_covering_the_module_restores_green(self, tmp_path: Path) -> None:
        """Annotating the shadow module makes ``lint --strict`` pass again (rc 0).

        Demonstrates the gate is satisfiable by classification, not just by lowering
        severity — the closed loop S3b establishes.
        """
        project = self._make_project(tmp_path, severity="error")
        shadow = project / "src" / "beadloom" / "graph" / "shadow.py"
        shadow.write_text("# beadloom:component=graph-loader\ndef secret():\n    return 1\n")
        runner = CliRunner()
        result = runner.invoke(main, ["lint", "--strict", "--project", str(project)])
        assert result.exit_code == 0, result.output

    def test_live_repo_error_rule_with_injected_shadow_fails(self, tmp_path: Path) -> None:
        """Synthetic-DB guard against the live error rule: an injected shadow IS a finding.

        Uses the REAL rules.yml (error severity) loaded as-is, so this regresses if a
        future edit silently demotes the rule back to warn AND a shadow appears.
        """
        rules = [r for r in load_rules(RULES_PATH) if isinstance(r, ModuleCoverageRule)]
        assert len(rules) == 1
        rule = rules[0]
        assert rule.severity == "error"
        # Build a tmp tree with a single uncovered module + the real rule's exempt set.
        src = tmp_path / "src" / "beadloom" / "graph"
        src.mkdir(parents=True)
        (src / "ghost.py").write_text("def g():\n    return 0\n")
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        create_schema(conn)
        try:
            violations = evaluate_module_coverage_rules(conn, [rule], project_root=tmp_path)
        finally:
            conn.close()
        ghosts = [v for v in violations if v.file_path == "src/beadloom/graph/ghost.py"]
        assert ghosts, violations
        assert all(v.severity == "error" for v in ghosts)


# ---------------------------------------------------------------------------
# dir-source coverage: nested depth, no over-cover, overlapping/nested sources
# ---------------------------------------------------------------------------


class TestDirSourceCoverageDepth:
    """A directory `source` covers its whole subtree (deeply), but not outside it."""

    def test_dir_source_covers_deeply_nested_modules(
        self, mem_db: sqlite3.Connection, tmp_path: Path
    ) -> None:
        """tui/ (dir source) covers BOTH tui/screens/* and tui/widgets/* — nested depth."""
        mem_db.execute(
            "INSERT INTO nodes (ref_id, kind, summary, source) VALUES (?, ?, ?, ?)",
            ("tui", "service", "tui", "src/beadloom/tui/"),
        )
        for path in (
            "src/beadloom/tui/screens/main_screen.py",
            "src/beadloom/tui/widgets/status_bar.py",
            "src/beadloom/tui/app.py",
        ):
            _insert_symbol(mem_db, path, "fn", {})
        flagged = {
            v.file_path
            for v in evaluate_module_coverage_rules(mem_db, [_mc_rule()], project_root=tmp_path)
        }
        assert "src/beadloom/tui/screens/main_screen.py" not in flagged
        assert "src/beadloom/tui/widgets/status_bar.py" not in flagged
        assert "src/beadloom/tui/app.py" not in flagged

    def test_dir_source_does_not_over_cover_siblings_outside(
        self, mem_db: sqlite3.Connection, tmp_path: Path
    ) -> None:
        """tui/ does NOT cover a sibling under a different dir (e.g. graph/), nor a prefix-twin.

        Guards against a naive ``startswith`` that would let ``tui/`` cover a
        sibling directory whose name merely starts with ``tui`` (``tui_extra/``).
        """
        mem_db.execute(
            "INSERT INTO nodes (ref_id, kind, summary, source) VALUES (?, ?, ?, ?)",
            ("tui", "service", "tui", "src/beadloom/tui/"),
        )
        _insert_symbol(mem_db, "src/beadloom/graph/outside.py", "fn", {"domain": "graph"})
        _insert_symbol(mem_db, "src/beadloom/tui_extra/twin.py", "fn", {"domain": "graph"})
        flagged = {
            v.file_path
            for v in evaluate_module_coverage_rules(mem_db, [_mc_rule()], project_root=tmp_path)
        }
        assert "src/beadloom/graph/outside.py" in flagged
        assert "src/beadloom/tui_extra/twin.py" in flagged

    def test_file_source_node_covers_only_its_own_file(
        self, mem_db: sqlite3.Connection, tmp_path: Path
    ) -> None:
        """A file-source node covers ONLY its file, not a sibling in the same dir."""
        mem_db.execute(
            "INSERT INTO nodes (ref_id, kind, summary, source) VALUES (?, ?, ?, ?)",
            ("graph-loader", "component", "loader", "src/beadloom/graph/loader.py"),
        )
        _insert_symbol(mem_db, "src/beadloom/graph/loader.py", "fn", {})
        _insert_symbol(mem_db, "src/beadloom/graph/sibling.py", "fn", {"domain": "graph"})
        flagged = {
            v.file_path
            for v in evaluate_module_coverage_rules(mem_db, [_mc_rule()], project_root=tmp_path)
        }
        assert "src/beadloom/graph/loader.py" not in flagged
        assert "src/beadloom/graph/sibling.py" in flagged

    def test_overlapping_nested_dir_sources_both_cover(
        self, mem_db: sqlite3.Connection, tmp_path: Path
    ) -> None:
        """A nested dir source inside an outer dir source: modules under either are covered."""
        mem_db.execute(
            "INSERT INTO nodes (ref_id, kind, summary, source) VALUES (?, ?, ?, ?)",
            ("tui", "service", "tui", "src/beadloom/tui/"),
        )
        mem_db.execute(
            "INSERT INTO nodes (ref_id, kind, summary, source) VALUES (?, ?, ?, ?)",
            ("tui-widgets", "component", "widgets", "src/beadloom/tui/widgets/"),
        )
        _insert_symbol(mem_db, "src/beadloom/tui/widgets/deep/inner.py", "fn", {})
        flagged = {
            v.file_path
            for v in evaluate_module_coverage_rules(mem_db, [_mc_rule()], project_root=tmp_path)
        }
        assert "src/beadloom/tui/widgets/deep/inner.py" not in flagged


# ---------------------------------------------------------------------------
# site-generation cluster: all 9 site*.py covered by ONE node
# ---------------------------------------------------------------------------


class TestSiteGenerationCluster:
    """The 9 application/site*.py modules are covered by the single site-generation node."""

    def test_all_nine_site_modules_exist_on_disk(self) -> None:
        """Sanity: exactly the expected site*.py cluster lives under application/."""
        site_files = sorted((REPO_ROOT / "src" / "beadloom" / "application").glob("site*.py"))
        names = {p.name for p in site_files}
        assert "site.py" in names
        # The cluster is the 9 modules the dev classified as one node.
        assert len(site_files) == 9, names

    def test_no_site_module_is_flagged_by_coverage(self) -> None:
        """None of the 9 site*.py modules appear as a module-coverage finding (live repo)."""
        runner = CliRunner()
        result = runner.invoke(
            main, ["lint", "--format", "json", "--project", str(REPO_ROOT), "--no-reindex"]
        )
        payload = json.loads(result.output)
        coverage_files = {
            str(v["file_path"])
            for v in payload["violations"]
            if v["rule_name"] == "module-coverage"
        }
        site_files = (REPO_ROOT / "src" / "beadloom" / "application").glob("site*.py")
        for path in site_files:
            rel = f"src/beadloom/application/{path.name}"
            assert rel not in coverage_files, rel

    def test_site_generation_node_round_trips_reindex(self) -> None:
        """`ctx site-generation` resolves the node post-reindex (round-trip through DB)."""
        runner = CliRunner()
        result = runner.invoke(
            main, ["ctx", "site-generation", "--project", str(REPO_ROOT), "--json"]
        )
        assert result.exit_code == 0, result.output
        bundle = json.loads(result.output)
        assert bundle["focus"]["ref_id"] == "site-generation"
        assert bundle["focus"]["kind"] == "feature"


# ---------------------------------------------------------------------------
# Every new node resolves via ctx; component kind loads/validates
# ---------------------------------------------------------------------------


class TestNewNodesResolve:
    NEW_FEATURES = (
        "code-indexer",
        "route-extraction",
        "test-mapping",
        "sync-check",
        "snapshot",
        "ci-gate",
        "config-check",
        "ai-techwriter-setup",
        "branch-protection",
        "agentic-flow-setup",
        "site-generation",
    )
    NEW_COMPONENTS = (
        "graph-loader",
        "contracts",
        "sdl",
        "context-builder",
        "doc-indexer",
        "db",
        "git-activity",
        "health",
        "mcp-tools",
        "bd-seam",
    )

    @pytest.mark.parametrize("ref_id", NEW_FEATURES)
    def test_new_feature_node_ctx_resolves(self, ref_id: str) -> None:
        """Each new S3b feature node resolves through `ctx` to a feature bundle."""
        runner = CliRunner()
        result = runner.invoke(
            main, ["ctx", ref_id, "--project", str(REPO_ROOT), "--json"]
        )
        assert result.exit_code == 0, result.output
        bundle = json.loads(result.output)
        assert bundle["focus"]["ref_id"] == ref_id
        assert bundle["focus"]["kind"] == "feature"

    @pytest.mark.parametrize("ref_id", NEW_COMPONENTS)
    def test_new_component_node_ctx_resolves(self, ref_id: str) -> None:
        """Each new S3b component node resolves through `ctx` to a component bundle."""
        runner = CliRunner()
        result = runner.invoke(
            main, ["ctx", ref_id, "--project", str(REPO_ROOT), "--json"]
        )
        assert result.exit_code == 0, result.output
        bundle = json.loads(result.output)
        assert bundle["focus"]["ref_id"] == ref_id
        assert bundle["focus"]["kind"] == "component"

    def test_component_nodes_part_of_a_parent(self) -> None:
        """Every new component declares a part_of edge to a domain/service (validates)."""
        import yaml

        data = yaml.safe_load(SERVICES_PATH.read_text())
        part_of_srcs = {
            str(e["src"]) for e in data.get("edges", []) if e.get("kind") == "part_of"
        }
        for ref_id in self.NEW_COMPONENTS:
            assert ref_id in part_of_srcs, f"{ref_id} has no part_of parent"


# ---------------------------------------------------------------------------
# annotation <-> node consistency (bidirectional)
# ---------------------------------------------------------------------------


class TestAnnotationNodeConsistency:
    """Annotations and nodes must agree: no dangling annotation, no unannotated source.

    The source of truth for "what annotations exist" is what the code indexer
    actually recorded in ``code_symbols.annotations`` — NOT a naive source regex
    (which would wrongly match literal ``# beadloom:feature=REF_ID`` example text
    inside docstrings/help strings). The coverage lint consumes the indexed
    annotations, so this is the correct, behavior-aligned consistency check.
    """

    def _annotation_values(self) -> dict[str, set[str]]:
        """Read indexed feature/component annotation values from the live DB."""
        db_path = REPO_ROOT / ".beadloom" / "beadloom.db"
        assert db_path.is_file(), f"reindex first: {db_path} missing"
        conn = sqlite3.connect(str(db_path))
        try:
            rows = conn.execute(
                "SELECT annotations FROM code_symbols"
                " WHERE annotations IS NOT NULL AND file_path LIKE 'src/beadloom/%'"
            ).fetchall()
        finally:
            conn.close()
        features: set[str] = set()
        components: set[str] = set()
        for (blob,) in rows:
            data = json.loads(blob) if blob else {}
            if "feature" in data:
                features.add(str(data["feature"]))
            if "component" in data:
                components.add(str(data["component"]))
        return {"feature": features, "component": components}

    def test_every_annotation_value_names_a_declared_node(self) -> None:
        """No annotation points at a ref_id that is not a declared node (no dangling)."""
        nodes = _load_real_nodes()
        values = self._annotation_values()
        all_annotated = values["feature"] | values["component"]
        missing = {v for v in all_annotated if v not in nodes}
        assert missing == set(), f"annotations point at non-existent nodes: {missing}"

    def test_feature_annotations_match_feature_kind(self) -> None:
        """A `feature=` annotation names a node of kind feature (not component/domain)."""
        nodes = _load_real_nodes()
        values = self._annotation_values()
        for ref_id in values["feature"]:
            assert nodes[ref_id].get("kind") == "feature", ref_id

    def test_component_annotations_match_component_kind(self) -> None:
        """A `component=` annotation names a node of kind component."""
        nodes = _load_real_nodes()
        values = self._annotation_values()
        for ref_id in values["component"]:
            assert nodes[ref_id].get("kind") == "component", ref_id

    def test_file_source_nodes_have_matching_annotation_or_are_the_source(self) -> None:
        """Every new file-source node's file carries the matching annotation.

        For the S3b file-source feature/component nodes, the source module must
        either carry the matching ``feature=``/``component=`` annotation (covered by
        annotation) — the architecture-model policy that there is no node whose
        source file silently lacks the annotation.
        """
        import re

        nodes = _load_real_nodes()
        new_ids = set(TestNewNodesResolve.NEW_FEATURES) | set(
            TestNewNodesResolve.NEW_COMPONENTS
        )
        unannotated: list[str] = []
        for ref_id in new_ids:
            node = nodes[ref_id]
            source = str(node.get("source", ""))
            if not source or source.endswith("/"):
                continue  # dir sources covered separately
            src_path = REPO_ROOT / source
            if not src_path.is_file():
                unannotated.append(f"{ref_id}: source missing {source}")
                continue
            text = src_path.read_text(encoding="utf-8", errors="ignore")
            kind = str(node["kind"])
            ann_re = re.compile(rf"#\s*beadloom:{kind}={re.escape(ref_id)}\b")
            if not ann_re.search(text):
                unannotated.append(f"{ref_id}: {source} lacks # beadloom:{kind}={ref_id}")
        assert unannotated == [], unannotated


# ---------------------------------------------------------------------------
# sync-check: new SPEC/DOC pairs tracked + fresh
# ---------------------------------------------------------------------------


class TestSyncCheckNewPairs:
    """The new SPEC/DOC skeletons are tracked by sync-check and currently fresh."""

    def _sync_pairs(self) -> list[dict[str, object]]:
        runner = CliRunner()
        result = runner.invoke(
            main, ["sync-check", "--json", "--project", str(REPO_ROOT)]
        )
        assert result.exit_code == 0, result.output
        pairs: list[dict[str, object]] = json.loads(result.output)["pairs"]
        return pairs

    def test_new_node_docs_are_tracked_pairs(self) -> None:
        """Each new node's SPEC/DOC appears as a tracked sync-check pair."""
        nodes = _load_real_nodes()
        tracked_refs = {str(p["ref_id"]) for p in self._sync_pairs()}
        sample = (
            "code-indexer",
            "sync-check",
            "ci-gate",
            "site-generation",
            "db",
            "graph-loader",
            "bd-seam",
        )
        for ref_id in sample:
            assert ref_id in nodes
            assert ref_id in tracked_refs, f"{ref_id} not tracked by sync-check"

    def test_all_new_node_pairs_are_fresh(self) -> None:
        """None of the new node SPEC/DOC pairs are stale (status == ok)."""
        sample = {
            "code-indexer",
            "route-extraction",
            "test-mapping",
            "sync-check",
            "snapshot",
            "ci-gate",
            "config-check",
            "branch-protection",
            "site-generation",
            "graph-loader",
            "contracts",
            "sdl",
            "context-builder",
            "doc-indexer",
            "db",
            "git-activity",
            "health",
            "mcp-tools",
            "bd-seam",
        }
        stale = [
            p
            for p in self._sync_pairs()
            if str(p["ref_id"]) in sample and p["status"] != "ok"
        ]
        assert stale == [], stale


# ---------------------------------------------------------------------------
# exempt stays minimal + honest (only the 4 seeded globs)
# ---------------------------------------------------------------------------


class TestExemptMinimal:
    """No new module was hidden via the exempt list — it stays the minimal 4 globs."""

    def test_exempt_is_exactly_the_four_seeded_globs(self) -> None:
        """The live module-coverage exempt list is exactly the 4 honest globs."""
        rules = [r for r in load_rules(RULES_PATH) if isinstance(r, ModuleCoverageRule)]
        assert len(rules) == 1
        exempt = set(rules[0].exempt)
        assert exempt == {
            "**/__init__.py",
            "**/__main__.py",
            "**/onboarding/config_reader.py",
            "**/onboarding/presets.py",
        }, exempt

    def test_no_real_module_glob_added_to_exempt(self) -> None:
        """The exempt list adds NO broad real-module glob (no silent shadow hideout).

        A directory-wide or wildcard module glob would let real code escape coverage.
        Only ``__init__``/``__main__`` (structural) + two named single files are allowed.
        """
        rules = [r for r in load_rules(RULES_PATH) if isinstance(r, ModuleCoverageRule)]
        for pat in rules[0].exempt:
            # No directory-wildcard over real modules (e.g. "**/application/*.py").
            assert not (pat.endswith("/*.py") or pat.endswith("/**")), pat
            assert "*" not in pat.rsplit("/", 1)[-1] or pat.endswith(
                ("__init__.py", "__main__.py")
            ), pat
