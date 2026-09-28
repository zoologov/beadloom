"""An incremental reindex re-extracts imports, so ``reindex && lint`` sees a fresh break.

#142 (S2 regressions): an incremental ``reindex`` never re-extracted imports, so
``lint --strict`` on the documented ``reindex && lint`` loop reported a clean
boundary while the working tree held a real violation. Written to bite on the
pre-fix code: see the bead comments for the measured before/after. Split out of
``tests/test_s2_lying_checks.py`` (BDL-074 ``beadloom-2mj3.7``).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from beadloom.application.reindex import incremental_reindex, reindex
from beadloom.graph.linter import lint as run_lint
from tests.support.boundary_break_project import (
    ALPHA_CLEAN,
    ALPHA_VIOLATING,
    make_project,
    query,
    services_yml,
)

if TYPE_CHECKING:
    from pathlib import Path


class TestIncrementalReindexRefreshesImports:
    """The documented ``reindex && lint`` loop must catch a fresh violation."""

    def test_violation_added_to_existing_file_is_caught(self, tmp_path: Path) -> None:
        """Edit a file into a boundary break -> incremental reindex -> lint sees it."""
        project = make_project(tmp_path)
        reindex(project)
        assert run_lint(project).violations == [], "baseline must be clean"

        (project / "src" / "app" / "alpha" / "service.py").write_text(ALPHA_VIOLATING)
        incremental_reindex(project)

        result = run_lint(project)
        indexed = query(project, "SELECT file_path, import_path FROM code_imports")
        assert [v.rule_name for v in result.violations] == ["alpha-no-beta-import"], (
            f"incremental reindex left the import graph stale: {indexed}"
        )

    def test_violation_in_a_new_file_is_caught(self, tmp_path: Path) -> None:
        """An ADDED file's imports reach the index too, not only a changed one."""
        project = make_project(tmp_path)
        reindex(project)

        (project / "src" / "app" / "alpha" / "extra.py").write_text(ALPHA_VIOLATING)
        incremental_reindex(project)

        result = run_lint(project)
        assert [v.file_path for v in result.violations] == ["src/app/alpha/extra.py"]

    def test_removed_import_stops_being_reported(self, tmp_path: Path) -> None:
        """The refresh works in both directions — a fixed violation goes away."""
        project = make_project(tmp_path)
        (project / "src" / "app" / "alpha" / "service.py").write_text(ALPHA_VIOLATING)
        reindex(project)
        assert run_lint(project).violations != []

        (project / "src" / "app" / "alpha" / "service.py").write_text(ALPHA_CLEAN)
        incremental_reindex(project)

        assert run_lint(project).violations == []
        assert query(project, "SELECT file_path FROM code_imports") == []

    def test_deleted_file_drops_its_imports_and_edge(self, tmp_path: Path) -> None:
        """Deleting the offending file removes both its imports and its edge."""
        project = make_project(tmp_path)
        (project / "src" / "app" / "alpha" / "service.py").write_text(ALPHA_VIOLATING)
        reindex(project)
        assert ("alpha", "beta") in query(
            project, "SELECT src_ref_id, dst_ref_id FROM edges WHERE kind = 'depends_on'"
        )

        (project / "src" / "app" / "alpha" / "service.py").unlink()
        incremental_reindex(project)

        assert query(project, "SELECT file_path FROM code_imports") == []
        assert (
            query(project, "SELECT src_ref_id, dst_ref_id FROM edges WHERE kind = 'depends_on'")
            == []
        )

    def test_declared_edge_survives_an_incremental_refresh(self, tmp_path: Path) -> None:
        """Refreshing DERIVED edges must not delete a YAML-declared one."""
        project = make_project(tmp_path)
        graph = project / ".beadloom" / "_graph" / "services.yml"
        graph.write_text(
            services_yml(edges="edges:\n  - src: beta\n    dst: alpha\n    kind: depends_on\n")
        )
        reindex(project)
        assert ("beta", "alpha") in query(
            project, "SELECT src_ref_id, dst_ref_id FROM edges WHERE kind = 'depends_on'"
        )

        (project / "src" / "app" / "alpha" / "service.py").write_text(ALPHA_VIOLATING)
        incremental_reindex(project)

        assert ("beta", "alpha") in query(
            project, "SELECT src_ref_id, dst_ref_id FROM edges WHERE kind = 'depends_on'"
        ), "a declared depends_on edge was collateral damage of the derived-edge refresh"
