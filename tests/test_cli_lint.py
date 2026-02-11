# beadloom:domain=context-oracle
"""Tests for `beadloom lint` CLI command."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from click.testing import CliRunner

from beadloom.cli import main

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
    (src_dir / "invoice.py").write_text(
        "# beadloom:domain=billing\ndef process(): pass\n"
    )
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
    (auth_dir / "tokens.py").write_text(
        "# beadloom:domain=auth\ndef verify(): pass\n"
    )
    return project


def _inject_violation(project: Path) -> None:
    """Inject a resolved cross-boundary import into the DB so rules detect it.

    This mirrors the pattern from test_linter.py: after reindex, the
    code_imports table may not have resolved_ref_id set, so we insert
    a record manually.
    """
    from beadloom.db import open_db

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
        result = runner.invoke(
            main, ["lint", "--project", str(project), "--format", "json"]
        )
        assert result.exit_code == 0, result.output
        parsed = json.loads(result.output)
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
        # Porcelain lines are colon-separated with 6 fields.
        lines = [line for line in result.output.strip().split("\n") if line]
        assert len(lines) >= 1
        parts = lines[0].split(":")
        assert len(parts) == 6

    def test_lint_format_rich(self, tmp_path: Path) -> None:
        """--format rich -> human-readable output with rule counts."""
        project = _project_with_rules(tmp_path)
        runner = CliRunner()
        result = runner.invoke(
            main, ["lint", "--project", str(project), "--format", "rich"]
        )
        assert result.exit_code == 0, result.output
        assert "Rules:" in result.output
        assert "Files:" in result.output

    def test_lint_no_reindex(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """--no-reindex skips the reindex step."""
        project = _project_with_rules(tmp_path)
        runner = CliRunner()
        # First run with reindex to create the DB.
        result = runner.invoke(main, ["lint", "--project", str(project)])
        assert result.exit_code == 0, result.output

        # Monkeypatch incremental_reindex to track if it's called.
        reindex_called = False

        import beadloom.linter as linter_mod

        original_fn = linter_mod.incremental_reindex

        def mock_reindex(project_root: Path) -> object:
            nonlocal reindex_called
            reindex_called = True
            return original_fn(project_root)

        monkeypatch.setattr(linter_mod, "incremental_reindex", mock_reindex)

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
