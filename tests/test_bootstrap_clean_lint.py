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
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from beadloom.application.reindex import incremental_reindex
from beadloom.graph.linter import lint
from beadloom.onboarding.scanner import bootstrap_project

if TYPE_CHECKING:
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


class TestCleanBootstrapLint:
    """A fresh bootstrap passes ``lint --strict`` with zero violations."""

    def test_feature_under_service_lint_is_clean(self, tmp_path: Path) -> None:
        """Bootstrap (features under services) -> lint -> zero violations."""
        _make_feature_under_service_project(tmp_path)

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
            (tmp_path / ".beadloom" / "_graph" / "services.yml").read_text()
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
