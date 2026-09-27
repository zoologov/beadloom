"""Self-checks of this repository's manifest, CI workflows and configuration (BDL-074 A3).

Moved out of ``tests/integration/doc_sync/audit/test_audit_three_populations.py``;
the product tests of the same code stay there.
Everything here asserts on this repository's own tree, so it carries the
``self_check`` marker by its folder (see ``tests/conftest.py``).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from beadloom.doc_sync.audit import FactRegistry
from beadloom.infrastructure.db import create_schema, open_db
from tests.support.repository_root import REPO_ROOT as BEADLOOM_ROOT

if TYPE_CHECKING:
    import sqlite3
    from pathlib import Path


#: This repository's root — the one project whose own surfaces the audit reports.


@pytest.fixture()
def conn(tmp_path: Path) -> sqlite3.Connection:
    c = open_db(tmp_path / "scratch.db")
    create_schema(c)
    return c


class TestAnUnknownSurfaceIsNotAnAbsentFact:
    """The measured instance: an unregistered CLI turned 3/9 into 3/8, silently.

    ``_collect_cli_command_count`` used to return without a trace when no CLI
    surface was registered, so the denominator moved and no output said which
    fact had left.  Running the audit in-process — which is what
    ``beadloom ci``'s gate step does — was enough to see it.
    """

    @pytest.fixture(autouse=True)
    def _no_cli_surface(self) -> object:
        import beadloom.infrastructure.surface_registry as registry

        saved = registry._cli_group_provider
        registry.reset_surface_providers()
        yield
        registry._cli_group_provider = saved

    def test_the_fact_is_declined_with_a_reason_not_dropped(
        self, conn: sqlite3.Connection
    ) -> None:
        from beadloom.infrastructure.surface_registry import get_cli_group

        assert get_cli_group() is None, "the surface must be unknown for this test"

        fact_set = FactRegistry().collect_set(BEADLOOM_ROOT, conn)

        assert "cli_command_count" not in fact_set.facts
        reason = fact_set.not_applicable["cli_command_count"]
        assert "registered" in reason, reason


class TestThisRepository:
    """The equality the RFC demands: on Beadloom, the derivation returns today's values."""

    def test_beadloom_declines_none_of_its_own_facts(
        self, conn: sqlite3.Connection
    ) -> None:
        import beadloom.services.cli  # noqa: F401  — registers the CLI surface

        fact_set = FactRegistry().collect_set(BEADLOOM_ROOT, conn)

        assert fact_set.not_applicable == {}, (
            "this repository must lose no fact, or its audit output changed"
        )
        assert "mcp_tool_count" in fact_set.facts
        assert "cli_command_count" in fact_set.facts
