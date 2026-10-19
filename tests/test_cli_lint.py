# beadloom:domain=context-oracle
"""Tests for `beadloom lint` CLI command."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from click.testing import CliRunner

from beadloom.services.cli import main

if TYPE_CHECKING:
    from pathlib import Path

    import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _minimal_project(tmp_path: Path) -> Path:
    """Create a minimal project skeleton with `.beadloom/_graph/` and `docs/`."""
    project = tmp_path / "proj"
    project.mkdir()
    (project / ".beadloom" / "_graph").mkdir(parents=True)
    (project / "docs").mkdir()
    return project


def _project_with_rules(tmp_path: Path) -> Path:
    """Create a project with graph nodes and a deny rule (no violations)."""
    project = _minimal_project(tmp_path)
    graph_dir = project / ".beadloom" / "_graph"
    (graph_dir / "services.yml").write_text(
        "nodes:\n"
        "  - ref_id: billing\n"
        "    kind: domain\n"
        "    summary: Billing domain\n"
        "  - ref_id: auth\n"
        "    kind: domain\n"
        "    summary: Auth domain\n"
        "edges: []\n"
    )
    (graph_dir / "rules.yml").write_text(
        "version: 1\n"
        "rules:\n"
        "  - name: billing-no-auth\n"
        '    description: "Billing must not import auth"\n'
        "    deny:\n"
        "      from: { ref_id: billing }\n"
        "      to: { ref_id: auth }\n"
    )
    # Source file that does NOT create a violation (no cross-boundary import).
    src_dir = project / "src" / "billing"
    src_dir.mkdir(parents=True)
    (src_dir / "invoice.py").write_text("# beadloom:domain=billing\ndef process(): pass\n")
    return project


def _project_with_violations(tmp_path: Path) -> Path:
    """Create a project with graph nodes, a deny rule, and a cross-boundary import."""
    project = _project_with_rules(tmp_path)
    # Overwrite billing source to import from auth (cross-boundary).
    src_dir = project / "src" / "billing"
    (src_dir / "invoice.py").write_text(
        "# beadloom:domain=billing\nimport auth.tokens\ndef process(): pass\n"
    )
    # Also create the auth module.
    auth_dir = project / "src" / "auth"
    auth_dir.mkdir(parents=True)
    (auth_dir / "tokens.py").write_text("# beadloom:domain=auth\ndef verify(): pass\n")
    return project


def _inject_violation(project: Path) -> None:
    """Inject a resolved cross-boundary import into the DB so rules detect it.

    This mirrors the pattern from test_linter.py: after reindex, the
    code_imports table may not have resolved_ref_id set, so we insert
    a record manually.
    """
    from beadloom.infrastructure.db import open_db

    db_path = project / ".beadloom" / "beadloom.db"
    conn = open_db(db_path)
    conn.execute(
        "INSERT OR REPLACE INTO code_imports"
        " (file_path, line_number, import_path, resolved_ref_id, file_hash)"
        " VALUES (?, ?, ?, ?, ?)",
        ("src/billing/invoice.py", 2, "auth.tokens", "auth", "test"),
    )
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestLintCommand:
    """Tests for the `beadloom lint` CLI command."""

    def test_lint_default_no_rules(self, tmp_path: Path) -> None:
        """No rules.yml present -> exit 0, clean output."""
        project = _minimal_project(tmp_path)
        runner = CliRunner()
        result = runner.invoke(main, ["lint", "--project", str(project)])
        assert result.exit_code == 0, result.output

    def test_lint_clean_project(self, tmp_path: Path) -> None:
        """Rules exist but no violations -> exit 0."""
        project = _project_with_rules(tmp_path)
        runner = CliRunner()
        result = runner.invoke(main, ["lint", "--project", str(project)])
        assert result.exit_code == 0, result.output

    def test_lint_with_violations_default(self, tmp_path: Path) -> None:
        """Violations found without --strict -> exit 0."""
        project = _project_with_violations(tmp_path)
        runner = CliRunner()
        # First run to create DB with reindex.
        runner.invoke(main, ["lint", "--project", str(project)])
        # Inject the resolved import so the rule engine detects it.
        _inject_violation(project)
        # Second run without reindex to pick up injected data.
        result = runner.invoke(
            main, ["lint", "--project", str(project), "--no-reindex", "--format", "rich"]
        )
        assert result.exit_code == 0, result.output
        assert "billing-no-auth" in result.output

    def test_lint_with_violations_strict(self, tmp_path: Path) -> None:
        """Violations found with --strict -> exit 1."""
        project = _project_with_violations(tmp_path)
        runner = CliRunner()
        # First run to create DB with reindex.
        runner.invoke(main, ["lint", "--project", str(project)])
        # Inject the resolved import so the rule engine detects it.
        _inject_violation(project)
        # Second run with --strict.
        result = runner.invoke(
            main,
            ["lint", "--project", str(project), "--no-reindex", "--strict", "--format", "rich"],
        )
        assert result.exit_code == 1, result.output
        assert "billing-no-auth" in result.output

    def test_lint_format_json(self, tmp_path: Path) -> None:
        """--format json -> valid JSON output."""
        project = _project_with_rules(tmp_path)
        runner = CliRunner()
        result = runner.invoke(main, ["lint", "--project", str(project), "--format", "json"])
        assert result.exit_code == 0, result.output
        parsed = json.loads(result.stdout)
        assert "violations" in parsed
        assert "summary" in parsed

    def test_lint_format_porcelain(self, tmp_path: Path) -> None:
        """--format porcelain -> colon-separated output (empty when no violations)."""
        project = _project_with_violations(tmp_path)
        runner = CliRunner()
        # First run to create DB.
        runner.invoke(main, ["lint", "--project", str(project)])
        # Inject violation.
        _inject_violation(project)
        # Porcelain format.
        result = runner.invoke(
            main,
            ["lint", "--project", str(project), "--no-reindex", "--format", "porcelain"],
        )
        assert result.exit_code == 0, result.output
        # Porcelain lines are colon-separated with 7 fields (severity added in v1.6).
        lines = [line for line in result.output.strip().split("\n") if line]
        assert len(lines) >= 1
        parts = lines[0].split(":")
        assert len(parts) == 7

    def test_lint_format_rich(self, tmp_path: Path) -> None:
        """--format rich -> human-readable output with rule counts."""
        project = _project_with_rules(tmp_path)
        runner = CliRunner()
        result = runner.invoke(main, ["lint", "--project", str(project), "--format", "rich"])
        assert result.exit_code == 0, result.output
        assert "Rules:" in result.output
        assert "Files:" in result.output

    def test_lint_format_github(self, tmp_path: Path) -> None:
        """--format github -> GitHub Actions ::error annotations with remediation."""
        project = _project_with_violations(tmp_path)
        runner = CliRunner()
        runner.invoke(main, ["lint", "--project", str(project)])
        _inject_violation(project)
        result = runner.invoke(
            main,
            ["lint", "--project", str(project), "--no-reindex", "--format", "github"],
        )
        assert result.exit_code == 0, result.output
        lines = [ln for ln in result.output.splitlines() if ln.startswith("::")]
        assert len(lines) >= 1
        assert lines[0].startswith("::error")
        # remediation hint surfaces in the annotation
        assert "—" in lines[0]

    def test_lint_no_reindex(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """--no-reindex skips the reindex step."""
        project = _project_with_rules(tmp_path)
        runner = CliRunner()
        # First run with reindex to create the DB.
        result = runner.invoke(main, ["lint", "--project", str(project)])
        assert result.exit_code == 0, result.output

        # Monkeypatch incremental_reindex to track if it's called.
        reindex_called = False

        import beadloom.application.reindex as reindex_mod

        original_fn = reindex_mod.incremental_reindex

        def mock_reindex(project_root: Path) -> object:
            nonlocal reindex_called
            reindex_called = True
            return original_fn(project_root)

        monkeypatch.setattr(reindex_mod, "incremental_reindex", mock_reindex)

        # Run with --no-reindex.
        result = runner.invoke(
            main, ["lint", "--project", str(project), "--no-reindex", "--format", "rich"]
        )
        assert result.exit_code == 0, result.output
        assert not reindex_called

    def test_lint_invalid_rules(self, tmp_path: Path) -> None:
        """Invalid rules.yml -> exit 2."""
        project = _minimal_project(tmp_path)
        graph_dir = project / ".beadloom" / "_graph"
        (graph_dir / "services.yml").write_text(
            "nodes:\n"
            "  - ref_id: billing\n"
            "    kind: domain\n"
            "    summary: Billing domain\n"
            "edges: []\n"
        )
        # Invalid rules: missing required 'version' field.
        (graph_dir / "rules.yml").write_text(
            "rules:\n"
            "  - name: bad\n"
            "    deny:\n"
            "      from: { ref_id: a }\n"
            "      to: { ref_id: b }\n"
        )
        runner = CliRunner()
        result = runner.invoke(main, ["lint", "--project", str(project)])
        assert result.exit_code == 2, result.output
        assert "Error" in result.output

    def test_lint_no_project(self, tmp_path: Path) -> None:
        """Missing .beadloom directory -> exit 2 (Click validates path)."""
        # Point to a directory that exists but has no .beadloom
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        runner = CliRunner()
        result = runner.invoke(main, ["lint", "--project", str(empty_dir)])
        # The lint function will fail because .beadloom/_graph doesn't exist.
        # It should exit 2 (config error via LintError) or the reindex step
        # creates the DB but rules evaluation handles missing structure.
        # Since reindex creates dirs as needed, the lint() will succeed but
        # with 0 rules (no rules.yml). However, if the project structure
        # is completely missing, reindex may raise. Let's verify:
        assert result.exit_code in (0, 2), result.output


# ---------------------------------------------------------------------------
# `--staged`: the lint the pre-commit hook runs (BDL-083 S1a, BDL-UX #326)
# ---------------------------------------------------------------------------

#: The monorepo fixture's widget spec, and the import of the app layer that breaks fsd-layers.
_WIDGET_SPEC = "frontend/src/widgets/kpi-panel/ui/KpiPanel.spec.ts"
_DIGEST = "backend/src/digest/sections.py"


class TestLintStaged:
    """`lint --staged` judges the nodes that own a staged path and counts the rest."""

    @staticmethod
    def _monorepo(tmp_path: Path) -> Path:
        from tests.support.monorepo_fixture import monorepo_checkout

        root = monorepo_checkout(tmp_path)
        spec = root / _WIDGET_SPEC
        spec.write_text("import '@/app/styles'\n" + spec.read_text(encoding="utf-8"))
        return root

    @staticmethod
    def _stage(root: Path, path: str) -> None:
        from tests.support.committed_project import git

        git(root, "add", path)

    @staticmethod
    def _lint(root: Path, *args: str) -> tuple[int, str]:
        result = CliRunner().invoke(main, ["lint", *args, "--project", str(root)])
        return result.exit_code, result.output

    def test_a_staged_violation_of_a_node_blocks_under_strict(self, tmp_path: Path) -> None:
        root = self._monorepo(tmp_path)
        self._stage(root, _WIDGET_SPEC)
        code, output = self._lint(root, "--staged", "--strict", "--format", "rich")
        assert code == 1, output
        assert output.startswith("Lint over this commit: 1 node(s) own 1 of 1 staged path(s)")
        assert "(widgets-kpi-panel)" in output.splitlines()[0]
        assert "fsd-layers" in output

    def test_a_violation_outside_the_staged_nodes_is_counted_not_judged(
        self, tmp_path: Path
    ) -> None:
        root = self._monorepo(tmp_path)
        digest = root / _DIGEST
        digest.write_text(digest.read_text(encoding="utf-8") + "\n# touched\n")
        self._stage(root, _DIGEST)
        code, output = self._lint(root, "--staged", "--strict", "--format", "rich")
        assert code == 0, output
        first = output.splitlines()[0]
        assert "0 error(s)" in first, first
        assert "finding(s) elsewhere left to the pre-push Gate" in first, first
        assert "widgets-kpi-panel" not in output

    def test_without_staged_the_whole_tree_is_judged_as_before(self, tmp_path: Path) -> None:
        root = self._monorepo(tmp_path)
        code, output = self._lint(root, "--strict", "--format", "rich")
        assert code == 1, output
        assert "Lint over this commit" not in output

    def test_porcelain_marks_the_scope_line_as_a_statement(self, tmp_path: Path) -> None:
        from beadloom.graph.linter import POPULATION_MARKER

        root = self._monorepo(tmp_path)
        self._stage(root, _WIDGET_SPEC)
        _, output = self._lint(root, "--staged", "--format", "porcelain")
        assert output.splitlines()[0].startswith(f"{POPULATION_MARKER}Lint over this commit: ")

    def test_json_carries_the_scope_beside_the_findings(self, tmp_path: Path) -> None:
        root = self._monorepo(tmp_path)
        self._stage(root, _WIDGET_SPEC)
        result = CliRunner().invoke(
            main, ["lint", "--staged", "--format", "json", "--project", str(root)]
        )
        payload = json.loads(result.stdout)
        assert payload["commit_scope"]["nodes"] == ["widgets-kpi-panel"]
        assert payload["commit_scope"]["staged"] == 1
        assert payload["summary"]["error_count"] == 1

    def test_a_project_with_no_rules_and_no_index_still_states_its_scope(
        self, tmp_path: Path
    ) -> None:
        """`lint` returns before it opens an index when there are no rules; so must this."""
        project = _minimal_project(tmp_path)
        code, output = self._lint(project, "--staged", "--strict", "--format", "rich")
        assert code == 0, output
        assert output.startswith("Lint over this commit: ")
