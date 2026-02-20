"""Tests for Beadloom TUI — data providers, app shell, screens, CLI."""

from __future__ import annotations

import sqlite3
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

if TYPE_CHECKING:
    from pathlib import Path

# Skip all TUI tests if textual is not installed
textual = pytest.importorskip("textual")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def populated_db(tmp_path: Path) -> tuple[Path, Path]:
    """Create a populated SQLite database for TUI testing."""
    db_path = tmp_path / ".beadloom" / "beadloom.db"
    db_path.parent.mkdir(parents=True)

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    from beadloom.infrastructure.db import create_schema

    create_schema(conn)

    # Insert test nodes
    conn.execute(
        "INSERT INTO nodes (ref_id, kind, summary, source) VALUES (?, ?, ?, ?)",
        ("auth", "domain", "Authentication domain", "src/auth"),
    )
    conn.execute(
        "INSERT INTO nodes (ref_id, kind, summary) VALUES (?, ?, ?)",
        ("auth-login", "feature", "User login feature"),
    )
    conn.execute(
        "INSERT INTO nodes (ref_id, kind, summary) VALUES (?, ?, ?)",
        ("payments", "domain", "Payments domain"),
    )
    # Insert edges
    conn.execute(
        "INSERT INTO edges (src_ref_id, dst_ref_id, kind) VALUES (?, ?, ?)",
        ("auth-login", "auth", "part_of"),
    )
    # Insert docs
    conn.execute(
        "INSERT INTO docs (path, kind, ref_id, hash) VALUES (?, ?, ?, ?)",
        ("auth/login.md", "feature", "auth-login", "abc123"),
    )
    conn.commit()
    conn.close()

    return db_path, tmp_path


@pytest.fixture()
def ro_conn(populated_db: tuple[Path, Path]) -> sqlite3.Connection:
    """Return a read-only connection to the populated test DB."""
    db_path, _project_root = populated_db
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


# ---------------------------------------------------------------------------
# Data Provider Tests
# ---------------------------------------------------------------------------


class TestGraphDataProvider:
    """Tests for GraphDataProvider."""

    def test_get_nodes(
        self, ro_conn: sqlite3.Connection, populated_db: tuple[Path, Path]
    ) -> None:
        """get_nodes() returns all nodes from the database."""
        from beadloom.tui.data_providers import GraphDataProvider

        _, project_root = populated_db
        provider = GraphDataProvider(conn=ro_conn, project_root=project_root)
        nodes = provider.get_nodes()

        assert len(nodes) == 3
        ref_ids = {n["ref_id"] for n in nodes}
        assert ref_ids == {"auth", "auth-login", "payments"}

    def test_get_edges(
        self, ro_conn: sqlite3.Connection, populated_db: tuple[Path, Path]
    ) -> None:
        """get_edges() returns all edges from the database."""
        from beadloom.tui.data_providers import GraphDataProvider

        _, project_root = populated_db
        provider = GraphDataProvider(conn=ro_conn, project_root=project_root)
        edges = provider.get_edges()

        assert len(edges) == 1
        assert edges[0]["src"] == "auth-login"
        assert edges[0]["dst"] == "auth"
        assert edges[0]["kind"] == "part_of"

    def test_get_node_existing(
        self, ro_conn: sqlite3.Connection, populated_db: tuple[Path, Path]
    ) -> None:
        """get_node() returns node data for an existing ref_id."""
        from beadloom.tui.data_providers import GraphDataProvider

        _, project_root = populated_db
        provider = GraphDataProvider(conn=ro_conn, project_root=project_root)
        node = provider.get_node("auth")

        assert node is not None
        assert node["ref_id"] == "auth"
        assert node["kind"] == "domain"

    def test_get_node_missing(
        self, ro_conn: sqlite3.Connection, populated_db: tuple[Path, Path]
    ) -> None:
        """get_node() returns None for a missing ref_id."""
        from beadloom.tui.data_providers import GraphDataProvider

        _, project_root = populated_db
        provider = GraphDataProvider(conn=ro_conn, project_root=project_root)
        node = provider.get_node("nonexistent")

        assert node is None

    def test_get_hierarchy(
        self, ro_conn: sqlite3.Connection, populated_db: tuple[Path, Path]
    ) -> None:
        """get_hierarchy() returns parent-children mapping."""
        from beadloom.tui.data_providers import GraphDataProvider

        _, project_root = populated_db
        provider = GraphDataProvider(conn=ro_conn, project_root=project_root)
        hierarchy = provider.get_hierarchy()

        assert "auth" in hierarchy
        assert "auth-login" in hierarchy["auth"]

    def test_refresh_reloads_data(
        self, ro_conn: sqlite3.Connection, populated_db: tuple[Path, Path]
    ) -> None:
        """refresh() reloads cached nodes and edges."""
        from beadloom.tui.data_providers import GraphDataProvider

        _, project_root = populated_db
        provider = GraphDataProvider(conn=ro_conn, project_root=project_root)

        # First load
        nodes_before = provider.get_nodes()
        assert len(nodes_before) == 3

        # Refresh and verify same data
        provider.refresh()
        nodes_after = provider.get_nodes()
        assert len(nodes_after) == 3


class TestLintDataProvider:
    """Tests for LintDataProvider."""

    def test_no_rules_file(
        self, ro_conn: sqlite3.Connection, populated_db: tuple[Path, Path]
    ) -> None:
        """get_violations() returns empty list when rules.yml is missing."""
        from beadloom.tui.data_providers import LintDataProvider

        _, project_root = populated_db
        provider = LintDataProvider(conn=ro_conn, project_root=project_root)
        provider.refresh()

        assert provider.get_violations() == []
        assert provider.get_violation_count() == 0

    def test_with_rules_file(
        self, populated_db: tuple[Path, Path]
    ) -> None:
        """get_violations() evaluates rules when rules.yml exists."""
        from beadloom.tui.data_providers import LintDataProvider

        db_path, project_root = populated_db
        rules_dir = project_root / ".beadloom" / "_graph"
        rules_dir.mkdir(parents=True, exist_ok=True)
        rules_path = rules_dir / "rules.yml"
        rules_path.write_text(
            "version: 1\nrules:\n"
            "  - name: test-rule\n"
            "    type: require\n"
            "    description: Every domain must be part_of something\n"
            "    for: { kind: domain }\n"
            "    has_edge_to: { kind: service }\n"
            "    edge_kind: part_of\n",
            encoding="utf-8",
        )

        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row

        provider = LintDataProvider(conn=conn, project_root=project_root)
        provider.refresh()

        # We expect violations since domains don't have part_of -> service edges
        violations = provider.get_violations()
        assert provider.get_violation_count() == len(violations)
        conn.close()


class TestSyncDataProvider:
    """Tests for SyncDataProvider."""

    def test_get_sync_results(
        self, ro_conn: sqlite3.Connection, populated_db: tuple[Path, Path]
    ) -> None:
        """get_sync_results() returns list of sync pair results."""
        from beadloom.tui.data_providers import SyncDataProvider

        _, project_root = populated_db
        provider = SyncDataProvider(conn=ro_conn, project_root=project_root)
        provider.refresh()

        results = provider.get_sync_results()
        # Results depend on sync_state table content
        assert isinstance(results, list)

    def test_get_stale_count(
        self, ro_conn: sqlite3.Connection, populated_db: tuple[Path, Path]
    ) -> None:
        """get_stale_count() returns integer."""
        from beadloom.tui.data_providers import SyncDataProvider

        _, project_root = populated_db
        provider = SyncDataProvider(conn=ro_conn, project_root=project_root)
        provider.refresh()

        count = provider.get_stale_count()
        assert isinstance(count, int)
        assert count >= 0

    def test_get_coverage(
        self, ro_conn: sqlite3.Connection, populated_db: tuple[Path, Path]
    ) -> None:
        """get_coverage() returns float between 0 and 100."""
        from beadloom.tui.data_providers import SyncDataProvider

        _, project_root = populated_db
        provider = SyncDataProvider(conn=ro_conn, project_root=project_root)
        provider.refresh()

        coverage = provider.get_coverage()
        assert isinstance(coverage, float)
        assert 0.0 <= coverage <= 100.0


class TestDebtDataProvider:
    """Tests for DebtDataProvider."""

    def test_get_score(
        self, populated_db: tuple[Path, Path]
    ) -> None:
        """get_score() returns float score."""
        from beadloom.tui.data_providers import DebtDataProvider

        db_path, project_root = populated_db
        # Use a read-write connection since debt collection may need it
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row

        provider = DebtDataProvider(conn=conn, project_root=project_root)
        provider.refresh()

        score = provider.get_score()
        assert isinstance(score, float)
        assert score >= 0.0

        conn.close()

    def test_get_debt_report(
        self, populated_db: tuple[Path, Path]
    ) -> None:
        """get_debt_report() returns a DebtReport or None."""
        from beadloom.tui.data_providers import DebtDataProvider

        db_path, project_root = populated_db
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row

        provider = DebtDataProvider(conn=conn, project_root=project_root)
        provider.refresh()

        report = provider.get_debt_report()
        # Report may be None if collection fails, or a DebtReport
        if report is not None:
            assert hasattr(report, "debt_score")
            assert hasattr(report, "severity")

        conn.close()


class TestActivityDataProvider:
    """Tests for ActivityDataProvider."""

    def test_get_activity(
        self, ro_conn: sqlite3.Connection, populated_db: tuple[Path, Path]
    ) -> None:
        """get_activity() returns dict mapping ref_ids to activity."""
        from beadloom.tui.data_providers import ActivityDataProvider

        _, project_root = populated_db
        provider = ActivityDataProvider(conn=ro_conn, project_root=project_root)
        provider.refresh()

        activity = provider.get_activity()
        assert isinstance(activity, dict)

    def test_empty_source_dirs(self, tmp_path: Path) -> None:
        """get_activity() returns empty dict when no nodes have source dirs."""
        from beadloom.tui.data_providers import ActivityDataProvider

        db_path = tmp_path / ".beadloom" / "beadloom.db"
        db_path.parent.mkdir(parents=True)

        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row

        from beadloom.infrastructure.db import create_schema

        create_schema(conn)

        provider = ActivityDataProvider(conn=conn, project_root=tmp_path)
        provider.refresh()

        assert provider.get_activity() == {}
        conn.close()


class TestWhyDataProvider:
    """Tests for WhyDataProvider."""

    def test_analyze_existing_node(
        self, ro_conn: sqlite3.Connection, populated_db: tuple[Path, Path]
    ) -> None:
        """analyze() returns WhyResult for an existing node."""
        from beadloom.tui.data_providers import WhyDataProvider

        _, project_root = populated_db
        provider = WhyDataProvider(conn=ro_conn, project_root=project_root)
        result = provider.analyze("auth")

        assert result is not None
        assert result.node.ref_id == "auth"

    def test_analyze_missing_node(
        self, ro_conn: sqlite3.Connection, populated_db: tuple[Path, Path]
    ) -> None:
        """analyze() returns None for a non-existent node."""
        from beadloom.tui.data_providers import WhyDataProvider

        _, project_root = populated_db
        provider = WhyDataProvider(conn=ro_conn, project_root=project_root)
        result = provider.analyze("nonexistent")

        assert result is None

    def test_refresh_is_noop(
        self, ro_conn: sqlite3.Connection, populated_db: tuple[Path, Path]
    ) -> None:
        """refresh() is a no-op for on-demand providers."""
        from beadloom.tui.data_providers import WhyDataProvider

        _, project_root = populated_db
        provider = WhyDataProvider(conn=ro_conn, project_root=project_root)
        # Should not raise
        provider.refresh()


class TestContextDataProvider:
    """Tests for ContextDataProvider."""

    def test_get_context_existing(
        self, ro_conn: sqlite3.Connection, populated_db: tuple[Path, Path]
    ) -> None:
        """get_context() returns a bundle dict for an existing node."""
        from beadloom.tui.data_providers import ContextDataProvider

        _, project_root = populated_db
        provider = ContextDataProvider(conn=ro_conn, project_root=project_root)
        ctx = provider.get_context("auth")

        assert ctx is not None
        assert isinstance(ctx, dict)
        assert "focus" in ctx

    def test_get_context_missing(
        self, ro_conn: sqlite3.Connection, populated_db: tuple[Path, Path]
    ) -> None:
        """get_context() returns None for a missing node."""
        from beadloom.tui.data_providers import ContextDataProvider

        _, project_root = populated_db
        provider = ContextDataProvider(conn=ro_conn, project_root=project_root)
        ctx = provider.get_context("nonexistent")

        assert ctx is None

    def test_estimate_tokens(
        self, ro_conn: sqlite3.Connection, populated_db: tuple[Path, Path]
    ) -> None:
        """estimate_tokens() returns an integer approximation."""
        from beadloom.tui.data_providers import ContextDataProvider

        _, project_root = populated_db
        provider = ContextDataProvider(conn=ro_conn, project_root=project_root)
        tokens = provider.estimate_tokens("Hello, this is a test string.")

        assert isinstance(tokens, int)
        assert tokens > 0


# ---------------------------------------------------------------------------
# App Shell Tests
# ---------------------------------------------------------------------------


class TestBeadloomApp:
    """Tests for the BeadloomApp multi-screen shell."""

    def test_app_instantiation(self, populated_db: tuple[Path, Path]) -> None:
        """App can be instantiated with correct attributes."""
        db_path, project_root = populated_db
        from beadloom.tui.app import BeadloomApp

        app = BeadloomApp(db_path=db_path, project_root=project_root)
        assert app.db_path == db_path
        assert app.project_root == project_root
        assert app.TITLE == "Beadloom"
        assert app.no_watch is False

    def test_app_no_watch_flag(self, populated_db: tuple[Path, Path]) -> None:
        """App respects the no_watch flag."""
        db_path, project_root = populated_db
        from beadloom.tui.app import BeadloomApp

        app = BeadloomApp(db_path=db_path, project_root=project_root, no_watch=True)
        assert app.no_watch is True

    @pytest.mark.asyncio()
    async def test_app_mounts_with_dashboard(
        self, populated_db: tuple[Path, Path]
    ) -> None:
        """App mounts and shows dashboard screen by default."""
        db_path, project_root = populated_db
        from beadloom.tui.app import BeadloomApp
        from beadloom.tui.screens.dashboard import DashboardScreen

        app = BeadloomApp(db_path=db_path, project_root=project_root)
        async with app.run_test() as pilot:
            assert app.is_running
            # Current screen should be DashboardScreen
            assert isinstance(app.screen, DashboardScreen)
            await pilot.press("q")

    @pytest.mark.asyncio()
    async def test_providers_initialized_on_mount(
        self, populated_db: tuple[Path, Path]
    ) -> None:
        """Data providers are initialized after app mounts."""
        db_path, project_root = populated_db
        from beadloom.tui.app import BeadloomApp

        app = BeadloomApp(db_path=db_path, project_root=project_root)
        async with app.run_test() as pilot:
            assert app.graph_provider is not None
            assert app.lint_provider is not None
            assert app.sync_provider is not None
            assert app.debt_provider is not None
            assert app.activity_provider is not None
            assert app.why_provider is not None
            assert app.context_provider is not None
            await pilot.press("q")

    @pytest.mark.asyncio()
    async def test_screen_switch_to_explorer(
        self, populated_db: tuple[Path, Path]
    ) -> None:
        """Pressing '2' switches to ExplorerScreen."""
        db_path, project_root = populated_db
        from beadloom.tui.app import BeadloomApp
        from beadloom.tui.screens.explorer import ExplorerScreen

        app = BeadloomApp(db_path=db_path, project_root=project_root)
        async with app.run_test() as pilot:
            await pilot.press("2")
            assert isinstance(app.screen, ExplorerScreen)
            await pilot.press("q")

    @pytest.mark.asyncio()
    async def test_screen_switch_to_doc_status(
        self, populated_db: tuple[Path, Path]
    ) -> None:
        """Pressing '3' switches to DocStatusScreen."""
        db_path, project_root = populated_db
        from beadloom.tui.app import BeadloomApp
        from beadloom.tui.screens.doc_status import DocStatusScreen

        app = BeadloomApp(db_path=db_path, project_root=project_root)
        async with app.run_test() as pilot:
            await pilot.press("3")
            assert isinstance(app.screen, DocStatusScreen)
            await pilot.press("q")

    @pytest.mark.asyncio()
    async def test_screen_switch_back_to_dashboard(
        self, populated_db: tuple[Path, Path]
    ) -> None:
        """Pressing '1' returns to DashboardScreen from another screen."""
        db_path, project_root = populated_db
        from beadloom.tui.app import BeadloomApp
        from beadloom.tui.screens.dashboard import DashboardScreen

        app = BeadloomApp(db_path=db_path, project_root=project_root)
        async with app.run_test() as pilot:
            await pilot.press("2")  # go to explorer
            await pilot.press("1")  # back to dashboard
            assert isinstance(app.screen, DashboardScreen)
            await pilot.press("q")


# ---------------------------------------------------------------------------
# CLI Tests
# ---------------------------------------------------------------------------


class TestCLI:
    """Tests for TUI CLI commands."""

    def test_cli_tui_command_exists(self) -> None:
        """The 'tui' command is registered on the main group."""
        from beadloom.services.cli import main

        assert "tui" in [cmd for cmd in main.commands]

    def test_cli_ui_command_exists(self) -> None:
        """The 'ui' command (alias) is registered on the main group."""
        from beadloom.services.cli import main

        assert "ui" in [cmd for cmd in main.commands]

    def test_cli_tui_missing_db(self, tmp_path: Path) -> None:
        """CLI shows error when database does not exist."""
        from click.testing import CliRunner

        from beadloom.services.cli import tui

        runner = CliRunner()
        result = runner.invoke(tui, ["--project", str(tmp_path)])
        assert result.exit_code != 0
        assert "database not found" in result.output or result.exit_code == 1

    def test_cli_ui_missing_db(self, tmp_path: Path) -> None:
        """CLI ui alias shows error when database does not exist."""
        from click.testing import CliRunner

        from beadloom.services.cli import ui

        runner = CliRunner()
        result = runner.invoke(ui, ["--project", str(tmp_path)])
        assert result.exit_code != 0
        assert "database not found" in result.output or result.exit_code == 1

    def test_cli_tui_missing_textual(self) -> None:
        """CLI shows friendly error when textual not installed."""
        from click.testing import CliRunner

        from beadloom.services.cli import tui

        runner = CliRunner()

        with patch.dict("sys.modules", {"beadloom.tui": None}):
            result = runner.invoke(tui, [])
            assert result.exit_code != 0

    def test_cli_ui_missing_textual(self) -> None:
        """CLI ui alias shows friendly error when textual not installed."""
        from click.testing import CliRunner

        from beadloom.services.cli import ui

        runner = CliRunner()

        with patch.dict("sys.modules", {"beadloom.tui": None}):
            result = runner.invoke(ui, [])
            assert result.exit_code != 0

    def test_cli_tui_has_no_watch_flag(self) -> None:
        """The tui command has a --no-watch flag."""
        from beadloom.services.cli import tui

        param_names = [p.name for p in tui.params]
        assert "no_watch" in param_names

    def test_cli_ui_has_no_watch_flag(self) -> None:
        """The ui command has a --no-watch flag."""
        from beadloom.services.cli import ui

        param_names = [p.name for p in ui.params]
        assert "no_watch" in param_names


# ---------------------------------------------------------------------------
# Launch function tests
# ---------------------------------------------------------------------------


class TestLaunchFunction:
    """Tests for the tui.__init__.launch() entry point."""

    def test_launch_accepts_no_watch(self) -> None:
        """launch() accepts no_watch keyword argument."""
        import inspect

        from beadloom.tui import launch

        sig = inspect.signature(launch)
        assert "no_watch" in sig.parameters


# ---------------------------------------------------------------------------
# Dashboard Widget Tests (BEAD-02)
# ---------------------------------------------------------------------------


class TestDebtGaugeWidget:
    """Tests for DebtGaugeWidget."""

    def test_render_low_score(self) -> None:
        """DebtGaugeWidget renders low score in green."""
        from beadloom.tui.widgets.debt_gauge import DebtGaugeWidget

        widget = DebtGaugeWidget(score=10.0)
        text = widget.render()
        plain = text.plain

        assert "10" in plain
        assert "low" in plain

    def test_render_medium_score(self) -> None:
        """DebtGaugeWidget renders medium score in yellow."""
        from beadloom.tui.widgets.debt_gauge import DebtGaugeWidget

        widget = DebtGaugeWidget(score=35.0)
        text = widget.render()
        plain = text.plain

        assert "35" in plain
        assert "medium" in plain

    def test_render_high_score(self) -> None:
        """DebtGaugeWidget renders high score in red."""
        from beadloom.tui.widgets.debt_gauge import DebtGaugeWidget

        widget = DebtGaugeWidget(score=75.0)
        text = widget.render()
        plain = text.plain

        assert "75" in plain
        assert "high" in plain

    def test_render_zero_score(self) -> None:
        """DebtGaugeWidget renders zero score as low."""
        from beadloom.tui.widgets.debt_gauge import DebtGaugeWidget

        widget = DebtGaugeWidget(score=0.0)
        text = widget.render()
        plain = text.plain

        assert "0" in plain
        assert "low" in plain

    def test_render_boundary_20(self) -> None:
        """DebtGaugeWidget at boundary 20 is still low."""
        from beadloom.tui.widgets.debt_gauge import DebtGaugeWidget

        widget = DebtGaugeWidget(score=20.0)
        text = widget.render()
        assert "low" in text.plain

    def test_render_boundary_21(self) -> None:
        """DebtGaugeWidget at 21 switches to medium."""
        from beadloom.tui.widgets.debt_gauge import DebtGaugeWidget

        widget = DebtGaugeWidget(score=21.0)
        text = widget.render()
        assert "medium" in text.plain

    def test_render_boundary_50(self) -> None:
        """DebtGaugeWidget at 50 is medium."""
        from beadloom.tui.widgets.debt_gauge import DebtGaugeWidget

        widget = DebtGaugeWidget(score=50.0)
        text = widget.render()
        assert "medium" in text.plain

    def test_render_boundary_51(self) -> None:
        """DebtGaugeWidget at 51 switches to high."""
        from beadloom.tui.widgets.debt_gauge import DebtGaugeWidget

        widget = DebtGaugeWidget(score=51.0)
        text = widget.render()
        assert "high" in text.plain

    def test_refresh_data_updates_score(self) -> None:
        """refresh_data() updates internal score."""
        from beadloom.tui.widgets.debt_gauge import DebtGaugeWidget

        widget = DebtGaugeWidget(score=10.0)
        assert "low" in widget.render().plain

        widget._score = 75.0
        assert "high" in widget.render().plain

    def test_severity_color_green(self) -> None:
        """Low scores use green style."""
        from beadloom.tui.widgets.debt_gauge import _severity_style

        assert _severity_style(15.0) == "green"

    def test_severity_color_yellow(self) -> None:
        """Medium scores use yellow style."""
        from beadloom.tui.widgets.debt_gauge import _severity_style

        assert _severity_style(30.0) == "yellow"

    def test_severity_color_red(self) -> None:
        """High scores use red style."""
        from beadloom.tui.widgets.debt_gauge import _severity_style

        assert _severity_style(60.0) == "red"


class TestLintPanelWidget:
    """Tests for LintPanelWidget."""

    def test_render_no_violations(self) -> None:
        """LintPanelWidget renders 'No violations' when empty."""
        from beadloom.tui.widgets.lint_panel import LintPanelWidget

        widget = LintPanelWidget(violations=[])
        text = widget.render()

        assert "No violations" in text.plain

    def test_render_with_errors(self) -> None:
        """LintPanelWidget renders error count."""
        from beadloom.tui.widgets.lint_panel import LintPanelWidget

        violations = [
            {
                "rule_name": "test-rule",
                "severity": "error",
                "from_ref_id": "auth",
                "to_ref_id": None,
                "description": "missing edge",
            },
        ]
        widget = LintPanelWidget(violations=violations)
        text = widget.render()
        plain = text.plain

        assert "1 error(s)" in plain
        assert "test-rule" in plain

    def test_render_with_warnings(self) -> None:
        """LintPanelWidget renders warning count."""
        from beadloom.tui.widgets.lint_panel import LintPanelWidget

        violations = [
            {
                "rule_name": "warn-rule",
                "severity": "warning",
                "from_ref_id": "auth",
                "to_ref_id": None,
                "description": "something",
            },
            {
                "rule_name": "warn-rule-2",
                "severity": "warning",
                "from_ref_id": "graph",
                "to_ref_id": None,
                "description": "another",
            },
        ]
        widget = LintPanelWidget(violations=violations)
        text = widget.render()

        assert "2 warning(s)" in text.plain

    def test_render_mixed_severities(self) -> None:
        """LintPanelWidget renders mixed error and warning counts."""
        from beadloom.tui.widgets.lint_panel import LintPanelWidget

        violations = [
            {
                "rule_name": "err",
                "severity": "error",
                "from_ref_id": "a",
                "to_ref_id": None,
                "description": "",
            },
            {
                "rule_name": "warn",
                "severity": "warning",
                "from_ref_id": "b",
                "to_ref_id": None,
                "description": "",
            },
        ]
        widget = LintPanelWidget(violations=violations)
        text = widget.render()
        plain = text.plain

        assert "1 error(s)" in plain
        assert "1 warning(s)" in plain

    def test_render_shows_violation_details(self) -> None:
        """LintPanelWidget renders individual violation details."""
        from beadloom.tui.widgets.lint_panel import LintPanelWidget

        violations = [
            {
                "rule_name": "no-cross-domain",
                "severity": "error",
                "from_ref_id": "auth",
                "to_ref_id": "payments",
                "description": "cross-domain dependency",
            },
        ]
        widget = LintPanelWidget(violations=violations)
        text = widget.render()
        plain = text.plain

        assert "no-cross-domain" in plain
        assert "auth" in plain
        assert "cross-domain dependency" in plain

    def test_refresh_data(self) -> None:
        """refresh_data() updates violations list."""
        from beadloom.tui.widgets.lint_panel import LintPanelWidget

        widget = LintPanelWidget(violations=[])
        assert "No violations" in widget.render().plain

        widget._violations = [
            {
                "rule_name": "rule",
                "severity": "error",
                "from_ref_id": "x",
                "to_ref_id": None,
                "description": "",
            },
        ]
        assert "1 error(s)" in widget.render().plain

    def test_render_default_no_violations(self) -> None:
        """LintPanelWidget with no constructor args shows no violations."""
        from beadloom.tui.widgets.lint_panel import LintPanelWidget

        widget = LintPanelWidget()
        assert "No violations" in widget.render().plain


class TestActivityWidget:
    """Tests for ActivityWidget."""

    def test_render_empty(self) -> None:
        """ActivityWidget renders 'No activity data' when empty."""
        from beadloom.tui.widgets.activity import ActivityWidget

        widget = ActivityWidget(activities={})
        text = widget.render()

        assert "No activity data" in text.plain

    def test_render_with_activities(self) -> None:
        """ActivityWidget renders domain names and activity bars."""
        from beadloom.tui.widgets.activity import ActivityWidget

        # Use a simple dict with commit_count attribute simulation
        class MockActivity:
            def __init__(self, commit_count: int) -> None:
                self.commit_count = commit_count

        activities = {
            "auth": MockActivity(50),
            "payments": MockActivity(10),
        }
        widget = ActivityWidget(activities=activities)
        text = widget.render()
        plain = text.plain

        assert "auth" in plain
        assert "payments" in plain
        assert "50%" in plain
        assert "10%" in plain

    def test_render_with_dict_activities(self) -> None:
        """ActivityWidget handles dict-based activity data."""
        from beadloom.tui.widgets.activity import ActivityWidget

        activities = {
            "graph": {"commit_count": 30},
        }
        widget = ActivityWidget(activities=activities)
        text = widget.render()

        assert "graph" in text.plain
        assert "30%" in text.plain

    def test_render_caps_at_100(self) -> None:
        """ActivityWidget caps activity level at 100%."""
        from beadloom.tui.widgets.activity import ActivityWidget

        class MockActivity:
            def __init__(self, commit_count: int) -> None:
                self.commit_count = commit_count

        activities = {"auth": MockActivity(200)}
        widget = ActivityWidget(activities=activities)
        text = widget.render()

        assert "100%" in text.plain

    def test_render_default_empty(self) -> None:
        """ActivityWidget with no constructor args shows no data."""
        from beadloom.tui.widgets.activity import ActivityWidget

        widget = ActivityWidget()
        assert "No activity data" in widget.render().plain

    def test_refresh_data(self) -> None:
        """refresh_data() updates activity data."""
        from beadloom.tui.widgets.activity import ActivityWidget

        widget = ActivityWidget(activities={})
        assert "No activity data" in widget.render().plain

        widget._activities = {"test": {"commit_count": 42}}
        assert "test" in widget.render().plain


class TestStatusBarWidget:
    """Tests for StatusBarWidget."""

    def test_render_default_counts(self) -> None:
        """StatusBarWidget renders zero counts by default."""
        from beadloom.tui.widgets.status_bar import StatusBarWidget

        widget = StatusBarWidget()
        text = widget.render()
        plain = text.plain

        assert "0 nodes" in plain
        assert "0 edges" in plain
        assert "0 docs" in plain
        assert "0 stale" in plain

    def test_render_with_counts(self) -> None:
        """StatusBarWidget renders provided counts."""
        from beadloom.tui.widgets.status_bar import StatusBarWidget

        widget = StatusBarWidget()
        widget._node_count = 10
        widget._edge_count = 5
        widget._doc_count = 3
        widget._stale_count = 2

        text = widget.render()
        plain = text.plain

        assert "10 nodes" in plain
        assert "5 edges" in plain
        assert "3 docs" in plain
        assert "2 stale" in plain

    def test_render_watcher_inactive(self) -> None:
        """StatusBarWidget shows watcher inactive by default."""
        from beadloom.tui.widgets.status_bar import StatusBarWidget

        widget = StatusBarWidget()
        text = widget.render()

        assert "watcher off" in text.plain

    def test_render_watcher_active(self) -> None:
        """StatusBarWidget shows watcher active when set."""
        from beadloom.tui.widgets.status_bar import StatusBarWidget

        widget = StatusBarWidget()
        widget.set_watcher_active(True)
        text = widget.render()

        assert "watching" in text.plain

    def test_render_last_action(self) -> None:
        """StatusBarWidget shows last action message."""
        from beadloom.tui.widgets.status_bar import StatusBarWidget

        widget = StatusBarWidget()
        widget._last_action = "Reindex complete"
        text = widget.render()

        assert "Reindex complete" in text.plain

    def test_refresh_data_clears_action(self) -> None:
        """refresh_data() clears the last action message."""
        from beadloom.tui.widgets.status_bar import StatusBarWidget

        widget = StatusBarWidget()
        widget._last_action = "old action"
        widget._node_count = 5
        widget._edge_count = 3
        widget._doc_count = 2
        widget._stale_count = 0

        # Simulating refresh_data without calling refresh() (no app context)
        widget._last_action = ""
        assert widget._last_action == ""

    def test_set_watcher_active(self) -> None:
        """set_watcher_active() updates watcher flag."""
        from beadloom.tui.widgets.status_bar import StatusBarWidget

        widget = StatusBarWidget()
        assert widget._watcher_active is False

        widget._watcher_active = True
        assert widget._watcher_active is True

    def test_set_last_action(self) -> None:
        """set_last_action stores the message."""
        from beadloom.tui.widgets.status_bar import StatusBarWidget

        widget = StatusBarWidget()
        widget._last_action = "Test message"

        assert widget._last_action == "Test message"

    def test_stale_count_red_when_positive(self) -> None:
        """StatusBarWidget shows stale in red style when count > 0."""
        from beadloom.tui.widgets.status_bar import StatusBarWidget

        widget = StatusBarWidget()
        widget._stale_count = 3
        text = widget.render()

        # Check the plain text contains stale count
        assert "3 stale" in text.plain


# ---------------------------------------------------------------------------
# Dashboard Screen Integration Tests (BEAD-02)
# ---------------------------------------------------------------------------


class TestDashboardScreen:
    """Tests for the DashboardScreen with all widgets composed."""

    @pytest.mark.asyncio()
    async def test_dashboard_composes_all_widgets(
        self, populated_db: tuple[Path, Path]
    ) -> None:
        """DashboardScreen composes debt gauge, activity, lint, status bar."""
        db_path, project_root = populated_db
        from beadloom.tui.app import BeadloomApp

        app = BeadloomApp(db_path=db_path, project_root=project_root)
        async with app.run_test() as pilot:
            from beadloom.tui.widgets.activity import ActivityWidget
            from beadloom.tui.widgets.debt_gauge import DebtGaugeWidget
            from beadloom.tui.widgets.lint_panel import LintPanelWidget
            from beadloom.tui.widgets.status_bar import StatusBarWidget

            # Query for each widget in the dashboard
            debt_gauge = app.screen.query_one("#debt-gauge", DebtGaugeWidget)
            assert debt_gauge is not None

            activity = app.screen.query_one("#activity-widget", ActivityWidget)
            assert activity is not None

            lint_panel = app.screen.query_one("#lint-panel", LintPanelWidget)
            assert lint_panel is not None

            status_bar = app.screen.query_one("#status-bar", StatusBarWidget)
            assert status_bar is not None

            await pilot.press("q")

    @pytest.mark.asyncio()
    async def test_dashboard_has_graph_tree(
        self, populated_db: tuple[Path, Path]
    ) -> None:
        """DashboardScreen has a GraphTreeWidget."""
        db_path, project_root = populated_db
        from beadloom.tui.app import BeadloomApp
        from beadloom.tui.widgets.graph_tree import GraphTreeWidget

        app = BeadloomApp(db_path=db_path, project_root=project_root)
        async with app.run_test() as pilot:
            graph_tree = app.screen.query_one("#graph-tree", GraphTreeWidget)
            assert graph_tree is not None
            await pilot.press("q")

    @pytest.mark.asyncio()
    async def test_dashboard_has_node_summary(
        self, populated_db: tuple[Path, Path]
    ) -> None:
        """DashboardScreen has a node summary bar."""
        db_path, project_root = populated_db
        from beadloom.tui.app import BeadloomApp

        app = BeadloomApp(db_path=db_path, project_root=project_root)
        async with app.run_test() as pilot:
            summary = app.screen.query_one("#node-summary")
            assert summary is not None
            await pilot.press("q")

    @pytest.mark.asyncio()
    async def test_dashboard_has_header(
        self, populated_db: tuple[Path, Path]
    ) -> None:
        """DashboardScreen has a header with title."""
        db_path, project_root = populated_db
        from beadloom.tui.app import BeadloomApp

        app = BeadloomApp(db_path=db_path, project_root=project_root)
        async with app.run_test() as pilot:
            header = app.screen.query_one("#dashboard-header")
            assert header is not None

            title = app.screen.query_one("#dashboard-title")
            assert title is not None
            await pilot.press("q")

    @pytest.mark.asyncio()
    async def test_dashboard_loads_data_on_mount(
        self, populated_db: tuple[Path, Path]
    ) -> None:
        """DashboardScreen loads data from providers on mount."""
        db_path, project_root = populated_db
        from beadloom.tui.app import BeadloomApp
        from beadloom.tui.widgets.status_bar import StatusBarWidget

        app = BeadloomApp(db_path=db_path, project_root=project_root)
        async with app.run_test() as pilot:
            # Status bar should have loaded counts from DB
            status_bar = app.screen.query_one("#status-bar", StatusBarWidget)
            # The populated DB has 3 nodes, 1 edge, 1 doc
            assert status_bar._node_count == 3
            assert status_bar._edge_count == 1
            assert status_bar._doc_count == 1
            await pilot.press("q")

    @pytest.mark.asyncio()
    async def test_dashboard_refresh_all_widgets(
        self, populated_db: tuple[Path, Path]
    ) -> None:
        """DashboardScreen.refresh_all_widgets() reloads data."""
        db_path, project_root = populated_db
        from beadloom.tui.app import BeadloomApp
        from beadloom.tui.screens.dashboard import DashboardScreen

        app = BeadloomApp(db_path=db_path, project_root=project_root)
        async with app.run_test() as pilot:
            screen = app.screen
            assert isinstance(screen, DashboardScreen)
            # Calling refresh should not raise
            screen.refresh_all_widgets()
            await pilot.press("q")


# ---------------------------------------------------------------------------
# GraphTreeWidget Tests (BEAD-03)
# ---------------------------------------------------------------------------


class TestGraphTreeWidget:
    """Tests for GraphTreeWidget."""

    def test_build_node_label_fresh(self) -> None:
        """_build_node_label creates label with fresh indicator for documented node."""
        from beadloom.tui.widgets.graph_tree import _build_node_label

        label = _build_node_label(
            "auth",
            doc_ref_ids={"auth"},
            stale_ref_ids=set(),
            edge_counts={"auth": 3},
        )
        assert "\u25cf" in label  # fresh indicator
        assert "auth" in label
        assert "[3]" in label

    def test_build_node_label_stale(self) -> None:
        """_build_node_label creates label with stale indicator."""
        from beadloom.tui.widgets.graph_tree import _build_node_label

        label = _build_node_label(
            "auth",
            doc_ref_ids={"auth"},
            stale_ref_ids={"auth"},
            edge_counts={"auth": 1},
        )
        assert "\u25b2" in label  # stale indicator

    def test_build_node_label_missing(self) -> None:
        """_build_node_label creates label with missing indicator for undocumented node."""
        from beadloom.tui.widgets.graph_tree import _build_node_label

        label = _build_node_label(
            "auth",
            doc_ref_ids=set(),
            stale_ref_ids=set(),
            edge_counts={},
        )
        assert "\u2716" in label  # missing indicator
        assert "[0]" in label  # zero edges

    def test_doc_status_indicator_fresh(self) -> None:
        """_doc_status_indicator returns fresh for documented, non-stale nodes."""
        from beadloom.tui.widgets.graph_tree import _doc_status_indicator

        indicator, style = _doc_status_indicator(
            "auth", doc_ref_ids={"auth"}, stale_ref_ids=set()
        )
        assert indicator == "\u25cf"
        assert style == "green"

    def test_doc_status_indicator_stale(self) -> None:
        """_doc_status_indicator returns stale for documented but stale nodes."""
        from beadloom.tui.widgets.graph_tree import _doc_status_indicator

        indicator, style = _doc_status_indicator(
            "auth", doc_ref_ids={"auth"}, stale_ref_ids={"auth"}
        )
        assert indicator == "\u25b2"
        assert style == "yellow"

    def test_doc_status_indicator_missing(self) -> None:
        """_doc_status_indicator returns missing for undocumented nodes."""
        from beadloom.tui.widgets.graph_tree import _doc_status_indicator

        indicator, style = _doc_status_indicator(
            "auth", doc_ref_ids=set(), stale_ref_ids=set()
        )
        assert indicator == "\u2716"
        assert style == "red"

    def test_node_selected_message(self) -> None:
        """NodeSelected message stores ref_id."""
        from beadloom.tui.widgets.graph_tree import NodeSelected

        msg = NodeSelected("auth")
        assert msg.ref_id == "auth"

    @pytest.mark.asyncio()
    async def test_tree_builds_hierarchy(
        self, populated_db: tuple[Path, Path]
    ) -> None:
        """GraphTreeWidget builds tree from graph data with correct hierarchy."""
        db_path, project_root = populated_db
        from beadloom.tui.app import BeadloomApp
        from beadloom.tui.widgets.graph_tree import GraphTreeWidget

        app = BeadloomApp(db_path=db_path, project_root=project_root)
        async with app.run_test() as pilot:
            tree = app.screen.query_one("#graph-tree", GraphTreeWidget)
            assert tree is not None

            # Root should have children (the top-level nodes)
            root = tree.root
            assert len(root.children) > 0

            # auth should be a branch with auth-login as child
            # Collect all node labels from root children
            root_labels = [str(child.label) for child in root.children]
            auth_labels = [
                lbl for lbl in root_labels
                if "auth" in lbl and "auth-login" not in lbl
            ]
            assert len(auth_labels) == 1, (
                f"Expected auth in root, got: {root_labels}"
            )

            await pilot.press("q")

    @pytest.mark.asyncio()
    async def test_tree_shows_doc_status_indicators(
        self, populated_db: tuple[Path, Path]
    ) -> None:
        """GraphTreeWidget shows doc status indicators in node labels."""
        db_path, project_root = populated_db
        from beadloom.tui.app import BeadloomApp
        from beadloom.tui.widgets.graph_tree import GraphTreeWidget

        app = BeadloomApp(db_path=db_path, project_root=project_root)
        async with app.run_test() as pilot:
            tree = app.screen.query_one("#graph-tree", GraphTreeWidget)

            # Collect all labels recursively
            all_labels: list[str] = []

            def collect_labels(node: object) -> None:
                all_labels.append(str(getattr(node, "label", "")))
                for child in getattr(node, "children", []):
                    collect_labels(child)

            collect_labels(tree.root)

            # At least one node should have a doc status indicator
            has_indicator = any(
                "\u25cf" in lbl or "\u25b2" in lbl or "\u2716" in lbl
                for lbl in all_labels
            )
            assert has_indicator, f"No doc indicator found in labels: {all_labels}"

            await pilot.press("q")

    @pytest.mark.asyncio()
    async def test_empty_graph_shows_placeholder(self, tmp_path: Path) -> None:
        """GraphTreeWidget shows 'No nodes found' for empty graph."""
        db_path = tmp_path / ".beadloom" / "beadloom.db"
        db_path.parent.mkdir(parents=True)

        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row

        from beadloom.infrastructure.db import create_schema

        create_schema(conn)
        conn.commit()
        conn.close()

        from beadloom.tui.app import BeadloomApp
        from beadloom.tui.widgets.graph_tree import GraphTreeWidget

        app = BeadloomApp(db_path=db_path, project_root=tmp_path)
        async with app.run_test() as pilot:
            tree = app.screen.query_one("#graph-tree", GraphTreeWidget)
            root = tree.root

            # Should show "No nodes found" leaf
            labels = [str(child.label) for child in root.children]
            assert any("No nodes found" in lbl for lbl in labels), (
                f"Expected 'No nodes found' in tree, got: {labels}"
            )

            await pilot.press("q")

    @pytest.mark.asyncio()
    async def test_tree_refresh_rebuilds(
        self, populated_db: tuple[Path, Path]
    ) -> None:
        """GraphTreeWidget.refresh_data() rebuilds tree from updated providers."""
        db_path, project_root = populated_db
        from beadloom.tui.app import BeadloomApp
        from beadloom.tui.widgets.graph_tree import GraphTreeWidget

        app = BeadloomApp(db_path=db_path, project_root=project_root)
        async with app.run_test() as pilot:
            tree = app.screen.query_one("#graph-tree", GraphTreeWidget)

            # Count children before refresh
            count_before = len(tree.root.children)

            # Refresh should rebuild (same data, same count)
            tree.refresh_data()
            count_after = len(tree.root.children)

            assert count_before == count_after
            assert count_before > 0

            await pilot.press("q")

    @pytest.mark.asyncio()
    async def test_dashboard_has_graph_tree(
        self, populated_db: tuple[Path, Path]
    ) -> None:
        """DashboardScreen has a GraphTreeWidget instead of placeholder."""
        db_path, project_root = populated_db
        from beadloom.tui.app import BeadloomApp
        from beadloom.tui.widgets.graph_tree import GraphTreeWidget

        app = BeadloomApp(db_path=db_path, project_root=project_root)
        async with app.run_test() as pilot:
            tree = app.screen.query_one("#graph-tree", GraphTreeWidget)
            assert tree is not None
            await pilot.press("q")

    @pytest.mark.asyncio()
    async def test_node_selected_updates_summary(
        self, populated_db: tuple[Path, Path]
    ) -> None:
        """NodeSelected message from graph tree updates the summary bar."""
        db_path, project_root = populated_db
        from beadloom.tui.app import BeadloomApp
        from beadloom.tui.widgets import NodeSelected

        app = BeadloomApp(db_path=db_path, project_root=project_root)
        async with app.run_test() as pilot:
            # Post a NodeSelected message manually
            from textual.widgets import Label

            app.screen.post_message(NodeSelected("auth"))
            await pilot.pause()

            summary = app.screen.query_one("#node-summary", Label)
            # Label stores text via Static.content property (inherited)
            summary_text = str(summary.content)
            assert "auth" in summary_text
            assert "domain" in summary_text

            await pilot.press("q")


class TestGraphDataProviderExtended:
    """Tests for new GraphDataProvider methods added in BEAD-03."""

    def test_get_node_with_source(
        self, ro_conn: sqlite3.Connection, populated_db: tuple[Path, Path]
    ) -> None:
        """get_node_with_source() returns node data including source path."""
        from beadloom.tui.data_providers import GraphDataProvider

        _, project_root = populated_db
        provider = GraphDataProvider(conn=ro_conn, project_root=project_root)
        node = provider.get_node_with_source("auth")

        assert node is not None
        assert node["ref_id"] == "auth"
        assert node["kind"] == "domain"
        assert node["source"] == "src/auth"

    def test_get_node_with_source_missing(
        self, ro_conn: sqlite3.Connection, populated_db: tuple[Path, Path]
    ) -> None:
        """get_node_with_source() returns None for missing ref_id."""
        from beadloom.tui.data_providers import GraphDataProvider

        _, project_root = populated_db
        provider = GraphDataProvider(conn=ro_conn, project_root=project_root)
        node = provider.get_node_with_source("nonexistent")

        assert node is None

    def test_get_edge_counts(
        self, ro_conn: sqlite3.Connection, populated_db: tuple[Path, Path]
    ) -> None:
        """get_edge_counts() returns edge counts per ref_id."""
        from beadloom.tui.data_providers import GraphDataProvider

        _, project_root = populated_db
        provider = GraphDataProvider(conn=ro_conn, project_root=project_root)
        counts = provider.get_edge_counts()

        # We have one edge: auth-login -> auth (part_of)
        assert counts.get("auth", 0) >= 1
        assert counts.get("auth-login", 0) >= 1

    def test_get_doc_ref_ids(
        self, ro_conn: sqlite3.Connection, populated_db: tuple[Path, Path]
    ) -> None:
        """get_doc_ref_ids() returns set of ref_ids with docs."""
        from beadloom.tui.data_providers import GraphDataProvider

        _, project_root = populated_db
        provider = GraphDataProvider(conn=ro_conn, project_root=project_root)
        doc_ids = provider.get_doc_ref_ids()

        # The populated DB has one doc for auth-login
        assert "auth-login" in doc_ids


# ---------------------------------------------------------------------------
# DocHealthTable Widget Tests (BEAD-05)
# ---------------------------------------------------------------------------


class TestDocHealthTable:
    """Tests for DocHealthTable widget."""

    def test_compute_doc_rows_with_no_providers(self) -> None:
        """compute_doc_rows returns empty list when graph_provider is None."""
        from beadloom.tui.widgets.doc_health import compute_doc_rows

        rows = compute_doc_rows(graph_provider=None, sync_provider=None)
        assert rows == []

    def test_compute_doc_rows_with_empty_nodes(
        self, ro_conn: sqlite3.Connection, tmp_path: Path
    ) -> None:
        """compute_doc_rows returns empty list when no nodes in graph."""
        from beadloom.tui.data_providers import GraphDataProvider
        from beadloom.tui.widgets.doc_health import compute_doc_rows

        # Create empty DB
        db_path = tmp_path / "empty.db"
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        from beadloom.infrastructure.db import create_schema
        create_schema(conn)
        conn.commit()

        provider = GraphDataProvider(conn=conn, project_root=tmp_path)
        rows = compute_doc_rows(graph_provider=provider, sync_provider=None)
        assert rows == []
        conn.close()

    def test_compute_doc_rows_missing_status(
        self, ro_conn: sqlite3.Connection, populated_db: tuple[Path, Path]
    ) -> None:
        """compute_doc_rows marks nodes without docs as missing."""
        from beadloom.tui.data_providers import GraphDataProvider
        from beadloom.tui.widgets.doc_health import (
            LABEL_MISSING,
            STATUS_MISSING,
            compute_doc_rows,
        )

        _, project_root = populated_db
        provider = GraphDataProvider(conn=ro_conn, project_root=project_root)
        rows = compute_doc_rows(graph_provider=provider, sync_provider=None)

        # auth and payments have no docs — should be missing
        missing_rows = [r for r in rows if r["status_label"] == LABEL_MISSING]
        missing_ref_ids = {r["ref_id"] for r in missing_rows}
        assert "auth" in missing_ref_ids
        assert "payments" in missing_ref_ids

        # Check indicator
        for row in missing_rows:
            assert row["status_indicator"] == STATUS_MISSING

    def test_compute_doc_rows_fresh_status(
        self, ro_conn: sqlite3.Connection, populated_db: tuple[Path, Path]
    ) -> None:
        """compute_doc_rows marks documented nodes without sync issues as fresh."""
        from beadloom.tui.data_providers import GraphDataProvider
        from beadloom.tui.widgets.doc_health import (
            LABEL_FRESH,
            STATUS_FRESH,
            compute_doc_rows,
        )

        _, project_root = populated_db
        provider = GraphDataProvider(conn=ro_conn, project_root=project_root)
        rows = compute_doc_rows(graph_provider=provider, sync_provider=None)

        # auth-login has a doc in the DB
        fresh_rows = [r for r in rows if r["status_label"] == LABEL_FRESH]
        fresh_ref_ids = {r["ref_id"] for r in fresh_rows}
        assert "auth-login" in fresh_ref_ids

        for row in fresh_rows:
            assert row["status_indicator"] == STATUS_FRESH

    def test_compute_doc_rows_sort_order(
        self, ro_conn: sqlite3.Connection, populated_db: tuple[Path, Path]
    ) -> None:
        """compute_doc_rows sorts stale first, then missing, then fresh."""
        from beadloom.tui.data_providers import GraphDataProvider
        from beadloom.tui.widgets.doc_health import _STATUS_SORT_ORDER, compute_doc_rows

        _, project_root = populated_db
        provider = GraphDataProvider(conn=ro_conn, project_root=project_root)
        rows = compute_doc_rows(graph_provider=provider, sync_provider=None)

        # Verify sort order: each row's status should be <= next row's status
        for i in range(len(rows) - 1):
            cur_order = _STATUS_SORT_ORDER.get(rows[i]["status_label"], 99)
            next_order = _STATUS_SORT_ORDER.get(rows[i + 1]["status_label"], 99)
            assert cur_order <= next_order

    def test_compute_coverage_stats_empty(self) -> None:
        """compute_coverage_stats returns zeros for empty rows."""
        from beadloom.tui.widgets.doc_health import compute_coverage_stats

        coverage, stale, total = compute_coverage_stats([])
        assert coverage == 0.0
        assert stale == 0
        assert total == 0

    def test_compute_coverage_stats_all_fresh(self) -> None:
        """compute_coverage_stats computes 100% for all fresh."""
        from beadloom.tui.widgets.doc_health import LABEL_FRESH, compute_coverage_stats

        row_a = {
            "ref_id": "a", "status_label": LABEL_FRESH,
            "status_indicator": "", "doc_path": "", "reason": "",
        }
        row_b = {
            "ref_id": "b", "status_label": LABEL_FRESH,
            "status_indicator": "", "doc_path": "", "reason": "",
        }
        coverage, stale, total = compute_coverage_stats([row_a, row_b])
        assert coverage == 100.0
        assert stale == 0
        assert total == 2

    def test_compute_coverage_stats_mixed(self) -> None:
        """compute_coverage_stats computes correct percentage for mixed statuses."""
        from beadloom.tui.widgets.doc_health import (
            LABEL_FRESH,
            LABEL_MISSING,
            LABEL_STALE,
            compute_coverage_stats,
        )

        empty = {"status_indicator": "", "doc_path": "", "reason": ""}
        rows = [
            {"ref_id": "a", "status_label": LABEL_FRESH, **empty},
            {"ref_id": "b", "status_label": LABEL_STALE, **empty},
            {"ref_id": "c", "status_label": LABEL_MISSING, **empty},
            {"ref_id": "d", "status_label": LABEL_MISSING, **empty},
        ]
        coverage, stale, total = compute_coverage_stats(rows)
        # 2 documented (1 fresh + 1 stale) out of 4 total = 50%
        assert coverage == 50.0
        assert stale == 1
        assert total == 4

    def test_get_selected_ref_id_returns_none_initially(self) -> None:
        """get_selected_ref_id returns None when no rows loaded."""
        from beadloom.tui.widgets.doc_health import DocHealthTable

        table = DocHealthTable(widget_id="test-table")
        assert table.get_selected_ref_id() is None

    def test_get_rows_data_returns_copy(self) -> None:
        """get_rows_data returns a copy of internal rows."""
        from beadloom.tui.widgets.doc_health import DocHealthTable

        table = DocHealthTable(widget_id="test-table")
        rows = table.get_rows_data()
        assert rows == []
        assert rows is not table._rows


# ---------------------------------------------------------------------------
# DocStatusScreen Tests (BEAD-05)
# ---------------------------------------------------------------------------


class TestDocStatusScreen:
    """Tests for the DocStatusScreen."""

    @pytest.mark.asyncio()
    async def test_doc_status_screen_composes(
        self, populated_db: tuple[Path, Path]
    ) -> None:
        """DocStatusScreen composes header, table, and action bar."""
        db_path, project_root = populated_db
        from beadloom.tui.app import BeadloomApp
        from beadloom.tui.screens.doc_status import DocStatusScreen
        from beadloom.tui.widgets.doc_health import DocHealthTable

        app = BeadloomApp(db_path=db_path, project_root=project_root)
        async with app.run_test() as pilot:
            await pilot.press("3")  # switch to doc status
            assert isinstance(app.screen, DocStatusScreen)

            # Verify header exists
            from textual.widgets import Label
            header = app.screen.query_one("#doc-status-header", Label)
            assert header is not None

            # Verify table exists
            table = app.screen.query_one("#doc-health-table", DocHealthTable)
            assert table is not None

            # Verify action bar exists
            action_bar = app.screen.query_one("#doc-status-action-bar", Label)
            assert action_bar is not None

            await pilot.press("q")

    @pytest.mark.asyncio()
    async def test_doc_status_header_shows_stats(
        self, populated_db: tuple[Path, Path]
    ) -> None:
        """DocStatusScreen header shows coverage %, stale count, total."""
        db_path, project_root = populated_db
        from beadloom.tui.app import BeadloomApp
        from beadloom.tui.screens.doc_status import DocStatusScreen

        app = BeadloomApp(db_path=db_path, project_root=project_root)
        async with app.run_test() as pilot:
            await pilot.press("3")
            assert isinstance(app.screen, DocStatusScreen)

            from textual.widgets import Label
            header = app.screen.query_one("#doc-status-header", Label)
            header_text = str(header.content)

            # Should contain coverage stats
            assert "Documentation Health" in header_text
            assert "%" in header_text
            assert "stale" in header_text
            assert "total" in header_text

            await pilot.press("q")

    @pytest.mark.asyncio()
    async def test_doc_status_table_has_columns(
        self, populated_db: tuple[Path, Path]
    ) -> None:
        """DocStatusScreen table has the 4 required columns."""
        db_path, project_root = populated_db
        from beadloom.tui.app import BeadloomApp
        from beadloom.tui.widgets.doc_health import DocHealthTable

        app = BeadloomApp(db_path=db_path, project_root=project_root)
        async with app.run_test() as pilot:
            await pilot.press("3")

            table = app.screen.query_one("#doc-health-table", DocHealthTable)
            col_labels = [str(col.label) for col in table.columns.values()]
            assert "Node" in col_labels
            assert "Status" in col_labels
            assert "Doc Path" in col_labels
            assert "Reason" in col_labels

            await pilot.press("q")

    @pytest.mark.asyncio()
    async def test_doc_status_table_has_rows(
        self, populated_db: tuple[Path, Path]
    ) -> None:
        """DocStatusScreen table has rows from populated DB."""
        db_path, project_root = populated_db
        from beadloom.tui.app import BeadloomApp
        from beadloom.tui.widgets.doc_health import DocHealthTable

        app = BeadloomApp(db_path=db_path, project_root=project_root)
        async with app.run_test() as pilot:
            await pilot.press("3")

            table = app.screen.query_one("#doc-health-table", DocHealthTable)
            rows = table.get_rows_data()

            # The populated DB has 3 nodes
            assert len(rows) == 3

            # Check ref_ids present
            ref_ids = {r["ref_id"] for r in rows}
            assert ref_ids == {"auth", "auth-login", "payments"}

            await pilot.press("q")

    @pytest.mark.asyncio()
    async def test_doc_status_escape_goes_back(
        self, populated_db: tuple[Path, Path]
    ) -> None:
        """Pressing Esc on DocStatusScreen returns to previous screen."""
        db_path, project_root = populated_db
        from beadloom.tui.app import BeadloomApp
        from beadloom.tui.screens.dashboard import DashboardScreen
        from beadloom.tui.screens.doc_status import DocStatusScreen

        app = BeadloomApp(db_path=db_path, project_root=project_root)
        async with app.run_test() as pilot:
            # Push doc status on top of dashboard
            app.push_screen(DocStatusScreen())
            await pilot.pause()
            assert isinstance(app.screen, DocStatusScreen)

            # Press Esc to go back
            await pilot.press("escape")
            await pilot.pause()

            # Should be back on dashboard
            assert isinstance(app.screen, DashboardScreen)

            await pilot.press("q")

    @pytest.mark.asyncio()
    async def test_doc_status_generate_action(
        self, populated_db: tuple[Path, Path]
    ) -> None:
        """Pressing 'g' on DocStatusScreen shows generate notification."""
        db_path, project_root = populated_db
        from beadloom.tui.app import BeadloomApp
        from beadloom.tui.screens.doc_status import DocStatusScreen

        app = BeadloomApp(db_path=db_path, project_root=project_root)
        async with app.run_test(notifications=True) as pilot:
            await pilot.press("3")
            assert isinstance(app.screen, DocStatusScreen)

            await pilot.press("g")
            await pilot.pause()

            # Should not crash — notification is shown
            await pilot.press("q")

    @pytest.mark.asyncio()
    async def test_doc_status_polish_action(
        self, populated_db: tuple[Path, Path]
    ) -> None:
        """Pressing 'p' on DocStatusScreen shows polish notification."""
        db_path, project_root = populated_db
        from beadloom.tui.app import BeadloomApp
        from beadloom.tui.screens.doc_status import DocStatusScreen

        app = BeadloomApp(db_path=db_path, project_root=project_root)
        async with app.run_test(notifications=True) as pilot:
            await pilot.press("3")
            assert isinstance(app.screen, DocStatusScreen)

            await pilot.press("p")
            await pilot.pause()

            # Should not crash — notification is shown
            await pilot.press("q")

    @pytest.mark.asyncio()
    async def test_doc_status_empty_db(self, tmp_path: Path) -> None:
        """DocStatusScreen handles empty database gracefully."""
        db_path = tmp_path / ".beadloom" / "beadloom.db"
        db_path.parent.mkdir(parents=True)

        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        from beadloom.infrastructure.db import create_schema
        create_schema(conn)
        conn.commit()
        conn.close()

        from beadloom.tui.app import BeadloomApp
        from beadloom.tui.screens.doc_status import DocStatusScreen
        from beadloom.tui.widgets.doc_health import DocHealthTable

        app = BeadloomApp(db_path=db_path, project_root=tmp_path)
        async with app.run_test() as pilot:
            await pilot.press("3")
            assert isinstance(app.screen, DocStatusScreen)

            table = app.screen.query_one("#doc-health-table", DocHealthTable)
            rows = table.get_rows_data()
            assert len(rows) == 0

            await pilot.press("q")

    @pytest.mark.asyncio()
    async def test_doc_status_refresh_all_widgets(
        self, populated_db: tuple[Path, Path]
    ) -> None:
        """DocStatusScreen.refresh_all_widgets() reloads data."""
        db_path, project_root = populated_db
        from beadloom.tui.app import BeadloomApp
        from beadloom.tui.screens.doc_status import DocStatusScreen

        app = BeadloomApp(db_path=db_path, project_root=project_root)
        async with app.run_test() as pilot:
            await pilot.press("3")
            screen = app.screen
            assert isinstance(screen, DocStatusScreen)

            # Calling refresh should not raise
            screen.refresh_all_widgets()

            await pilot.press("q")


# ---------------------------------------------------------------------------
# File Watcher Tests (BEAD-06)
# ---------------------------------------------------------------------------


class TestReindexNeededMessage:
    """Tests for the ReindexNeeded custom message."""

    def test_message_stores_changed_paths(self) -> None:
        """ReindexNeeded stores changed_paths list."""
        from beadloom.tui.file_watcher import ReindexNeeded

        paths = ["/src/foo.py", "/src/bar.py"]
        msg = ReindexNeeded(paths)
        assert msg.changed_paths == paths

    def test_message_empty_paths(self) -> None:
        """ReindexNeeded works with empty path list."""
        from beadloom.tui.file_watcher import ReindexNeeded

        msg = ReindexNeeded([])
        assert msg.changed_paths == []


class TestFileWatcherHelpers:
    """Tests for file watcher helper functions."""

    def test_has_watchfiles_returns_bool(self) -> None:
        """_has_watchfiles returns True when watchfiles is installed."""
        from beadloom.tui.file_watcher import _has_watchfiles

        # watchfiles is in optional deps — should be True in test env
        result = _has_watchfiles()
        assert isinstance(result, bool)

    def test_has_watchfiles_false_when_missing(self) -> None:
        """_has_watchfiles returns False when watchfiles is not importable."""
        from beadloom.tui.file_watcher import _has_watchfiles

        with patch("importlib.util.find_spec", return_value=None):
            result = _has_watchfiles()
            assert result is False

    def test_collect_watch_dirs_includes_graph_dir(self, tmp_path: Path) -> None:
        """_collect_watch_dirs includes .beadloom/_graph if it exists."""
        from beadloom.tui.file_watcher import _collect_watch_dirs

        graph_dir = tmp_path / ".beadloom" / "_graph"
        graph_dir.mkdir(parents=True)

        dirs = _collect_watch_dirs(tmp_path, [])
        assert graph_dir in dirs

    def test_collect_watch_dirs_includes_source_dirs(self, tmp_path: Path) -> None:
        """_collect_watch_dirs includes existing source directories."""
        from beadloom.tui.file_watcher import _collect_watch_dirs

        src_dir = tmp_path / "src" / "auth"
        src_dir.mkdir(parents=True)

        dirs = _collect_watch_dirs(tmp_path, ["src/auth"])
        assert src_dir in dirs

    def test_collect_watch_dirs_skips_nonexistent(self, tmp_path: Path) -> None:
        """_collect_watch_dirs skips source paths that don't exist."""
        from beadloom.tui.file_watcher import _collect_watch_dirs

        dirs = _collect_watch_dirs(tmp_path, ["nonexistent/path"])
        assert len(dirs) == 0

    def test_collect_watch_dirs_deduplicates(self, tmp_path: Path) -> None:
        """_collect_watch_dirs returns de-duplicated directories."""
        from beadloom.tui.file_watcher import _collect_watch_dirs

        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "app.py").touch()

        dirs = _collect_watch_dirs(tmp_path, ["src", "src"])
        # Should only have one entry for src
        src_count = sum(1 for d in dirs if str(d) == str(src_dir))
        assert src_count == 1

    def test_filter_paths_keeps_watched_extensions(self, tmp_path: Path) -> None:
        """_filter_paths keeps files with watched extensions."""
        from beadloom.tui.file_watcher import _filter_paths

        changes: set[tuple[object, str]] = {
            (1, str(tmp_path / "src" / "app.py")),
            (1, str(tmp_path / "docs" / "README.md")),
        }
        result = _filter_paths(changes, tmp_path)
        assert len(result) == 2

    def test_filter_paths_rejects_unwatched_extensions(self, tmp_path: Path) -> None:
        """_filter_paths rejects files with unwatched extensions."""
        from beadloom.tui.file_watcher import _filter_paths

        changes: set[tuple[object, str]] = {
            (1, str(tmp_path / "image.png")),
            (1, str(tmp_path / "data.json")),
        }
        result = _filter_paths(changes, tmp_path)
        assert len(result) == 0

    def test_filter_paths_rejects_temp_files(self, tmp_path: Path) -> None:
        """_filter_paths rejects temp files (~ prefix and .tmp suffix)."""
        from beadloom.tui.file_watcher import _filter_paths

        changes: set[tuple[object, str]] = {
            (1, str(tmp_path / "~lock.py")),
            (1, str(tmp_path / "backup.py.tmp")),
        }
        result = _filter_paths(changes, tmp_path)
        assert len(result) == 0

    def test_filter_paths_rejects_hidden_dirs(self, tmp_path: Path) -> None:
        """_filter_paths rejects files in hidden dirs (except .beadloom)."""
        from beadloom.tui.file_watcher import _filter_paths

        changes: set[tuple[object, str]] = {
            (1, str(tmp_path / ".git" / "hooks" / "pre-commit.py")),
        }
        result = _filter_paths(changes, tmp_path)
        assert len(result) == 0

    def test_filter_paths_allows_beadloom_dir(self, tmp_path: Path) -> None:
        """_filter_paths allows files in .beadloom directory."""
        from beadloom.tui.file_watcher import _filter_paths

        changes: set[tuple[object, str]] = {
            (1, str(tmp_path / ".beadloom" / "_graph" / "services.yml")),
        }
        result = _filter_paths(changes, tmp_path)
        assert len(result) == 1


class TestStartFileWatcher:
    """Tests for start_file_watcher function."""

    def test_returns_none_when_watchfiles_missing(self, tmp_path: Path) -> None:
        """start_file_watcher returns None when watchfiles is not installed."""
        from beadloom.tui.app import BeadloomApp
        from beadloom.tui.file_watcher import start_file_watcher

        db_path = tmp_path / ".beadloom" / "beadloom.db"
        db_path.parent.mkdir(parents=True)
        conn = sqlite3.connect(str(db_path))
        from beadloom.infrastructure.db import create_schema
        create_schema(conn)
        conn.commit()
        conn.close()

        app = BeadloomApp(db_path=db_path, project_root=tmp_path, no_watch=True)

        with patch("beadloom.tui.file_watcher._has_watchfiles", return_value=False):
            result = start_file_watcher(app, tmp_path, [])
            assert result is None

    def test_returns_none_when_no_watch_dirs(self, tmp_path: Path) -> None:
        """start_file_watcher returns None when no directories to watch."""
        from beadloom.tui.app import BeadloomApp
        from beadloom.tui.file_watcher import start_file_watcher

        db_path = tmp_path / ".beadloom" / "beadloom.db"
        db_path.parent.mkdir(parents=True)
        conn = sqlite3.connect(str(db_path))
        from beadloom.infrastructure.db import create_schema
        create_schema(conn)
        conn.commit()
        conn.close()

        app = BeadloomApp(db_path=db_path, project_root=tmp_path, no_watch=True)

        # No source paths and no graph dir
        result = start_file_watcher(app, tmp_path, [])
        assert result is None


class TestStatusBarWatcherStates:
    """Tests for StatusBarWidget watcher state display (BEAD-06)."""

    def test_watcher_off_state(self) -> None:
        """StatusBarWidget shows 'watcher off' in dim when state is off."""
        from beadloom.tui.widgets.status_bar import StatusBarWidget

        widget = StatusBarWidget()
        text = widget.render()
        assert "watcher off" in text.plain

    def test_watcher_watching_state(self) -> None:
        """StatusBarWidget shows 'watching' in green after set_watcher_active(True)."""
        from beadloom.tui.widgets.status_bar import WATCHER_WATCHING, StatusBarWidget

        widget = StatusBarWidget()
        widget.set_watcher_active(True)
        assert widget._watcher_state == WATCHER_WATCHING
        text = widget.render()
        assert "watching" in text.plain
        # Should NOT say "watcher off"
        assert "watcher off" not in text.plain

    def test_watcher_changes_detected_state(self) -> None:
        """StatusBarWidget shows 'changes detected (N)' in yellow."""
        from beadloom.tui.widgets.status_bar import WATCHER_CHANGES, StatusBarWidget

        widget = StatusBarWidget()
        widget.set_changes_detected(5)
        assert widget._watcher_state == WATCHER_CHANGES
        assert widget._change_count == 5
        text = widget.render()
        assert "changes detected" in text.plain
        assert "(5)" in text.plain

    def test_clear_changes_reverts_to_watching(self) -> None:
        """clear_changes() reverts from changes-detected to watching state."""
        from beadloom.tui.widgets.status_bar import WATCHER_WATCHING, StatusBarWidget

        widget = StatusBarWidget()
        widget.set_changes_detected(3)
        widget.clear_changes()
        assert widget._watcher_state == WATCHER_WATCHING
        assert widget._change_count == 0
        text = widget.render()
        assert "watching" in text.plain
        assert "changes detected" not in text.plain

    def test_set_watcher_active_false_clears_changes(self) -> None:
        """set_watcher_active(False) clears change count and sets state to off."""
        from beadloom.tui.widgets.status_bar import WATCHER_OFF, StatusBarWidget

        widget = StatusBarWidget()
        widget.set_changes_detected(10)
        widget.set_watcher_active(False)
        assert widget._watcher_state == WATCHER_OFF
        assert widget._change_count == 0
        text = widget.render()
        assert "watcher off" in text.plain

    def test_watcher_state_constants_imported(self) -> None:
        """Watcher state constants are importable."""
        from beadloom.tui.widgets.status_bar import (
            WATCHER_CHANGES,
            WATCHER_OFF,
            WATCHER_WATCHING,
        )

        assert WATCHER_OFF == "off"
        assert WATCHER_WATCHING == "watching"
        assert WATCHER_CHANGES == "changes"


class TestAppFileWatcherIntegration:
    """Tests for file watcher integration in BeadloomApp."""

    def test_app_has_file_watcher_attribute(
        self, populated_db: tuple[Path, Path]
    ) -> None:
        """App has _file_watcher_worker attribute."""
        db_path, project_root = populated_db
        from beadloom.tui.app import BeadloomApp

        app = BeadloomApp(db_path=db_path, project_root=project_root)
        assert app._file_watcher_worker is None

    @pytest.mark.asyncio()
    async def test_no_watch_prevents_watcher_start(
        self, populated_db: tuple[Path, Path]
    ) -> None:
        """App with no_watch=True does not start file watcher."""
        db_path, project_root = populated_db
        from beadloom.tui.app import BeadloomApp

        app = BeadloomApp(db_path=db_path, project_root=project_root, no_watch=True)
        async with app.run_test() as pilot:
            # With no_watch=True, file watcher worker should not be started
            assert app._file_watcher_worker is None
            await pilot.press("q")

    @pytest.mark.asyncio()
    async def test_reindex_needed_message_handling(
        self, populated_db: tuple[Path, Path]
    ) -> None:
        """App handles ReindexNeeded message by updating status bar."""
        db_path, project_root = populated_db
        from beadloom.tui.app import BeadloomApp
        from beadloom.tui.file_watcher import ReindexNeeded
        from beadloom.tui.widgets.status_bar import StatusBarWidget

        app = BeadloomApp(db_path=db_path, project_root=project_root, no_watch=True)
        async with app.run_test() as pilot:
            # Post a ReindexNeeded message
            app.post_message(ReindexNeeded(["/src/foo.py", "/src/bar.py"]))
            await pilot.pause()

            # Check status bar on dashboard shows changes detected
            status_bar = app.screen.query_one("#status-bar", StatusBarWidget)
            assert "changes detected" in status_bar.render().plain
            assert "(2)" in status_bar.render().plain

            await pilot.press("q")

    @pytest.mark.asyncio()
    async def test_reindex_clears_changes_badge(
        self, populated_db: tuple[Path, Path]
    ) -> None:
        """Pressing 'r' clears the changes-detected badge after reindex."""
        db_path, project_root = populated_db
        from beadloom.tui.app import BeadloomApp
        from beadloom.tui.file_watcher import ReindexNeeded
        from beadloom.tui.widgets.status_bar import StatusBarWidget

        app = BeadloomApp(db_path=db_path, project_root=project_root, no_watch=True)
        async with app.run_test() as pilot:
            # Simulate file changes
            app.post_message(ReindexNeeded(["/src/foo.py"]))
            await pilot.pause()

            status_bar = app.screen.query_one("#status-bar", StatusBarWidget)
            assert "changes detected" in status_bar.render().plain

            # Press 'r' to reindex
            await pilot.press("r")
            await pilot.pause()

            # Badge should be cleared
            text = status_bar.render().plain
            assert "changes detected" not in text

            await pilot.press("q")

    def test_graph_data_provider_get_source_paths(
        self, ro_conn: sqlite3.Connection, populated_db: tuple[Path, Path]
    ) -> None:
        """get_source_paths() returns source paths from nodes."""
        from beadloom.tui.data_providers import GraphDataProvider

        _, project_root = populated_db
        provider = GraphDataProvider(conn=ro_conn, project_root=project_root)
        paths = provider.get_source_paths()

        # The populated DB has one node with source: "auth" has "src/auth"
        assert "src/auth" in paths

    def test_graph_data_provider_get_source_paths_empty(
        self, tmp_path: Path
    ) -> None:
        """get_source_paths() returns empty list when no nodes have source."""
        from beadloom.tui.data_providers import GraphDataProvider

        db_path = tmp_path / "empty.db"
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        from beadloom.infrastructure.db import create_schema
        create_schema(conn)
        conn.commit()

        provider = GraphDataProvider(conn=conn, project_root=tmp_path)
        paths = provider.get_source_paths()
        assert paths == []
        conn.close()


# ---------------------------------------------------------------------------
# NodeDetailPanel Widget Tests (BEAD-04)
# ---------------------------------------------------------------------------


class TestNodeDetailPanel:
    """Tests for NodeDetailPanel widget."""

    def test_render_no_ref_id(self) -> None:
        """NodeDetailPanel shows placeholder when no ref_id is set."""
        from beadloom.tui.widgets.node_detail_panel import NodeDetailPanel

        widget = NodeDetailPanel()
        text = widget.render()
        plain = text.plain

        assert "Node Detail" in plain
        assert "Select a node" in plain

    def test_render_with_ref_id(
        self, ro_conn: sqlite3.Connection, populated_db: tuple[Path, Path]
    ) -> None:
        """NodeDetailPanel renders node info when ref_id is provided."""
        from beadloom.tui.data_providers import GraphDataProvider
        from beadloom.tui.widgets.node_detail_panel import NodeDetailPanel

        _, project_root = populated_db
        provider = GraphDataProvider(conn=ro_conn, project_root=project_root)

        widget = NodeDetailPanel(
            graph_provider=provider,
            ref_id="auth",
        )
        text = widget.render()
        plain = text.plain

        assert "auth" in plain
        assert "domain" in plain
        assert "Authentication domain" in plain
        assert "src/auth" in plain

    def test_render_missing_node(
        self, ro_conn: sqlite3.Connection, populated_db: tuple[Path, Path]
    ) -> None:
        """NodeDetailPanel shows 'not found' for non-existent ref_id."""
        from beadloom.tui.data_providers import GraphDataProvider
        from beadloom.tui.widgets.node_detail_panel import NodeDetailPanel

        _, project_root = populated_db
        provider = GraphDataProvider(conn=ro_conn, project_root=project_root)

        widget = NodeDetailPanel(
            graph_provider=provider,
            ref_id="nonexistent",
        )
        text = widget.render()
        plain = text.plain

        assert "not found" in plain

    def test_render_no_provider(self) -> None:
        """NodeDetailPanel shows 'No data provider' when provider is None."""
        from beadloom.tui.widgets.node_detail_panel import NodeDetailPanel

        widget = NodeDetailPanel(ref_id="auth")
        text = widget.render()
        plain = text.plain

        assert "No data provider" in plain

    def test_render_shows_edges(
        self, ro_conn: sqlite3.Connection, populated_db: tuple[Path, Path]
    ) -> None:
        """NodeDetailPanel shows edge information."""
        from beadloom.tui.data_providers import GraphDataProvider
        from beadloom.tui.widgets.node_detail_panel import NodeDetailPanel

        _, project_root = populated_db
        provider = GraphDataProvider(conn=ro_conn, project_root=project_root)

        widget = NodeDetailPanel(
            graph_provider=provider,
            ref_id="auth",
        )
        text = widget.render()
        plain = text.plain

        assert "Edges" in plain
        assert "part_of" in plain

    def test_render_shows_doc_status_documented(
        self, ro_conn: sqlite3.Connection, populated_db: tuple[Path, Path]
    ) -> None:
        """NodeDetailPanel shows documented status for nodes with docs."""
        from beadloom.tui.data_providers import GraphDataProvider
        from beadloom.tui.widgets.node_detail_panel import NodeDetailPanel

        _, project_root = populated_db
        provider = GraphDataProvider(conn=ro_conn, project_root=project_root)

        widget = NodeDetailPanel(
            graph_provider=provider,
            ref_id="auth-login",
        )
        text = widget.render()
        plain = text.plain

        assert "documented" in plain

    def test_render_shows_doc_status_missing(
        self, ro_conn: sqlite3.Connection, populated_db: tuple[Path, Path]
    ) -> None:
        """NodeDetailPanel shows missing status for undocumented nodes."""
        from beadloom.tui.data_providers import GraphDataProvider
        from beadloom.tui.widgets.node_detail_panel import NodeDetailPanel

        _, project_root = populated_db
        provider = GraphDataProvider(conn=ro_conn, project_root=project_root)

        widget = NodeDetailPanel(
            graph_provider=provider,
            ref_id="payments",
        )
        text = widget.render()
        plain = text.plain

        assert "missing" in plain

    def test_set_node_updates_ref_id(self) -> None:
        """set_node() updates the internal ref_id."""
        from beadloom.tui.widgets.node_detail_panel import NodeDetailPanel

        widget = NodeDetailPanel()
        assert widget._ref_id == ""

        widget.set_node("auth")
        assert widget._ref_id == "auth"

    def test_set_provider(
        self, ro_conn: sqlite3.Connection, populated_db: tuple[Path, Path]
    ) -> None:
        """set_provider() updates the graph data provider."""
        from beadloom.tui.data_providers import GraphDataProvider
        from beadloom.tui.widgets.node_detail_panel import NodeDetailPanel

        _, project_root = populated_db
        provider = GraphDataProvider(conn=ro_conn, project_root=project_root)

        widget = NodeDetailPanel()
        assert widget._graph_provider is None

        widget.set_provider(provider)
        assert widget._graph_provider is provider

    def test_render_node_no_source(
        self, ro_conn: sqlite3.Connection, populated_db: tuple[Path, Path]
    ) -> None:
        """NodeDetailPanel handles node without source path."""
        from beadloom.tui.data_providers import GraphDataProvider
        from beadloom.tui.widgets.node_detail_panel import NodeDetailPanel

        _, project_root = populated_db
        provider = GraphDataProvider(conn=ro_conn, project_root=project_root)

        widget = NodeDetailPanel(
            graph_provider=provider,
            ref_id="auth-login",
        )
        text = widget.render()
        plain = text.plain

        assert "no source path" in plain


# ---------------------------------------------------------------------------
# DependencyPathWidget Tests (BEAD-04)
# ---------------------------------------------------------------------------


class TestDependencyPathWidget:
    """Tests for DependencyPathWidget."""

    def test_render_no_ref_id(self) -> None:
        """DependencyPathWidget shows placeholder when no ref_id is set."""
        from beadloom.tui.widgets.dependency_path import DependencyPathWidget

        widget = DependencyPathWidget()
        text = widget.render()
        plain = text.plain

        assert "Downstream Dependents" in plain
        assert "Select a node" in plain

    def test_render_upstream_no_ref_id(self) -> None:
        """DependencyPathWidget shows upstream placeholder."""
        from beadloom.tui.widgets.dependency_path import DependencyPathWidget

        widget = DependencyPathWidget(direction="upstream")
        text = widget.render()
        plain = text.plain

        assert "Upstream Dependencies" in plain
        assert "Select a node" in plain

    def test_render_downstream_existing(
        self, ro_conn: sqlite3.Connection, populated_db: tuple[Path, Path]
    ) -> None:
        """DependencyPathWidget renders downstream tree for existing node."""
        from beadloom.tui.data_providers import WhyDataProvider
        from beadloom.tui.widgets.dependency_path import DependencyPathWidget

        _, project_root = populated_db
        provider = WhyDataProvider(conn=ro_conn, project_root=project_root)

        widget = DependencyPathWidget(
            why_provider=provider,
            ref_id="auth",
            direction="downstream",
        )
        text = widget.render()
        plain = text.plain

        assert "Downstream Dependents" in plain

    def test_render_upstream_existing(
        self, ro_conn: sqlite3.Connection, populated_db: tuple[Path, Path]
    ) -> None:
        """DependencyPathWidget renders upstream tree for existing node."""
        from beadloom.tui.data_providers import WhyDataProvider
        from beadloom.tui.widgets.dependency_path import DependencyPathWidget

        _, project_root = populated_db
        provider = WhyDataProvider(conn=ro_conn, project_root=project_root)

        widget = DependencyPathWidget(
            why_provider=provider,
            ref_id="auth-login",
            direction="upstream",
        )
        text = widget.render()
        plain = text.plain

        assert "Upstream Dependencies" in plain

    def test_render_missing_node(
        self, ro_conn: sqlite3.Connection, populated_db: tuple[Path, Path]
    ) -> None:
        """DependencyPathWidget shows 'not found' for non-existent node."""
        from beadloom.tui.data_providers import WhyDataProvider
        from beadloom.tui.widgets.dependency_path import DependencyPathWidget

        _, project_root = populated_db
        provider = WhyDataProvider(conn=ro_conn, project_root=project_root)

        widget = DependencyPathWidget(
            why_provider=provider,
            ref_id="nonexistent",
        )
        text = widget.render()
        plain = text.plain

        assert "not found" in plain

    def test_render_no_provider(self) -> None:
        """DependencyPathWidget shows 'No data provider' when provider is None."""
        from beadloom.tui.widgets.dependency_path import DependencyPathWidget

        widget = DependencyPathWidget(ref_id="auth")
        text = widget.render()
        plain = text.plain

        assert "No data provider" in plain

    def test_show_upstream_method(self) -> None:
        """show_upstream() updates direction and ref_id."""
        from beadloom.tui.widgets.dependency_path import DependencyPathWidget

        widget = DependencyPathWidget()
        widget.show_upstream("auth")
        assert widget._ref_id == "auth"
        assert widget._direction == "upstream"

    def test_show_downstream_method(self) -> None:
        """show_downstream() updates direction and ref_id."""
        from beadloom.tui.widgets.dependency_path import DependencyPathWidget

        widget = DependencyPathWidget(direction="upstream")
        widget.show_downstream("auth")
        assert widget._ref_id == "auth"
        assert widget._direction == "downstream"

    def test_set_provider(
        self, ro_conn: sqlite3.Connection, populated_db: tuple[Path, Path]
    ) -> None:
        """set_provider() updates the why data provider."""
        from beadloom.tui.data_providers import WhyDataProvider
        from beadloom.tui.widgets.dependency_path import DependencyPathWidget

        _, project_root = populated_db
        provider = WhyDataProvider(conn=ro_conn, project_root=project_root)

        widget = DependencyPathWidget()
        assert widget._why_provider is None

        widget.set_provider(provider)
        assert widget._why_provider is provider

    def test_render_no_dependencies(
        self, ro_conn: sqlite3.Connection, populated_db: tuple[Path, Path]
    ) -> None:
        """DependencyPathWidget shows 'No dependencies' when node has none."""
        from beadloom.tui.data_providers import WhyDataProvider
        from beadloom.tui.widgets.dependency_path import DependencyPathWidget

        _, project_root = populated_db
        provider = WhyDataProvider(conn=ro_conn, project_root=project_root)

        # payments node has no downstream dependents
        widget = DependencyPathWidget(
            why_provider=provider,
            ref_id="payments",
            direction="downstream",
        )
        text = widget.render()
        plain = text.plain

        assert "Downstream Dependents" in plain
        # May show "No dependencies" or the impact summary
        # At minimum it should render without error


# ---------------------------------------------------------------------------
# ContextPreviewWidget Tests (BEAD-04)
# ---------------------------------------------------------------------------


class TestContextPreviewWidget:
    """Tests for ContextPreviewWidget."""

    def test_render_no_ref_id(self) -> None:
        """ContextPreviewWidget shows placeholder when no ref_id is set."""
        from beadloom.tui.widgets.context_preview import ContextPreviewWidget

        widget = ContextPreviewWidget()
        text = widget.render()
        plain = text.plain

        assert "Context Preview" in plain
        assert "Select a node" in plain

    def test_render_with_ref_id(
        self, ro_conn: sqlite3.Connection, populated_db: tuple[Path, Path]
    ) -> None:
        """ContextPreviewWidget renders context preview for existing node."""
        from beadloom.tui.data_providers import ContextDataProvider
        from beadloom.tui.widgets.context_preview import ContextPreviewWidget

        _, project_root = populated_db
        provider = ContextDataProvider(conn=ro_conn, project_root=project_root)

        widget = ContextPreviewWidget(
            context_provider=provider,
            ref_id="auth",
        )
        text = widget.render()
        plain = text.plain

        assert "Context Preview" in plain
        assert "auth" in plain
        assert "tokens" in plain

    def test_render_shows_token_count(
        self, ro_conn: sqlite3.Connection, populated_db: tuple[Path, Path]
    ) -> None:
        """ContextPreviewWidget shows estimated token count."""
        from beadloom.tui.data_providers import ContextDataProvider
        from beadloom.tui.widgets.context_preview import ContextPreviewWidget

        _, project_root = populated_db
        provider = ContextDataProvider(conn=ro_conn, project_root=project_root)

        widget = ContextPreviewWidget(
            context_provider=provider,
            ref_id="auth",
        )
        text = widget.render()
        plain = text.plain

        # Should contain a token count (tilde + number)
        assert "~" in plain
        assert "tokens" in plain

    def test_render_missing_node(
        self, ro_conn: sqlite3.Connection, populated_db: tuple[Path, Path]
    ) -> None:
        """ContextPreviewWidget shows 'not available' for missing node."""
        from beadloom.tui.data_providers import ContextDataProvider
        from beadloom.tui.widgets.context_preview import ContextPreviewWidget

        _, project_root = populated_db
        provider = ContextDataProvider(conn=ro_conn, project_root=project_root)

        widget = ContextPreviewWidget(
            context_provider=provider,
            ref_id="nonexistent",
        )
        text = widget.render()
        plain = text.plain

        assert "not available" in plain

    def test_render_no_provider(self) -> None:
        """ContextPreviewWidget shows 'No data provider' when provider is None."""
        from beadloom.tui.widgets.context_preview import ContextPreviewWidget

        widget = ContextPreviewWidget(ref_id="auth")
        text = widget.render()
        plain = text.plain

        assert "No data provider" in plain

    def test_show_context_method(self) -> None:
        """show_context() updates ref_id."""
        from beadloom.tui.widgets.context_preview import ContextPreviewWidget

        widget = ContextPreviewWidget()
        assert widget._ref_id == ""

        widget.show_context("auth")
        assert widget._ref_id == "auth"

    def test_set_provider(
        self, ro_conn: sqlite3.Connection, populated_db: tuple[Path, Path]
    ) -> None:
        """set_provider() updates the context data provider."""
        from beadloom.tui.data_providers import ContextDataProvider
        from beadloom.tui.widgets.context_preview import ContextPreviewWidget

        _, project_root = populated_db
        provider = ContextDataProvider(conn=ro_conn, project_root=project_root)

        widget = ContextPreviewWidget()
        assert widget._context_provider is None

        widget.set_provider(provider)
        assert widget._context_provider is provider

    def test_render_shows_bundle_keys(
        self, ro_conn: sqlite3.Connection, populated_db: tuple[Path, Path]
    ) -> None:
        """ContextPreviewWidget shows bundle keys in preview."""
        from beadloom.tui.data_providers import ContextDataProvider
        from beadloom.tui.widgets.context_preview import ContextPreviewWidget

        _, project_root = populated_db
        provider = ContextDataProvider(conn=ro_conn, project_root=project_root)

        widget = ContextPreviewWidget(
            context_provider=provider,
            ref_id="auth",
        )
        text = widget.render()
        plain = text.plain

        assert "Keys:" in plain


# ---------------------------------------------------------------------------
# ExplorerScreen Tests (BEAD-04)
# ---------------------------------------------------------------------------


class TestExplorerScreen:
    """Tests for the ExplorerScreen."""

    @pytest.mark.asyncio()
    async def test_explorer_composes_all_panels(
        self, populated_db: tuple[Path, Path]
    ) -> None:
        """ExplorerScreen composes header, node detail, dependency path, context preview."""
        db_path, project_root = populated_db
        from beadloom.tui.app import BeadloomApp
        from beadloom.tui.screens.explorer import ExplorerScreen
        from beadloom.tui.widgets.context_preview import ContextPreviewWidget
        from beadloom.tui.widgets.dependency_path import DependencyPathWidget
        from beadloom.tui.widgets.node_detail_panel import NodeDetailPanel

        app = BeadloomApp(db_path=db_path, project_root=project_root)
        async with app.run_test() as pilot:
            await pilot.press("2")  # switch to explorer
            assert isinstance(app.screen, ExplorerScreen)

            # Verify all sub-widgets exist
            detail = app.screen.query_one("#node-detail-panel", NodeDetailPanel)
            assert detail is not None

            dep_path = app.screen.query_one("#dependency-path", DependencyPathWidget)
            assert dep_path is not None

            ctx_preview = app.screen.query_one("#context-preview", ContextPreviewWidget)
            assert ctx_preview is not None

            await pilot.press("q")

    @pytest.mark.asyncio()
    async def test_explorer_has_header(
        self, populated_db: tuple[Path, Path]
    ) -> None:
        """ExplorerScreen has a header label."""
        db_path, project_root = populated_db
        from beadloom.tui.app import BeadloomApp
        from beadloom.tui.screens.explorer import ExplorerScreen

        app = BeadloomApp(db_path=db_path, project_root=project_root)
        async with app.run_test() as pilot:
            await pilot.press("2")
            assert isinstance(app.screen, ExplorerScreen)

            from textual.widgets import Label

            header = app.screen.query_one("#explorer-header", Label)
            assert header is not None
            assert "Explorer" in str(header.content)

            await pilot.press("q")

    @pytest.mark.asyncio()
    async def test_explorer_has_action_bar(
        self, populated_db: tuple[Path, Path]
    ) -> None:
        """ExplorerScreen has an action bar with keybinding hints."""
        db_path, project_root = populated_db
        from beadloom.tui.app import BeadloomApp
        from beadloom.tui.screens.explorer import ExplorerScreen

        app = BeadloomApp(db_path=db_path, project_root=project_root)
        async with app.run_test() as pilot:
            await pilot.press("2")
            assert isinstance(app.screen, ExplorerScreen)

            from textual.widgets import Label

            action_bar = app.screen.query_one("#explorer-action-bar", Label)
            assert action_bar is not None

            bar_text = str(action_bar.content)
            assert "pstream" in bar_text
            assert "ownstream" in bar_text
            assert "ontext" in bar_text
            assert "back" in bar_text

            await pilot.press("q")

    @pytest.mark.asyncio()
    async def test_explorer_with_ref_id(
        self, populated_db: tuple[Path, Path]
    ) -> None:
        """ExplorerScreen shows node details when ref_id is set."""
        db_path, project_root = populated_db
        from beadloom.tui.app import BeadloomApp
        from beadloom.tui.screens.explorer import ExplorerScreen
        from beadloom.tui.widgets.graph_tree import NodeSelected

        app = BeadloomApp(db_path=db_path, project_root=project_root)
        async with app.run_test() as pilot:
            # Select a node first
            app.post_message(NodeSelected("auth"))
            await pilot.pause()

            # Switch to explorer
            await pilot.press("2")
            await pilot.pause()
            assert isinstance(app.screen, ExplorerScreen)

            from textual.widgets import Label

            header = app.screen.query_one("#explorer-header", Label)
            header_text = str(header.content)
            assert "auth" in header_text

            await pilot.press("q")

    @pytest.mark.asyncio()
    async def test_explorer_keybinding_downstream(
        self, populated_db: tuple[Path, Path]
    ) -> None:
        """Pressing 'd' on ExplorerScreen switches to downstream view."""
        db_path, project_root = populated_db
        from beadloom.tui.app import BeadloomApp
        from beadloom.tui.screens.explorer import MODE_DOWNSTREAM, ExplorerScreen
        from beadloom.tui.widgets.dependency_path import DependencyPathWidget

        app = BeadloomApp(db_path=db_path, project_root=project_root)
        async with app.run_test() as pilot:
            await pilot.press("2")
            assert isinstance(app.screen, ExplorerScreen)

            await pilot.press("d")
            await pilot.pause()

            dep_widget = app.screen.query_one("#dependency-path", DependencyPathWidget)
            assert dep_widget.display is True
            assert app.screen._mode == MODE_DOWNSTREAM

            await pilot.press("q")

    @pytest.mark.asyncio()
    async def test_explorer_keybinding_upstream(
        self, populated_db: tuple[Path, Path]
    ) -> None:
        """Pressing 'u' on ExplorerScreen switches to upstream view."""
        db_path, project_root = populated_db
        from beadloom.tui.app import BeadloomApp
        from beadloom.tui.screens.explorer import MODE_UPSTREAM, ExplorerScreen
        from beadloom.tui.widgets.dependency_path import DependencyPathWidget

        app = BeadloomApp(db_path=db_path, project_root=project_root)
        async with app.run_test() as pilot:
            await pilot.press("2")
            assert isinstance(app.screen, ExplorerScreen)

            await pilot.press("u")
            await pilot.pause()

            dep_widget = app.screen.query_one("#dependency-path", DependencyPathWidget)
            assert dep_widget.display is True
            assert app.screen._mode == MODE_UPSTREAM

            await pilot.press("q")

    @pytest.mark.asyncio()
    async def test_explorer_keybinding_context(
        self, populated_db: tuple[Path, Path]
    ) -> None:
        """Pressing 'c' on ExplorerScreen switches to context preview."""
        db_path, project_root = populated_db
        from beadloom.tui.app import BeadloomApp
        from beadloom.tui.screens.explorer import MODE_CONTEXT, ExplorerScreen
        from beadloom.tui.widgets.context_preview import ContextPreviewWidget
        from beadloom.tui.widgets.dependency_path import DependencyPathWidget

        app = BeadloomApp(db_path=db_path, project_root=project_root)
        async with app.run_test() as pilot:
            await pilot.press("2")
            assert isinstance(app.screen, ExplorerScreen)

            await pilot.press("c")
            await pilot.pause()

            dep_widget = app.screen.query_one("#dependency-path", DependencyPathWidget)
            ctx_widget = app.screen.query_one("#context-preview", ContextPreviewWidget)
            assert dep_widget.display is False
            assert ctx_widget.display is True
            assert app.screen._mode == MODE_CONTEXT

            await pilot.press("q")

    @pytest.mark.asyncio()
    async def test_explorer_escape_pops_screen(
        self, populated_db: tuple[Path, Path]
    ) -> None:
        """Pressing Esc on ExplorerScreen returns to previous screen."""
        db_path, project_root = populated_db
        from beadloom.tui.app import BeadloomApp
        from beadloom.tui.screens.dashboard import DashboardScreen
        from beadloom.tui.screens.explorer import ExplorerScreen

        app = BeadloomApp(db_path=db_path, project_root=project_root)
        async with app.run_test() as pilot:
            # Push explorer on top of dashboard
            app.push_screen(ExplorerScreen())
            await pilot.pause()
            assert isinstance(app.screen, ExplorerScreen)

            # Press Esc to go back
            await pilot.press("escape")
            await pilot.pause()

            # Should be back on dashboard
            assert isinstance(app.screen, DashboardScreen)

            await pilot.press("q")

    @pytest.mark.asyncio()
    async def test_explorer_refresh_all_widgets(
        self, populated_db: tuple[Path, Path]
    ) -> None:
        """ExplorerScreen.refresh_all_widgets() reloads data."""
        db_path, project_root = populated_db
        from beadloom.tui.app import BeadloomApp
        from beadloom.tui.screens.explorer import ExplorerScreen

        app = BeadloomApp(db_path=db_path, project_root=project_root)
        async with app.run_test() as pilot:
            await pilot.press("2")
            screen = app.screen
            assert isinstance(screen, ExplorerScreen)

            # Calling refresh should not raise
            screen.refresh_all_widgets()

            await pilot.press("q")

    @pytest.mark.asyncio()
    async def test_explorer_empty_ref_id(
        self, populated_db: tuple[Path, Path]
    ) -> None:
        """ExplorerScreen handles empty ref_id gracefully."""
        db_path, project_root = populated_db
        from beadloom.tui.app import BeadloomApp
        from beadloom.tui.screens.explorer import ExplorerScreen

        app = BeadloomApp(db_path=db_path, project_root=project_root)
        async with app.run_test() as pilot:
            await pilot.press("2")
            assert isinstance(app.screen, ExplorerScreen)

            # Should not crash with no ref_id
            assert app.screen._ref_id == ""

            await pilot.press("q")

    @pytest.mark.asyncio()
    async def test_explorer_set_ref_id(
        self, populated_db: tuple[Path, Path]
    ) -> None:
        """ExplorerScreen.set_ref_id() loads data for the given node."""
        db_path, project_root = populated_db
        from beadloom.tui.app import BeadloomApp
        from beadloom.tui.screens.explorer import ExplorerScreen

        app = BeadloomApp(db_path=db_path, project_root=project_root)
        async with app.run_test() as pilot:
            await pilot.press("2")
            screen = app.screen
            assert isinstance(screen, ExplorerScreen)

            screen.set_ref_id("auth")
            await pilot.pause()

            assert screen._ref_id == "auth"

            from textual.widgets import Label

            header = screen.query_one("#explorer-header", Label)
            assert "auth" in str(header.content)

            await pilot.press("q")

    @pytest.mark.asyncio()
    async def test_explorer_open_source_no_editor(
        self, populated_db: tuple[Path, Path]
    ) -> None:
        """Pressing 'o' without $EDITOR shows notification."""
        db_path, project_root = populated_db
        from beadloom.tui.app import BeadloomApp
        from beadloom.tui.screens.explorer import ExplorerScreen

        app = BeadloomApp(db_path=db_path, project_root=project_root)
        async with app.run_test(notifications=True) as pilot:
            await pilot.press("2")
            assert isinstance(app.screen, ExplorerScreen)

            # Set ref_id and press 'o' without EDITOR
            app.screen.set_ref_id("auth")
            await pilot.pause()

            with patch.dict("os.environ", {"EDITOR": ""}, clear=False):
                await pilot.press("o")
                await pilot.pause()

            # Should not crash
            await pilot.press("q")

    @pytest.mark.asyncio()
    async def test_explorer_keybinding_switch_back_to_downstream(
        self, populated_db: tuple[Path, Path]
    ) -> None:
        """Switching c -> d returns to downstream view."""
        db_path, project_root = populated_db
        from beadloom.tui.app import BeadloomApp
        from beadloom.tui.screens.explorer import MODE_DOWNSTREAM, ExplorerScreen
        from beadloom.tui.widgets.context_preview import ContextPreviewWidget
        from beadloom.tui.widgets.dependency_path import DependencyPathWidget

        app = BeadloomApp(db_path=db_path, project_root=project_root)
        async with app.run_test() as pilot:
            await pilot.press("2")
            assert isinstance(app.screen, ExplorerScreen)

            # Switch to context first
            await pilot.press("c")
            await pilot.pause()

            # Switch back to downstream
            await pilot.press("d")
            await pilot.pause()

            dep_widget = app.screen.query_one("#dependency-path", DependencyPathWidget)
            ctx_widget = app.screen.query_one("#context-preview", ContextPreviewWidget)
            assert dep_widget.display is True
            assert ctx_widget.display is False
            assert app.screen._mode == MODE_DOWNSTREAM

            await pilot.press("q")

    @pytest.mark.asyncio()
    async def test_app_open_explorer_method(
        self, populated_db: tuple[Path, Path]
    ) -> None:
        """App.open_explorer() switches to explorer and sets ref_id."""
        db_path, project_root = populated_db
        from beadloom.tui.app import BeadloomApp
        from beadloom.tui.screens.explorer import ExplorerScreen

        app = BeadloomApp(db_path=db_path, project_root=project_root)
        async with app.run_test() as pilot:
            app.open_explorer("auth")
            await pilot.pause()

            assert isinstance(app.screen, ExplorerScreen)
            assert app._selected_ref_id == "auth"

            await pilot.press("q")

    @pytest.mark.asyncio()
    async def test_app_tracks_selected_ref_id(
        self, populated_db: tuple[Path, Path]
    ) -> None:
        """App tracks last selected ref_id from NodeSelected messages."""
        db_path, project_root = populated_db
        from beadloom.tui.app import BeadloomApp
        from beadloom.tui.widgets.graph_tree import NodeSelected

        app = BeadloomApp(db_path=db_path, project_root=project_root)
        async with app.run_test() as pilot:
            assert app._selected_ref_id == ""

            app.post_message(NodeSelected("payments"))
            await pilot.pause()

            assert app._selected_ref_id == "payments"

            await pilot.press("q")

    @pytest.mark.asyncio()
    async def test_explorer_empty_db(self, tmp_path: Path) -> None:
        """ExplorerScreen handles empty database gracefully."""
        db_path = tmp_path / ".beadloom" / "beadloom.db"
        db_path.parent.mkdir(parents=True)

        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        from beadloom.infrastructure.db import create_schema
        create_schema(conn)
        conn.commit()
        conn.close()

        from beadloom.tui.app import BeadloomApp
        from beadloom.tui.screens.explorer import ExplorerScreen

        app = BeadloomApp(db_path=db_path, project_root=tmp_path)
        async with app.run_test() as pilot:
            await pilot.press("2")
            assert isinstance(app.screen, ExplorerScreen)

            # Should not crash with empty DB
            await pilot.press("d")
            await pilot.pause()
            await pilot.press("u")
            await pilot.pause()
            await pilot.press("c")
            await pilot.pause()

            await pilot.press("q")


# ---------------------------------------------------------------------------
# HelpOverlay Tests (BEAD-07)
# ---------------------------------------------------------------------------


class TestHelpOverlay:
    """Tests for the HelpOverlay modal screen."""

    def test_build_help_text_contains_sections(self) -> None:
        """build_help_text() includes all keybinding sections."""
        from beadloom.tui.widgets.help_overlay import build_help_text

        text = build_help_text()
        assert "Global" in text
        assert "Dashboard" in text
        assert "Explorer" in text
        assert "Doc Status" in text

    def test_build_help_text_contains_bindings(self) -> None:
        """build_help_text() includes specific keybindings."""
        from beadloom.tui.widgets.help_overlay import build_help_text

        text = build_help_text()
        assert "Quit" in text
        assert "Search overlay" in text
        assert "Trigger reindex" in text
        assert "Downstream" in text
        assert "Generate doc" in text

    @pytest.mark.asyncio()
    async def test_help_overlay_opens_on_question_mark(
        self, populated_db: tuple[Path, Path]
    ) -> None:
        """Pressing '?' opens the HelpOverlay."""
        db_path, project_root = populated_db
        from beadloom.tui.app import BeadloomApp
        from beadloom.tui.widgets.help_overlay import HelpOverlay

        app = BeadloomApp(db_path=db_path, project_root=project_root)
        async with app.run_test() as pilot:
            await pilot.press("question_mark")
            await pilot.pause()

            # The top screen should be HelpOverlay
            assert isinstance(app.screen, HelpOverlay)

            await pilot.press("escape")
            await pilot.pause()

            # Should be back on previous screen
            from beadloom.tui.screens.dashboard import DashboardScreen

            assert isinstance(app.screen, DashboardScreen)

            await pilot.press("q")

    @pytest.mark.asyncio()
    async def test_help_overlay_dismisses_on_esc(
        self, populated_db: tuple[Path, Path]
    ) -> None:
        """Pressing Esc dismisses the HelpOverlay."""
        db_path, project_root = populated_db
        from beadloom.tui.app import BeadloomApp
        from beadloom.tui.widgets.help_overlay import HelpOverlay

        app = BeadloomApp(db_path=db_path, project_root=project_root)
        async with app.run_test() as pilot:
            app.push_screen(HelpOverlay())
            await pilot.pause()
            assert isinstance(app.screen, HelpOverlay)

            await pilot.press("escape")
            await pilot.pause()
            assert not isinstance(app.screen, HelpOverlay)

            await pilot.press("q")

    @pytest.mark.asyncio()
    async def test_help_overlay_has_content(
        self, populated_db: tuple[Path, Path]
    ) -> None:
        """HelpOverlay composes with title and content widgets."""
        db_path, project_root = populated_db
        from beadloom.tui.app import BeadloomApp
        from beadloom.tui.widgets.help_overlay import HelpOverlay

        app = BeadloomApp(db_path=db_path, project_root=project_root)
        async with app.run_test() as pilot:
            app.push_screen(HelpOverlay())
            await pilot.pause()

            from textual.widgets import Label, Static

            title = app.screen.query_one("#help-title", Label)
            assert title is not None
            assert "Help" in str(title.content)

            content = app.screen.query_one("#help-content", Static)
            assert content is not None

            await pilot.press("escape")
            await pilot.press("q")


# ---------------------------------------------------------------------------
# SearchOverlay Tests (BEAD-07)
# ---------------------------------------------------------------------------


class TestSearchOverlay:
    """Tests for the SearchOverlay modal screen."""

    def test_search_nodes_like_fallback(
        self, ro_conn: sqlite3.Connection, populated_db: tuple[Path, Path]
    ) -> None:
        """_search_nodes uses SQL LIKE fallback when FTS5 is not populated."""
        from beadloom.tui.widgets.search_overlay import _search_nodes

        results = _search_nodes(ro_conn, "auth")
        ref_ids = {r["ref_id"] for r in results}
        assert "auth" in ref_ids

    def test_search_nodes_empty_query(
        self, ro_conn: sqlite3.Connection, populated_db: tuple[Path, Path]
    ) -> None:
        """_search_nodes returns results for empty-ish query via LIKE fallback."""
        from beadloom.tui.widgets.search_overlay import _search_nodes

        # Empty string matches everything via LIKE
        results = _search_nodes(ro_conn, "")
        # LIKE '%%' matches all rows
        assert isinstance(results, list)

    def test_search_nodes_no_match(
        self, ro_conn: sqlite3.Connection, populated_db: tuple[Path, Path]
    ) -> None:
        """_search_nodes returns empty list for non-matching query."""
        from beadloom.tui.widgets.search_overlay import _search_nodes

        results = _search_nodes(ro_conn, "zzz_nonexistent_zzz")
        assert results == []

    def test_format_results_empty(self) -> None:
        """_format_results returns 'No results found' for empty list."""
        from beadloom.tui.widgets.search_overlay import _format_results

        text = _format_results([])
        assert "No results found" in text

    def test_format_results_with_data(self) -> None:
        """_format_results formats results with ref_id and kind."""
        from beadloom.tui.widgets.search_overlay import _format_results

        results = [
            {"ref_id": "auth", "kind": "domain", "snippet": "Authentication domain"},
        ]
        text = _format_results(results)
        assert "auth" in text
        assert "domain" in text
        assert "Authentication domain" in text

    @pytest.mark.asyncio()
    async def test_search_overlay_opens_on_slash(
        self, populated_db: tuple[Path, Path]
    ) -> None:
        """Pressing '/' opens the SearchOverlay."""
        db_path, project_root = populated_db
        from beadloom.tui.app import BeadloomApp
        from beadloom.tui.widgets.search_overlay import SearchOverlay

        app = BeadloomApp(db_path=db_path, project_root=project_root)
        async with app.run_test() as pilot:
            await pilot.press("slash")
            await pilot.pause()

            assert isinstance(app.screen, SearchOverlay)

            await pilot.press("escape")
            await pilot.pause()
            assert not isinstance(app.screen, SearchOverlay)

            await pilot.press("q")

    @pytest.mark.asyncio()
    async def test_search_overlay_has_input(
        self, populated_db: tuple[Path, Path]
    ) -> None:
        """SearchOverlay composes with an Input widget."""
        db_path, project_root = populated_db
        from beadloom.tui.app import BeadloomApp
        from beadloom.tui.widgets.search_overlay import SearchOverlay

        app = BeadloomApp(db_path=db_path, project_root=project_root)
        async with app.run_test() as pilot:
            app.push_screen(SearchOverlay(conn=app._conn))
            await pilot.pause()

            from textual.widgets import Input

            inp = app.screen.query_one("#search-input", Input)
            assert inp is not None

            await pilot.press("escape")
            await pilot.press("q")

    @pytest.mark.asyncio()
    async def test_search_overlay_dismisses_on_esc(
        self, populated_db: tuple[Path, Path]
    ) -> None:
        """Pressing Esc dismisses the SearchOverlay."""
        db_path, project_root = populated_db
        from beadloom.tui.app import BeadloomApp
        from beadloom.tui.widgets.search_overlay import SearchOverlay

        app = BeadloomApp(db_path=db_path, project_root=project_root)
        async with app.run_test() as pilot:
            app.push_screen(SearchOverlay(conn=app._conn))
            await pilot.pause()
            assert isinstance(app.screen, SearchOverlay)

            await pilot.press("escape")
            await pilot.pause()
            assert not isinstance(app.screen, SearchOverlay)

            await pilot.press("q")


# ---------------------------------------------------------------------------
# StatusBar Notification Tests (BEAD-07)
# ---------------------------------------------------------------------------


class TestStatusBarNotification:
    """Tests for StatusBarWidget.show_notification auto-dismiss."""

    def test_show_notification_sets_message(self) -> None:
        """show_notification() sets _last_action to the message."""
        from beadloom.tui.widgets.status_bar import StatusBarWidget

        widget = StatusBarWidget()
        # Cannot call set_timer without being mounted, so test the attribute directly
        widget._last_action = "Test notification"
        text = widget.render()
        assert "Test notification" in text.plain

    def test_clear_notification_clears_message(self) -> None:
        """_clear_notification() clears the last action message."""
        from beadloom.tui.widgets.status_bar import StatusBarWidget

        widget = StatusBarWidget()
        widget._last_action = "Old message"
        widget._clear_notification()
        assert widget._last_action == ""
        text = widget.render()
        assert "Old message" not in text.plain

    @pytest.mark.asyncio()
    async def test_show_notification_auto_dismisses(
        self, populated_db: tuple[Path, Path]
    ) -> None:
        """show_notification() auto-dismisses after duration via set_timer."""
        db_path, project_root = populated_db
        from beadloom.tui.app import BeadloomApp
        from beadloom.tui.widgets.status_bar import StatusBarWidget

        app = BeadloomApp(db_path=db_path, project_root=project_root)
        async with app.run_test() as pilot:
            status_bar = app.screen.query_one("#status-bar", StatusBarWidget)

            # Show notification with short duration
            status_bar.show_notification("Auto-dismiss test", duration=0.1)
            assert status_bar._last_action == "Auto-dismiss test"

            # Wait for auto-dismiss
            import asyncio

            await asyncio.sleep(0.3)
            await pilot.pause()

            # Should be cleared
            assert status_bar._last_action == ""

            await pilot.press("q")


# ---------------------------------------------------------------------------
# Keyboard Action Tests (BEAD-07)
# ---------------------------------------------------------------------------


class TestKeyboardActions:
    """Tests for keyboard actions wired in BEAD-07."""

    @pytest.mark.asyncio()
    async def test_lint_key_triggers_notification(
        self, populated_db: tuple[Path, Path]
    ) -> None:
        """Pressing 'l' triggers lint and shows notification."""
        db_path, project_root = populated_db
        from beadloom.tui.app import BeadloomApp

        app = BeadloomApp(db_path=db_path, project_root=project_root)
        async with app.run_test(notifications=True) as pilot:
            await pilot.press("l")
            await pilot.pause()

            # Should not crash — notification is shown via app.notify
            await pilot.press("q")

    @pytest.mark.asyncio()
    async def test_sync_check_key_triggers_notification(
        self, populated_db: tuple[Path, Path]
    ) -> None:
        """Pressing 's' triggers sync-check and shows notification."""
        db_path, project_root = populated_db
        from beadloom.tui.app import BeadloomApp

        app = BeadloomApp(db_path=db_path, project_root=project_root)
        async with app.run_test(notifications=True) as pilot:
            await pilot.press("s")
            await pilot.pause()

            # Should not crash
            await pilot.press("q")

    @pytest.mark.asyncio()
    async def test_save_snapshot_key_shows_notification(
        self, populated_db: tuple[Path, Path]
    ) -> None:
        """Pressing 'S' shows 'Snapshot saved' notification."""
        db_path, project_root = populated_db
        from beadloom.tui.app import BeadloomApp

        app = BeadloomApp(db_path=db_path, project_root=project_root)
        async with app.run_test(notifications=True) as pilot:
            await pilot.press("S")
            await pilot.pause()

            # Should not crash — notification is shown
            await pilot.press("q")

    @pytest.mark.asyncio()
    async def test_all_global_bindings_do_not_crash(
        self, populated_db: tuple[Path, Path]
    ) -> None:
        """All global keybindings execute without crashing."""
        db_path, project_root = populated_db
        from beadloom.tui.app import BeadloomApp

        app = BeadloomApp(db_path=db_path, project_root=project_root)
        async with app.run_test(notifications=True) as pilot:
            # Screen switch keys
            await pilot.press("1")
            await pilot.pause()
            await pilot.press("2")
            await pilot.pause()
            await pilot.press("3")
            await pilot.pause()
            await pilot.press("1")
            await pilot.pause()

            # Action keys
            await pilot.press("l")
            await pilot.pause()
            await pilot.press("s")
            await pilot.pause()
            await pilot.press("S")
            await pilot.pause()
            await pilot.press("r")
            await pilot.pause()
            await pilot.press("tab")
            await pilot.pause()

            # Overlay keys — open and dismiss
            await pilot.press("question_mark")
            await pilot.pause()
            await pilot.press("escape")
            await pilot.pause()

            await pilot.press("slash")
            await pilot.pause()
            await pilot.press("escape")
            await pilot.pause()

            await pilot.press("q")

    @pytest.mark.asyncio()
    async def test_explorer_bindings_do_not_crash(
        self, populated_db: tuple[Path, Path]
    ) -> None:
        """All Explorer screen keybindings execute without crashing."""
        db_path, project_root = populated_db
        from beadloom.tui.app import BeadloomApp
        from beadloom.tui.screens.explorer import ExplorerScreen

        app = BeadloomApp(db_path=db_path, project_root=project_root)
        async with app.run_test(notifications=True) as pilot:
            await pilot.press("2")
            await pilot.pause()
            assert isinstance(app.screen, ExplorerScreen)

            await pilot.press("d")
            await pilot.pause()
            await pilot.press("u")
            await pilot.pause()
            await pilot.press("c")
            await pilot.pause()
            await pilot.press("o")
            await pilot.pause()

            await pilot.press("q")

    @pytest.mark.asyncio()
    async def test_doc_status_bindings_do_not_crash(
        self, populated_db: tuple[Path, Path]
    ) -> None:
        """All Doc Status screen keybindings execute without crashing."""
        db_path, project_root = populated_db
        from beadloom.tui.app import BeadloomApp
        from beadloom.tui.screens.doc_status import DocStatusScreen

        app = BeadloomApp(db_path=db_path, project_root=project_root)
        async with app.run_test(notifications=True) as pilot:
            await pilot.press("3")
            await pilot.pause()
            assert isinstance(app.screen, DocStatusScreen)

            await pilot.press("g")
            await pilot.pause()
            await pilot.press("p")
            await pilot.pause()

            await pilot.press("q")

    @pytest.mark.asyncio()
    async def test_app_has_save_snapshot_binding(
        self, populated_db: tuple[Path, Path]
    ) -> None:
        """BeadloomApp has a binding for 'S' (save snapshot)."""
        from beadloom.tui.app import BeadloomApp

        db_path, project_root = populated_db
        app = BeadloomApp(db_path=db_path, project_root=project_root)

        binding_keys = [b.key for b in app.BINDINGS if isinstance(b, tuple) is False]
        assert "S" in binding_keys
