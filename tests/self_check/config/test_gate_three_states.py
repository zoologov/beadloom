"""Self-checks of this repository's manifest, CI workflows and configuration (BDL-074 A3).

Moved out of ``tests/test_gate_three_states.py``;
the product tests of the same code stay there.
Everything here asserts on this repository's own tree, so it carries the
``self_check`` marker by its folder (see ``tests/conftest.py``).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from tests.support.gate_states import (
    gate_over_state,
    names_after,
)
from tests.support.repository_root import REPO_ROOT as _REPO_ROOT


def _assert_no_self_count_leaks(line: str) -> None:
    r"""Fail if *line* carries one of THIS package's surface counts as a number.

    Bounded by ``(?<!\d)…(?!\d)`` rather than by substring: ``"18" in line``
    also matches ``180``, so it would report a leak that is not one. A different
    fact of this project that happens to equal one of the two counts would still
    be a false positive — it names the number when it fires, so the reader can
    see which it was, and a red naming its evidence is actionable in a way a
    literal that silently stopped guarding is not.
    """
    for name, count in _our_own_surface_counts().items():
            assert not re.search(rf"(?<!\d){count}(?!\d)", line), (
                f"the Gate line for a foreign project carries {count}, which is "
                f"THIS package's {name} — a self-fact reported as theirs:\n{line}"
            )


#: This package's own checkout — the only project whose surface counts are
#: its own, which is exactly what the leak check below must know.


def _our_own_surface_counts() -> dict[str, int]:
    """What Beadloom's own MCP and CLI surfaces currently count.

    Read through the same registry the product reports with, rather than by
    counting the surfaces a second time here: ``MCP_TOOL_CATALOG`` and the
    registered Click group are already summed by ``FactRegistry``, and a
    second copy of that arithmetic is a thing that can disagree. So the check
    above cannot go stale against a product that has grown a tool or a
    command. Measured when written: 18 and 43, the two literals this replaced.
    """
    from beadloom.doc_sync.audit import FactRegistry
    from beadloom.infrastructure.db import create_schema, open_db

    conn = open_db(Path(":memory:"))
    create_schema(conn)
    try:
        collected = FactRegistry().collect_set(_REPO_ROOT, conn)
    finally:
        conn.close()

    counts: dict[str, int] = {}
    for name in ("mcp_tool_count", "cli_command_count"):
        fact = collected.facts.get(name)
        assert fact is not None, (
            f"this package does not compute its own {name} in this process, so "
            f"the check below would look for a number that does not exist and "
            f"pass vacuously — declined as: {collected.not_applicable.get(name)}"
        )
        assert isinstance(fact.value, int) and fact.value > 0, fact
        counts[name] = fact.value
    return counts


class TestTheThreePopulationsStayApartInTheGateLine:
    """``verified`` / ``declared but unverified`` / ``not applicable``, disjoint."""

    def _audit_line(self, tmp_path: Path, state: str) -> str:
        _, payload = gate_over_state(tmp_path, state)
        steps = payload["steps"]
        assert isinstance(steps, list)
        for step in steps:
            if step["name"] == "docs-audit":
                return str(step["summary"])
        raise AssertionError("the Gate ran no docs-audit step")

    def test_the_project_is_told_neither_of_our_own_surface_counts(self, tmp_path: Path) -> None:
        """A SELF-FACT IS NOT A PROJECT FACT, asserted where a user reads it.

        ``invoice-svc`` was measured being told it had 18 MCP tools and 43 CLI
        commands. Both facts are now declined; this holds the Gate line to
        naming them as declined rather than quietly counting them.

        The two numbers are READ from the surfaces they describe rather than
        written here as ``18`` and ``43`` (BDL-062.10, m5). A literal stops
        guarding the leak it was written for on the day Beadloom gains a tool or
        a command, and says nothing when it does — the assertion keeps passing
        against a number the product no longer produces. Reading them means the
        check follows the surface.
        """
        line = self._audit_line(tmp_path, "agrees")
        declined = names_after(line, "NOT APPLICABLE to this project:")

        assert {"mcp_tool_count", "cli_command_count"} <= declined
        _assert_no_self_count_leaks(line)

    def test_the_number_check_is_not_carried_by_the_name_check(self) -> None:
        """The second assertion bites on its own, measured on a synthetic line.

        Reverting the ``.5`` correction makes the two names disappear from the
        declined clause, so the set-membership assertion above fails FIRST and
        the numbers are never reached — measured. That is what let two literals
        sit there guarding nothing. This drives the number check with a line
        whose names are correctly declined and whose value leaked anyway, which
        is the only shape the number check is the sole guard against.
        """
        counts = _our_own_surface_counts()
        clean = (
            "6/9 declared fact(s) verified, NOT APPLICABLE to this project: "
            "cli_command_count, mcp_tool_count"
        )
        _assert_no_self_count_leaks(clean)

        leaked = f"{clean} (mcp_tool_count={counts['mcp_tool_count']})"
        with pytest.raises(AssertionError, match="self-fact reported as theirs"):
            _assert_no_self_count_leaks(leaked)

    def test_the_number_check_does_not_fire_on_a_longer_number(self) -> None:
        """``18`` inside ``180`` is not a leak, and a substring test would say so."""
        counts = _our_own_surface_counts()
        digits = str(counts["mcp_tool_count"])
        _assert_no_self_count_leaks(f"a line mentioning {digits}0 and 9{digits} only")
