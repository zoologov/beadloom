"""Self-checks of this repository's agent roles, hooks, tracker and commits (BDL-074 A3).

Moved out of ``tests/test_bd_answers.py``;
the product tests of the same code stay there.
Everything here asserts on this repository's own tree, so it carries the
``self_check`` marker by its folder (see ``tests/conftest.py``).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from beadloom.services.bd_seam.assumptions import (
    ASSUMPTION_UNBLOCKED_IS_READY,
    VERDICT_UNSECURED,
)
from beadloom.services.bd_seam.population import project_report

if TYPE_CHECKING:
    from pathlib import Path


def test_no_artifact_of_ours_instructs_the_suggestion_without_its_confirmation(
    self_check_snapshot: Path
) -> None:
    """The project-wide check, red on the tree this bead started from.

    Measured at that point: NINE artifacts instructed `bd close --suggest-next`
    and named `bd ready` nowhere — `.claude/agents/{test,review,tech-writer}.md`,
    their three sources under `templates/roles/core/`, their three vendored
    snapshots under `templates/agentic_flow/agents/`, and `services/mcp_server.py`.
    `dev.md`, `CLAUDE.md`, `checkpoint.md` and `coordinator.md` already carried it.
    A role core added later without the confirmation fails here.
    """
    report = project_report(self_check_snapshot)
    unsecured = sorted(
        {
            site.source
            for site in report.sites
            if any(
                a.name == ASSUMPTION_UNBLOCKED_IS_READY and a.verdict == VERDICT_UNSECURED
                for a in site.assumptions
            )
        }
    )
    assert unsecured == [], (
        "these artifacts instruct `bd close --suggest-next` and name `bd ready` "
        "nowhere, so a reader of them alone is never told the suggestion can "
        "include still-blocked beads: " + ", ".join(unsecured)
    )


def test_the_project_asks_bd_ready_for_its_whole_answer_wherever_it_asks_at_all(
    self_check_snapshot: Path
) -> None:
    """Any `bd ready` in our Python names the limit, because the cap is 100.

    This flow calls `bd ready` authoritative at forty sites. The moment our own
    code depends on it, the call form has to lift the cap or the confirmation is
    itself narrowed.
    """
    report = project_report(self_check_snapshot)
    ready = [
        site for site in report.sites if site.channel == "python" and site.subcommand == "ready"
    ]
    assert ready, "no python call site asks `bd ready` at all"
    for site in ready:
        assert not site.unsettled, f"{site.source}:{site.line} `{site.text}` is capped"
