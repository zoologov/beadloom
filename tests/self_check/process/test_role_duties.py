"""Self-checks of this repository's agent roles, hooks, tracker and commits (BDL-074 A3).

Moved out of ``tests/test_role_duties.py``;
the product tests of the same code stay there.
Everything here asserts on this repository's own tree, so it carries the
``self_check`` marker by its folder (see ``tests/conftest.py``).
"""

from __future__ import annotations

from beadloom.onboarding.role_duties import duty_report
from tests.support.repository_root import REPO_ROOT as _REPO_ROOT


def test_every_duty_this_repository_declares_reaches_the_roles_it_names() -> None:
    """Beadloom's own flow, checked against itself.

    A self-fact rather than a fixture: it holds today because this repository
    declares no duty yet, and it goes on holding when `beadloom-67t1` declares
    the example-duty duty and writes it into the role cores. A regression there is
    exactly the finding this check exists to make.
    """
    report = duty_report(_REPO_ROOT)

    assert report.findings == ()
