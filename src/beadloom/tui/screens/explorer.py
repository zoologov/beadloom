# beadloom:service=tui
"""Explorer screen — node deep-dive with detail, dependencies, context."""

from __future__ import annotations

import logging
import os
import subprocess
from typing import TYPE_CHECKING, ClassVar

from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import Footer, Label

from beadloom.tui.widgets.context_preview import ContextPreviewWidget
from beadloom.tui.widgets.dependency_path import DependencyPathWidget
from beadloom.tui.widgets.node_detail_panel import NodeDetailPanel

if TYPE_CHECKING:
    from textual.app import ComposeResult
    from textual.events import ScreenResume

    from beadloom.tui.app import BeadloomApp

logger = logging.getLogger(__name__)

# Right panel modes
MODE_DOWNSTREAM = "downstream"
MODE_UPSTREAM = "upstream"
MODE_CONTEXT = "context"


class ExplorerScreen(Screen[None]):
    """Node explorer screen for deep-dive analysis.

    Layout:
    - Header: "Explorer: {ref_id}"
    - Left panel (50%): NodeDetailPanel
    - Right panel (50%): DependencyPathWidget or ContextPreviewWidget (switchable)
    - Action bar: [u]pstream [d]ownstream [c]ontext [o]pen [Esc]back
    """

    CSS_PATH = "../styles/explorer.tcss"

    BINDINGS: ClassVar[list[Binding | tuple[str, str] | tuple[str, str, str]]] = [
        Binding("d", "show_downstream", "Downstream", key_display="d"),
        Binding("u", "show_upstream", "Upstream", key_display="u"),
        Binding("c", "show_context", "Context", key_display="c"),
        Binding("o", "open_source", "Open", key_display="o"),
        Binding("escape", "go_back", "Back", key_display="Esc"),
    ]

    def __init__(
        self,
        ref_id: str = "",
        *,
        name: str | None = None,
        id: str | None = None,  # noqa: A002 — Textual API requires 'id'
        classes: str | None = None,
    ) -> None:
        super().__init__(name=name, id=id, classes=classes)
        self._ref_id = ref_id
        self._mode = MODE_UPSTREAM
        self._prev_dep_mode = MODE_UPSTREAM

    def compose(self) -> ComposeResult:
        """Compose the explorer layout."""
        with Vertical(id="explorer-container"):
            yield Label(
                self._header_text(),
                id="explorer-header",
            )
            yield Label(
                "Node deep-dive: detail, dependencies, context bundle",
                id="screen-description",
                classes="screen-desc",
            )
            with Horizontal(id="explorer-main"):
                with VerticalScroll(id="explorer-left"):
                    yield NodeDetailPanel(
                        ref_id=self._ref_id,
                        widget_id="node-detail-panel",
                    )
                with Vertical(id="explorer-right"):
                    yield DependencyPathWidget(
                        ref_id=self._ref_id,
                        direction=MODE_UPSTREAM,
                        widget_id="dependency-path",
                    )
                    with VerticalScroll(id="context-scroll"):
                        yield ContextPreviewWidget(
                            ref_id=self._ref_id,
                            widget_id="context-preview",
                        )

        yield Footer()

    def on_mount(self) -> None:
        """Load data from providers when the screen mounts."""
        self._load_data()
        self._update_right_panel_visibility()

    def on_screen_resume(self, event: ScreenResume) -> None:
        """Reload data when the screen becomes active again.

        Handles the case where the user visits Explorer before selecting
        any node, returns to Dashboard, selects a node, and comes back.
        """
        app = self._get_app()
        if app is None:
            return

        pending = app._selected_ref_id
        if pending and pending != self._ref_id:
            self.set_ref_id(pending)

    def set_ref_id(self, ref_id: str) -> None:
        """Set the ref_id to explore and reload data.

        Parameters
        ----------
        ref_id:
            The node ref_id to display.
        """
        self._ref_id = ref_id
        self._mode = MODE_UPSTREAM
        self._load_data()
        self._update_right_panel_visibility()

    def _header_text(self) -> str:
        """Generate the header text for the current ref_id."""
        if self._ref_id:
            return f"Explorer: {self._ref_id}"
        return "Explorer"

    def _load_data(self) -> None:
        """Load data into all sub-widgets from providers."""
        app = self._get_app()

        # Update header
        try:
            header = self.query_one("#explorer-header", Label)
            header.update(self._header_text())
        except Exception:
            logger.debug("Failed to update explorer header", exc_info=True)

        # Node detail panel
        try:
            detail = self.query_one("#node-detail-panel", NodeDetailPanel)
            if app is not None and app.graph_provider is not None:
                detail.set_provider(app.graph_provider)
            detail.set_node(self._ref_id)
        except Exception:
            logger.debug("Failed to update node detail panel", exc_info=True)

        # Dependency path widget
        try:
            dep_widget = self.query_one("#dependency-path", DependencyPathWidget)
            if app is not None and app.why_provider is not None:
                dep_widget.set_provider(app.why_provider)
            if self._mode == MODE_UPSTREAM:
                dep_widget.show_upstream(self._ref_id)
            else:
                dep_widget.show_downstream(self._ref_id)
        except Exception:
            logger.debug("Failed to update dependency path", exc_info=True)

        # Context preview widget
        try:
            ctx_widget = self.query_one("#context-preview", ContextPreviewWidget)
            if app is not None and app.context_provider is not None:
                ctx_widget.set_provider(app.context_provider)
            ctx_widget.show_context(self._ref_id)
        except Exception:
            logger.debug("Failed to update context preview", exc_info=True)
        self._scroll_context_home()

    def _update_right_panel_visibility(self) -> None:
        """Show/hide right panel widgets based on current mode."""
        try:
            dep_widget = self.query_one("#dependency-path", DependencyPathWidget)
            ctx_scroll = self.query_one("#context-scroll", VerticalScroll)

            if self._mode == MODE_CONTEXT:
                dep_widget.display = False
                ctx_scroll.display = True
            else:
                dep_widget.display = True
                ctx_scroll.display = False
        except Exception:
            logger.debug("Failed to update panel visibility", exc_info=True)

    def _scroll_context_home(self) -> None:
        """Reset the context scroll container to the top."""
        try:
            ctx_scroll = self.query_one("#context-scroll", VerticalScroll)
            ctx_scroll.scroll_home(animate=False)
        except Exception:
            logger.debug("Failed to reset context scroll", exc_info=True)

    def action_show_downstream(self) -> None:
        """Switch right panel to downstream dependents."""
        self._mode = MODE_DOWNSTREAM
        self._update_right_panel_visibility()
        try:
            dep_widget = self.query_one("#dependency-path", DependencyPathWidget)
            dep_widget.show_downstream(self._ref_id)
        except Exception:
            logger.debug("Failed to show downstream", exc_info=True)

    def action_show_upstream(self) -> None:
        """Switch right panel to upstream dependencies."""
        self._mode = MODE_UPSTREAM
        self._update_right_panel_visibility()
        try:
            dep_widget = self.query_one("#dependency-path", DependencyPathWidget)
            dep_widget.show_upstream(self._ref_id)
        except Exception:
            logger.debug("Failed to show upstream", exc_info=True)

    def action_show_context(self) -> None:
        """Toggle right panel between context preview and dependency view."""
        if self._mode == MODE_CONTEXT:
            # Return to previous dependency mode
            if self._prev_dep_mode == MODE_DOWNSTREAM:
                self.action_show_downstream()
            else:
                self.action_show_upstream()
            return

        self._prev_dep_mode = self._mode
        self._mode = MODE_CONTEXT
        self._update_right_panel_visibility()
        try:
            ctx_widget = self.query_one("#context-preview", ContextPreviewWidget)
            ctx_widget.show_context(self._ref_id)
        except Exception:
            logger.debug("Failed to show context", exc_info=True)
        self._scroll_context_home()

    def action_open_source(self) -> None:
        """Open the node's primary source file in $EDITOR."""
        app = self._get_app()
        if app is None or app.graph_provider is None:
            self.notify("No data available", title="Open")
            return

        node = app.graph_provider.get_node_with_source(self._ref_id)
        if node is None:
            self.notify(f"Node '{self._ref_id}' not found", title="Open")
            return

        source = node.get("source")
        if not source:
            self.notify(
                f"No source path for '{self._ref_id}'",
                title="Open",
            )
            return

        editor = os.environ.get("EDITOR", "")
        if not editor:
            self.notify(
                f"$EDITOR not set. Source: {source}",
                title="Open",
            )
            return

        source_path = app.project_root / source
        try:
            subprocess.Popen(  # noqa: S603 — user controls $EDITOR
                [editor, str(source_path)],
                start_new_session=True,
            )
            self.notify(f"Opened {source} in {editor}", title="Open")
        except OSError as exc:
            self.notify(
                f"Failed to open: {exc}",
                title="Open",
            )

    def action_go_back(self) -> None:
        """Return to the dashboard screen."""
        from beadloom.tui.app import SCREEN_DASHBOARD

        app = self._get_app()
        if app is not None:
            app._safe_switch_screen(SCREEN_DASHBOARD)
        else:
            self.app.switch_screen(SCREEN_DASHBOARD)

    def refresh_all_widgets(self) -> None:
        """Refresh all explorer widgets with fresh data from providers."""
        self._load_data()

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
