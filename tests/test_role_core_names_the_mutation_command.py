"""The test role's mutation duty names the command that answers it.

BDL-061 S4 shipped a mutation DUTY into every composed test role and no runner,
so the duty could only be discharged in prose. BDL-068 S3 built the instrument:
`beadloom mutation` refuses to turn an absence into a number, a nightly job runs
it under a floor, and `pyproject` carries the scope. The duty and the instrument
still arrived at different readers — the role core read "Record the tool, the
target and the surviving count in the bead comment" while the string
`beadloom mutation` appeared in no role file.

The population below is DERIVED, not spelled: every bullet of the mutation
section that routes a result to the tracker is judged, so a bullet added later
in the same shape is judged too. The same slice wired `beadloom rooms` into
every role through `_rooms.md.txt`; this is that wiring for the one duty it
skipped, and the general form — a duty declared for a role is carried by that
role's composed core, in both directions — is a separate bead.
"""

from __future__ import annotations

import re

from beadloom.onboarding.agentic_flow_setup import vendored_flow_root
from beadloom.onboarding.role_composer import compose_role, roles_templates_root

#: The command the duty is discharged with.
MUTATION_COMMAND = "beadloom mutation"

#: Where a result is routed when it is written rather than reported.
_ROUTES_TO_THE_TRACKER = re.compile(r"bead comment|checkpoint", re.IGNORECASE)

#: The mutation section's heading, and the level a sibling section starts at.
_SECTION_HEADING = "### Mutation testing"


def _mutation_section(text: str) -> str:
    """The mutation section of a composed role, up to the next heading."""
    _, _, after = text.partition(_SECTION_HEADING)
    assert after, f"no {_SECTION_HEADING!r} section in this role"
    section, _, _ = after.partition("\n### ")
    return section


def _bullets(section: str) -> list[str]:
    """The section's bullets, each with its continuation lines."""
    bullets: list[str] = []
    for line in section.splitlines():
        if line.startswith("- "):
            bullets.append(line)
        elif bullets and line.startswith("  "):
            bullets[-1] += "\n" + line
    return bullets


def _composed_test_role() -> str:
    return compose_role("test", architecture="ddd", stack=("python",))


class TestTheDutyAndTheInstrumentReachTheSameReader:
    def test_the_composed_test_role_names_the_command(self) -> None:
        assert MUTATION_COMMAND in _mutation_section(_composed_test_role())

    def test_a_bullet_that_routes_a_result_to_the_tracker_names_the_command(
        self,
    ) -> None:
        """A result written into a comment by hand is the shape S3 removed.

        The population is every bullet that sends something to a bead comment or
        a checkpoint, so this bites on a bullet nobody has written yet.
        """
        section = _mutation_section(_composed_test_role())
        prose_only = [
            bullet
            for bullet in _bullets(section)
            if _ROUTES_TO_THE_TRACKER.search(bullet)
            and MUTATION_COMMAND not in bullet
        ]
        assert prose_only == []

    def test_the_core_is_the_single_home_of_the_statement(self) -> None:
        """One home, for the reason `_rooms.md.txt` has one: copies drift."""
        core = roles_templates_root() / "core"
        carriers = [
            path.name
            for path in sorted(core.glob("*.md.txt"))
            if MUTATION_COMMAND in path.read_text(encoding="utf-8")
        ]
        assert carriers == ["test.md.txt"]


class TestTheShippedAdaptersCarryItAfterRecomposition:
    def test_the_vendored_test_adapter_carries_the_command(self) -> None:
        """What an adopter's `setup-agentic-flow` actually drops on disk."""
        vendored = (vendored_flow_root() / "agents" / "test.md.txt").read_text(
            encoding="utf-8"
        )
        assert MUTATION_COMMAND in _mutation_section(vendored)
