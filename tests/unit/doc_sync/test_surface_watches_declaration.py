"""What tells a document that MAKES a watch declaration from one that SHOWS it.

BDL-061.86, measured on this repository 2026-08-24: ``sync-check`` reported
``docs/domains/context-oracle/features/code-indexer/SPEC.md`` as a reference
document watching ``cli,graph``. That SPEC declares no watch — its header carries
no annotation. It opted in from an EXAMPLE inside a fenced python block whose own
caption reads ``<- also an example: not read``. The caption was false, and the
document it is written in is the one that proved it.

**The honest answer to "how do you tell them apart" is that the SYNTAX cannot.**
An annotation inside a fence is byte-identical to one outside it. What separates
them is POSITION, and position decides three of the four shapes a real document
uses: fenced, indented, and written inside a sentence. The fourth — an unfenced
example at column 0, in prose — position cannot decide, and this module does not
pretend to: such a document is read as declaring. The remedy is the one a
markdown document uses anyway, which is to fence the sample it is showing.
"""

from __future__ import annotations

from beadloom.doc_sync.surface import parse_watches


class TestADeclarationIsMadeAtTheStartOfALine:
    """The form every real reference document in this repository already uses."""

    def test_a_header_annotation_declares(self) -> None:
        text = "# Title\n\n<!-- beadloom:watches=cli,graph -->\n\nProse.\n"

        assert parse_watches(text) == ["cli", "graph"]

    def test_three_spaces_of_indentation_are_still_a_declaration(self) -> None:
        """Markdown's own boundary: a fourth space starts a code block, three do not."""
        text = "   <!-- beadloom:watches=cli -->\n"

        assert parse_watches(text) == ["cli"]

    def test_the_first_declaration_decides(self) -> None:
        text = "<!-- beadloom:watches=cli -->\n<!-- beadloom:watches=graph -->\n"

        assert parse_watches(text) == ["cli"]


class TestADemonstrationIsNotADeclaration:
    """Four shapes a document that documents the syntax really contains."""

    def test_a_fenced_sample_is_shown_not_declared(self) -> None:
        text = "How to declare one:\n\n```markdown\n<!-- beadloom:watches=cli,graph -->\n```\n"

        assert parse_watches(text) is None

    def test_a_tilde_fenced_sample_is_shown_not_declared(self) -> None:
        text = "~~~markdown\n<!-- beadloom:watches=cli,graph -->\n~~~\n"

        assert parse_watches(text) is None

    def test_an_indented_sample_is_shown_not_declared(self) -> None:
        text = 'Write it at the top::\n\n    <!-- beadloom:watches=cli,graph -->  <- an example\n'

        assert parse_watches(text) is None

    def test_an_annotation_inside_a_sentence_is_shown_not_declared(self) -> None:
        text = "A doc opts in with `<!-- beadloom:watches=cli,graph -->` near its top.\n"

        assert parse_watches(text) is None

    def test_a_fence_ends_only_on_its_own_marker(self) -> None:
        """A tilde block is not closed by backticks, so what follows stays a sample."""
        text = "~~~markdown\n```\n<!-- beadloom:watches=cli,graph -->\n~~~\n"

        assert parse_watches(text) is None


