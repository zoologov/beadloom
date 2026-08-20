"""Port for the live CLI surface, provided by the services layer.

# beadloom:domain=infrastructure
# beadloom:component=surface-registry

Several checks compare a DOCUMENTED claim against RUNTIME TRUTH: `doctor` counts
the CLI's registered commands and the MCP server's tools to verify what
`CLAUDE.md` asserts; `docs audit` does the same for prose numbers; `sync-check`
hashes the CLI's command/option tree to detect surface drift behind a
`watches=cli` doc.

Getting that truth means asking the services layer — the OUTERMOST layer — from
the domain and application layers underneath it. Four call sites did exactly
that with `from beadloom.services… import …` nested inside a function, which
inverted the dependency direction and, because nested imports were invisible to
the graph, went unseen by the very boundary and cycle rules meant to catch it
(BDL-UX #159).

This module is the port that fixes the direction: the lower layer declares WHAT
it needs, and the services layer registers HOW to get it on import. Nothing here
imports `beadloom.services`.

Only the CLI needs a port. The MCP tool list already has a canonical
lower-layer source — `infrastructure/mcp_tools.MCP_TOOL_CATALOG`, pinned equal
to the server's registry by a test — so its consumers read that directly and no
registration is involved. The CLI's command/option tree has no such static
mirror: `sync-check` hashes the LIVE Click group to detect surface drift, so it
must be handed the real thing.

**Unknown is not zero.** When no provider is registered the getters return
``None`` — distinct from an empty surface — so a caller must decide, explicitly,
between reporting "not verified" and reporting a number. A check that cannot see
the surface and silently reports zero is the failure mode this whole codebase is
built to avoid.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

logger = logging.getLogger(__name__)


_cli_group_provider: Callable[[], Any] | None = None


def register_cli_group(provider: Callable[[], Any]) -> None:
    """Register how to obtain the root CLI command group (called by services)."""
    global _cli_group_provider
    _cli_group_provider = provider



def reset_surface_providers() -> None:
    """Clear the provider — for tests that need a known-empty registry."""
    global _cli_group_provider
    _cli_group_provider = None


def get_cli_group() -> Any | None:
    """The root CLI command group, or ``None`` when the surface is unknown.

    ``None`` means "nobody provided it" — the caller must report that as
    unverified rather than as an absence of commands.
    """
    if _cli_group_provider is None:
        return None
    try:
        return _cli_group_provider()
    except Exception:
        logger.warning("CLI surface provider failed", exc_info=True)
        return None
