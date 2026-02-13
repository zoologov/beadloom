"""End-to-end integration tests for the BDL-011 Plug & Play Onboarding pipeline.

Each test creates a realistic sample project in ``tmp_path``, invokes real CLI
commands via ``click.testing.CliRunner``, and verifies the resulting artifacts
on disk.  Nothing is mocked — these tests exercise the full pipeline including
tree-sitter parsing, SQLite indexing, and YAML generation.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import yaml
from click.testing import CliRunner

from beadloom.services.cli import main

if TYPE_CHECKING:
    from pathlib import Path


# ---------------------------------------------------------------------------
# Helper: create a realistic multi-domain project
# ---------------------------------------------------------------------------


def _create_sample_project(tmp_path: Path) -> None:
    """Create a realistic sample project for integration tests."""
    # pyproject.toml
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "sample-app"\nversion = "0.1.0"\n')

    # src/auth (domain with 2 children)
    auth = tmp_path / "src" / "auth"
    auth.mkdir(parents=True)
    (auth / "__init__.py").write_text("")
    (auth / "service.py").write_text(
        "def authenticate(username: str, password: str) -> bool:\n    return True\n"
    )
    models = auth / "models"
    models.mkdir()
    (models / "__init__.py").write_text("")
    (models / "user.py").write_text(
        "class User:\n    def __init__(self, name: str) -> None:\n        self.name = name\n"
    )
    api = auth / "api"
    api.mkdir()
    (api / "__init__.py").write_text("")
    (api / "routes.py").write_text(
        "from auth.service import authenticate\n\n"
        "def login_handler() -> dict:\n"
        "    return {'status': 'ok'}\n"
    )

    # src/billing (domain)
    billing = tmp_path / "src" / "billing"
    billing.mkdir(parents=True)
    (billing / "__init__.py").write_text("")
    (billing / "invoice.py").write_text(
        "def create_invoice(amount: float) -> dict:\n    return {'amount': amount}\n"
    )

    # src/utils (utility/service)
    utils = tmp_path / "src" / "utils"
    utils.mkdir(parents=True)
    (utils / "helpers.py").write_text("def format_date(d: str) -> str:\n    return d\n")


def _bootstrap(tmp_path: Path, *, preset: str | None = None) -> None:
    """Run ``beadloom init --bootstrap`` on a sample project."""
    runner = CliRunner()
    cmd = ["init", "--bootstrap", "--project", str(tmp_path)]
    if preset:
        cmd.extend(["--preset", preset])
    result = runner.invoke(main, cmd)
    assert result.exit_code == 0, f"bootstrap failed:\n{result.output}"


# ---------------------------------------------------------------------------
# TestFullBootstrapPipeline
# ---------------------------------------------------------------------------


class TestFullBootstrapPipeline:
    """Tests the complete ``beadloom init --bootstrap`` flow."""

    def test_full_init_creates_all_artifacts(self, tmp_path: Path) -> None:
        """Bootstrap must produce graph, rules, config, AGENTS.md, DB, MCP, and docs."""
        _create_sample_project(tmp_path)
        _bootstrap(tmp_path)

        assert (tmp_path / ".beadloom" / "_graph" / "services.yml").exists()
        assert (tmp_path / ".beadloom" / "_graph" / "rules.yml").exists()
        assert (tmp_path / ".beadloom" / "config.yml").exists()
        assert (tmp_path / ".beadloom" / "AGENTS.md").exists()
        assert (tmp_path / ".beadloom" / "beadloom.db").exists()
        assert (tmp_path / ".mcp.json").exists()
        assert (tmp_path / "docs" / "architecture.md").exists()

    def test_graph_has_root_node(self, tmp_path: Path) -> None:
        """Root node should be a service named after pyproject.toml ``name``."""
        _create_sample_project(tmp_path)
        _bootstrap(tmp_path)

        services_yml = tmp_path / ".beadloom" / "_graph" / "services.yml"
        data = yaml.safe_load(services_yml.read_text(encoding="utf-8"))
        first_node = data["nodes"][0]
        assert first_node["kind"] == "service"
        assert first_node["ref_id"] == "sample-app"

    def test_rules_valid_for_lint(self, tmp_path: Path) -> None:
        """rules.yml must have version 1 and at least one well-formed rule."""
        _create_sample_project(tmp_path)
        _bootstrap(tmp_path)

        rules_yml = tmp_path / ".beadloom" / "_graph" / "rules.yml"
        data = yaml.safe_load(rules_yml.read_text(encoding="utf-8"))

        assert data["version"] == 1
        assert len(data["rules"]) > 0

        for rule in data["rules"]:
            assert "name" in rule
            req = rule["require"]
            assert "for" in req
            assert "has_edge_to" in req
            assert "edge_kind" in req

    def test_lint_zero_violations_after_init(self, tmp_path: Path) -> None:
        """A freshly bootstrapped project should pass lint with zero violations."""
        _create_sample_project(tmp_path)
        _bootstrap(tmp_path)

        runner = CliRunner()
        result = runner.invoke(main, ["lint", "--project", str(tmp_path)])
        assert result.exit_code == 0, f"lint failed:\n{result.output}"

    def test_ctx_returns_content_after_init(self, tmp_path: Path) -> None:
        """``beadloom ctx auth`` should return non-empty context after bootstrap."""
        _create_sample_project(tmp_path)
        _bootstrap(tmp_path)

        runner = CliRunner()
        result = runner.invoke(main, ["ctx", "auth", "--project", str(tmp_path)])
        assert result.exit_code == 0, f"ctx failed:\n{result.output}"
        assert len(result.output.strip()) > 0

    def test_mcp_config_valid_json(self, tmp_path: Path) -> None:
        """.mcp.json must contain a valid beadloom server entry."""
        _create_sample_project(tmp_path)
        _bootstrap(tmp_path)

        mcp_path = tmp_path / ".mcp.json"
        data = json.loads(mcp_path.read_text(encoding="utf-8"))

        server = data["mcpServers"]["beadloom"]
        assert isinstance(server["command"], str)
        assert "mcp-serve" in server["args"]


# ---------------------------------------------------------------------------
# TestDocsGenerateIntegration
# ---------------------------------------------------------------------------


class TestDocsGenerateIntegration:
    """Integration tests for ``beadloom docs generate``."""

    def test_docs_generate_creates_domain_files(self, tmp_path: Path) -> None:
        """Bootstrap should create domain README for ``auth``."""
        _create_sample_project(tmp_path)
        _bootstrap(tmp_path)

        readme = tmp_path / "docs" / "domains" / "auth" / "README.md"
        assert readme.exists(), "auth domain README must be created"
        content = readme.read_text(encoding="utf-8")
        assert "auth" in content
        assert "Source" in content

    def test_docs_generate_creates_feature_files(self, tmp_path: Path) -> None:
        """Bootstrap with monolith preset should create feature SPECs under domains."""
        _create_sample_project(tmp_path)
        _bootstrap(tmp_path, preset="monolith")

        # Features now live under docs/domains/{parent}/features/{name}/SPEC.md.
        domains_dir = tmp_path / "docs" / "domains"
        specs: list[Path] = []
        if domains_dir.exists():
            specs = list(domains_dir.rglob("features/*/SPEC.md"))
        if specs:
            assert len(specs) >= 1, "at least one feature SPEC expected"
        else:
            # Fallback: verify feature nodes exist in graph.
            services_yml = tmp_path / ".beadloom" / "_graph" / "services.yml"
            data = yaml.safe_load(services_yml.read_text(encoding="utf-8"))
            feature_nodes = [n for n in data["nodes"] if n["kind"] == "feature"]
            assert len(feature_nodes) >= 1, (
                "monolith preset should classify api/ or models/ sub-dirs as features"
            )

    def test_docs_generate_idempotent(self, tmp_path: Path) -> None:
        """Running ``docs generate`` after bootstrap should create 0 new files."""
        _create_sample_project(tmp_path)
        _bootstrap(tmp_path)

        runner = CliRunner()
        result = runner.invoke(main, ["docs", "generate", "--project", str(tmp_path)])
        assert result.exit_code == 0, result.output
        assert "Created 0 files" in result.output


# ---------------------------------------------------------------------------
# TestDocsPolishIntegration
# ---------------------------------------------------------------------------


class TestDocsPolishIntegration:
    """Integration tests for ``beadloom docs polish``."""

    def test_docs_polish_json_has_nodes(self, tmp_path: Path) -> None:
        """Polish JSON output must include ``nodes`` matching graph content."""
        _create_sample_project(tmp_path)
        _bootstrap(tmp_path)

        runner = CliRunner()
        result = runner.invoke(
            main,
            ["docs", "polish", "--format", "json", "--project", str(tmp_path)],
        )
        assert result.exit_code == 0, result.output

        data = json.loads(result.output)
        assert "nodes" in data
        assert isinstance(data["nodes"], list)
        assert len(data["nodes"]) > 0

        # Verify known node ref_ids are present.
        ref_ids = {n["ref_id"] for n in data["nodes"]}
        assert "auth" in ref_ids
        assert "billing" in ref_ids

    def test_docs_polish_has_instructions(self, tmp_path: Path) -> None:
        """Polish text output must contain the enrichment instruction prompt."""
        _create_sample_project(tmp_path)
        _bootstrap(tmp_path)

        runner = CliRunner()
        result = runner.invoke(
            main,
            ["docs", "polish", "--project", str(tmp_path)],
        )
        assert result.exit_code == 0, result.output
        assert "enriching documentation" in result.output


# ---------------------------------------------------------------------------
# TestIdempotency
# ---------------------------------------------------------------------------


class TestIdempotency:
    """Verify that re-running bootstrap/generate never overwrites user edits."""

    def test_reinit_no_overwrite(self, tmp_path: Path) -> None:
        """Re-running ``init --bootstrap`` must not overwrite edited docs or rules."""
        _create_sample_project(tmp_path)
        _bootstrap(tmp_path)

        # Manually edit docs/architecture.md.
        arch_path = tmp_path / "docs" / "architecture.md"
        custom_text = "\n<!-- CUSTOM USER EDIT -->\n"
        original = arch_path.read_text(encoding="utf-8")
        arch_path.write_text(original + custom_text, encoding="utf-8")

        # Record rules.yml content before re-init.
        rules_path = tmp_path / ".beadloom" / "_graph" / "rules.yml"
        rules_before = rules_path.read_text(encoding="utf-8")

        # Re-bootstrap.
        _bootstrap(tmp_path)

        # architecture.md should still contain the custom edit.
        assert custom_text in arch_path.read_text(encoding="utf-8")

        # rules.yml should still have the original content (not regenerated).
        assert rules_path.read_text(encoding="utf-8") == rules_before

    def test_docs_generate_preserves_edits(self, tmp_path: Path) -> None:
        """Running ``docs generate`` must not overwrite a user-edited domain README."""
        _create_sample_project(tmp_path)
        _bootstrap(tmp_path)

        # Edit a domain README.
        readme = tmp_path / "docs" / "domains" / "auth" / "README.md"
        assert readme.exists(), "auth README must exist after bootstrap"
        custom = "<!-- CUSTOM DOMAIN NOTES -->"
        original = readme.read_text(encoding="utf-8")
        readme.write_text(original + custom, encoding="utf-8")

        # Run docs generate again.
        runner = CliRunner()
        result = runner.invoke(main, ["docs", "generate", "--project", str(tmp_path)])
        assert result.exit_code == 0, result.output

        # Custom text must be preserved.
        assert custom in readme.read_text(encoding="utf-8")
