"""Tests for README/doc ingestion during bootstrap (BEAD-01)."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import yaml

if TYPE_CHECKING:
    from pathlib import Path


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_src_tree(tmp_path: Path) -> Path:
    """Create a multi-level src tree for bootstrap tests."""
    src = tmp_path / "src"
    src.mkdir()

    auth = src / "auth"
    auth.mkdir()
    (auth / "login.py").write_text("def login(): pass\n")
    models = auth / "models"
    models.mkdir()
    (models / "user.py").write_text("class User: pass\n")
    api = auth / "api"
    api.mkdir()
    (api / "routes.py").write_text("def get_users(): pass\n")

    billing = src / "billing"
    billing.mkdir()
    (billing / "invoice.py").write_text("def create_invoice(): pass\n")

    utils = src / "utils"
    utils.mkdir()
    (utils / "helpers.py").write_text("def format_date(): pass\n")

    return src


# ---------------------------------------------------------------------------
# _ingest_readme — unit tests
# ---------------------------------------------------------------------------


class TestIngestReadme:
    """Tests for _ingest_readme() function."""

    def test_extracts_first_paragraph_from_readme(self, tmp_path: Path) -> None:
        """_ingest_readme extracts the first non-heading paragraph from README.md."""
        (tmp_path / "README.md").write_text(
            "# My Project\n\nA powerful web framework for building APIs.\n\nMore text here.\n"
        )
        from beadloom.onboarding.scanner import _ingest_readme

        result = _ingest_readme(tmp_path)
        assert result["readme_description"] == "A powerful web framework for building APIs."

    def test_skips_heading_lines(self, tmp_path: Path) -> None:
        """_ingest_readme skips lines starting with # to find the first paragraph."""
        (tmp_path / "README.md").write_text(
            "# My Project\n## Overview\n### Details\n\nActual description here.\n"
        )
        from beadloom.onboarding.scanner import _ingest_readme

        result = _ingest_readme(tmp_path)
        assert result["readme_description"] == "Actual description here."

    def test_detects_tech_stack_keywords_case_insensitive(self, tmp_path: Path) -> None:
        """_ingest_readme detects tech keywords in a case-insensitive way."""
        (tmp_path / "README.md").write_text(
            "# My Project\n\nBuilt with Python and React using Docker containers.\n"
        )
        from beadloom.onboarding.scanner import _ingest_readme

        result = _ingest_readme(tmp_path)
        tech = result["tech_stack"]
        assert isinstance(tech, list)
        assert "python" in tech
        assert "react" in tech
        assert "docker" in tech

    def test_extracts_architecture_notes(self, tmp_path: Path) -> None:
        """_ingest_readme extracts content from ARCHITECTURE.md if present."""
        (tmp_path / "README.md").write_text("# Project\n\nSome project.\n")
        (tmp_path / "ARCHITECTURE.md").write_text(
            "# Architecture\n\nThis system uses a microservices pattern "
            "with event-driven communication between services.\n"
        )
        from beadloom.onboarding.scanner import _ingest_readme

        result = _ingest_readme(tmp_path)
        assert "architecture_notes" in result
        assert "microservices pattern" in result["architecture_notes"]

    def test_handles_missing_files_gracefully(self, tmp_path: Path) -> None:
        """_ingest_readme returns empty dict when no doc files exist."""
        from beadloom.onboarding.scanner import _ingest_readme

        result = _ingest_readme(tmp_path)
        assert result == {}

    def test_reads_docs_readme_as_fallback(self, tmp_path: Path) -> None:
        """_ingest_readme reads docs/README.md when no root README.md exists."""
        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "README.md").write_text("# Docs\n\nDocumentation for the project.\n")
        from beadloom.onboarding.scanner import _ingest_readme

        result = _ingest_readme(tmp_path)
        assert result["readme_description"] == "Documentation for the project."

    def test_architecture_notes_truncated_to_500_chars(self, tmp_path: Path) -> None:
        """Architecture notes are truncated to 500 chars of non-heading content."""
        (tmp_path / "README.md").write_text("# Project\n\nA project.\n")
        long_content = "x" * 600
        (tmp_path / "ARCHITECTURE.md").write_text(f"# Architecture\n\n{long_content}\n")
        from beadloom.onboarding.scanner import _ingest_readme

        result = _ingest_readme(tmp_path)
        assert len(result["architecture_notes"]) <= 500

    def test_tech_stack_uses_word_boundaries(self, tmp_path: Path) -> None:
        """Tech keywords are matched with word boundaries, not substrings."""
        (tmp_path / "README.md").write_text("# Project\n\nExpression handling library.\n")
        from beadloom.onboarding.scanner import _ingest_readme

        result = _ingest_readme(tmp_path)
        # "expression" contains "rest" as substring but should NOT match
        tech = result.get("tech_stack", [])
        assert "rest" not in tech


# ---------------------------------------------------------------------------
# bootstrap_project — readme ingestion integration
# ---------------------------------------------------------------------------


class TestBootstrapReadmeIntegration:
    """Tests for _ingest_readme integration in bootstrap_project."""

    def test_bootstrap_stores_readme_data_in_extra(self, tmp_path: Path) -> None:
        """bootstrap_project stores readme data in root node's extra field."""
        (tmp_path / "README.md").write_text(
            "# Test Project\n\nA test project built with Python and Docker.\n"
        )
        _make_src_tree(tmp_path)

        from beadloom.onboarding.scanner import bootstrap_project

        result = bootstrap_project(tmp_path)
        root = result["nodes"][0]
        assert "extra" in root
        extra = json.loads(root["extra"])
        assert "readme_description" in extra
        assert "tech_stack" in extra

    def test_bootstrap_uses_readme_description_in_summary(self, tmp_path: Path) -> None:
        """bootstrap_project updates root node summary with readme description."""
        (tmp_path / "README.md").write_text("# Test Project\n\nA test project for unit testing.\n")
        (tmp_path / "pyproject.toml").write_text('[project]\nname = "testproj"\n')
        _make_src_tree(tmp_path)

        from beadloom.onboarding.scanner import bootstrap_project

        result = bootstrap_project(tmp_path)
        root = result["nodes"][0]
        assert "A test project for unit testing." in root["summary"]
        assert "testproj" in root["summary"]

    def test_bootstrap_truncates_long_description(self, tmp_path: Path) -> None:
        """Root node summary is truncated to 100 chars when description is long."""
        long_desc = "A" * 120
        (tmp_path / "README.md").write_text(f"# Test\n\n{long_desc}\n")
        _make_src_tree(tmp_path)

        from beadloom.onboarding.scanner import bootstrap_project

        result = bootstrap_project(tmp_path)
        root = result["nodes"][0]
        # The summary is "project_name: desc..." — the desc part is truncated
        # total desc portion should be at most 100 chars (97 + "...")
        assert "..." in root["summary"]

    def test_bootstrap_includes_tech_stack_in_summary(self, tmp_path: Path) -> None:
        """Root node summary mentions key technologies if detected."""
        (tmp_path / "README.md").write_text(
            "# My App\n\nA web application built with modern tools.\n\n"
            "Uses Python, React, and Docker for deployment.\n"
        )
        (tmp_path / "pyproject.toml").write_text('[project]\nname = "myapp"\n')
        _make_src_tree(tmp_path)

        from beadloom.onboarding.scanner import bootstrap_project

        result = bootstrap_project(tmp_path)
        root = result["nodes"][0]
        # Tech stack should be mentioned in the summary
        summary = root["summary"]
        assert "Python" in summary or "python" in summary.lower()

    def test_bootstrap_no_readme_no_readme_extra(self, tmp_path: Path) -> None:
        """bootstrap_project without README does not add readme fields to extra."""
        _make_src_tree(tmp_path)

        from beadloom.onboarding.scanner import bootstrap_project

        result = bootstrap_project(tmp_path)
        root = result["nodes"][0]
        if "extra" in root:
            extra = json.loads(root["extra"])
            assert "tech_stack" not in extra
            assert "summary" not in extra

    def test_bootstrap_readme_data_in_yaml(self, tmp_path: Path) -> None:
        """README data is persisted in the services.yml YAML file."""
        (tmp_path / "README.md").write_text("# Project\n\nA cool project using Python.\n")
        _make_src_tree(tmp_path)

        from beadloom.onboarding.scanner import bootstrap_project

        bootstrap_project(tmp_path)
        graph_dir = tmp_path / ".beadloom" / "_graph"
        data = yaml.safe_load((graph_dir / "services.yml").read_text())
        root = data["nodes"][0]
        assert "extra" in root
        extra = json.loads(root["extra"])
        assert "python" in extra["tech_stack"]
