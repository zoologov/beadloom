"""The one definition of what retires a declared exclusion, and where it lives.

BDL-070 B2 (``beadloom-xmfs``). Two surfaces declare an exit condition and are
required to read the same answer: ``forbid_import.exempt[].until`` in
``rules.yml``, which the ``graph`` domain evaluates, and
``guards.<name>.exclusions[].until`` in ``flow.yml``, which ``onboarding``
evaluates. The definition was written in ``graph/rules/types.py`` because the
first of the two was built first, and ``onboarding`` reached UP across a peer
domain to get it — two of the sixteen same-layer crossings this bead triaged
(``config-check -> rule-engine`` and ``flow-suppression -> rule-engine``) were
that one import.

A vocabulary two peers share belongs BELOW both of them, which in this
declaration is ``infrastructure``; ``scan-paths`` and ``doc-roots`` are the same
shape and the same reason. The public import path does not move, so no adopter
reading ``beadloom.graph.rules.exit_condition_deadline`` notices.
"""

from __future__ import annotations

import ast
from datetime import date
from pathlib import Path

import pytest

from beadloom.graph.rules import exit_condition_deadline as reexported
from beadloom.infrastructure.exit_condition import (
    deadline_passed,
    exit_condition_deadline,
)

_ONBOARDING = Path(__file__).resolve().parents[1] / "src" / "beadloom" / "onboarding"

#: The two ``onboarding`` modules that read an exit condition. Named rather than
#: derived, because the property is about these files and not about the package:
#: ``graph_files`` and ``agent-prime`` import the ``graph`` domain for reasons
#: this bead exempted, and a blanket assertion would be false.
DECLARERS = ("config_sync.py", "flow_suppression.py")


def _imported_modules(path: Path) -> set[str]:
    """Every dotted module name *path* imports, at any nesting depth."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            found.add(node.module)
    return found


class TestWhereTheDefinitionLives:
    """The vocabulary is one function, below both layers that declare one."""

    def test_the_public_import_path_still_answers(self) -> None:
        """``beadloom.graph.rules`` re-exports the same object, not a copy."""
        assert reexported is exit_condition_deadline

    @pytest.mark.parametrize("module", DECLARERS)
    def test_an_exit_condition_declarer_does_not_reach_into_the_graph_domain(
        self, module: str
    ) -> None:
        """Neither onboarding declarer imports ``graph`` for this vocabulary."""
        imported = _imported_modules(_ONBOARDING / module)
        graph_imports = {name for name in imported if name.startswith("beadloom.graph")}
        assert graph_imports == set()

    @pytest.mark.parametrize("module", DECLARERS)
    def test_an_exit_condition_declarer_reads_it_from_infrastructure(self, module: str) -> None:
        """It reads the definition from where the definition now lives."""
        assert "beadloom.infrastructure.exit_condition" in _imported_modules(
            _ONBOARDING / module
        )


class TestDeadlinePassed:
    """The question both expiry checks ask, asked in one place."""

    def test_an_event_has_no_deadline_to_pass(self) -> None:
        assert deadline_passed("the repository read seam lands", today=date(2030, 1, 1)) is False

    def test_the_deadline_day_itself_is_still_live(self) -> None:
        """``until`` names the last day covered, so today is not yet past it."""
        assert deadline_passed("2026-09-13", today=date(2026, 9, 13)) is False

    def test_the_day_after_the_deadline_has_passed(self) -> None:
        assert deadline_passed("2026-09-13", today=date(2026, 9, 14)) is True
