"""Tests for the CLI surface port — dependency inversion for introspection.

Call sites in the domain and application layers reached UP into
`beadloom.services` to introspect the live CLI group, so they could compare a
documented claim against runtime truth. The intent is good; the direction was
wrong, and it was invisible because the imports were nested inside functions.

The fix is a port: the lower layer declares WHAT it needs, the services layer
provides it. These tests pin the contract that makes that safe — above all, that
an unprovided surface is reported as *unknown*, never as a plausible number.

(The MCP tool count needs no port: `infrastructure/mcp_tools.MCP_TOOL_CATALOG`
is a canonical lower-layer source, pinned equal to the server's registry by a
test, and available in every process.)
"""

from __future__ import annotations

import pytest

from beadloom.infrastructure.surface_registry import (
    get_cli_group,
    register_cli_group,
    reset_surface_providers,
)


@pytest.fixture(autouse=True)
def _clean_registry() -> object:
    """Each test starts empty and RESTORES what was there afterwards.

    The registry is process-wide, so merely clearing it would leak into every
    later test that expects the real CLI surface (doctor's command count,
    sync-check's `watches=cli` signature). Save and restore instead.
    """
    import beadloom.infrastructure.surface_registry as registry

    saved = registry._cli_group_provider
    reset_surface_providers()
    yield
    registry._cli_group_provider = saved


class TestUnregisteredSurface:
    """Absence must read as 'unknown', never as an answer."""

    def test_cli_group_is_none_when_nothing_registered(self) -> None:
        assert get_cli_group() is None


    def test_unknown_is_distinguishable_from_a_real_but_empty_group(self) -> None:
        """`None` (nobody provided it) must not collapse into an empty group.

        This is the whole point: a check that cannot see the surface must say so
        rather than report a count of zero as if it had looked.
        """

        class _Empty:
            def __init__(self) -> None:
                self.commands: dict[str, object] = {}

        register_cli_group(_Empty)
        group = get_cli_group()
        assert group is not None
        assert group.commands == {}
        reset_surface_providers()
        assert get_cli_group() is None


class TestRegisteredSurface:
    def test_registered_cli_group_is_returned(self) -> None:
        sentinel = object()
        register_cli_group(lambda: sentinel)
        assert get_cli_group() is sentinel


    def test_provider_is_called_lazily_on_each_read(self) -> None:
        """Registration stores a callable, so a late-built surface still works."""
        calls: list[int] = []

        def provider() -> object:
            calls.append(1)
            return "group"

        register_cli_group(provider)
        assert calls == []
        get_cli_group()
        get_cli_group()
        assert len(calls) == 2

    def test_later_registration_replaces_the_earlier_one(self) -> None:
        register_cli_group(lambda: "first")
        register_cli_group(lambda: "second")
        assert get_cli_group() == "second"


class TestProviderFailure:
    """A broken provider must degrade to unknown, not crash the caller."""

    def test_raising_cli_provider_reads_as_unknown(self) -> None:
        def boom() -> object:
            raise RuntimeError("no CLI here")

        register_cli_group(boom)
        assert get_cli_group() is None



class TestServicesRegisterTheirOwnSurface:
    """Importing the services layer wires the real CLI surface into the port."""

    def test_importing_cli_registers_the_click_group(self) -> None:
        import importlib

        import beadloom.services.cli as cli_module

        importlib.reload(cli_module)
        group = get_cli_group()

        assert group is not None
        assert hasattr(group, "commands")

