"""Self-checks of this repository's documents and published site (BDL-074 A3).

Moved out of ``tests/test_two_readers_of_one_markdown_table.py``;
the product tests of the same code stay there.
Everything here asserts on this repository's own tree, so it carries the
``self_check`` marker by its folder (see ``tests/conftest.py``).
"""

from __future__ import annotations

from beadloom.application.active_table.table import split_table_row
from beadloom.doc_sync.tables import cells_of
from tests.support.repository_root import REPO_ROOT

_PLANNING = (
    REPO_ROOT / ".claude" / "development" / "docs" / "features"
)


class TestTheTwoReadersOnThisRepositorysOwnDocuments:
    """The control: on this arrangement the two readers agree, which is the point.

    A divergence nobody can produce here is exactly the defect class BDL-UX #240
    records, so the measurement is kept as a test rather than as a sentence.
    """

    def test_they_agree_on_every_line_of_every_planning_document(self) -> None:
        documents = sorted(_PLANNING.glob("*/*.md"))
        assert len(documents) > 50, f"only {len(documents)} planning documents found"
        disagreements = [
            (path.name, number, line)
            for path in documents
            for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1)
            if cells_of(line) != split_table_row(line)
        ]
        assert disagreements == []

    def test_the_agreement_is_a_property_of_the_documents_and_not_of_the_readers(
        self,
    ) -> None:
        """The same two readers, given a row this repository does not write."""
        assert cells_of("|| a | b ||") != split_table_row("|| a | b ||")
