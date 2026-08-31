"""Regression test for BDL-UX-Issues #71 — clean bootstrap out-of-the-box.

A fresh ``beadloom init --bootstrap`` must pass ``beadloom lint --strict``
with zero violations.  Previously the bootstrap classifier nested ``feature``
directories (api/rest/graphql) inside ``service`` directories (core/tasks),
while the generated ``feature-needs-domain`` rule required a ``domain`` parent.
With architecture rules restored to ``severity: error`` (BEAD-03), that made a
freshly bootstrapped repo fail its own lint gate on day one.

The fix renames the generated rule to ``feature-needs-parent`` with an empty
``has_edge_to`` matcher, so features are valid under either a domain or a
service parent.  These tests reproduce the feature-under-service layout and
assert lint is genuinely clean.

BDL-067 (BDL-UX #192) added the second layout.  The assertion in this file was
always the right one — ``not has_errors`` *and* ``violations == []`` — but every
source directory in the #71 fixture has code-bearing subdirectories, so the
bootstrap's cluster loop attached every node it wrote and the fallback branch
was never entered.  A layout that enters it shipped a domain with no ``part_of``
edge for two major releases while this file stayed green.  The lint assertion is
now parametrised over both layouts, so the branch that forgot the edge is under
the check that was written to catch exactly this.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from beadloom.application.reindex import incremental_reindex
from beadloom.graph.linter import lint
from beadloom.onboarding.scanner import bootstrap_project

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path


def _make_feature_under_service_project(root: Path) -> None:
    """Create a project where feature dirs are nested inside service dirs.

    ``core`` and ``tasks`` match ``_SERVICE_DIRS`` (classified ``service``);
    their children ``rest``/``graphql`` match ``_FEATURE_DIRS`` (classified
    ``feature``).  This is the exact #71 layout that produced a feature whose
    only ``part_of`` edge points at a service, not a domain.
    """
    (root / "core" / "rest").mkdir(parents=True)
    (root / "core" / "graphql").mkdir(parents=True)
    (root / "tasks" / "api").mkdir(parents=True)
    (root / "billing" / "models").mkdir(parents=True)
    (root / "core" / "__init__.py").write_text("x = 1\n")
    (root / "core" / "rest" / "api.py").write_text("def route():\n    return 1\n")
    (root / "core" / "graphql" / "schema.py").write_text("def handler():\n    return 1\n")
    (root / "tasks" / "__init__.py").write_text("x = 1\n")
    (root / "tasks" / "api" / "jobs.py").write_text("def run():\n    return 1\n")
    (root / "billing" / "__init__.py").write_text("x = 1\n")
    (root / "billing" / "models" / "user.py").write_text("class User:\n    pass\n")


def _make_flat_single_source_dir_project(root: Path) -> None:
    """Create a project whose only source file sits directly in its source dir.

    The shape BDL-UX #192 was reported against, and the one the fixture above
    cannot reach: ``src`` holds a module and no code-bearing subdirectory, so
    ``_cluster_with_children`` yields nothing and the bootstrap takes its
    fallback branch — one node per source dir at the preset's default kind
    (``domain`` under MONOLITH).  Before BDL-067 that node left the bootstrap
    with no ``part_of`` edge, and ``domain-needs-parent`` — written by the same
    command, one step later — failed over it.
    """
    (root / "pyproject.toml").write_text(
        '[project]\nname = "flat-app"\nversion = "0.1.0"\n', encoding="utf-8"
    )
    src = root / "src"
    src.mkdir(parents=True)
    (src / "app.py").write_text("def run() -> int:\n    return 1\n", encoding="utf-8")


class TestCleanBootstrapLint:
    """A fresh bootstrap passes ``lint --strict`` with zero violations."""

    @pytest.mark.parametrize(
        "make_project",
        [_make_feature_under_service_project, _make_flat_single_source_dir_project],
        ids=["feature-under-service", "flat-single-source-dir"],
    )
    def test_bootstrap_lint_is_clean(
        self, tmp_path: Path, make_project: Callable[[Path], None]
    ) -> None:
        """Bootstrap -> lint -> zero violations, on each layout that reaches a branch.

        The first leg is #71 (features nested under services).  The second is
        BDL-UX #192 (a flat source directory), and it is the leg this assertion
        could not make before BDL-067: pointed only at the nested layout, the
        check passed while a virgin bootstrap wrote a graph that failed its own
        ``domain-needs-parent``.
        """
        make_project(tmp_path)

        bootstrap_project(tmp_path, preset_name="monolith")

        result = lint(tmp_path, reindex=incremental_reindex)

        # The whole point of #71: no error-severity violations means
        # `lint --strict` would exit 0.
        assert not result.has_errors, [
            (v.rule_name, v.from_ref_id, v.message) for v in result.violations
        ]
        assert result.violations == []

    def test_feature_node_actually_under_service(self, tmp_path: Path) -> None:
        """Guard: the layout really does place a feature part_of a service.

        If this stops holding, the lint assertion above would pass trivially
        and the regression would no longer be exercised.
        """
        import yaml

        _make_feature_under_service_project(tmp_path)
        bootstrap_project(tmp_path, preset_name="monolith")

        graph = yaml.safe_load(
            # UTF-8 stated rather than inherited: this artifact is generated by us and read
            # back by other tools, so its codec is a contract - `read_text()` alone would
            # use whatever the image's locale says (BDL-061.42).
            (tmp_path / ".beadloom" / "_graph" / "services.yml").read_text(encoding="utf-8")
        )
        kinds = {n["ref_id"]: n["kind"] for n in graph["nodes"]}
        feature_ids = {ref for ref, kind in kinds.items() if kind == "feature"}
        assert feature_ids, "expected at least one feature node"

        # At least one feature's part_of edge points at a service (not a domain).
        edges = graph.get("edges", [])
        feature_to_service = [
            e
            for e in edges
            if e["kind"] == "part_of"
            and e["src"] in feature_ids
            and kinds.get(e["dst"]) == "service"
        ]
        assert feature_to_service, (
            "expected a feature whose part_of edge targets a service "
            f"(graph kinds={kinds}, edges={edges})"
        )

    def test_flat_layout_reaches_the_branch_that_forgot_the_edge(
        self, tmp_path: Path
    ) -> None:
        """Guard + regression: the flat leg writes a domain, and it is parented.

        The first two assertions are the guard.  If a preset change stopped
        classifying a bare source directory as a ``domain``, the flat leg of the
        lint test above would pass without exercising #192 at all, which is the
        failure mode this whole file exists to avoid.  The third assertion is
        the regression: it names the edge, so a fix that satisfied the linter by
        some other route would still have to say where the domain belongs.
        """
        _make_flat_single_source_dir_project(tmp_path)

        result = bootstrap_project(tmp_path, preset_name="monolith")

        kinds = {n["ref_id"]: n["kind"] for n in result["nodes"]}
        assert kinds.get("src") == "domain", kinds
        assert kinds.get("flat-app") == "service", kinds
        part_of = [(e["src"], e["dst"]) for e in result["edges"] if e["kind"] == "part_of"]
        assert part_of == [("src", "flat-app")], result["edges"]

    def test_rule_is_feature_needs_parent(self, tmp_path: Path) -> None:
        """The generated rule is the parent-agnostic ``feature-needs-parent``."""
        import yaml

        _make_feature_under_service_project(tmp_path)
        bootstrap_project(tmp_path, preset_name="monolith")

        rules = yaml.safe_load(
            (tmp_path / ".beadloom" / "_graph" / "rules.yml").read_text()
        )
        rule_names = {r["name"] for r in rules["rules"]}
        assert "feature-needs-parent" in rule_names
        assert "feature-needs-domain" not in rule_names
        feature_rule = next(
            r for r in rules["rules"] if r["name"] == "feature-needs-parent"
        )
        assert feature_rule["require"]["has_edge_to"] == {}
