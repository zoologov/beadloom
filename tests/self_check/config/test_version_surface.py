"""Self-checks of this repository's manifest, CI workflows and configuration (BDL-074 A3).

Moved out of ``tests/integration/doc_sync/version_surface/test_version_surface.py``;
the product tests of the same code stay there.
Everything here asserts on this repository's own tree, so it carries the
``self_check`` marker by its folder (see ``tests/conftest.py``).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from beadloom.doc_sync.version_surface import (
    DOCS_AUDIT,
    DOCTOR,
    GRAPH_SUMMARY_FACTS,
    PACKAGING_MANIFEST,
    TEST_SUITE,
    VersionSurface,
    read_version_surface,
)
from tests.support.repository_root import REPO_ROOT
from tests.support.version_surface import (
    places_at,
)


@pytest.fixture(scope="module")
def surface() -> VersionSurface:
    """This repository's own surface, read once for the class below."""
    return read_version_surface(REPO_ROOT)


@pytest.mark.skipif(
    not (REPO_ROOT / "src" / "beadloom" / "__init__.py").is_file(),
    reason="the nine places are this repository's own measurement",
)
class TestThisRepositoryIsFoundByDerivation:
    """The nine of 2026-09-10, found without any of them being written down.

    The count is the floor and not the ceiling: this epic's own waves 1 and 2
    added documents stating the current release, and the command is the answer
    to the question the hand-written list of nine kept getting wrong.

    The fixture projects above declare a version of their own for a reason. A
    fixture that happened to equal this project's real one put 50 rows of its
    own data into the first run of the command it feeds, which is the limit the
    module states wearing a different coat: a literal used as data and a literal
    used as a statement are told apart by no structure either of them carries.
    """

    def test_the_source_of_truth_is_this_project_s_own_manifest_chain(
        self, surface: VersionSurface
    ) -> None:
        assert surface.source_of_truth is not None
        assert surface.source_of_truth.path == Path("src/beadloom/__init__.py")

    @pytest.mark.parametrize(
        ("relative", "checkers"),
        [
            ("src/beadloom/__init__.py", (PACKAGING_MANIFEST,)),
            (".beadloom/_graph/beadloom.yml", (GRAPH_SUMMARY_FACTS,)),
            (".claude/CLAUDE.md", (DOCTOR,)),
            ("docs/getting-started.md", (DOCS_AUDIT,)),
            ("docs/services/cli.md", (DOCS_AUDIT,)),
            ("tests/test_integration_v1.py", (TEST_SUITE,)),
            ("CHANGELOG.md", ()),
            (".claude/development/ROADMAP.md", ()),
            ("docs/domains/doc-sync/features/docs-audit/SPEC.md", ()),
        ],
    )
    def test_each_of_the_nine_is_found_with_its_checker(
        self, surface: VersionSurface, relative: str, checkers: tuple[str, ...]
    ) -> None:
        found = places_at(surface, relative)

        assert found, f"{relative} was not derived"
        assert checkers in {place.checkers for place in found}

    def test_the_three_nothing_checks_are_named_as_such(self, surface: VersionSurface) -> None:
        unchecked = {str(place.path) for place in surface.unchecked}

        assert {
            "CHANGELOG.md",
            ".claude/development/ROADMAP.md",
            "docs/domains/doc-sync/features/docs-audit/SPEC.md",
        } <= unchecked

    def test_it_reports_the_population_it_swept(self, surface: VersionSurface) -> None:
        assert surface.population.files_read > 100
        assert surface.population.not_read
