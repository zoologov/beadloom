# beadloom:service=tui
"""Dashboard screen -- main overview with graph tree, debt gauge, lint panel, activity."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Label

from beadloom.tui.widgets.activity import ActivityWidget
from beadloom.tui.widgets.debt_gauge import DebtGaugeWidget
from beadloom.tui.widgets.graph_tree import GraphTreeWidget, NodeSelected
from beadloom.tui.widgets.lint_panel import LintPanelWidget
from beadloom.tui.widgets.status_bar import StatusBarWidget

if TYPE_CHECKING:
    from textual.app import ComposeResult

    from beadloom.tui.app import BeadloomApp

logger = logging.getLogger(__name__)


class DashboardScreen(Screen[None]):
    """Main dashboard screen with architecture overview.

    Layout:
    - Header: project title + debt gauge
    - Left panel (40%): graph tree widget
    - Right panel (60%): activity widget + lint panel
    - Node summary bar below main panels
    - Status bar at the bottom
    """

    CSS_PATH = "../styles/dashboard.tcss"

    def compose(self) -> ComposeResult:
        """Compose the dashboard layout."""
        with Vertical(id="dashboard-container"):
            # Header bar
            with Horizontal(id="dashboard-header"):
                yield Label("beadloom tui", id="dashboard-title")
                yield DebtGaugeWidget(widget_id="debt-gauge")

            yield Label(
                "Architecture overview: graph structure, git activity, lint & debt health",
                id="screen-description",
                classes="screen-desc",
            )

            # Main content: left + right panels
            with Horizontal(id="dashboard-main"):
                # Left panel: graph tree
                with Vertical(id="dashboard-left"):
                    yield GraphTreeWidget(widget_id="graph-tree")

                # Right panel: activity + lint
                with Vertical(id="dashboard-right"):
                    yield ActivityWidget(widget_id="activity-widget")
                    yield LintPanelWidget(widget_id="lint-panel")

            # Node summary bar
            yield Label(
                "Select a node to see details",
                id="node-summary",
            )

            # Status bar
            yield StatusBarWidget(widget_id="status-bar")

            # Action bar (keybinding hints)
            yield Label(
                "[Enter]explore  [r]eindex  [l]int  [s]ync-check  [S]napshot  [?]help",
                id="dashboard-action-bar",
            )

    def on_mount(self) -> None:
        """Load data from providers when the screen mounts."""
        self._load_data()

    def on_node_selected(self, event: NodeSelected) -> None:
        """Handle node selection from the graph tree — update summary bar.

        On leaf nodes (features, services without children), also open Explorer.
        """
        app = self._get_app()
        if app is None or app.graph_provider is None:
            return

        node_data = app.graph_provider.get_node_with_source(event.ref_id)
        if node_data is None:
            return

        ref_id = node_data.get("ref_id", "")
        kind = node_data.get("kind", "")
        summary = node_data.get("summary", "")
        source = node_data.get("source") or ""

        summary_text = f"{ref_id} ({kind})"
        if summary:
            summary_text += f" — {summary}"
        if source:
            summary_text += f"  [{source}]"

        try:
            label = self.query_one("#node-summary", Label)
            label.update(summary_text)
        except Exception:
            logger.debug("Failed to update node summary", exc_info=True)

        # Open Explorer for leaf nodes (no children in hierarchy)
        hierarchy = app.graph_provider.get_hierarchy()
        if event.ref_id not in hierarchy:
            app.open_explorer(event.ref_id)

    def _load_data(self) -> None:
        """Load data from all providers and push to widgets."""
        app = self._get_app()
        if app is None:
            return

        # Graph tree
        try:
            graph_tree = self.query_one("#graph-tree", GraphTreeWidget)
            graph_tree.refresh_data(
                graph_provider=app.graph_provider,
                sync_provider=app.sync_provider,
            )
        except Exception:
            logger.debug("Failed to load graph tree data", exc_info=True)

        # Debt gauge
        if app.debt_provider is not None:
            try:
                score = app.debt_provider.get_score()
                debt_gauge = self.query_one("#debt-gauge", DebtGaugeWidget)
                debt_gauge.refresh_data(score)
            except Exception:
                logger.debug("Failed to load debt data", exc_info=True)

        # Activity
        if app.activity_provider is not None:
            try:
                activities = app.activity_provider.get_activity()
                activity_widget = self.query_one("#activity-widget", ActivityWidget)
                activity_widget.refresh_data(activities)
            except Exception:
                logger.debug("Failed to load activity data", exc_info=True)

        # Lint
        if app.lint_provider is not None:
            try:
                violations = app.lint_provider.get_violations()
                lint_panel = self.query_one("#lint-panel", LintPanelWidget)
                lint_panel.refresh_data(violations)
            except Exception:
                logger.debug("Failed to load lint data", exc_info=True)

        # Status bar counts
        self._load_status_bar(app)

    def _load_status_bar(self, app: BeadloomApp) -> None:
        """Load counts into the status bar from graph and sync providers."""
        node_count = 0
        edge_count = 0
        doc_count = 0
        stale_count = 0

        if app.graph_provider is not None:
            try:
                node_count = len(app.graph_provider.get_nodes())
                edge_count = len(app.graph_provider.get_edges())
            except Exception:
                logger.debug("Failed to load graph counts", exc_info=True)

        if app.sync_provider is not None:
            try:
                stale_count = app.sync_provider.get_stale_count()
            except Exception:
                logger.debug("Failed to load stale count", exc_info=True)

        # Doc count from graph provider nodes (approximation via DB)
        if app.graph_provider is not None and app._conn is not None:
            try:
                row = app._conn.execute("SELECT count(*) FROM docs").fetchone()
                if row is not None:
                    doc_count = int(row[0])
            except Exception:
                logger.debug("Failed to load doc count", exc_info=True)

        try:
            status_bar = self.query_one("#status-bar", StatusBarWidget)
            status_bar.refresh_data(
                node_count=node_count,
                edge_count=edge_count,
                doc_count=doc_count,
                stale_count=stale_count,
            )
        except Exception:
            logger.debug("Failed to update status bar", exc_info=True)

    def _get_app(self) -> BeadloomApp | None:
        """Get the BeadloomApp instance, returning None if not available."""
        try:
            from beadloom.tui.app import BeadloomApp

            app = self.app
            if isinstance(app, BeadloomApp):
                return app
        except Exception:
            logger.debug("Failed to get BeadloomApp instance", exc_info=True)
        return None

    def refresh_all_widgets(self) -> None:
        """Refresh all dashboard widgets with fresh data from providers."""
        self._load_data()
