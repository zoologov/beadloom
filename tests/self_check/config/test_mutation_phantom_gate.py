"""Self-checks of this repository's manifest, CI workflows and configuration (BDL-074 A3).

Moved out of ``tests/test_mutation_phantom_gate.py``;
the product tests of the same code stay there.
Everything here asserts on this repository's own tree, so it carries the
``self_check`` marker by its folder (see ``tests/conftest.py``).
"""

from __future__ import annotations

from beadloom.application.mutation_scope import (
    check_mutation_scope,
)
from tests.support.repository_root import REPO_ROOT

#: This repository, whose own declaration must survive the join unchanged.


class TestThisRepositorysOwnDeclarationSurvivesTheJoin:
    """The nightly job's own invocation must stay answerable, not become red."""

    def test_every_declared_target_of_this_project_could_run_a_mutant(self) -> None:
        # Arrange
        project = REPO_ROOT

        # Act
        findings = check_mutation_scope(project)

        # Assert
        assert findings == []
