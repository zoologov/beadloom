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
        models_node = next(
            (n for n in nodes if n["ref_id"] == "auth-models"), None
        )
        assert models_node is not None
        assert models_node["kind"] == "entity"

    def test_monolith_child_api_are_features(self, tmp_path: Path) -> None:
        _make_src_tree(tmp_path)
        result = bootstrap_project(tmp_path, preset_name="monolith")
        nodes = result["nodes"]
        api_node = next(
            (n for n in nodes if n["ref_id"] == "auth-api"), None
        )
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
        config = yaml.safe_load(
            (tmp_path / ".beadloom" / "config.yml").read_text()
        )
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
        config = yaml.safe_load(
            (tmp_path / ".beadloom" / "config.yml").read_text()
        )
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
        config = yaml.safe_load(
            (tmp_path / ".beadloom" / "config.yml").read_text()
        )
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
        (a / "package.json").write_text(
            '{"dependencies": {"@org/core": "workspace:*"}}'
        )

        b = pkgs / "core"
        b.mkdir()
        (b / "index.ts").write_text("export default {}\n")

        result = bootstrap_project(tmp_path, preset_name="monorepo")
        dep_edges = [
            e for e in result["edges"] if e["kind"] == "depends_on"
        ]
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
        dep_edges = [
            e for e in result["edges"] if e["kind"] == "depends_on"
        ]
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

        from beadloom.cli import main

        src = tmp_path / "src"
        src.mkdir()
        (src / "app.py").write_text("def main():\n    pass\n")
        runner = CliRunner()
        result = runner.invoke(
            main, ["init", "--bootstrap", "--project", str(tmp_path)]
        )
        assert result.exit_code == 0, result.output
        assert (tmp_path / ".beadloom" / "_graph").is_dir()

    def test_init_bootstrap_with_preset(self, tmp_path: Path) -> None:
        from click.testing import CliRunner

        from beadloom.cli import main

        _make_src_tree(tmp_path)
        runner = CliRunner()
        result = runner.invoke(
            main,
            [
                "init", "--bootstrap",
                "--preset", "monolith",
                "--project", str(tmp_path),
            ],
        )
        assert result.exit_code == 0, result.output
        assert "monolith" in result.output
        assert "nodes" in result.output

    def test_init_import(self, tmp_path: Path) -> None:
        from click.testing import CliRunner

        from beadloom.cli import main

        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "readme.md").write_text("# Hello\n\nWorld.\n")
        (tmp_path / ".beadloom" / "_graph").mkdir(parents=True)
        runner = CliRunner()
        result = runner.invoke(
            main, ["init", "--import", str(docs), "--project", str(tmp_path)]
        )
        assert result.exit_code == 0, result.output

    def test_init_interactive_bootstrap(self, tmp_path: Path) -> None:
        """init without flags should trigger interactive mode."""
        from unittest.mock import patch

        from click.testing import CliRunner

        from beadloom.cli import main

        src = tmp_path / "src"
        src.mkdir()
        (src / "app.py").write_text("def main():\n    pass\n")

        with patch(
            "rich.prompt.Prompt.ask",
            side_effect=["bootstrap", "yes"],
        ), patch("rich.console.Console"):
            runner = CliRunner()
            result = runner.invoke(
                main, ["init", "--project", str(tmp_path)]
            )
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

        with patch(
            "rich.prompt.Prompt.ask",
            side_effect=["bootstrap", "yes"],
        ), patch("rich.console.Console"):
            result = interactive_init(tmp_path)

        assert result["mode"] == "bootstrap"
        assert (tmp_path / ".beadloom" / "_graph").is_dir()

    def test_import_mode(self, tmp_path: Path) -> None:
        """Interactive init with import selection."""
        from unittest.mock import patch

        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "readme.md").write_text("# Hello\n\nWorld.\n")

        with patch("rich.prompt.Prompt.ask", return_value="import"), \
             patch("rich.console.Console"):
            result = interactive_init(tmp_path)

        assert result["mode"] == "import"

    def test_reinit_cancel(self, tmp_path: Path) -> None:
        """Re-init detection with cancel choice."""
        from unittest.mock import patch

        (tmp_path / ".beadloom").mkdir()

        with patch("rich.prompt.Prompt.ask", return_value="cancel"), \
             patch("rich.console.Console"):
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

        with patch(
            "rich.prompt.Prompt.ask",
            side_effect=["overwrite", "bootstrap", "yes"],
        ), patch("rich.console.Console"):
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
        with patch("rich.prompt.Prompt.ask", ask_mock), \
             patch("rich.console.Console"):
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

        with patch(
            "rich.prompt.Prompt.ask",
            side_effect=["bootstrap", "edit"],
        ), patch("rich.console.Console"):
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

        with patch(
            "rich.prompt.Prompt.ask",
            side_effect=["bootstrap", "cancel"],
        ), patch("rich.console.Console"):
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

        with patch(
            "rich.prompt.Prompt.ask",
            side_effect=["bootstrap", "yes"],
        ), patch("rich.console.Console"):
            result = interactive_init(tmp_path)

        assert result["mode"] == "bootstrap"
        assert "reindex" in result
        assert result["reindex"]["symbols"] >= 1

        # Verify DB was created and populated.
        db_path = tmp_path / ".beadloom" / "beadloom.db"
        assert db_path.exists()
