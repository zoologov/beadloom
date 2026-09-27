"""Self-checks of this repository's agent roles, hooks, tracker and commits (BDL-074 A3).

Moved out of ``tests/test_the_explore_role_is_composed_like_the_others.py``;
the product tests of the same code stay there.
Everything here asserts on this repository's own tree, so it carries the
``self_check`` marker by its folder (see ``tests/conftest.py``).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from beadloom.application.planning_report import planning_report
from beadloom.application.work_item_routing import (
    AXES_ROLE,
)
from beadloom.doc_sync.work_item_type import (
    ROUTE_NOT_SUPPORTED_BY_THE_AXES,
    ROUTED_WITHOUT_AXES,
)
from beadloom.onboarding.agentic_flow_setup import (
    composed_command,
)
from beadloom.onboarding.flow_config import (
    load_flow_config,
)
from beadloom.onboarding.role_composer import (
    compose_role,
)

if TYPE_CHECKING:
    from pathlib import Path


_REPO_ROOT_MARKER = "pyproject.toml"


def _repo_root() -> Path:
    from pathlib import Path as _Path

    here = _Path(__file__).resolve().parent
    for candidate in (here, *here.parents):
        if (candidate / _REPO_ROOT_MARKER).is_file():
            return candidate
    msg = "the repository root was not found above this test file"
    raise AssertionError(msg)


class TestTheReportCarriesTheTwoChecksAndTheirPopulation:
    """A check reported as "0 findings" over a population of zero has verified nothing."""

    def test_this_repository_enters_the_population(self) -> None:
        """A check that reads nothing here would be verified nowhere."""
        # Arrange
        from beadloom.application.doc_shape import planning_documents

        root = _repo_root()

        # Act
        report = planning_report(planning_documents(root), project_root=root)

        # Assert
        assert report.applicable[ROUTED_WITHOUT_AXES] > 0
        for finding in report.findings:
            if finding.check in {ROUTED_WITHOUT_AXES, ROUTE_NOT_SUPPORTED_BY_THE_AXES}:
                assert (root / finding.path).is_file(), finding.path


class TestTheLiveFlowCarriesTheRole:
    """This repository is the reference implementation; its own flow must hold."""

    def test_the_live_adapter_equals_its_composition(self) -> None:
        root = _repo_root()
        live = (root / ".claude" / "agents" / f"{AXES_ROLE}.md").read_text(
            encoding="utf-8"
        )
        assert live == compose_role(
            AXES_ROLE, architecture="ddd", stack=("python",), project_root=root
        )

    def test_the_live_command_equals_its_composition(self) -> None:
        root = _repo_root()
        live = (root / ".claude" / "commands" / "task-init.md").read_text(
            encoding="utf-8"
        )
        assert live == composed_command(
            "task-init", load_flow_config(root), root
        )
