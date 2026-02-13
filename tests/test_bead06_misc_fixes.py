"""Tests for BEAD-06 misc fixes (sub-issues #9, #10, #12, #13)."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import patch

import yaml

if TYPE_CHECKING:
    from pathlib import Path


# ---------------------------------------------------------------------------
# Sub-issue #9: Generic summaries — detect framework patterns
# ---------------------------------------------------------------------------


class TestFrameworkSummaries:
    """Dir-level framework detection produces descriptive summaries."""

    def test_django_app_detected(self, tmp_path: Path) -> None:
        """Directory containing apps.py produces 'Django app: ...' summary."""
        from beadloom.onboarding.scanner import _detect_framework_summary

        dir_path = tmp_path / "users"
        dir_path.mkdir()
        (dir_path / "apps.py").write_text("class UsersConfig: pass\n")

        result = _detect_framework_summary(dir_path, "users", "domain", 5)
        assert result == "Django app: users (5 files)"

    def test_react_component_tsx_detected(self, tmp_path: Path) -> None:
        """Directory containing index.tsx produces 'React component: ...' summary."""
        from beadloom.onboarding.scanner import _detect_framework_summary

        dir_path = tmp_path / "header"
        dir_path.mkdir()
        (dir_path / "index.tsx").write_text("export default function Header() {}\n")

        result = _detect_framework_summary(dir_path, "header", "feature", 3)
        assert result == "React component: header (3 files)"

    def test_react_component_jsx_detected(self, tmp_path: Path) -> None:
        """Directory containing index.jsx produces 'React component: ...' summary."""
        from beadloom.onboarding.scanner import _detect_framework_summary

        dir_path = tmp_path / "sidebar"
        dir_path.mkdir()
        (dir_path / "index.jsx").write_text("export default function Sidebar() {}\n")

        result = _detect_framework_summary(dir_path, "sidebar", "feature", 2)
        assert result == "React component: sidebar (2 files)"

    def test_python_package_with_setup_py(self, tmp_path: Path) -> None:
        """Directory with __init__.py + setup.py produces 'Python package: ...'."""
        from beadloom.onboarding.scanner import _detect_framework_summary

        dir_path = tmp_path / "mylib"
        dir_path.mkdir()
        (dir_path / "__init__.py").write_text("")
        (dir_path / "setup.py").write_text("from setuptools import setup\nsetup()\n")

        result = _detect_framework_summary(dir_path, "mylib", "domain", 10)
        assert result == "Python package: mylib (10 files)"

    def test_python_package_with_pyproject(self, tmp_path: Path) -> None:
        """Directory with __init__.py + pyproject.toml produces 'Python package: ...'."""
        from beadloom.onboarding.scanner import _detect_framework_summary

        dir_path = tmp_path / "core"
        dir_path.mkdir()
        (dir_path / "__init__.py").write_text("")
        (dir_path / "pyproject.toml").write_text("[project]\nname = 'core'\n")

        result = _detect_framework_summary(dir_path, "core", "domain", 8)
        assert result == "Python package: core (8 files)"

    def test_containerized_service_detected(self, tmp_path: Path) -> None:
        """Directory containing Dockerfile produces 'Containerized service: ...'."""
        from beadloom.onboarding.scanner import _detect_framework_summary

        dir_path = tmp_path / "api"
        dir_path.mkdir()
        (dir_path / "Dockerfile").write_text("FROM python:3.11\n")

        result = _detect_framework_summary(dir_path, "api", "service", 7)
        assert result == "Containerized service: api (7 files)"

    def test_default_fallback(self, tmp_path: Path) -> None:
        """Directory without framework markers uses default format."""
        from beadloom.onboarding.scanner import _detect_framework_summary

        dir_path = tmp_path / "utils"
        dir_path.mkdir()

        result = _detect_framework_summary(dir_path, "utils", "service", 4)
        assert result == "Service: utils (4 files)"

    def test_summary_under_120_chars(self, tmp_path: Path) -> None:
        """Framework summaries stay under 120 characters."""
        from beadloom.onboarding.scanner import _detect_framework_summary

        long_name = "a" * 80
        dir_path = tmp_path / long_name
        dir_path.mkdir()
        (dir_path / "apps.py").write_text("")

        result = _detect_framework_summary(dir_path, long_name, "domain", 999)
        assert len(result) <= 120

    def test_bootstrap_uses_framework_summary(self, tmp_path: Path) -> None:
        """Bootstrap project uses framework-aware summaries for Django apps."""
        from beadloom.onboarding import bootstrap_project

        src = tmp_path / "src"
        src.mkdir()
        users = src / "users"
        users.mkdir()
        (users / "apps.py").write_text("class UsersConfig: pass\n")
        (users / "models.py").write_text("class User: pass\n")

        result = bootstrap_project(tmp_path, preset_name="monolith")
        users_node = next(n for n in result["nodes"] if n["ref_id"] == "users")
        assert "Django app:" in users_node["summary"]


# ---------------------------------------------------------------------------
# Sub-issue #10: Parenthesized ref_ids
# ---------------------------------------------------------------------------


class TestParenthesizedRefIds:
    """Parenthesized directory names have parentheses stripped from ref_id."""

    def test_sanitize_ref_id_strips_parens(self) -> None:
        """_sanitize_ref_id strips parentheses."""
        from beadloom.onboarding.scanner import _sanitize_ref_id

        assert _sanitize_ref_id("(tabs)") == "tabs"
        assert _sanitize_ref_id("normal") == "normal"
        assert _sanitize_ref_id("(foo)bar") == "foobar"

    def test_bootstrap_strips_parens_from_ref_id(self, tmp_path: Path) -> None:
        """Directory named (tabs) gets ref_id = 'tabs' in bootstrap."""
        from beadloom.onboarding import bootstrap_project

        app = tmp_path / "app"
        app.mkdir()
        tabs = app / "(tabs)"
        tabs.mkdir()
        (tabs / "index.tsx").write_text("export default function Tabs() {}\n")

        result = bootstrap_project(tmp_path, preset_name="monolith")
        ref_ids = {n["ref_id"] for n in result["nodes"]}
        assert "tabs" in ref_ids
        assert "(tabs)" not in ref_ids

    def test_child_ref_id_strips_parens(self, tmp_path: Path) -> None:
        """Child of parenthesized dir also has clean ref_id."""
        from beadloom.onboarding import bootstrap_project

        src = tmp_path / "src"
        src.mkdir()
        parent = src / "(app)"
        parent.mkdir()
        child = parent / "(screens)"
        child.mkdir()
        (child / "home.tsx").write_text("export default function Home() {}\n")
        # Need a direct file in (app) for it to appear as a cluster
        (parent / "index.tsx").write_text("export default {}\n")

        result = bootstrap_project(tmp_path, preset_name="monolith")
        ref_ids = {n["ref_id"] for n in result["nodes"]}
        # Parent should be "app", child should be "app-screens"
        assert "app" in ref_ids
        assert "app-screens" in ref_ids
        assert "(app)" not in ref_ids
        assert "(screens)" not in ref_ids

    def test_part_of_edges_use_sanitized_ids(self, tmp_path: Path) -> None:
        """part_of edges use sanitized ref_ids."""
        from beadloom.onboarding import bootstrap_project

        app = tmp_path / "app"
        app.mkdir()
        tabs = app / "(tabs)"
        tabs.mkdir()
        (tabs / "index.tsx").write_text("export default function Tabs() {}\n")

        result = bootstrap_project(tmp_path, preset_name="monolith")
        edge_srcs = {e["src"] for e in result["edges"]}
        edge_dsts = {e["dst"] for e in result["edges"]}
        all_refs = edge_srcs | edge_dsts
        for ref in all_refs:
            assert "(" not in ref
            assert ")" not in ref


# ---------------------------------------------------------------------------
# Sub-issue #12: reindex ignores new parser availability
# ---------------------------------------------------------------------------


class TestParserFingerprint:
    """Incremental reindex detects new parser availability via fingerprint."""

    def test_parser_fingerprint_stored_after_full_reindex(self, tmp_path: Path) -> None:
        """Full reindex stores parser fingerprint in file_index."""
        from beadloom.infrastructure.db import open_db
        from beadloom.infrastructure.reindex import reindex

        # Setup minimal project
        graph_dir = tmp_path / ".beadloom" / "_graph"
        graph_dir.mkdir(parents=True)
        (tmp_path / "docs").mkdir()
        (tmp_path / "src").mkdir()

        reindex(tmp_path)

        db_path = tmp_path / ".beadloom" / "beadloom.db"
        conn = open_db(db_path)
        row = conn.execute(
            "SELECT hash FROM file_index WHERE path = '__parser_fingerprint__'"
        ).fetchone()
        assert row is not None
        assert len(row["hash"]) > 0
        conn.close()

    def test_changed_fingerprint_triggers_full_reindex(self, tmp_path: Path) -> None:
        """When supported_extensions() changes, incremental_reindex does full reindex."""
        from beadloom.infrastructure.reindex import (
            _compute_parser_fingerprint,
            incremental_reindex,
        )

        # Setup minimal project
        graph_dir = tmp_path / ".beadloom" / "_graph"
        graph_dir.mkdir(parents=True)
        (graph_dir / "g.yml").write_text(
            "nodes:\n  - ref_id: N1\n    kind: domain\n    summary: N1\n"
        )
        (tmp_path / "docs").mkdir()
        (tmp_path / "src").mkdir()

        # First run: populates file_index + fingerprint
        incremental_reindex(tmp_path)

        # Simulate new parser installed: mock supported_extensions to return
        # a different set (add .java), which changes the fingerprint
        original_fp = _compute_parser_fingerprint()

        with patch(
            "beadloom.infrastructure.reindex.supported_extensions",
            return_value=frozenset({".py", ".ts", ".tsx", ".js", ".jsx", ".go", ".rs", ".java"}),
        ):
            new_fp = _compute_parser_fingerprint()
            # Fingerprints should differ
            assert new_fp != original_fp

            # Incremental reindex should detect the change and do a full reindex
            result = incremental_reindex(tmp_path)
            # Full reindex loads nodes; incremental with no changes would set nothing_changed
            assert result.nodes_loaded == 1

    def test_same_fingerprint_does_not_trigger_full_reindex(self, tmp_path: Path) -> None:
        """When parsers haven't changed, incremental reindex stays incremental."""
        from beadloom.infrastructure.reindex import incremental_reindex

        # Setup minimal project
        graph_dir = tmp_path / ".beadloom" / "_graph"
        graph_dir.mkdir(parents=True)
        (graph_dir / "g.yml").write_text(
            "nodes:\n  - ref_id: N1\n    kind: domain\n    summary: N1\n"
        )
        (tmp_path / "docs").mkdir()
        (tmp_path / "src").mkdir()

        # First run
        incremental_reindex(tmp_path)

        # Second run — same parsers, nothing changed
        result = incremental_reindex(tmp_path)
        assert result.nothing_changed is True


# ---------------------------------------------------------------------------
# Sub-issue #13: Bootstrap skeleton count — created vs skipped
# ---------------------------------------------------------------------------


class TestBootstrapSkeletonCount:
    """CLI output distinguishes created vs skipped skeleton counts."""

    def test_all_new_skeletons_shows_created_only(self, tmp_path: Path) -> None:
        """When no pre-existing docs, output shows only 'N skeletons created'."""
        from click.testing import CliRunner

        from beadloom.services.cli import main

        src = tmp_path / "src"
        src.mkdir()
        auth = src / "auth"
        auth.mkdir()
        (auth / "login.py").write_text("def login(): pass\n")

        runner = CliRunner()
        result = runner.invoke(main, ["init", "--bootstrap", "--project", str(tmp_path)])
        assert result.exit_code == 0, result.output
        assert "skeletons created" in result.output
        # Should NOT mention skipped when all are new
        assert "skipped" not in result.output

    def test_some_skipped_shows_both_counts(self, tmp_path: Path) -> None:
        """When some docs pre-exist, output shows 'N created, M skipped'."""
        from click.testing import CliRunner

        from beadloom.services.cli import main

        src = tmp_path / "src"
        src.mkdir()
        auth = src / "auth"
        auth.mkdir()
        (auth / "login.py").write_text("def login(): pass\n")

        # Pre-create architecture.md so it will be skipped
        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "architecture.md").write_text("# Existing architecture doc\n")

        runner = CliRunner()
        result = runner.invoke(main, ["init", "--bootstrap", "--project", str(tmp_path)])
        assert result.exit_code == 0, result.output
        assert "skeletons created" in result.output
        assert "skipped (pre-existing)" in result.output

    def test_generate_skeletons_returns_counts(self, tmp_path: Path) -> None:
        """generate_skeletons returns both files_created and files_skipped."""
        from beadloom.onboarding.doc_generator import generate_skeletons

        graph_dir = tmp_path / ".beadloom" / "_graph"
        graph_dir.mkdir(parents=True)
        data = {
            "nodes": [
                {"ref_id": "proj", "kind": "service", "summary": "Root: proj", "source": ""},
                {
                    "ref_id": "auth",
                    "kind": "domain",
                    "summary": "Domain: auth",
                    "source": "src/auth/",
                },
            ],
            "edges": [
                {"src": "auth", "dst": "proj", "kind": "part_of"},
            ],
        }
        (graph_dir / "services.yml").write_text(
            yaml.dump(data, default_flow_style=False),
            encoding="utf-8",
        )

        # First run: creates files
        result1 = generate_skeletons(tmp_path)
        assert result1["files_created"] >= 1
        assert result1["files_skipped"] == 0

        # Second run: all files exist
        result2 = generate_skeletons(tmp_path)
        assert result2["files_created"] == 0
        assert result2["files_skipped"] >= 1
