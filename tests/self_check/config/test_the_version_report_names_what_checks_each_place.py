"""Self-checks of this repository's manifest, CI workflows and configuration (BDL-074 A3).

Moved out of ``tests/test_the_version_report_names_what_checks_each_place.py``;
the product tests of the same code stay there.
Everything here asserts on this repository's own tree, so it carries the
``self_check`` marker by its folder (see ``tests/conftest.py``).
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from tests.test_the_version_report_names_what_checks_each_place import (
    _block,
    _run,
)

if TYPE_CHECKING:
    from collections.abc import Iterator


REPO_ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture(scope="module")
def repository_report() -> Iterator[str]:
    """One sweep of this repository, shared — it reads over a thousand files."""
    _, output = _run(REPO_ROOT)
    yield output


class TestTheNinePlacesTheReleaseHadToEdit:
    """The answer, checked against what cutting 4.0.0 actually edited.

    Commit ``f3b5593e`` is the record: nine files carrying a version literal that
    had to move, plus ``.beads/issues.jsonl``, which is the tracker's own export
    and is pruned by the sweep because no release edits it by hand.
    """

    @pytest.mark.parametrize(
        ("relative", "checker"),
        [
            ("src/beadloom/__init__.py", "packaging-manifest"),
            (".beadloom/_graph/beadloom.yml", "graph-summary-facts"),
            (".claude/CLAUDE.md", "doctor"),
            ("docs/getting-started.md", "docs-audit"),
            ("docs/services/cli.md", "docs-audit"),
            ("tests/test_integration_v1.py", "test-suite"),
        ],
    )
    def test_a_place_an_instrument_holds_is_reported_under_that_instrument(
        self, repository_report: str, relative: str, checker: str
    ) -> None:
        checked = _block(repository_report, "Checked (")

        assert relative in checked, checked
        group = next(line for line in checked.splitlines() if relative in line)
        assert checker in group, group

    @pytest.mark.parametrize(
        "relative",
        [
            "CHANGELOG.md",
            ".claude/development/ROADMAP.md",
            "docs/domains/doc-sync/features/docs-audit/SPEC.md",
        ],
    )
    def test_a_place_the_release_met_one_at_a_time_is_reported_as_checked_by_nothing(
        self, repository_report: str, relative: str
    ) -> None:
        assert relative in _block(repository_report, "Checked by nothing"), repository_report

    def test_the_tracker_export_is_not_a_place_because_no_release_edits_it(
        self, repository_report: str
    ) -> None:
        assert ".beads/issues.jsonl" not in repository_report
