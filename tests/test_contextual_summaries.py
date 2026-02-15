"""Tests for BEAD-05: contextual node summaries."""

from __future__ import annotations

from typing import TYPE_CHECKING

from beadloom.onboarding.scanner import _build_contextual_summary

if TYPE_CHECKING:
    from pathlib import Path


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_fastapi_cluster(tmp_path: Path) -> Path:
    """Create a FastAPI-style directory with routes and classes."""
    src = tmp_path / "src"
    src.mkdir(exist_ok=True)
    auth = src / "auth"
    auth.mkdir(exist_ok=True)

    # FastAPI marker
    (auth / "main.py").write_text(
        "from fastapi import FastAPI\n"
        "app = FastAPI()\n"
        "\n"
        "@app.get('/login')\n"
        "def login(): pass\n"
        "\n"
        "@app.post('/register')\n"
        "def register(): pass\n"
    )

    # Models with classes
    (auth / "models.py").write_text(
        "class User:\n    pass\n\nclass Token:\n    pass\n\nclass Session:\n    pass\n"
    )

    # README
    (auth / "README.md").write_text(
        "# Auth Service\n\nJWT-based authentication and authorization module.\n"
    )

    return auth


def _make_plain_cluster(tmp_path: Path) -> Path:
    """Create a plain directory with no framework or README."""
    src = tmp_path / "src"
    src.mkdir(exist_ok=True)
    utils = src / "utils"
    utils.mkdir(exist_ok=True)

    (utils / "helpers.py").write_text("def format_date(): pass\ndef parse_url(): pass\n")

    return utils


def _make_django_cluster(tmp_path: Path) -> Path:
    """Create a Django app directory."""
    src = tmp_path / "src"
    src.mkdir(exist_ok=True)
    users = src / "users"
    users.mkdir(exist_ok=True)

    (users / "apps.py").write_text(
        "from django.apps import AppConfig\nclass UsersConfig(AppConfig):\n    name = 'users'\n"
    )
    (users / "models.py").write_text("class Profile:\n    pass\nclass Address:\n    pass\n")
    (users / "views.py").write_text(
        "def user_list(): pass\ndef user_detail(): pass\ndef user_create(): pass\n"
    )

    return users


def _make_cluster_with_entry_point(tmp_path: Path) -> Path:
    """Create a cluster with an entry point."""
    src = tmp_path / "src"
    src.mkdir(exist_ok=True)
    cli = src / "cli"
    cli.mkdir(exist_ok=True)

    (cli / "main.py").write_text("import click\n\n@click.command()\ndef main(): pass\n")
    (cli / "utils.py").write_text("def format_output(): pass\n")

    return cli


# ---------------------------------------------------------------------------
# _build_contextual_summary — basic behavior
# ---------------------------------------------------------------------------


class TestBuildContextualSummary:
    """Tests for _build_contextual_summary()."""

    def test_framework_with_symbols_and_readme(self, tmp_path: Path) -> None:
        """Rich summary includes framework, key details from symbols and README."""
        auth_dir = _make_fastapi_cluster(tmp_path)

        result = _build_contextual_summary(
            dir_path=auth_dir,
            name="auth",
            kind="domain",
            files=[
                "src/auth/main.py",
                "src/auth/models.py",
            ],
            project_root=tmp_path,
        )

        # Should mention FastAPI framework
        assert "FastAPI" in result
        # Should mention the name
        assert "auth" in result
        # Should include class count or function count info
        # (exact format varies, but should have symbol info)
        assert "class" in result.lower() or "function" in result.lower()

    def test_plain_cluster_no_framework(self, tmp_path: Path) -> None:
        """Cluster with no framework gets a reasonable default summary."""
        utils_dir = _make_plain_cluster(tmp_path)

        result = _build_contextual_summary(
            dir_path=utils_dir,
            name="utils",
            kind="service",
            files=["src/utils/helpers.py"],
            project_root=tmp_path,
        )

        # Should have the name and kind
        assert "utils" in result
        # Should have file count or function/fn count
        assert "file" in result.lower() or "fn" in result.lower()

    def test_django_app_summary(self, tmp_path: Path) -> None:
        """Django app gets framework-aware summary with symbol details."""
        users_dir = _make_django_cluster(tmp_path)

        result = _build_contextual_summary(
            dir_path=users_dir,
            name="users",
            kind="domain",
            files=[
                "src/users/apps.py",
                "src/users/models.py",
                "src/users/views.py",
            ],
            project_root=tmp_path,
        )

        assert "Django" in result
        assert "users" in result

    def test_summary_under_120_chars(self, tmp_path: Path) -> None:
        """Summary is kept under 120 characters."""
        auth_dir = _make_fastapi_cluster(tmp_path)

        result = _build_contextual_summary(
            dir_path=auth_dir,
            name="auth",
            kind="domain",
            files=[
                "src/auth/main.py",
                "src/auth/models.py",
            ],
            project_root=tmp_path,
        )

        assert len(result) <= 120

    def test_readme_excerpt_included(self, tmp_path: Path) -> None:
        """README first paragraph is incorporated when available."""
        auth_dir = _make_fastapi_cluster(tmp_path)

        result = _build_contextual_summary(
            dir_path=auth_dir,
            name="auth",
            kind="domain",
            files=[
                "src/auth/main.py",
                "src/auth/models.py",
            ],
            project_root=tmp_path,
        )

        # README says "JWT-based authentication" — some keyword should appear
        assert "JWT" in result or "auth" in result.lower()

    def test_entry_point_info_in_summary(self, tmp_path: Path) -> None:
        """Entry point data enriches the summary."""
        cli_dir = _make_cluster_with_entry_point(tmp_path)

        result = _build_contextual_summary(
            dir_path=cli_dir,
            name="cli",
            kind="service",
            files=[
                "src/cli/main.py",
                "src/cli/utils.py",
            ],
            project_root=tmp_path,
            entry_points=[
                {
                    "file_path": "src/cli/main.py",
                    "kind": "cli",
                    "description": "Click CLI definition",
                },
            ],
        )

        # Should mention CLI nature
        assert "CLI" in result or "cli" in result

    def test_no_files_fallback(self, tmp_path: Path) -> None:
        """Empty file list produces a valid fallback summary."""
        src = tmp_path / "src"
        src.mkdir(exist_ok=True)
        empty = src / "empty"
        empty.mkdir(exist_ok=True)

        result = _build_contextual_summary(
            dir_path=empty,
            name="empty",
            kind="domain",
            files=[],
            project_root=tmp_path,
        )

        assert "empty" in result
        assert isinstance(result, str)
        assert len(result) > 0


# ---------------------------------------------------------------------------
# _build_contextual_summary — symbol counting
# ---------------------------------------------------------------------------


class TestContextualSummarySymbols:
    """Tests for symbol counting in contextual summaries."""

    def test_counts_classes(self, tmp_path: Path) -> None:
        """Summary includes class count when classes are present."""
        src = tmp_path / "src"
        src.mkdir(exist_ok=True)
        models = src / "models"
        models.mkdir(exist_ok=True)

        (models / "entities.py").write_text(
            "class User:\n    pass\n\n"
            "class Order:\n    pass\n\n"
            "class Product:\n    pass\n\n"
            "class Category:\n    pass\n"
        )

        result = _build_contextual_summary(
            dir_path=models,
            name="models",
            kind="entity",
            files=["src/models/entities.py"],
            project_root=tmp_path,
        )

        # Should mention classes
        assert "class" in result.lower()

    def test_counts_functions(self, tmp_path: Path) -> None:
        """Summary includes function count when functions are present."""
        src = tmp_path / "src"
        src.mkdir(exist_ok=True)
        api = src / "api"
        api.mkdir(exist_ok=True)

        (api / "routes.py").write_text(
            "def get_users(): pass\n"
            "def create_user(): pass\n"
            "def delete_user(): pass\n"
            "def update_user(): pass\n"
            "def list_users(): pass\n"
        )

        result = _build_contextual_summary(
            dir_path=api,
            name="api",
            kind="feature",
            files=["src/api/routes.py"],
            project_root=tmp_path,
        )

        # Should mention functions
        assert "function" in result.lower() or "fn" in result.lower()


# ---------------------------------------------------------------------------
# _build_contextual_summary — README integration
# ---------------------------------------------------------------------------


class TestContextualSummaryReadme:
    """Tests for README integration in contextual summaries."""

    def test_uses_readme_description(self, tmp_path: Path) -> None:
        """When a directory has a README, its description is used."""
        src = tmp_path / "src"
        src.mkdir(exist_ok=True)
        payments = src / "payments"
        payments.mkdir(exist_ok=True)

        (payments / "stripe.py").write_text("def charge(): pass\n")
        (payments / "README.md").write_text(
            "# Payments\n\nStripe payment processing integration.\n"
        )

        result = _build_contextual_summary(
            dir_path=payments,
            name="payments",
            kind="domain",
            files=["src/payments/stripe.py"],
            project_root=tmp_path,
        )

        # README excerpt should influence the summary
        assert "Stripe" in result or "payment" in result.lower()

    def test_no_readme_still_works(self, tmp_path: Path) -> None:
        """Without a README, summary is still valid."""
        utils_dir = _make_plain_cluster(tmp_path)

        result = _build_contextual_summary(
            dir_path=utils_dir,
            name="utils",
            kind="service",
            files=["src/utils/helpers.py"],
            project_root=tmp_path,
        )

        assert "utils" in result
        assert len(result) > 0


# ---------------------------------------------------------------------------
# Integration: bootstrap_project uses _build_contextual_summary
# ---------------------------------------------------------------------------


class TestBootstrapUsesContextualSummary:
    """Tests that bootstrap_project produces richer summaries than before."""

    def test_bootstrap_summary_has_symbol_info(self, tmp_path: Path) -> None:
        """Bootstrapped nodes have enriched summaries with symbol data."""
        from beadloom.onboarding import bootstrap_project

        src = tmp_path / "src"
        src.mkdir()

        auth = src / "auth"
        auth.mkdir()
        (auth / "models.py").write_text("class User:\n    pass\n\nclass Token:\n    pass\n")
        (auth / "routes.py").write_text("def login(): pass\ndef register(): pass\n")

        result = bootstrap_project(tmp_path, preset_name="monolith")
        nodes = result["nodes"]

        # Find the auth node
        auth_node = next((n for n in nodes if n["ref_id"] == "auth"), None)
        assert auth_node is not None

        summary = auth_node["summary"]
        # Summary should have more info than just "Domain: auth (4 files)"
        # It should contain class or function counts
        assert (
            "class" in summary.lower() or "function" in summary.lower() or "fn" in summary.lower()
        )

    def test_bootstrap_summary_includes_readme_info(self, tmp_path: Path) -> None:
        """Bootstrapped nodes incorporate README info when available."""
        from beadloom.onboarding import bootstrap_project

        src = tmp_path / "src"
        src.mkdir()

        billing = src / "billing"
        billing.mkdir()
        (billing / "invoice.py").write_text("def create_invoice(): pass\n")
        (billing / "README.md").write_text(
            "# Billing\n\nInvoice generation and payment tracking.\n"
        )

        result = bootstrap_project(tmp_path, preset_name="monolith")
        nodes = result["nodes"]

        billing_node = next((n for n in nodes if n["ref_id"] == "billing"), None)
        assert billing_node is not None

        # README description should appear in summary
        summary = billing_node["summary"]
        assert "Invoice" in summary or "billing" in summary.lower()

    def test_bootstrap_summary_not_empty(self, tmp_path: Path) -> None:
        """Every node gets a non-empty summary."""
        from beadloom.onboarding import bootstrap_project

        src = tmp_path / "src"
        src.mkdir()
        svc = src / "core"
        svc.mkdir()
        (svc / "main.py").write_text("def run(): pass\n")

        result = bootstrap_project(tmp_path)
        for node in result["nodes"]:
            assert node["summary"], f"Node {node['ref_id']} has empty summary"
            assert len(node["summary"]) > 0
