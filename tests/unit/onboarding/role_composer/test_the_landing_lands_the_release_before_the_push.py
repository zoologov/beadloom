"""The composed landing states the release before the push (BDL-083 S2g, BDL-UX #354, D12).

Measured on 9.0.0: the landing fragment and the coordinator's checklist said acquire
before the commit and release after, and nothing about the push. The first outside
adopter's second clone pushed between the commit and the release, so the release reached
no merged commit and the trunk exported the slot as held by a closed bead. Every composed
landing block now runs acquire -> commit -> release -> export -> the export landed -> push,
in that order, and these tests read the order off the composed text.
"""

from __future__ import annotations

import pytest

from beadloom.onboarding.agentic_flow_setup import composed_command
from beadloom.onboarding.flow_config import FlowConfig
from beadloom.onboarding.role_composer import compose_role

#: The steps of one landing, as the first word(s) each step's line starts with.
_SEQUENCE = (
    "bd merge-slot acquire --holder <bead-id>",
    "# ... ",
    "bd merge-slot release --holder <bead-id>",
    "bd export -o .beads/issues.jsonl",
    "git commit ",
    "git push",
)


def _landing_block(text: str) -> list[str]:
    """The lines of the fenced block that instructs the acquire."""
    start = text.index("bd merge-slot acquire --holder <bead-id>")
    opening = text.rindex("```", 0, start)
    closing = text.index("```", start)
    return [line.strip() for line in text[opening:closing].splitlines()[1:] if line.strip()]


def _order(lines: list[str]) -> list[int]:
    return [next(i for i, line in enumerate(lines) if line.startswith(step)) for step in _SEQUENCE]


@pytest.mark.parametrize("language", ["en", "ru"])
@pytest.mark.parametrize("role", ["dev", "test", "review", "tech-writer", "explore"])
def test_every_role_s_landing_releases_and_exports_before_the_push(
    role: str, language: str
) -> None:
    text = compose_role(role, architecture="ddd", stack=("python",), language=language)
    order = _order(_landing_block(text))
    assert order == sorted(order), _landing_block(text)


def test_the_coordinator_checklist_releases_and_exports_before_the_push() -> None:
    config = FlowConfig(tools=("claude",), architecture="ddd", stack=("python",))
    text = composed_command("coordinator", config, None)
    order = _order(_landing_block(text))
    assert order == sorted(order), _landing_block(text)


@pytest.mark.parametrize(
    ("language", "named"),
    [("en", "beadloom landing-check"), ("ru", "beadloom landing-check")],
)
def test_the_landing_names_the_check_that_refuses_a_push_carrying_its_hold(
    language: str, named: str
) -> None:
    text = compose_role("dev", architecture="ddd", stack=("python",), language=language)
    assert named in text
