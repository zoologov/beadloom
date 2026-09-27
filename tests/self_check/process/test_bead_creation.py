"""Self-checks of this repository's agent roles, hooks, tracker and commits (BDL-074 A3).

Moved out of ``tests/test_bead_creation.py``;
the product tests of the same code stay there.
Everything here asserts on this repository's own tree, so it carries the
``self_check`` marker by its folder (see ``tests/conftest.py``).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from beadloom.services.bd_seam.assumptions import (
    ASSUMPTION_ALLOCATED_ID,
    ASSUMPTION_INTENDED_ID,
    VERDICT_UNSECURED,
)
from beadloom.services.bd_seam.population import project_report

if TYPE_CHECKING:
    from pathlib import Path


class TestTheAnswerIsReadFromBdRatherThanScraped:
    def test_the_creation_site_is_visible_to_the_derivation_that_judges_it(
        self, self_check_snapshot: Path
    ) -> None:
        """The argv is spelled at the call, because a helper would hide it.

        `bd_seam.invocations` resolves a list literal handed to ``run_bd`` and
        cannot follow a function call, so an argv builder here would leave the
        scaffold reporting NOTHING rather than reporting `secured`. This reddens
        the day the literal is tidied into a helper.
        """
        report = project_report(self_check_snapshot)
        creates = [
            site
            for site in report.sites
            if site.channel == "python" and site.subcommand == "create"
        ]
        assert creates, "the scaffold's `bd create` is invisible to the derivation"
        assert all("--graph" in site.flags and "--json" in site.flags for site in creates)


class TestThisProjectSOwnPopulation:
    """What the derived report says about this repository after the fix."""

    def test_no_python_call_site_of_ours_authors_a_bead_id(
        self, self_check_snapshot: Path
    ) -> None:
        """The two sites BDL-UX #171 named in our own code are settled.

        This reddens the day a Python creation path goes back to scraping an id
        out of ``--silent`` or wiring an edge from an id it authored.
        """
        report = project_report(self_check_snapshot)
        offending = [
            f"{site.source}:{site.line} {site.subcommand}"
            for site in report.sites
            if site.channel == "python"
            for entry in site.assumptions
            if entry.name in (ASSUMPTION_ALLOCATED_ID, ASSUMPTION_INTENDED_ID)
            and entry.verdict == VERDICT_UNSECURED
        ]
        assert offending == []
