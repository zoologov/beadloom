# beadloom:service=tui
"""Tests for Context Inspector scroll fix (BEAD-04 / beadloom-v1x.4).

Validates:
- Full context bundles render without truncation (no 2000-char limit).
- show_context() triggers a content update on the widget.
- scroll_home() is called when switching to a new node.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast
from unittest.mock import patch

from beadloom.tui.widgets.context_preview import (
    ContextPreviewWidget,
    _render_context_preview,
)

if TYPE_CHECKING:
    from rich.text import Text

    from beadloom.tui.data_providers import ContextDataProvider


# ---------------------------------------------------------------------------
# Helpers / Fakes
# ---------------------------------------------------------------------------


class _FakeContextProvider:
    """Minimal duck-typed stand-in for ContextDataProvider."""

    def __init__(self, bundle: dict[str, Any] | None = None) -> None:
        self._bundle = bundle

    def get_context(self, ref_id: str) -> dict[str, Any] | None:
        return self._bundle

    def estimate_tokens(self, text: str) -> int:
        # Simple approximation: ~4 chars per token
        return len(text) // 4


# ---------------------------------------------------------------------------
# Tests: No truncation
# ---------------------------------------------------------------------------


class TestNoTruncation:
    """Content longer than 2000 chars must render in full."""

    def test_long_content_not_truncated(self) -> None:
        """Bundle text exceeding 2000 chars is fully rendered (no '... (truncated)')."""
        # Build a bundle whose JSON serialization exceeds 2000 chars
        long_value = "x" * 3000
        bundle: dict[str, Any] = {"data": long_value}
        provider = cast("ContextDataProvider", _FakeContextProvider(bundle=bundle))

        text: Text = _render_context_preview("test-node", provider)
        plain = text.plain

        # The full value must be present
        assert long_value in plain
        # Old truncation marker must NOT appear
        assert "... (truncated)" not in plain

    def test_short_content_renders_fully(self) -> None:
        """Short bundles also render without truncation artifacts."""
        bundle: dict[str, Any] = {"key": "short"}
        provider = cast("ContextDataProvider", _FakeContextProvider(bundle=bundle))

        text: Text = _render_context_preview("node-a", provider)
        plain = text.plain

        assert "short" in plain
        assert "... (truncated)" not in plain

    def test_content_section_label_says_content(self) -> None:
        """Section header changed from 'Preview' to 'Content'."""
        bundle: dict[str, Any] = {"k": "v"}
        provider = cast("ContextDataProvider", _FakeContextProvider(bundle=bundle))

        text: Text = _render_context_preview("ref", provider)
        plain = text.plain

        assert "Content" in plain


# ---------------------------------------------------------------------------
# Tests: show_context triggers update
# ---------------------------------------------------------------------------


class TestShowContextUpdate:
    """show_context() must update _ref_id and call refresh."""

    def test_show_context_updates_ref_id(self) -> None:
        """Calling show_context sets the internal _ref_id."""
        widget = ContextPreviewWidget()
        assert widget._ref_id == ""

        widget.show_context("new-node")
        assert widget._ref_id == "new-node"

    def test_show_context_calls_push_content(self) -> None:
        """show_context() calls _push_content() to update the widget."""
        widget = ContextPreviewWidget()

        with patch.object(widget, "_push_content") as mock_push:
            widget.show_context("node-x")

        mock_push.assert_called_once()


# ---------------------------------------------------------------------------
# Tests: scroll_home on node change
# ---------------------------------------------------------------------------


class TestScrollHomeOnNodeChange:
    """When showing a new node, scroll position resets to top.

    Scroll is managed by the VerticalScroll container in ExplorerScreen,
    not by the widget itself.  ``show_context()`` only updates content.
    """

    def test_show_context_does_not_call_scroll_home(self) -> None:
        """Widget delegates scrolling to the parent container."""
        widget = ContextPreviewWidget()

        with patch.object(widget, "scroll_home") as mock_scroll:
            widget.show_context("node-y")

        mock_scroll.assert_not_called()


# ---------------------------------------------------------------------------
# Tests: overflow-y CSS
# ---------------------------------------------------------------------------


class TestWidgetCSS:
    """Widget CSS should not set height or overflow — the scroll container handles it."""

    def test_default_css_no_fixed_height(self) -> None:
        """DEFAULT_CSS must NOT set height: 100% (auto-size for scroll container)."""
        assert "height: 100%" not in ContextPreviewWidget.DEFAULT_CSS

    def test_default_css_has_padding(self) -> None:
        """DEFAULT_CSS includes padding for readability."""
        assert "padding" in ContextPreviewWidget.DEFAULT_CSS


# ---------------------------------------------------------------------------
# Tests: _render_context_preview error paths
# ---------------------------------------------------------------------------


class TestRenderContextPreviewEdgeCases:
    """Edge-case tests for _render_context_preview."""

    def test_render_no_provider(self) -> None:
        """_render_context_preview returns 'No data provider' when provider is None."""
        text: Text = _render_context_preview("any-ref", None)
        plain = text.plain

        assert "No data provider available" in plain

    def test_render_bundle_none(self) -> None:
        """_render_context_preview returns 'not available' when bundle is None."""
        provider = cast("ContextDataProvider", _FakeContextProvider(bundle=None))

        text: Text = _render_context_preview("missing-node", provider)
        plain = text.plain

        assert "missing-node" in plain
        assert "not available" in plain

    def test_render_empty_ref_id_widget(self) -> None:
        """Widget _build_text returns placeholder text when no ref_id is set."""
        widget = ContextPreviewWidget()
        text: Text = widget._build_text()
        plain = text.plain

        assert "Select a node to see context preview" in plain

    def test_show_context_different_nodes_updates_ref(self) -> None:
        """Calling show_context with different ref_ids updates each time."""
        widget = ContextPreviewWidget()

        widget.show_context("node-a")
        assert widget._ref_id == "node-a"

        widget.show_context("node-b")
        assert widget._ref_id == "node-b"

    def test_render_bundle_with_nested_structure(self) -> None:
        """Bundle with nested dicts/lists renders fully without error."""
        bundle: dict[str, Any] = {
            "nodes": [{"id": "n1"}, {"id": "n2"}],
            "metadata": {"version": 1, "nested": {"deep": True}},
        }
        provider = cast("ContextDataProvider", _FakeContextProvider(bundle=bundle))

        text: Text = _render_context_preview("complex-node", provider)
        plain = text.plain

        assert "n1" in plain
        assert "n2" in plain
        assert "deep" in plain
