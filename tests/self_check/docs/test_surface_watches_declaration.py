"""Self-checks of this repository's documents and published site (BDL-074 A3).

Moved out of ``tests/test_surface_watches_declaration.py``;
the product tests of the same code stay there.
Everything here asserts on this repository's own tree, so it carries the
``self_check`` marker by its folder (see ``tests/conftest.py``).
"""

from __future__ import annotations

from beadloom.doc_sync.surface import parse_watches
from tests.support.repository_root import REPO_ROOT


class TestADemonstrationIsNotADeclaration:
    """Four shapes a document that documents the syntax really contains."""

    def test_a_document_that_only_shows_the_form_declares_nothing(self) -> None:
        """The measured case, read from the file that was measured.

        Read from disk rather than restated: the finding was that this SPEC's own
        caption claimed the sample was not read, and a fixture copy of the sample
        could go on being true after the SPEC changed.
        """
        spec = REPO_ROOT / "docs/domains/context-oracle/features/code-indexer/SPEC.md"
        text = spec.read_text(encoding="utf-8")

        assert "beadloom:watches" in text, "the SPEC no longer shows the form it was measured on"
        assert parse_watches(text) is None


class TestTheDeclarationsThisRepositoryReallyMakes:
    """The population after the fix, so a silent loss of one is a failing test."""

    def test_the_reference_documents_still_declare_what_they_declared(self) -> None:
        expected = {
            "README.md": ["cli", "graph", "flow.yml"],
            "README.ru.md": ["cli", "graph", "flow.yml"],
            "docs/architecture.md": ["graph", "cli"],
            "docs/getting-started.md": ["cli", "flow.yml"],
            "docs/guides/bdd-scenarios.md": ["cli", "graph", "flow.yml"],
            "docs/guides/document-kinds.md": ["cli", "flow.yml"],
            "docs/guides/parallel-waves.md": ["cli", "graph", "flow.yml"],
            "docs/guides/project-overlays.md": ["cli", "flow.yml"],
            "docs/services/cli.md": ["cli", "graph", "flow.yml"],
        }

        found = {
            path: parse_watches((REPO_ROOT / path).read_text(encoding="utf-8"))
            for path in expected
        }

        assert found == expected

    def test_the_documents_that_only_describe_the_mechanism_leave_the_population(
        self,
    ) -> None:
        """CHANGELOG and two SPECs were enrolled by a sentence about the feature.

        Each was measured in ``reference_state`` before the fix. None of them
        declares a watch in its header, and a permanently drifting entry nobody
        can attest is how the ``surface_drift`` channel stops being read.
        """
        described_only = [
            "CHANGELOG.md",
            "docs/domains/context-oracle/features/code-indexer/SPEC.md",
            "docs/domains/doc-sync/features/sync-check/SPEC.md",
        ]

        found = {
            path: parse_watches((REPO_ROOT / path).read_text(encoding="utf-8"))
            for path in described_only
        }

        assert found == dict.fromkeys(described_only)
