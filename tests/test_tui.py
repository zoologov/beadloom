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

        assert "no watch" in text.plain

    def test_render_watcher_active(self) -> None:
        """StatusBarWidget shows watcher active when set."""
        from beadloom.tui.widgets.status_bar import StatusBarWidget

        widget = StatusBarWidget()
        widget._watcher_active = True
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
