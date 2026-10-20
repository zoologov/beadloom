"""The composed ``CLAUDE.md`` states the project-root rule (BDL-083 S2e, BDL-UX #325).

``beadloom-7pd6``, the owner's ruling of 2026-10-12. ``init`` and ``doctor`` refuse a project
root below the git root, and an agent reading the composed file meets the rule before it runs
either: in the one-time Setup section, with the commands that refuse it.
"""

from __future__ import annotations

from beadloom.onboarding.agentic_flow_setup import composed_claude_md
from beadloom.onboarding.flow_config import FlowConfig


def _setup_section() -> str:
    text = composed_claude_md(
        FlowConfig(tools=("claude",), architecture="ddd", stack=("python",)),
        None,
        project_name="example",
    )
    start = text.index("### Setup (one-time, per clone)")
    return " ".join(text[start : text.index("### BEFORE any work", start)].split())


def test_the_setup_section_says_the_project_root_is_the_git_root() -> None:
    section = _setup_section()

    assert "The project root is the git root." in section


def test_the_setup_section_names_the_commands_that_refuse_a_nested_root() -> None:
    section = _setup_section()

    for command in ("beadloom init", "beadloom doctor", "beadloom sync-check --since"):
        assert command in section, command
