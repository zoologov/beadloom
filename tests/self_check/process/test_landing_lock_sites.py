"""Self-checks of this repository's agent roles, hooks, tracker and commits (BDL-074 A3).

Moved out of ``tests/test_landing_lock_sites.py``;
the product tests of the same code stay there.
Everything here asserts on this repository's own tree, so it carries the
``self_check`` marker by its folder (see ``tests/conftest.py``).
"""

from __future__ import annotations

from pathlib import Path

from beadloom.application.waves import (
    LOCK_COMMAND,
)
from tests.test_landing_lock_sites import (
    _lock_sites,
)

REPO_ROOT = Path(__file__).resolve().parents[3]


def _this_projects_instructions() -> list[tuple[str, str]]:
    """Every artifact of this repository that INSTRUCTS an agent, plus what it ships.

    Two halves, and the boundary between them matters. The composed half is
    exactly the population :func:`beadloom.application.waves` checks through the
    command — imported rather than restated, so a tool added to the flow is
    covered here by the same act. The second half is the templates this project
    ships, which reach an adopter's agents without ever being composed in this
    tree.

    **What is deliberately outside it.** ``.claude/development/`` holds the issue
    log and the epic documents, and both QUOTE the defective call form because
    quoting it is how the defect was recorded (BDL-UX #194, #237). A record of a
    defect is not an instruction to repeat it. The cost of the exclusion is real
    and is stated rather than hidden: an instruction written into a planning
    document is invisible to this assertion, which is the same limit
    ``role-duties`` states about the coordinator's launch prompt.
    """
    from beadloom.services.bd_seam.population import flow_artifacts, shipped_templates

    found: list[tuple[str, str]] = list(flow_artifacts(REPO_ROOT))
    found.extend(
        (label, text) for label, text in shipped_templates() if LOCK_COMMAND in text
    )
    return found


class TestThisRepositoryInstructsOnlyTheFormThatGrantsIt:
    """The fix, held in place. Red before this bead, green after it."""

    def test_the_lock_is_instructed_somewhere_at_all(self) -> None:
        """Otherwise the assertion below would pass over an empty population."""
        assert _this_projects_instructions()

    def test_no_instruction_this_project_ships_or_composes_is_defective(self) -> None:
        defective = [
            f"{site.source}:{site.line} `{site.invocation}` {site.defects}"
            for site in _lock_sites(_this_projects_instructions())
            if site.defects
        ]
        assert defective == []
