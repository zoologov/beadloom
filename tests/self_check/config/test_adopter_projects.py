"""Self-checks of this repository's manifest, CI workflows and configuration (BDL-074 A3).

Moved out of ``tests/test_adopter_projects.py``;
the product tests of the same code stay there.
Everything here asserts on this repository's own tree, so it carries the
``self_check`` marker by its folder (see ``tests/conftest.py``).
"""

from __future__ import annotations


class TestTheAdoptersVersionIsTheAdoptersOwn:
    """The rendered version must come from the project, or not be rendered."""

    def test_this_repository_can_read_its_own_declared_version(self) -> None:
        """The dogfood leg — and the one case where being right proves little."""
        from pathlib import Path as _Path

        from beadloom import __version__
        from beadloom.onboarding.scanner.project_facts import detect_project_version

        repo = _Path(__file__).resolve().parents[3]

        assert detect_project_version(repo) == __version__
