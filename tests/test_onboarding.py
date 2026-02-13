"""Tests for beadloom.onboarding — project bootstrap and import."""

from __future__ import annotations

from typing import TYPE_CHECKING

import yaml

from beadloom.onboarding import (
    bootstrap_project,
    classify_doc,
    generate_agents_md,
    import_docs,
    interactive_init,
    scan_project,
    setup_mcp_auto,
)

if TYPE_CHECKING:
    from pathlib import Path


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_src_tree(tmp_path: Path) -> Path:
    """Create a multi-level src tree for bootstrap tests."""
    src = tmp_path / "src"
    src.mkdir()

    # Top-level: auth domain with models and api subdirs.
    auth = src / "auth"
    auth.mkdir()
    (auth / "login.py").write_text("def login(): pass\n")
    models = auth / "models"
    models.mkdir()
    (models / "user.py").write_text("class User: pass\n")
    api = auth / "api"
    api.mkdir()
    (api / "routes.py").write_text("def get_users(): pass\n")

    # Top-level: billing domain.
    billing = src / "billing"
    billing.mkdir()
    (billing / "invoice.py").write_text("def create_invoice(): pass\n")

    # Top-level: utils (utility dir).
    utils = src / "utils"
    utils.mkdir()
    (utils / "helpers.py").write_text("def format_date(): pass\n")

    return src


# ---------------------------------------------------------------------------
# scan_project
# ---------------------------------------------------------------------------


class TestScanProject:
    def test_detects_pyproject(self, tmp_path: Path) -> None:
        (tmp_path / "pyproject.toml").write_text("[project]\nname='test'\n")
        (tmp_path / "src").mkdir()
        result = scan_project(tmp_path)
        assert "pyproject.toml" in result["manifests"]

    def test_detects_package_json(self, tmp_path: Path) -> None:
        (tmp_path / "package.json").write_text('{"name": "test"}')
        result = scan_project(tmp_path)
        assert "package.json" in result["manifests"]

    def test_detects_source_dirs(self, tmp_path: Path) -> None:
        (tmp_path / "src").mkdir()
        (tmp_path / "lib").mkdir()
        result = scan_project(tmp_path)
        assert "src" in result["source_dirs"]
        assert "lib" in result["source_dirs"]

    def test_counts_files(self, tmp_path: Path) -> None:
        src = tmp_path / "src"
        src.mkdir()
        (src / "main.py").write_text("print('hello')")
        (src / "utils.py").write_text("pass")
        result = scan_project(tmp_path)
        assert result["file_count"] >= 2

    def test_empty_project(self, tmp_path: Path) -> None:
        result = scan_project(tmp_path)
        assert result["manifests"] == []
        assert result["source_dirs"] == []

    def test_detects_backend_frontend(self, tmp_path: Path) -> None:
        """backend/ and frontend/ are in the known source dirs list."""
        be = tmp_path / "backend"
        be.mkdir()
        (be / "manage.py").write_text("pass")
        fe = tmp_path / "frontend"
        fe.mkdir()
        (fe / "App.tsx").write_text("export default {}")
        result = scan_project(tmp_path)
        assert "backend" in result["source_dirs"]
        assert "frontend" in result["source_dirs"]

    def test_fallback_discovers_unknown_dirs(self, tmp_path: Path) -> None:
        """Dirs not in _SOURCE_DIRS are found via fallback scan."""
        custom = tmp_path / "myapp"
        custom.mkdir()
        (custom / "main.py").write_text("def main(): pass\n")
        result = scan_project(tmp_path)
        assert "myapp" in result["source_dirs"]
        assert result["file_count"] >= 1

    def test_fallback_skips_node_modules(self, tmp_path: Path) -> None:
        """node_modules should be skipped during fallback scan."""
        nm = tmp_path / "node_modules"
        nm.mkdir()
        (nm / "pkg.js").write_text("module.exports = {}")
        result = scan_project(tmp_path)
        assert "node_modules" not in result["source_dirs"]

    def test_detects_vue_files(self, tmp_path: Path) -> None:
        """Vue.js .vue files are counted as code."""
        fe = tmp_path / "frontend"
        fe.mkdir()
        (fe / "App.vue").write_text("<template><div/></template>")
        result = scan_project(tmp_path)
        assert result["file_count"] >= 1
        assert ".vue" in result["languages"]


# ---------------------------------------------------------------------------
# classify_doc
# ---------------------------------------------------------------------------


class TestClassifyDoc:
    def test_adr(self, tmp_path: Path) -> None:
        doc = tmp_path / "adr-001.md"
        doc.write_text("# ADR-001\n\n## Status: Accepted\n\n## Decision\nUse SQLite.\n")
        assert classify_doc(doc) == "adr"

    def test_feature(self, tmp_path: Path) -> None:
        doc = tmp_path / "feature.md"
        doc.write_text("# Feature\n\n## User story\nAs a user...\n")
        assert classify_doc(doc) == "feature"

    def test_architecture(self, tmp_path: Path) -> None:
        doc = tmp_path / "arch.md"
        doc.write_text("# Architecture\n\n## System design\nMicroservices.\n")
        assert classify_doc(doc) == "architecture"

    def test_other(self, tmp_path: Path) -> None:
        doc = tmp_path / "readme.md"
        doc.write_text("# README\n\nJust a readme.\n")
        assert classify_doc(doc) == "other"


# ---------------------------------------------------------------------------
# generate_agents_md
# ---------------------------------------------------------------------------


class TestGenerateAgentsMd:
    def test_creates_file(self, tmp_path: Path) -> None:
        path = generate_agents_md(tmp_path)
        assert path.exists()
        assert path == tmp_path / ".beadloom" / "AGENTS.md"

    def test_contains_mcp_tools(self, tmp_path: Path) -> None:
        generate_agents_md(tmp_path)
        content = (tmp_path / ".beadloom" / "AGENTS.md").read_text()
        assert "get_context" in content
        assert "sync_check" in content
        assert "list_nodes" in content

    def test_contains_instructions(self, tmp_path: Path) -> None:
        generate_agents_md(tmp_path)
        content = (tmp_path / ".beadloom" / "AGENTS.md").read_text()
        assert "Before starting work" in content
        assert "After changing code" in content
        assert "beadloom:feature=" in content

    def test_idempotent(self, tmp_path: Path) -> None:
        generate_agents_md(tmp_path)
        generate_agents_md(tmp_path)
        assert (tmp_path / ".beadloom" / "AGENTS.md").exists()


# ---------------------------------------------------------------------------
# bootstrap_project — basic
# ---------------------------------------------------------------------------


class TestBootstrapProject:
    def test_creates_graph_dir(self, tmp_path: Path) -> None:
        src = tmp_path / "src"
        src.mkdir()
        (src / "api.py").write_text("def handler():\n    pass\n")
        bootstrap_project(tmp_path)
        graph_dir = tmp_path / ".beadloom" / "_graph"
        assert graph_dir.is_dir()

    def test_creates_config(self, tmp_path: Path) -> None:
        (tmp_path / "src").mkdir()
        bootstrap_project(tmp_path)
        config = tmp_path / ".beadloom" / "config.yml"
        assert config.exists()

    def test_creates_agents_md(self, tmp_path: Path) -> None:
        (tmp_path / "src").mkdir()
        result = bootstrap_project(tmp_path)
        agents = tmp_path / ".beadloom" / "AGENTS.md"
        assert agents.exists()
        assert result["agents_md_created"] is True

    def test_creates_yaml_files(self, tmp_path: Path) -> None:
        src = tmp_path / "src"
        src.mkdir()
        services = src / "api"
        services.mkdir()
        (services / "__init__.py").write_text("")
        (services / "routes.py").write_text("def list_items():\n    pass\n")
        bootstrap_project(tmp_path)
        graph_dir = tmp_path / ".beadloom" / "_graph"
        yml_files = list(graph_dir.glob("*.yml"))
        assert len(yml_files) >= 1

    def test_generated_yaml_is_valid(self, tmp_path: Path) -> None:
        _make_src_tree(tmp_path)
        bootstrap_project(tmp_path)
        graph_dir = tmp_path / ".beadloom" / "_graph"
        for yml_path in graph_dir.glob("*.yml"):
            data = yaml.safe_load(yml_path.read_text())
            assert data is not None
            if "nodes" in data:
                for node in data["nodes"]:
                    assert "ref_id" in node
                    assert "kind" in node

    def test_idempotent(self, tmp_path: Path) -> None:
        (tmp_path / "src").mkdir()
        bootstrap_project(tmp_path)
        # Second call should not crash.
        bootstrap_project(tmp_path)


# ---------------------------------------------------------------------------
# bootstrap_project — preset-aware
# ---------------------------------------------------------------------------


class TestBootstrapPresets:
    """Tests for preset-aware bootstrap with multi-level scanning."""

    def test_monolith_top_dirs_are_domains(self, tmp_path: Path) -> None:
        _make_src_tree(tmp_path)
        result = bootstrap_project(tmp_path, preset_name="monolith")
        assert result["preset"] == "monolith"
        nodes = result["nodes"]
        top_names = {n["ref_id"] for n in nodes if "-" not in n["ref_id"]}
        # auth, billing → domain; utils → service (utility pattern)
        auth_node = next(n for n in nodes if n["ref_id"] == "auth")
        assert auth_node["kind"] == "domain"
        billing_node = next(n for n in nodes if n["ref_id"] == "billing")
        assert billing_node["kind"] == "domain"
        assert "auth" in top_names
        assert "billing" in top_names

    def test_monolith_child_models_are_entities(self, tmp_path: Path) -> None:
        _make_src_tree(tmp_path)
        result = bootstrap_project(tmp_path, preset_name="monolith")
        nodes = result["nodes"]
        models_node = next((n for n in nodes if n["ref_id"] == "auth-models"), None)
        assert models_node is not None
        assert models_node["kind"] == "entity"

    def test_monolith_child_api_are_features(self, tmp_path: Path) -> None:
        _make_src_tree(tmp_path)
        result = bootstrap_project(tmp_path, preset_name="monolith")
        nodes = result["nodes"]
        api_node = next((n for n in nodes if n["ref_id"] == "auth-api"), None)
        assert api_node is not None
        assert api_node["kind"] == "feature"

    def test_part_of_edges_generated(self, tmp_path: Path) -> None:
        _make_src_tree(tmp_path)
        result = bootstrap_project(tmp_path, preset_name="monolith")
        edges = result["edges"]
        assert len(edges) > 0
        part_of = [e for e in edges if e["kind"] == "part_of"]
        assert len(part_of) >= 2  # auth-models, auth-api → auth
        srcs = {e["src"] for e in part_of}
        assert "auth-models" in srcs
        assert "auth-api" in srcs

    def test_microservices_top_dirs_are_services(self, tmp_path: Path) -> None:
        _make_src_tree(tmp_path)
        result = bootstrap_project(tmp_path, preset_name="microservices")
        assert result["preset"] == "microservices"
        nodes = result["nodes"]
        auth_node = next(n for n in nodes if n["ref_id"] == "auth")
        assert auth_node["kind"] == "service"

    def test_auto_detect_preset(self, tmp_path: Path) -> None:
        """Without explicit preset, bootstrap auto-detects."""
        _make_src_tree(tmp_path)
        result = bootstrap_project(tmp_path)
        # Default for src/ layout is monolith.
        assert result["preset"] == "monolith"

    def test_auto_detect_microservices(self, tmp_path: Path) -> None:
        (tmp_path / "services").mkdir()
        svc = tmp_path / "services" / "auth"
        svc.mkdir()
        (svc / "main.go").write_text("package main\n")
        result = bootstrap_project(tmp_path)
        assert result["preset"] == "microservices"

    def test_auto_detect_monorepo(self, tmp_path: Path) -> None:
        (tmp_path / "packages").mkdir()
        pkg = tmp_path / "packages" / "core"
        pkg.mkdir()
        (pkg / "index.ts").write_text("export default {}\n")
        result = bootstrap_project(tmp_path)
        assert result["preset"] == "monorepo"

    def test_edges_generated_count(self, tmp_path: Path) -> None:
        _make_src_tree(tmp_path)
        result = bootstrap_project(tmp_path, preset_name="monolith")
        assert result["edges_generated"] >= 2

    def test_config_includes_preset(self, tmp_path: Path) -> None:
        _make_src_tree(tmp_path)
        bootstrap_project(tmp_path, preset_name="monolith")
        config = yaml.safe_load((tmp_path / ".beadloom" / "config.yml").read_text())
        assert config["preset"] == "monolith"


# ---------------------------------------------------------------------------
# bootstrap_project — noise directory filtering (DEEP-04)
# ---------------------------------------------------------------------------


class TestBootstrapNoiseFilter:
    """Non-code directories should not become architecture nodes."""

    def test_static_dir_excluded(self, tmp_path: Path) -> None:
        """static/ should not generate a node even if it has .js files."""
        be = tmp_path / "backend"
        be.mkdir()
        # Real code dir.
        apps = be / "apps"
        apps.mkdir()
        (apps / "views.py").write_text("def index(): pass\n")
        # Noise dir with JS files (like Django staticfiles).
        static = be / "static"
        static.mkdir()
        admin = static / "admin"
        admin.mkdir()
        (admin / "jquery.js").write_text("// jQuery\n")

        result = bootstrap_project(tmp_path, preset_name="monolith")
        ref_ids = {n["ref_id"] for n in result["nodes"]}
        assert "apps" in ref_ids
        assert "static" not in ref_ids

    def test_templates_dir_excluded(self, tmp_path: Path) -> None:
        """templates/ directory should be excluded from clustering."""
        be = tmp_path / "backend"
        be.mkdir()
        apps = be / "apps"
        apps.mkdir()
        (apps / "views.py").write_text("pass\n")
        tpl = be / "templates"
        tpl.mkdir()
        # Even with a .py file, templates should be skipped.
        (tpl / "tags.py").write_text("pass\n")

        result = bootstrap_project(tmp_path, preset_name="monolith")
        ref_ids = {n["ref_id"] for n in result["nodes"]}
        assert "templates" not in ref_ids

    def test_migrations_dir_excluded(self, tmp_path: Path) -> None:
        """migrations/ as a child dir should not become a node."""
        src = tmp_path / "src"
        src.mkdir()
        apps = src / "users"
        apps.mkdir()
        (apps / "models.py").write_text("class User: pass\n")
        mig = apps / "migrations"
        mig.mkdir()
        (mig / "0001_initial.py").write_text("pass\n")

        result = bootstrap_project(tmp_path, preset_name="monolith")
        ref_ids = {n["ref_id"] for n in result["nodes"]}
        assert "users" in ref_ids
        assert "users-migrations" not in ref_ids

    def test_fixtures_dir_excluded(self, tmp_path: Path) -> None:
        """fixtures/ directory should not become a node."""
        src = tmp_path / "src"
        src.mkdir()
        apps = src / "core"
        apps.mkdir()
        (apps / "models.py").write_text("pass\n")
        fix = apps / "fixtures"
        fix.mkdir()
        (fix / "data.py").write_text("pass\n")

        result = bootstrap_project(tmp_path, preset_name="monolith")
        ref_ids = {n["ref_id"] for n in result["nodes"]}
        assert "core" in ref_ids
        assert "core-fixtures" not in ref_ids


# ---------------------------------------------------------------------------
# bootstrap_project — zero-doc mode
# ---------------------------------------------------------------------------


class TestBootstrapZeroDoc:
    """Tests for zero-doc mode support."""

    def test_no_docs_dir_sets_null(self, tmp_path: Path) -> None:
        """Config docs_dir is null when no docs/ exists."""
        src = tmp_path / "src"
        src.mkdir()
        (src / "app.py").write_text("pass\n")
        bootstrap_project(tmp_path)
        config = yaml.safe_load((tmp_path / ".beadloom" / "config.yml").read_text())
        assert config.get("docs_dir") is None

    def test_with_docs_dir_no_null(self, tmp_path: Path) -> None:
        """Config omits docs_dir=null when docs/ exists."""
        src = tmp_path / "src"
        src.mkdir()
        (src / "app.py").write_text("pass\n")
        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "readme.md").write_text("# Hello\n")
        bootstrap_project(tmp_path)
        config = yaml.safe_load((tmp_path / ".beadloom" / "config.yml").read_text())
        assert "docs_dir" not in config

    def test_bootstrap_succeeds_without_docs(self, tmp_path: Path) -> None:
        _make_src_tree(tmp_path)
        result = bootstrap_project(tmp_path)
        assert result["nodes_generated"] > 0
        assert result["config_created"] is True


# ---------------------------------------------------------------------------
# bootstrap_project — monorepo manifest deps
# ---------------------------------------------------------------------------


class TestBootstrapMonorepoDeps:
    """Tests for monorepo depends_on edge inference from manifests."""

    def test_package_json_workspace_deps(self, tmp_path: Path) -> None:
        pkgs = tmp_path / "packages"
        pkgs.mkdir()

        # Package A depends on B via workspace protocol.
        a = pkgs / "app"
        a.mkdir()
        (a / "index.ts").write_text("import b from 'core'\n")
        (a / "package.json").write_text('{"dependencies": {"@org/core": "workspace:*"}}')

        b = pkgs / "core"
        b.mkdir()
        (b / "index.ts").write_text("export default {}\n")

        result = bootstrap_project(tmp_path, preset_name="monorepo")
        dep_edges = [e for e in result["edges"] if e["kind"] == "depends_on"]
        assert len(dep_edges) >= 1
        assert dep_edges[0]["src"] == "app"
        assert dep_edges[0]["dst"] == "core"

    def test_no_deps_no_edges(self, tmp_path: Path) -> None:
        pkgs = tmp_path / "packages"
        pkgs.mkdir()
        a = pkgs / "solo"
        a.mkdir()
        (a / "main.ts").write_text("console.log('hi')\n")
        result = bootstrap_project(tmp_path, preset_name="monorepo")
        dep_edges = [e for e in result["edges"] if e["kind"] == "depends_on"]
        assert dep_edges == []


# ---------------------------------------------------------------------------
# import_docs
# ---------------------------------------------------------------------------


class TestImportDocs:
    def test_classifies_docs(self, tmp_path: Path) -> None:
        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "adr-001.md").write_text("# ADR\n\n## Decision\nUse X.\n")
        (docs / "readme.md").write_text("# README\n\nHello.\n")
        result = import_docs(tmp_path, docs)
        assert len(result) >= 2
        kinds = {r["kind"] for r in result}
        assert "adr" in kinds

    def test_creates_graph_yaml(self, tmp_path: Path) -> None:
        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "spec.md").write_text("# Feature Spec\n\n## User story\nStory.\n")
        (tmp_path / ".beadloom" / "_graph").mkdir(parents=True)
        import_docs(tmp_path, docs)
        graph_dir = tmp_path / ".beadloom" / "_graph"
        yml_files = list(graph_dir.glob("*.yml"))
        assert len(yml_files) >= 1

    def test_empty_docs(self, tmp_path: Path) -> None:
        docs = tmp_path / "docs"
        docs.mkdir()
        result = import_docs(tmp_path, docs)
        assert result == []


# ---------------------------------------------------------------------------
# CLI init
# ---------------------------------------------------------------------------


class TestInitCli:
    def test_init_bootstrap(self, tmp_path: Path) -> None:
        from click.testing import CliRunner

        from beadloom.services.cli import main

        src = tmp_path / "src"
        src.mkdir()
        (src / "app.py").write_text("def main():\n    pass\n")
        runner = CliRunner()
        result = runner.invoke(main, ["init", "--bootstrap", "--project", str(tmp_path)])
        assert result.exit_code == 0, result.output
        assert (tmp_path / ".beadloom" / "_graph").is_dir()

    def test_init_bootstrap_with_preset(self, tmp_path: Path) -> None:
        from click.testing import CliRunner

        from beadloom.services.cli import main

        _make_src_tree(tmp_path)
        runner = CliRunner()
        result = runner.invoke(
            main,
            [
                "init",
                "--bootstrap",
                "--preset",
                "monolith",
                "--project",
                str(tmp_path),
            ],
        )
        assert result.exit_code == 0, result.output
        assert "monolith" in result.output
        assert "nodes" in result.output

    def test_init_import(self, tmp_path: Path) -> None:
        from click.testing import CliRunner

        from beadloom.services.cli import main

        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "readme.md").write_text("# Hello\n\nWorld.\n")
        (tmp_path / ".beadloom" / "_graph").mkdir(parents=True)
        runner = CliRunner()
        result = runner.invoke(main, ["init", "--import", str(docs), "--project", str(tmp_path)])
        assert result.exit_code == 0, result.output

    def test_init_interactive_bootstrap(self, tmp_path: Path) -> None:
        """init without flags should trigger interactive mode."""
        from unittest.mock import patch

        from click.testing import CliRunner

        from beadloom.services.cli import main

        src = tmp_path / "src"
        src.mkdir()
        (src / "app.py").write_text("def main():\n    pass\n")

        with (
            patch(
                "rich.prompt.Prompt.ask",
                side_effect=["bootstrap", "yes"],
            ),
            patch("rich.console.Console"),
        ):
            runner = CliRunner()
            result = runner.invoke(main, ["init", "--project", str(tmp_path)])
        assert result.exit_code == 0, result.output


# ---------------------------------------------------------------------------
# interactive_init
# ---------------------------------------------------------------------------


class TestInteractiveInit:
    """Tests for interactive init mode."""

    def test_bootstrap_mode(self, tmp_path: Path) -> None:
        """Interactive init with bootstrap selection."""
        from unittest.mock import patch

        src = tmp_path / "src"
        src.mkdir()
        svc = src / "api"
        svc.mkdir()
        (svc / "app.py").write_text("def main():\n    pass\n")

        with (
            patch(
                "rich.prompt.Prompt.ask",
                side_effect=["bootstrap", "yes"],
            ),
            patch("rich.console.Console"),
        ):
            result = interactive_init(tmp_path)

        assert result["mode"] == "bootstrap"
        assert (tmp_path / ".beadloom" / "_graph").is_dir()

    def test_import_mode(self, tmp_path: Path) -> None:
        """Interactive init with import selection."""
        from unittest.mock import patch

        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "readme.md").write_text("# Hello\n\nWorld.\n")

        with patch("rich.prompt.Prompt.ask", return_value="import"), patch("rich.console.Console"):
            result = interactive_init(tmp_path)

        assert result["mode"] == "import"

    def test_reinit_cancel(self, tmp_path: Path) -> None:
        """Re-init detection with cancel choice."""
        from unittest.mock import patch

        (tmp_path / ".beadloom").mkdir()

        with patch("rich.prompt.Prompt.ask", return_value="cancel"), patch("rich.console.Console"):
            result = interactive_init(tmp_path)

        assert result["mode"] == "cancelled"
        assert result["reinit"] is False

    def test_reinit_overwrite(self, tmp_path: Path) -> None:
        """Re-init detection with overwrite choice."""
        from unittest.mock import patch

        (tmp_path / ".beadloom").mkdir()
        src = tmp_path / "src"
        src.mkdir()
        svc = src / "api"
        svc.mkdir()
        (svc / "app.py").write_text("def main():\n    pass\n")

        with (
            patch(
                "rich.prompt.Prompt.ask",
                side_effect=["overwrite", "bootstrap", "yes"],
            ),
            patch("rich.console.Console"),
        ):
            result = interactive_init(tmp_path)

        assert result["reinit"] is True
        assert result["mode"] == "bootstrap"

    def test_zero_doc_no_import_choice(self, tmp_path: Path) -> None:
        """Without docs dir, only bootstrap is offered."""
        from unittest.mock import MagicMock, patch

        src = tmp_path / "src"
        src.mkdir()
        svc = src / "api"
        svc.mkdir()
        (svc / "app.py").write_text("pass\n")

        ask_mock = MagicMock(side_effect=["bootstrap", "yes"])
        with patch("rich.prompt.Prompt.ask", ask_mock), patch("rich.console.Console"):
            result = interactive_init(tmp_path)

        assert result["mode"] == "bootstrap"
        # Verify the first prompt offered only bootstrap.
        first_call = ask_mock.call_args_list[0]
        assert first_call[1].get("choices") == ["bootstrap"]

    def test_review_edit_returns_early(self, tmp_path: Path) -> None:
        """Choosing 'edit' during review returns without reindex hint."""
        from unittest.mock import patch

        src = tmp_path / "src"
        src.mkdir()
        svc = src / "api"
        svc.mkdir()
        (svc / "app.py").write_text("pass\n")

        with (
            patch(
                "rich.prompt.Prompt.ask",
                side_effect=["bootstrap", "edit"],
            ),
            patch("rich.console.Console"),
        ):
            result = interactive_init(tmp_path)

        assert result.get("review") == "edit"
        assert result["agents_md_created"] is True

    def test_review_cancel(self, tmp_path: Path) -> None:
        """Choosing 'cancel' during review aborts."""
        from unittest.mock import patch

        src = tmp_path / "src"
        src.mkdir()
        svc = src / "api"
        svc.mkdir()
        (svc / "app.py").write_text("pass\n")

        with (
            patch(
                "rich.prompt.Prompt.ask",
                side_effect=["bootstrap", "cancel"],
            ),
            patch("rich.console.Console"),
        ):
            result = interactive_init(tmp_path)

        assert result["mode"] == "cancelled"

    def test_auto_reindex_after_bootstrap(self, tmp_path: Path) -> None:
        """Interactive init runs reindex automatically after bootstrap."""
        from unittest.mock import patch

        src = tmp_path / "src"
        src.mkdir()
        svc = src / "api"
        svc.mkdir()
        (svc / "app.py").write_text("import os\ndef main():\n    pass\n")

        with (
            patch(
                "rich.prompt.Prompt.ask",
                side_effect=["bootstrap", "yes"],
            ),
            patch("rich.console.Console"),
        ):
            result = interactive_init(tmp_path)

        assert result["mode"] == "bootstrap"
        assert "reindex" in result
        assert result["reindex"]["symbols"] >= 1

        # Verify DB was created and populated.
        db_path = tmp_path / ".beadloom" / "beadloom.db"
        assert db_path.exists()


# ---------------------------------------------------------------------------
# _detect_project_name
# ---------------------------------------------------------------------------


class TestDetectProjectName:
    """Tests for _detect_project_name() private helper."""

    def test_pyproject_toml(self, tmp_path: Path) -> None:
        (tmp_path / "pyproject.toml").write_text('[project]\nname = "myproject"\n')
        from beadloom.onboarding.scanner import _detect_project_name

        assert _detect_project_name(tmp_path) == "myproject"

    def test_package_json(self, tmp_path: Path) -> None:
        (tmp_path / "package.json").write_text('{"name": "mypackage"}')
        from beadloom.onboarding.scanner import _detect_project_name

        assert _detect_project_name(tmp_path) == "mypackage"

    def test_package_json_scoped(self, tmp_path: Path) -> None:
        (tmp_path / "package.json").write_text('{"name": "@org/core"}')
        from beadloom.onboarding.scanner import _detect_project_name

        assert _detect_project_name(tmp_path) == "core"

    def test_go_mod(self, tmp_path: Path) -> None:
        (tmp_path / "go.mod").write_text("module github.com/org/myapp\n")
        from beadloom.onboarding.scanner import _detect_project_name

        assert _detect_project_name(tmp_path) == "myapp"

    def test_cargo_toml(self, tmp_path: Path) -> None:
        (tmp_path / "Cargo.toml").write_text('[package]\nname = "rustproj"\n')
        from beadloom.onboarding.scanner import _detect_project_name

        assert _detect_project_name(tmp_path) == "rustproj"

    def test_directory_fallback(self, tmp_path: Path) -> None:
        from beadloom.onboarding.scanner import _detect_project_name

        assert _detect_project_name(tmp_path) == tmp_path.name

    def test_priority_pyproject_over_package_json(self, tmp_path: Path) -> None:
        (tmp_path / "pyproject.toml").write_text('[project]\nname = "from-pyproject"\n')
        (tmp_path / "package.json").write_text('{"name": "from-package"}')
        from beadloom.onboarding.scanner import _detect_project_name

        assert _detect_project_name(tmp_path) == "from-pyproject"


# ---------------------------------------------------------------------------
# bootstrap_project — root node
# ---------------------------------------------------------------------------


class TestBootstrapRootNode:
    """Tests for root node creation in bootstrap_project()."""

    def test_root_node_exists(self, tmp_path: Path) -> None:
        _make_src_tree(tmp_path)
        result = bootstrap_project(tmp_path)
        nodes = result["nodes"]
        assert len(nodes) >= 1
        root = nodes[0]
        assert root["kind"] == "service"
        assert root["summary"].startswith("Root:")

    def test_root_node_ref_id_from_pyproject(self, tmp_path: Path) -> None:
        (tmp_path / "pyproject.toml").write_text('[project]\nname = "testproj"\n')
        _make_src_tree(tmp_path)
        result = bootstrap_project(tmp_path)
        root = result["nodes"][0]
        assert root["ref_id"] == "testproj"

    def test_root_node_ref_id_fallback(self, tmp_path: Path) -> None:
        _make_src_tree(tmp_path)
        result = bootstrap_project(tmp_path)
        root = result["nodes"][0]
        assert root["ref_id"] == tmp_path.name

    def test_part_of_edges_to_root(self, tmp_path: Path) -> None:
        (tmp_path / "pyproject.toml").write_text('[project]\nname = "myproj"\n')
        _make_src_tree(tmp_path)
        result = bootstrap_project(tmp_path, preset_name="monolith")
        edges = result["edges"]
        root_part_of = [e for e in edges if e["kind"] == "part_of" and e["dst"] == "myproj"]
        cluster_names = {"auth", "billing", "utils"}
        sources = {e["src"] for e in root_part_of}
        for name in cluster_names:
            assert name in sources, f"Expected '{name}' to have a part_of edge to root"

    def test_project_name_in_result(self, tmp_path: Path) -> None:
        _make_src_tree(tmp_path)
        result = bootstrap_project(tmp_path)
        assert "project_name" in result
        assert isinstance(result["project_name"], str)
        assert len(result["project_name"]) > 0

    def test_root_node_empty_source(self, tmp_path: Path) -> None:
        _make_src_tree(tmp_path)
        result = bootstrap_project(tmp_path)
        root = result["nodes"][0]
        assert root["source"] == ""


# ---------------------------------------------------------------------------
# setup_mcp_auto
# ---------------------------------------------------------------------------


class TestSetupMcpAuto:
    """Tests for setup_mcp_auto() — editor detection and MCP config generation."""

    def test_default_claude_code(self, tmp_path: Path) -> None:
        """Clean directory defaults to claude-code editor."""
        import json

        result = setup_mcp_auto(tmp_path)
        assert result == "claude-code"

        mcp_path = tmp_path / ".mcp.json"
        assert mcp_path.exists()

        data = json.loads(mcp_path.read_text(encoding="utf-8"))
        assert "mcpServers" in data
        assert "beadloom" in data["mcpServers"]
        assert isinstance(data["mcpServers"]["beadloom"]["command"], str)
        assert data["mcpServers"]["beadloom"]["args"] == ["mcp-serve"]

    def test_detect_cursor(self, tmp_path: Path) -> None:
        """Presence of .cursor dir selects cursor editor."""
        (tmp_path / ".cursor").mkdir()

        result = setup_mcp_auto(tmp_path)
        assert result == "cursor"
        assert (tmp_path / ".cursor" / "mcp.json").exists()

    def test_detect_windsurf(self, tmp_path: Path) -> None:
        """Presence of .windsurfrules selects windsurf; config in mocked home."""
        import json
        from unittest.mock import patch

        (tmp_path / ".windsurfrules").write_text("")

        fake_home = tmp_path / "fake_home"
        fake_home.mkdir()

        with patch("pathlib.Path.home", return_value=fake_home):
            result = setup_mcp_auto(tmp_path)

        assert result == "windsurf"
        windsurf_cfg = fake_home / ".codeium" / "windsurf" / "mcp_config.json"
        assert windsurf_cfg.exists()

        data = json.loads(windsurf_cfg.read_text(encoding="utf-8"))
        assert "--project" in data["mcpServers"]["beadloom"]["args"]

    def test_detect_claude_marker(self, tmp_path: Path) -> None:
        """Presence of .claude dir selects claude-code."""
        (tmp_path / ".claude").mkdir()

        result = setup_mcp_auto(tmp_path)
        assert result == "claude-code"

    def test_idempotent_skip_existing(self, tmp_path: Path) -> None:
        """Existing .mcp.json is not overwritten; returns None."""
        mcp_path = tmp_path / ".mcp.json"
        mcp_path.write_text('{"existing": true}\n')

        result = setup_mcp_auto(tmp_path)
        assert result is None

    def test_cursor_priority_over_claude(self, tmp_path: Path) -> None:
        """Cursor marker is more specific and wins over .claude."""
        (tmp_path / ".cursor").mkdir()
        (tmp_path / ".claude").mkdir()

        result = setup_mcp_auto(tmp_path)
        assert result == "cursor"

    def test_valid_json_structure(self, tmp_path: Path) -> None:
        """Generated MCP config has the correct JSON structure."""
        import json

        setup_mcp_auto(tmp_path)

        mcp_path = tmp_path / ".mcp.json"
        data = json.loads(mcp_path.read_text(encoding="utf-8"))

        assert "mcpServers" in data
        assert "beadloom" in data["mcpServers"]
        server = data["mcpServers"]["beadloom"]
        assert isinstance(server["command"], str)
        assert isinstance(server["args"], list)


# ---------------------------------------------------------------------------
# bootstrap_project — MCP integration
# ---------------------------------------------------------------------------


class TestBootstrapMcpIntegration:
    """Tests that bootstrap_project calls setup_mcp_auto."""

    def test_bootstrap_creates_mcp_config(self, tmp_path: Path) -> None:
        """Bootstrap creates .mcp.json in the project root."""
        _make_src_tree(tmp_path)
        bootstrap_project(tmp_path)
        assert (tmp_path / ".mcp.json").exists()

    def test_bootstrap_mcp_editor_in_result(self, tmp_path: Path) -> None:
        """Bootstrap result includes mcp_editor field."""
        _make_src_tree(tmp_path)
        result = bootstrap_project(tmp_path)
        assert result["mcp_editor"] is not None
        assert result["mcp_editor"] == "claude-code"


# ---------------------------------------------------------------------------
# generate_rules — unit tests
# ---------------------------------------------------------------------------


class TestGenerateRules:
    """Tests for generate_rules() auto-rules generation."""

    def test_domains_only(self, tmp_path: Path) -> None:
        """Nodes with domain kinds produce exactly 1 rule (domain-needs-parent)."""
        from beadloom.onboarding.scanner import generate_rules

        nodes = [
            {"ref_id": "myproject", "kind": "service", "summary": "Root: myproject", "source": ""},
            {"ref_id": "auth", "kind": "domain", "summary": "Domain: auth", "source": "src/auth/"},
            {
                "ref_id": "billing",
                "kind": "domain",
                "summary": "Domain: billing",
                "source": "src/billing/",
            },
        ]
        edges = [
            {"src": "auth", "dst": "myproject", "kind": "part_of"},
            {"src": "billing", "dst": "myproject", "kind": "part_of"},
        ]
        rules_path = tmp_path / "rules.yml"
        count = generate_rules(nodes, edges, "myproject", rules_path)

        assert count == 1
        assert rules_path.exists()

        data = yaml.safe_load(rules_path.read_text())
        assert data["version"] == 1
        assert len(data["rules"]) == 1
        assert data["rules"][0]["name"] == "domain-needs-parent"
        assert data["rules"][0]["require"]["for"] == {"kind": "domain"}
        assert data["rules"][0]["require"]["has_edge_to"] == {"ref_id": "myproject"}
        assert data["rules"][0]["require"]["edge_kind"] == "part_of"

    def test_domains_and_features(self, tmp_path: Path) -> None:
        """Domain + feature nodes produce 2 rules."""
        from beadloom.onboarding.scanner import generate_rules

        nodes = [
            {"ref_id": "myproj", "kind": "service", "summary": "Root: myproj", "source": ""},
            {"ref_id": "auth", "kind": "domain", "summary": "Domain: auth", "source": "src/auth/"},
            {
                "ref_id": "auth-api",
                "kind": "feature",
                "summary": "Feature: api",
                "source": "src/auth/api/",
            },
        ]
        edges = [
            {"src": "auth", "dst": "myproj", "kind": "part_of"},
            {"src": "auth-api", "dst": "auth", "kind": "part_of"},
        ]
        rules_path = tmp_path / "rules.yml"
        count = generate_rules(nodes, edges, "myproj", rules_path)

        assert count == 2
        data = yaml.safe_load(rules_path.read_text())
        rule_names = {r["name"] for r in data["rules"]}
        assert "domain-needs-parent" in rule_names
        assert "feature-needs-domain" in rule_names

    def test_all_three_kinds(self, tmp_path: Path) -> None:
        """Root (service) + domain + feature + extra service node produce 3 rules."""
        from beadloom.onboarding.scanner import generate_rules

        nodes = [
            {"ref_id": "myproj", "kind": "service", "summary": "Root: myproj", "source": ""},
            {"ref_id": "auth", "kind": "domain", "summary": "Domain: auth", "source": "src/auth/"},
            {
                "ref_id": "auth-api",
                "kind": "feature",
                "summary": "Feature: api",
                "source": "src/auth/api/",
            },
            {
                "ref_id": "utils",
                "kind": "service",
                "summary": "Service: utils",
                "source": "src/utils/",
            },
        ]
        edges = [
            {"src": "auth", "dst": "myproj", "kind": "part_of"},
            {"src": "auth-api", "dst": "auth", "kind": "part_of"},
            {"src": "utils", "dst": "myproj", "kind": "part_of"},
        ]
        rules_path = tmp_path / "rules.yml"
        count = generate_rules(nodes, edges, "myproj", rules_path)

        assert count == 3
        data = yaml.safe_load(rules_path.read_text())
        rule_names = {r["name"] for r in data["rules"]}
        assert "domain-needs-parent" in rule_names
        assert "feature-needs-domain" in rule_names
        assert "service-needs-parent" in rule_names

    def test_empty_graph(self, tmp_path: Path) -> None:
        """Empty nodes list returns 0 and does not create the file."""
        from beadloom.onboarding.scanner import generate_rules

        rules_path = tmp_path / "rules.yml"
        count = generate_rules([], [], "myproj", rules_path)

        assert count == 0
        assert not rules_path.exists()

    def test_service_only_root(self, tmp_path: Path) -> None:
        """Only a root service node (no other services/domains/features) generates 0 rules."""
        from beadloom.onboarding.scanner import generate_rules

        nodes = [
            {"ref_id": "myproj", "kind": "service", "summary": "Root: myproj", "source": ""},
        ]
        edges: list[dict[str, str]] = []
        rules_path = tmp_path / "rules.yml"
        count = generate_rules(nodes, edges, "myproj", rules_path)

        assert count == 0
        assert not rules_path.exists()

    def test_idempotent_skip_existing(self, tmp_path: Path) -> None:
        """generate_rules overwrites if called directly (idempotency is in bootstrap_project)."""
        from beadloom.onboarding.scanner import generate_rules

        rules_path = tmp_path / "rules.yml"
        rules_path.write_text("version: 1\nrules: []\n")

        nodes = [
            {"ref_id": "myproj", "kind": "service", "summary": "Root: myproj", "source": ""},
            {"ref_id": "auth", "kind": "domain", "summary": "Domain: auth", "source": "src/auth/"},
        ]
        edges = [
            {"src": "auth", "dst": "myproj", "kind": "part_of"},
        ]
        count = generate_rules(nodes, edges, "myproj", rules_path)

        assert count == 1
        data = yaml.safe_load(rules_path.read_text())
        assert len(data["rules"]) == 1
        assert data["rules"][0]["name"] == "domain-needs-parent"

    def test_root_detection_from_edges(self, tmp_path: Path) -> None:
        """Root is the node without outgoing part_of edges; its ref_id appears in rules."""
        from beadloom.onboarding.scanner import generate_rules

        nodes = [
            {"ref_id": "theroot", "kind": "service", "summary": "Root: theroot", "source": ""},
            {"ref_id": "web", "kind": "domain", "summary": "Domain: web", "source": "src/web/"},
        ]
        edges = [
            {"src": "web", "dst": "theroot", "kind": "part_of"},
        ]
        rules_path = tmp_path / "rules.yml"
        generate_rules(nodes, edges, "theroot", rules_path)

        data = yaml.safe_load(rules_path.read_text())
        domain_rule = data["rules"][0]
        assert domain_rule["require"]["has_edge_to"]["ref_id"] == "theroot"
        assert "theroot" in domain_rule["description"]

    def test_yaml_valid_for_rule_engine(self, tmp_path: Path) -> None:
        """Generated YAML matches rule_engine schema."""
        from beadloom.onboarding.scanner import generate_rules

        nodes = [
            {"ref_id": "proj", "kind": "service", "summary": "Root: proj", "source": ""},
            {"ref_id": "core", "kind": "domain", "summary": "Domain: core", "source": "src/core/"},
            {
                "ref_id": "core-api",
                "kind": "feature",
                "summary": "Feature: api",
                "source": "src/core/api/",
            },
            {
                "ref_id": "infra",
                "kind": "service",
                "summary": "Service: infra",
                "source": "src/infra/",
            },
        ]
        edges = [
            {"src": "core", "dst": "proj", "kind": "part_of"},
            {"src": "core-api", "dst": "core", "kind": "part_of"},
            {"src": "infra", "dst": "proj", "kind": "part_of"},
        ]
        rules_path = tmp_path / "rules.yml"
        generate_rules(nodes, edges, "proj", rules_path)

        data = yaml.safe_load(rules_path.read_text())
        assert data["version"] == 1
        assert isinstance(data["rules"], list)

        for rule in data["rules"]:
            assert "name" in rule
            assert "description" in rule
            assert "require" in rule
            require = rule["require"]
            assert "for" in require
            assert "has_edge_to" in require
            assert "edge_kind" in require
            assert require["edge_kind"] == "part_of"


# ---------------------------------------------------------------------------
# bootstrap_project — rules integration
# ---------------------------------------------------------------------------


class TestBootstrapRulesIntegration:
    """Tests that bootstrap_project integrates generate_rules correctly."""

    def test_bootstrap_creates_rules_yml(self, tmp_path: Path) -> None:
        """Bootstrap with a real source tree creates rules.yml in _graph/ dir."""
        _make_src_tree(tmp_path)
        bootstrap_project(tmp_path)
        rules_path = tmp_path / ".beadloom" / "_graph" / "rules.yml"
        assert rules_path.exists()

    def test_bootstrap_rules_count_in_result(self, tmp_path: Path) -> None:
        """Bootstrap with monolith preset reports rules_generated >= 1."""
        _make_src_tree(tmp_path)
        result = bootstrap_project(tmp_path, preset_name="monolith")
        assert "rules_generated" in result
        assert result["rules_generated"] >= 1

    def test_bootstrap_rules_idempotent(self, tmp_path: Path) -> None:
        """Pre-existing rules.yml is not overwritten by bootstrap_project."""
        _make_src_tree(tmp_path)
        graph_dir = tmp_path / ".beadloom" / "_graph"
        graph_dir.mkdir(parents=True)
        rules_path = graph_dir / "rules.yml"
        original_content = "version: 1\nrules:\n- name: custom-rule\n"
        rules_path.write_text(original_content)

        result = bootstrap_project(tmp_path)
        assert result["rules_generated"] == 0
        assert rules_path.read_text() == original_content
