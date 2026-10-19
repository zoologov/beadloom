"""The monorepo fixture holds the adopter's layout and indexes green (BDL-083 S1g).

Bead ``beadloom-483w``. The fixture is what S1 to S4 of BDL-083 measure on, so its shape is
asserted here rather than assumed there: a later edit that drops the backend's lockfile or a
spec file beside the code fails this module, not a measurement that quietly stops reproducing
its issue.

The node set below is written out from the layout, independently of the graph files that
declare it. Which node a test file binds to is not asserted: the backend's unit test binds by
the mirror of its path, and that binding is the measurement of BDL-UX #339, owned by a later
slice.
"""

from __future__ import annotations

import sqlite3
from typing import TYPE_CHECKING

from click.testing import CliRunner

from beadloom.services.cli import main
from tests.support.monorepo_fixture import MONOREPO, monorepo_checkout

if TYPE_CHECKING:
    from pathlib import Path

#: Every node of the fixture, by ``ref_id`` and kind: the product, its two projects, the
#: backend's two domains and one feature, and one node per frontend slice or segment.
DECLARED_NODES = {
    ("metrics-desk", "service"),
    ("backend", "service"),
    ("frontend", "service"),
    ("digest", "domain"),
    ("file-history", "domain"),
    ("application-digest", "feature"),
    ("app-styles", "component"),
    ("pages-dashboard", "component"),
    ("widgets-kpi-panel", "component"),
    ("features-filter-metrics", "component"),
    ("entities-metric", "component"),
    ("shared-lib", "component"),
}

#: The two spec files beside the frontend code, and the backend's one test under its root.
TEST_FILES = {
    "backend/tests/unit/digest/test_sections.py",
    "frontend/src/app/styles/base.spec.ts",
    "frontend/src/widgets/kpi-panel/ui/KpiPanel.spec.ts",
}


def _rows(root: Path, sql: str) -> set[tuple[str, ...]]:
    with sqlite3.connect(root / ".beadloom" / "beadloom.db") as conn:
        return {tuple(row) for row in conn.execute(sql)}


class TestTheFixtureHoldsTheAdoptersLayout:
    """The four traits of the adopter's repository the slices measure, each present."""

    def test_the_backend_is_a_python_project_below_the_root(self) -> None:
        assert (MONOREPO / "backend" / "pyproject.toml").is_file()
        assert (MONOREPO / "backend" / "uv.lock").is_file()
        assert not (MONOREPO / "pyproject.toml").exists()

    def test_the_pipeline_is_a_gitlab_pipeline_only(self) -> None:
        assert (MONOREPO / ".gitlab-ci.yml").is_file()
        assert not (MONOREPO / ".github").exists()

    def test_two_spec_files_sit_beside_the_frontend_code(self) -> None:
        specs = {
            path.relative_to(MONOREPO).as_posix()
            for path in (MONOREPO / "frontend" / "src").rglob("*.spec.ts")
        }

        assert specs == {name for name in TEST_FILES if name.startswith("frontend/")}

    def test_a_domain_and_a_feature_share_a_subpackage_name(self) -> None:
        source = MONOREPO / "backend" / "src"

        assert (source / "digest" / "sections.py").is_file()
        assert (source / "application" / "digest" / "sections.py").is_file()


class TestTheFixtureIndexes:
    """A reindex of the committed checkout is green and holds what the layout declares.

    The checkout is also clean under ``lint --strict`` and ``sync-check``, so a finding a
    later slice provokes on it is that slice's own and not the fixture's.
    """

    def test_the_reindex_exits_zero(self, tmp_path: Path) -> None:
        root = monorepo_checkout(tmp_path)

        result = CliRunner().invoke(main, ["reindex", "--project", str(root)])

        assert result.exit_code == 0, result.output

    def test_the_index_holds_the_declared_node_set(self, tmp_path: Path) -> None:
        root = monorepo_checkout(tmp_path)
        CliRunner().invoke(main, ["reindex", "--project", str(root)])

        assert _rows(root, "SELECT ref_id, kind FROM nodes") == DECLARED_NODES

    def test_the_index_reads_the_three_test_files(self, tmp_path: Path) -> None:
        root = monorepo_checkout(tmp_path)
        CliRunner().invoke(main, ["reindex", "--project", str(root)])

        assert {path for (path,) in _rows(root, "SELECT path FROM test_files")} == TEST_FILES

    def test_the_checkout_passes_lint_strict(self, tmp_path: Path) -> None:
        root = monorepo_checkout(tmp_path)
        CliRunner().invoke(main, ["reindex", "--project", str(root)])

        result = CliRunner().invoke(main, ["lint", "--strict", "--project", str(root)])

        assert result.exit_code == 0, result.output

    def test_the_checkout_has_no_stale_pair(self, tmp_path: Path) -> None:
        root = monorepo_checkout(tmp_path)
        CliRunner().invoke(main, ["reindex", "--project", str(root)])

        result = CliRunner().invoke(main, ["sync-check", "--project", str(root)])

        assert result.exit_code == 0, result.output
