# beadloom:service=tui
"""Dashboard screen -- main overview with graph tree, debt gauge, lint panel, activity."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, ClassVar

from textual import work
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Footer, Label

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

    BINDINGS: ClassVar[list[Binding | tuple[str, str] | tuple[str, str, str]]] = [
        Binding("e", "explore_node", "Explore", key_display="e"),
    ]

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

        yield Footer()

    def on_mount(self) -> None:
        """Load data from providers when the screen mounts."""
        self._load_data()

    def _load_data(self) -> None:
        """Paint the cheap panels now and kick off the expensive ones.

        Everything here reads the graph index and returns in milliseconds. Debt
        and activity are handed to a background worker so the terminal is never
        left blank waiting for them.
        """
        self._load_fast_data()
        self._load_slow_data()

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

    def action_explore_node(self) -> None:
        """Open the currently highlighted tree node in Explorer."""
        app = self._get_app()
        if app is None:
            return

        try:
            graph_tree = self.query_one("#graph-tree", GraphTreeWidget)
        except Exception:
            return

        # Get the currently highlighted node
        cursor_node = graph_tree.cursor_node
        if cursor_node is None or cursor_node.data is None:
            self.notify("No node selected", title="Explore")
            return

        ref_id = cursor_node.data
        if ref_id == "No nodes found":
            return

        app.open_explorer(ref_id)

    def _load_fast_data(self) -> None:
        """Load the graph index data — all cheap SQLite reads."""
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

        # Debt and activity arrive later from the background worker
        try:
            self.query_one("#debt-gauge", DebtGaugeWidget).set_pending()
            self.query_one("#activity-widget", ActivityWidget).set_pending()
        except Exception:
            logger.debug("Failed to set loading placeholders", exc_info=True)

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

    @work(thread=True, exclusive=True, group="dashboard-slow")
    def _load_slow_data(self) -> None:
        """Compute the debt score and git activity off the event loop.

        Both walk the working tree and shell out to git, which takes seconds on
        a real repository. Textual has already switched the terminal to the
        alternate screen by this point, so running them inline would show the
        user nothing but a black screen until they finished.

        Runs on a worker thread against the app's worker connection, holding
        ``worker_conn_lock`` so a re-triggered load cannot overlap this one.
        """
        app = self._get_app()
        if app is None:
            return

        score: float | None = None
        activities: dict[str, Any] = {}

        with app.worker_conn_lock:
            if app.is_shutting_down:
                return

            if app.debt_provider is not None:
                try:
                    app.debt_provider.refresh()
                    score = app.debt_provider.get_score()
                except Exception:
                    logger.debug("Failed to load debt data", exc_info=True)

            if app.activity_provider is not None:
                try:
                    app.activity_provider.refresh()
                    activities = app.activity_provider.get_activity()
                except Exception:
                    logger.debug("Failed to load activity data", exc_info=True)

        if app.is_shutting_down:
            return

        try:
            app.call_from_thread(self._apply_slow_data, score, activities)
        except Exception:
            logger.debug("Failed to deliver background data", exc_info=True)

    def _apply_slow_data(self, score: float | None, activities: dict[str, Any]) -> None:
        """Push background-loaded debt and activity data into their widgets."""
        try:
            self.query_one("#debt-gauge", DebtGaugeWidget).refresh_data(score)
            self.query_one("#activity-widget", ActivityWidget).refresh_data(activities)
        except Exception:
            logger.debug("Failed to apply background data", exc_info=True)

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

        # Doc count via the application read facade (no raw SQLite in tui).
        if app.graph_provider is not None and app._conn is not None:
            try:
                from beadloom.application import graph_reads

                doc_count = graph_reads.count_docs(app._conn)
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
