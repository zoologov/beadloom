"""Self-checks of this repository's graph, rules and code structure (BDL-074 A3).

Moved out of ``tests/test_bead15_s3b_coverage.py``;
the product tests of the same code stay there.
Everything here asserts on this repository's own tree, so it carries the
``self_check`` marker by its folder (see ``tests/conftest.py``).
"""

from __future__ import annotations

import json
import sqlite3
from typing import TYPE_CHECKING

import pytest
from click.testing import CliRunner

from beadloom.graph.rule_engine import (
    ModuleCoverageRule,
    evaluate_module_coverage_rules,
    load_rules,
)
from beadloom.infrastructure.db import create_schema
from beadloom.onboarding.graph_files import each_graph_file
from beadloom.services.cli import main
from tests.support.repository_root import REPO_ROOT

if TYPE_CHECKING:
    from pathlib import Path

RULES_PATH = REPO_ROOT / ".beadloom" / "_graph" / "rules.yml"


def _load_real_nodes(root: Path) -> dict[str, dict[str, object]]:
    """Load *root*'s graph DIRECTORY's nodes into ``{ref_id: node_dict}`` (no DB).

    *root* is the self-check snapshot, so the nodes are read from the same copy
    whose index the caller reads (BDL-074 A2).

    The directory rather than one file since BDL-UX #265 split this repository's
    graph into one file per node. `each_graph_file` owns the codec and the skip
    policy, so neither is restated here.
    """
    nodes: dict[str, dict[str, object]] = {}
    for _path, data in each_graph_file(root / ".beadloom" / "_graph"):
        for node in data.get("nodes") or []:
            if isinstance(node, dict) and node.get("ref_id"):
                nodes[str(node["ref_id"])] = node
    return nodes


class TestErrorLevelRegressionGuard:
    """The promoted (error) coverage-lint must FAIL the gate on a new shadow module.

    This is the entire point of S3b: once every module is classified, the rule is
    promoted warn -> error so any *future* uncovered module breaks CI. The dev's
    tests prove the clean tree exits 0; these prove the gate bites otherwise.
    """


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


class TestSiteGenerationCluster:
    """The portal's modules form one package, covered by the single site-generation node."""

    def test_all_nine_site_modules_exist_on_disk(self, self_check_snapshot: Path) -> None:
        """Sanity: the portal package lives under application/, and nothing is left beside it.

        BDL-059 S4 decomposed the former ``site_dashboard.py`` into a package, and
        BDL-076 K1 (``beadloom-ujzb.2``) moved every portal module out of
        ``application/`` into ``application/site/``, whose single owner is the
        ``site-generation`` node: eleven modules plus the ``dashboard/`` package.
        BDL-076 A3 (``beadloom-7091``) added ``repository_link.py``, the twelfth.
        BDL-076 B1 (``beadloom-dfwt``) added ``scaffold.py`` and ``site_config.py``,
        the portal's shipped files and its identity: fourteen.
        ``beadloom-ujzb.11`` added ``markdown_links.py``, the one rule for a link in
        the project's own text on a portal page: fifteen.
        BDL-076 B2 (``beadloom-qki6``) added ``pages_workflow.py``, the GitHub Pages
        workflow that publishes the portal: sixteen.
        ``beadloom-ujzb.12`` added ``markdown_code.py``, where a project's Markdown
        holds code, and ``project_text.py``, the one path project text takes onto a
        page, shown as written rather than compiled as a Vue template: eighteen.
        ``beadloom-ujzb.13`` added ``pages_base.py``, whether the portal's base can
        match the path GitHub Pages serves the project under: nineteen.
        BDL-076 B4 (``beadloom-ujzb.8``) added ``forge_routes.py``, the routes a
        forge serves a path under and which forge serves a host: twenty.
        ``beadloom-ujzb.21`` replaced the hand-written ``markdown_code.py`` with
        markdown-it-py read as VitePress reads Markdown: ``vitepress_markdown.py`` (the
        parser), ``markdown_positions.py`` (where each token's text came from),
        ``markdown_source.py`` (the located reading) and ``raw_html.py`` (raw HTML as
        Vue's tokenizer reads it): twenty-three.
        The test keeps its historical name so its collected id is unchanged.
        """
        app_dir = self_check_snapshot / "src" / "beadloom" / "application"
        site_dir = app_dir / "site"
        assert (site_dir / "__init__.py").is_file()
        names = {p.name for p in site_dir.glob("*.py")} - {"__init__.py"}
        assert "generate.py" in names
        assert len(names) == 23, names
        assert (site_dir / "dashboard").is_dir()
        assert sorted(p.name for p in app_dir.glob("site*.py")) == []

    def test_no_site_module_is_flagged_by_coverage(self, self_check_snapshot: Path) -> None:
        """No module of the portal package appears as a module-coverage finding (live repo)."""
        runner = CliRunner()
        result = runner.invoke(
            main,
            ["lint", "--format", "json", "--project", str(self_check_snapshot), "--no-reindex"],
        )
        payload = json.loads(result.stdout)
        coverage_files = {
            str(v["file_path"])
            for v in payload["violations"]
            if v["rule_name"] == "module-coverage"
        }
        site_files = sorted(
            (self_check_snapshot / "src" / "beadloom" / "application" / "site").rglob("*.py")
        )
        assert site_files
        for path in site_files:
            rel = path.relative_to(self_check_snapshot).as_posix()
            assert rel not in coverage_files, rel

    def test_site_generation_node_round_trips_reindex(self, self_check_snapshot: Path) -> None:
        """`ctx site-generation` resolves the node post-reindex (round-trip through DB)."""
        runner = CliRunner()
        result = runner.invoke(
            main, ["ctx", "site-generation", "--project", str(self_check_snapshot), "--json"]
        )
        assert result.exit_code == 0, result.output
        bundle = json.loads(result.stdout)
        assert bundle["focus"]["ref_id"] == "site-generation"
        assert bundle["focus"]["kind"] == "feature"


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
    def test_new_feature_node_ctx_resolves(self, ref_id: str, self_check_snapshot: Path) -> None:
        """Each new S3b feature node resolves through `ctx` to a feature bundle."""
        runner = CliRunner()
        result = runner.invoke(
            main, ["ctx", ref_id, "--project", str(self_check_snapshot), "--json"]
        )
        assert result.exit_code == 0, result.output
        bundle = json.loads(result.stdout)
        assert bundle["focus"]["ref_id"] == ref_id
        assert bundle["focus"]["kind"] == "feature"

    @pytest.mark.parametrize("ref_id", NEW_COMPONENTS)
    def test_new_component_node_ctx_resolves(self, ref_id: str, self_check_snapshot: Path) -> None:
        """Each new S3b component node resolves through `ctx` to a component bundle."""
        runner = CliRunner()
        result = runner.invoke(
            main, ["ctx", ref_id, "--project", str(self_check_snapshot), "--json"]
        )
        assert result.exit_code == 0, result.output
        bundle = json.loads(result.stdout)
        assert bundle["focus"]["ref_id"] == ref_id
        assert bundle["focus"]["kind"] == "component"

    def test_component_nodes_part_of_a_parent(self, self_check_snapshot: Path) -> None:
        """Every new component declares a part_of edge to a domain/service (validates)."""
        part_of_srcs = {
            str(edge["src"])
            for _path, data in each_graph_file(self_check_snapshot / ".beadloom" / "_graph")
            for edge in (data.get("edges") or [])
            if isinstance(edge, dict) and edge.get("kind") == "part_of"
        }
        for ref_id in self.NEW_COMPONENTS:
            assert ref_id in part_of_srcs, f"{ref_id} has no part_of parent"


class TestAnnotationNodeConsistency:
    """Annotations and nodes must agree: no dangling annotation, no unannotated source.

    The source of truth for "what annotations exist" is what the code indexer
    actually recorded in ``code_symbols.annotations`` — NOT a naive source regex
    (which would wrongly match literal ``# beadloom:feature=REF_ID`` example text
    inside docstrings/help strings). The coverage lint consumes the indexed
    annotations, so this is the correct, behavior-aligned consistency check.
    """

    def _annotation_values(self, root: Path) -> dict[str, set[str]]:
        """Read indexed feature/component annotation values from the live DB."""
        db_path = root / ".beadloom" / "beadloom.db"
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

    def test_every_annotation_value_names_a_declared_node(self, self_check_snapshot: Path) -> None:
        """No annotation points at a ref_id that is not a declared node (no dangling)."""
        nodes = _load_real_nodes(self_check_snapshot)
        values = self._annotation_values(self_check_snapshot)
        all_annotated = values["feature"] | values["component"]
        missing = {v for v in all_annotated if v not in nodes}
        assert missing == set(), f"annotations point at non-existent nodes: {missing}"

    def test_feature_annotations_match_feature_kind(self, self_check_snapshot: Path) -> None:
        """A `feature=` annotation names a node of kind feature (not component/domain)."""
        nodes = _load_real_nodes(self_check_snapshot)
        values = self._annotation_values(self_check_snapshot)
        for ref_id in values["feature"]:
            assert nodes[ref_id].get("kind") == "feature", ref_id

    def test_component_annotations_match_component_kind(self, self_check_snapshot: Path) -> None:
        """A `component=` annotation names a node of kind component."""
        nodes = _load_real_nodes(self_check_snapshot)
        values = self._annotation_values(self_check_snapshot)
        for ref_id in values["component"]:
            assert nodes[ref_id].get("kind") == "component", ref_id

    def test_file_source_nodes_have_matching_annotation_or_are_the_source(
        self, self_check_snapshot: Path
    ) -> None:
        """Every new file-source node's file carries the matching annotation.

        For the S3b file-source feature/component nodes, the source module must
        either carry the matching ``feature=``/``component=`` annotation (covered by
        annotation) — the architecture-model policy that there is no node whose
        source file silently lacks the annotation.
        """
        import re

        nodes = _load_real_nodes(self_check_snapshot)
        new_ids = set(TestNewNodesResolve.NEW_FEATURES) | set(TestNewNodesResolve.NEW_COMPONENTS)
        unannotated: list[str] = []
        for ref_id in new_ids:
            node = nodes[ref_id]
            source = str(node.get("source", ""))
            if not source or source.endswith("/"):
                continue  # dir sources covered separately
            src_path = self_check_snapshot / source
            if not src_path.is_file():
                unannotated.append(f"{ref_id}: source missing {source}")
                continue
            text = src_path.read_text(encoding="utf-8", errors="ignore")
            kind = str(node["kind"])
            ann_re = re.compile(rf"#\s*beadloom:{kind}={re.escape(ref_id)}\b")
            if not ann_re.search(text):
                unannotated.append(f"{ref_id}: {source} lacks # beadloom:{kind}={ref_id}")
        assert unannotated == [], unannotated


class TestExemptMinimal:
    """No new module was hidden via the exempt list — every entry is named and argued."""

    def test_exempt_is_exactly_the_seeded_globs(self) -> None:
        """The live module-coverage exempt list is exactly the honest entries.

        This guard exists to catch a module being quietly excused rather than
        classified. Any change here must be a deliberate edit with a written
        reason in `rules.yml`, which is why the set is pinned literally.

        `**/graph/rule_engine.py` was added when the `rule-engine` node was
        repointed from that 84-line back-compat shim to the `rules/` PACKAGE
        where the engine actually lives — sourcing the node at the shim made
        every symbol count, node page and size limit describe the shim instead
        of the engine (BDL-UX #157). The shim keeps its
        `# beadloom:feature=rule-engine` annotation, so its MEMBERSHIP is still
        recorded; the exemption covers only the fact that it has no code of its
        own (0 symbols).
        """
        rules = [r for r in load_rules(RULES_PATH) if isinstance(r, ModuleCoverageRule)]
        assert len(rules) == 1
        exempt = set(rules[0].exempt)
        assert exempt == {
            "**/__init__.py",
            "**/__main__.py",
            "**/onboarding/config_reader.py",
            "**/onboarding/presets.py",
            "**/graph/rule_engine.py",
        }, exempt

    def test_the_shim_exemption_stays_true_to_its_reason(self, self_check_snapshot: Path) -> None:
        """`rule_engine.py` is exempt BECAUSE it is a pure re-export shim.

        The other named exemptions were argued on the seeded criterion (few
        symbols, internal-only glue) and are left to it. This one was argued on
        a stronger claim — that the file holds no code of its own — so the claim
        is pinned: if anyone ever adds a symbol to the shim, the exemption stops
        being honest and this fails rather than silently hiding real code.
        """
        import sqlite3

        conn = sqlite3.connect(self_check_snapshot / ".beadloom" / "beadloom.db")
        try:
            count = conn.execute(
                "SELECT count(*) FROM code_symbols WHERE file_path = ?",
                ("src/beadloom/graph/rule_engine.py",),
            ).fetchone()[0]
        finally:
            conn.close()

        assert count == 0, (
            f"src/beadloom/graph/rule_engine.py holds {count} symbols but is "
            "exempt as a pure re-export shim — either move that code into the "
            "`rules/` package or drop the exemption"
        )

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
