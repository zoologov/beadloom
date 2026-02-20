# beadloom:service=tui
"""Context preview widget showing context bundle preview with token count."""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

from rich.text import Text
from textual.widgets import Static

if TYPE_CHECKING:
    from beadloom.tui.data_providers import ContextDataProvider

logger = logging.getLogger(__name__)

# Maximum preview characters to display
_MAX_PREVIEW_CHARS = 2000

# Label for the widget header
_LABEL = "Context Preview"


def _render_context_preview(
    ref_id: str,
    context_provider: ContextDataProvider | None,
) -> Text:
    """Render a context bundle preview as Rich Text.

    Parameters
    ----------
    ref_id:
        The ref_id to build context for.
    context_provider:
        The ContextDataProvider instance.
    """
    text = Text()
    text.append(_LABEL, style="bold underline")

    if context_provider is None:
        text.append("\n  No data provider available")
        return text

    bundle = context_provider.get_context(ref_id)

    if bundle is None:
        text.append(f"\n  Context for '{ref_id}' not available")
        return text

    # Serialize bundle for display and token estimation
    bundle_text = json.dumps(bundle, indent=2, default=str)
    token_count = context_provider.estimate_tokens(bundle_text)

    # Header info
    text.append("\n\n")
    text.append("  ref_id: ", style="dim")
    text.append(ref_id, style="bold cyan")
    text.append("\n")
    text.append("  tokens: ", style="dim")
    text.append(f"~{token_count:,}", style="bold yellow")
    text.append("\n")
    text.append("  length: ", style="dim")
    text.append(f"{len(bundle_text):,} chars", style="bold")

    # Bundle keys summary
    text.append("\n\n")
    text.append("  \u2500" * 30, style="dim")
    text.append("\n  Keys: ", style="bold underline")
    text.append(", ".join(sorted(bundle.keys())), style="dim")

    # Truncated preview
    text.append("\n\n")
    text.append("  \u2500" * 30, style="dim")
    text.append("\n  Preview\n", style="bold underline")

    preview = bundle_text[:_MAX_PREVIEW_CHARS]
    if len(bundle_text) > _MAX_PREVIEW_CHARS:
        preview += "\n  ... (truncated)"

    # Indent each line
    for line in preview.split("\n"):
        text.append(f"  {line}\n", style="dim")

    return text


class ContextPreviewWidget(Static):
    """Widget showing context bundle preview with estimated token count.

    Uses ContextDataProvider for context bundle building and token estimation.
    """

    DEFAULT_CSS = """
    ContextPreviewWidget {
        width: 100%;
        height: 100%;
        padding: 0 1;
        overflow-y: auto;
    }
    """

    def __init__(
        self,
        *,
        context_provider: ContextDataProvider | None = None,
        ref_id: str = "",
        widget_id: str | None = None,
    ) -> None:
        super().__init__(id=widget_id)
        self._context_provider = context_provider
        self._ref_id = ref_id

    def render(self) -> Text:
        """Render the context preview widget."""
        if not self._ref_id:
            text = Text()
            text.append(_LABEL, style="bold underline")
            text.append("\n  Select a node to see context preview")
            return text

        return _render_context_preview(self._ref_id, self._context_provider)

    def show_context(self, ref_id: str) -> None:
        """Show context preview for the given ref_id.

        Parameters
        ----------
        ref_id:
            The ref_id to build context for.
        """
        self._ref_id = ref_id
        self.refresh()

    def set_provider(self, context_provider: ContextDataProvider) -> None:
        """Set the context data provider."""
        self._context_provider = context_provider
