"""Tests for doc skeleton generation in init flow (BEAD-10).

Covers:
- interactive_init() prompts for doc generation after reindex
- interactive_init() skips doc generation when user declines
- interactive_init() generates docs by default
- Doc coverage > 0% after init with doc generation
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

if TYPE_CHECKING:
    from pathlib import Path


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_src_tree(tmp_path: Path) -> None:
    """Create a multi-level src tree for bootstrap tests."""
    src = tmp_path / "src"
    src.mkdir()

    auth = src / "auth"
    auth.mkdir()
    (auth / "login.py").write_text("def login(): pass\n")
    models = auth / "models"
    models.mkdir()
    (models / "user.py").write_text("class User: pass\n")

    billing = src / "billing"
    billing.mkdir()
    (billing / "invoice.py").write_text("def create_invoice(): pass\n")


# ---------------------------------------------------------------------------
# interactive_init — doc generation prompt
# ---------------------------------------------------------------------------


class TestInteractiveInitDocGeneration:
    """Tests for doc skeleton generation in interactive_init()."""

    def test_interactive_init_generates_docs_when_accepted(
        self, tmp_path: Path
    ) -> None:
        """Interactive init generates doc skeletons when user accepts."""
        from beadloom.onboarding import interactive_init

        _make_src_tree(tmp_path)

        # Responses: "bootstrap" (mode), "yes" (graph review), "yes" (doc gen)
        with (
            patch(
                "rich.prompt.Prompt.ask",
                side_effect=["bootstrap", "yes"],
            ),
            patch(
                "rich.prompt.Confirm.ask",
                return_value=True,
            ),
            patch("rich.console.Console"),
        ):
            result = interactive_init(tmp_path)

        assert result["mode"] == "bootstrap"
        # Docs should have been generated.
        docs_dir = tmp_path / "docs"
        assert docs_dir.exists()
        # At least architecture.md should exist.
        assert (docs_dir / "architecture.md").exists()
        # Result should record doc generation.
        assert "docs" in result
        assert result["docs"]["files_created"] > 0

    def test_interactive_init_skips_docs_when_declined(
        self, tmp_path: Path
    ) -> None:
        """Interactive init skips doc generation when user declines."""
        from beadloom.onboarding import interactive_init

        _make_src_tree(tmp_path)

        with (
            patch(
                "rich.prompt.Prompt.ask",
                side_effect=["bootstrap", "yes"],
            ),
            patch(
                "rich.prompt.Confirm.ask",
                return_value=False,
            ),
            patch("rich.console.Console"),
        ):
            result = interactive_init(tmp_path)

        assert result["mode"] == "bootstrap"
        # Docs dir should not have architecture.md.
        docs_dir = tmp_path / "docs"
        arch_file = docs_dir / "architecture.md"
        assert not arch_file.exists()
        # Result should record skipped doc generation.
        assert "docs" not in result or result.get("docs", {}).get("files_created", 0) == 0

    def test_interactive_init_doc_coverage_after_generation(
        self, tmp_path: Path
    ) -> None:
        """Doc coverage should be > 0% after init with doc generation."""
        from beadloom.onboarding import interactive_init

        _make_src_tree(tmp_path)

        with (
            patch(
                "rich.prompt.Prompt.ask",
                side_effect=["bootstrap", "yes"],
            ),
            patch(
                "rich.prompt.Confirm.ask",
                return_value=True,
            ),
            patch("rich.console.Console"),
        ):
            result = interactive_init(tmp_path)

        assert result["mode"] == "bootstrap"

        # Check that at least one doc was created for a node.
        import sqlite3

        db_path = tmp_path / ".beadloom" / "beadloom.db"
        assert db_path.exists()
        conn = sqlite3.connect(str(db_path))
        nodes_count = conn.execute("SELECT count(*) FROM nodes").fetchone()[0]
        # After reindex with docs, there should be docs linked to nodes.
        docs_count = conn.execute("SELECT count(*) FROM docs").fetchone()[0]
        conn.close()

        assert nodes_count > 0
        assert docs_count > 0

    def test_interactive_init_import_mode_no_doc_prompt(
        self, tmp_path: Path
    ) -> None:
        """Import mode does not prompt for doc generation (no graph to generate from)."""
        from beadloom.onboarding import interactive_init

        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "readme.md").write_text("# Hello\n\nWorld.\n")

        confirm_mock = MagicMock()
        with (
            patch("rich.prompt.Prompt.ask", return_value="import"),
            patch("rich.prompt.Confirm.ask", confirm_mock),
            patch("rich.console.Console"),
        ):
            result = interactive_init(tmp_path)

        assert result["mode"] == "import"
        # Confirm.ask should NOT have been called for doc generation.
        confirm_mock.assert_not_called()

    def test_interactive_init_edit_review_no_doc_prompt(
        self, tmp_path: Path
    ) -> None:
        """Choosing 'edit' during graph review skips doc generation prompt."""
        from beadloom.onboarding import interactive_init

        _make_src_tree(tmp_path)

        confirm_mock = MagicMock()
        with (
            patch(
                "rich.prompt.Prompt.ask",
                side_effect=["bootstrap", "edit"],
            ),
            patch("rich.prompt.Confirm.ask", confirm_mock),
            patch("rich.console.Console"),
        ):
            result = interactive_init(tmp_path)

        assert result.get("review") == "edit"
        # Should not have prompted for doc generation.
        confirm_mock.assert_not_called()


# ---------------------------------------------------------------------------
# CLI init --bootstrap — doc generation (non-interactive)
# ---------------------------------------------------------------------------


class TestInitBootstrapDocGeneration:
    """Tests that init --bootstrap always generates docs (non-interactive mode)."""

    def test_init_bootstrap_generates_docs(self, tmp_path: Path) -> None:
        """init --bootstrap generates doc skeletons automatically."""
        from click.testing import CliRunner

        from beadloom.services.cli import main

        _make_src_tree(tmp_path)
        runner = CliRunner()
        result = runner.invoke(main, ["init", "--bootstrap", "--project", str(tmp_path)])
        assert result.exit_code == 0, result.output

        # Docs should have been created.
        docs_dir = tmp_path / "docs"
        assert docs_dir.exists()
        assert (docs_dir / "architecture.md").exists()
        # Output should mention docs.
        assert "Docs:" in result.output

    def test_init_bootstrap_doc_coverage_gt_zero(self, tmp_path: Path) -> None:
        """After init --bootstrap, doc coverage should be > 0%."""
        from click.testing import CliRunner

        from beadloom.services.cli import main

        _make_src_tree(tmp_path)
        runner = CliRunner()
        result = runner.invoke(main, ["init", "--bootstrap", "--project", str(tmp_path)])
        assert result.exit_code == 0, result.output

        # Check DB for docs.
        import sqlite3

        db_path = tmp_path / ".beadloom" / "beadloom.db"
        assert db_path.exists()
        conn = sqlite3.connect(str(db_path))
        nodes_count = conn.execute("SELECT count(*) FROM nodes").fetchone()[0]
        docs_count = conn.execute("SELECT count(*) FROM docs").fetchone()[0]
        conn.close()

        assert nodes_count > 0
        assert docs_count > 0
