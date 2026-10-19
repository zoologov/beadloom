"""The composed `task-init` names an absolute plan path (BDL-083 S2h, BDL-UX #356 g).

Measured on 9.0.0: the `task-init` text passed `plan.json` to `bd create --graph`
three times with no directory, so an agent working from the document folder wrote
the plan there and left it behind in both work items of the adopter's audit. The
MCP `task_init` already writes its plan into a temporary directory; the text now
says the same.
"""

from __future__ import annotations

import re

import pytest

from beadloom.onboarding.agentic_flow_setup import composed_command
from beadloom.onboarding.flow_config import FlowConfig

#: Every argument a `bd create --graph` line in the text passes.
_GRAPH_ARGUMENT = re.compile(r"bd create --graph (\S+)")


@pytest.fixture()
def task_init() -> str:
    config = FlowConfig(tools=("claude",), architecture="ddd", stack=("python",))
    return composed_command("task-init", config, None)


def test_every_plan_argument_is_the_temporary_path(task_init: str) -> None:
    arguments = _GRAPH_ARGUMENT.findall(task_init)
    assert len(arguments) == 3
    assert set(arguments) == {'"$plan"'}


def test_the_plan_path_is_made_outside_the_project(task_init: str) -> None:
    assert 'plan="$(mktemp -d)/plan.json"' in task_init


def test_no_relative_plan_file_is_named(task_init: str) -> None:
    assert re.search(r"(?<![/\w])plan\.json(?!\")", task_init) is None
