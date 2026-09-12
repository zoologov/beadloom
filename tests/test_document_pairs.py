"""BDL-069 S4 (`beadloom-19m6`) — the declared document pair, compared by shape.

The reproduction is the last class here and is not a hand-written stand-in: it
runs over the two READMEs exactly as they stood on 2026-09-10 at commit
``31f8c9cb``, the parent of the commit that repaired them, kept under
``tests/acceptance/fixtures/readme_pair_2026_09_10/``. The English file was missing a
paragraph the Russian one had, and the only number that differed between the two
files was a line count — 362 against 360, which nothing reads and which cannot
be told apart from a translator wrapping two sentences differently. That is why
the check compares block SEQUENCES and not sizes.

The red case is measured, not assumed. The pair AGREES at ``0404280f`` (86
blocks each) and at ``aa21caff`` (109 each); the divergence was introduced by
the Russian-side edits of 2026-09-10 and lived only between ``31f8c9cb`` and
``97fafca5``.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from beadloom.doc_sync.document_pairs import (
    BLOCK_KIND,
    CODE,
    HEADING,
    LIST,
    PARAGRAPH,
    ROW_COUNT,
    TABLE,
    UNPAIRED_BLOCK,
    PairReport,
    check_document_pairs,
    compare_documents,
    read_blocks,
    read_pair_declaration,
)

#: Shared with the acceptance steps, and it lives under ``tests/acceptance/``
#: because the suite there is copied out and run on its own.
FIXTURE_PAIR = (
    Path(__file__).resolve().parent / "acceptance" / "fixtures" / "readme_pair_2026_09_10"
)


def _declare(root: Path, *pairs: tuple[str, str]) -> None:
    body = "document_pairs:\n" + "".join(
        f"  - source: {source}\n    follower: {follower}\n" for source, follower in pairs
    )
    (root / ".beadloom").mkdir(parents=True, exist_ok=True)
    (root / ".beadloom" / "config.yml").write_text(body, encoding="utf-8")


# ---------------------------------------------------------------------------
# The block reader
# ---------------------------------------------------------------------------


class TestReadBlocks:
    def test_a_heading_carries_its_level(self) -> None:
        blocks = read_blocks("# One\n\n### Three\n")
        assert [(b.kind, b.level, b.line) for b in blocks] == [
            (HEADING, 1, 1),
            (HEADING, 3, 3),
        ]

    def test_consecutive_lines_are_one_paragraph(self) -> None:
        blocks = read_blocks("alpha\nbeta\n\ngamma\n")
        assert [b.kind for b in blocks] == [PARAGRAPH, PARAGRAPH]
        assert [b.line for b in blocks] == [1, 4]

    def test_a_fenced_block_is_code_and_its_body_is_not_read(self) -> None:
        blocks = read_blocks("```\n# not a heading\n- not a list\n```\n")
        assert [b.kind for b in blocks] == [CODE]
        assert blocks[0].rows == 2

    def test_an_unclosed_fence_is_still_one_code_block(self) -> None:
        blocks = read_blocks("```\nleft open\n")
        assert [b.kind for b in blocks] == [CODE]

    def test_a_list_counts_its_items(self) -> None:
        blocks = read_blocks("- one\n- two\n  - nested\n")
        assert [b.kind for b in blocks] == [LIST]
        assert blocks[0].rows == 3

    def test_an_ordered_list_is_a_list(self) -> None:
        blocks = read_blocks("1. one\n2. two\n")
        assert [(b.kind, b.rows) for b in blocks] == [(LIST, 2)]

    def test_a_table_counts_its_data_rows_without_the_alignment_row(self) -> None:
        blocks = read_blocks("| a | b |\n|---|---|\n| 1 | 2 |\n| 3 | 4 |\n")
        assert [(b.kind, b.rows) for b in blocks] == [(TABLE, 3)]

    def test_two_tables_separated_by_prose_are_two_blocks(self) -> None:
        text = "| a |\n|---|\n| 1 |\n\nbetween\n\n| b |\n|---|\n| 2 |\n"
        assert [b.kind for b in read_blocks(text)] == [TABLE, PARAGRAPH, TABLE]

    def test_a_thematic_break_reads_as_a_paragraph_block(self) -> None:
        # Folded deliberately: the check reports five kinds, and a break is a
        # one-line block whose presence is still compared.
        assert [b.kind for b in read_blocks("---\n")] == [PARAGRAPH]


# ---------------------------------------------------------------------------
# The comparison
# ---------------------------------------------------------------------------


class TestCompareDocuments:
    def test_two_files_with_the_same_shape_report_nothing(self) -> None:
        # The pair standing in two scripts is the point of the check; ruff flags the Cyrillic.
        source = "# Заголовок\n\nАбзац.\n\n- один\n- два\n"  # noqa: RUF001
        follower = "# Title\n\nA paragraph.\n\n- one\n- two\n"
        result = compare_documents(read_blocks(source), read_blocks(follower))
        assert result.findings == ()
        assert result.compared == 3

    def test_a_paragraph_only_the_source_has_is_reported_under_its_heading(self) -> None:
        # The finding names where the two sequences DIVERGE and the heading it
        # sits under. It cannot name which of three identical-shaped paragraphs
        # went missing, and claiming otherwise would be a precision the
        # comparison does not have.
        source = "# Title\n\nfirst\n\nsecond\n\nthird\n"
        follower = "# Title\n\nfirst\n\nthird\n"
        result = compare_documents(read_blocks(source), read_blocks(follower))
        assert [
            (f.check, f.kind, f.source_line, f.follower_line, f.section)
            for f in result.findings
        ] == [(UNPAIRED_BLOCK, PARAGRAPH, 7, None, "Title")]

    def test_a_paragraph_only_the_follower_has_is_reported_with_its_line(self) -> None:
        source = "# Title\n\nfirst\n"
        follower = "# Title\n\nfirst\n\nextra\n"
        result = compare_documents(read_blocks(source), read_blocks(follower))
        assert [(f.check, f.source_line, f.follower_line) for f in result.findings] == [
            (UNPAIRED_BLOCK, None, 5)
        ]

    def test_a_heading_whose_level_changed_is_reported_as_a_kind_mismatch(self) -> None:
        result = compare_documents(read_blocks("## T\n"), read_blocks("### T\n"))
        assert [f.check for f in result.findings] == [BLOCK_KIND]

    def test_a_list_that_lost_a_row_is_reported_against_both_files(self) -> None:
        result = compare_documents(read_blocks("- a\n- b\n- c\n"), read_blocks("- a\n- b\n"))
        finding = result.findings[0]
        assert finding.check == ROW_COUNT
        assert finding.source_line == 1
        assert finding.follower_line == 1
        assert "3" in finding.detail and "2" in finding.detail

    def test_a_paragraph_wrapped_differently_is_not_a_finding(self) -> None:
        source = read_blocks("одна строка\n")
        follower = read_blocks("a line that the translator\nwrapped over two\n")
        assert compare_documents(source, follower).findings == ()

    def test_the_compared_count_is_the_number_of_aligned_pairs(self) -> None:
        result = compare_documents(read_blocks("# T\n\na\n\nb\n"), read_blocks("# T\n\na\n"))
        assert result.compared == 2
        assert result.source_blocks == 3
        assert result.follower_blocks == 2


# ---------------------------------------------------------------------------
# The declaration
# ---------------------------------------------------------------------------


class TestDeclaration:
    def test_a_project_with_no_config_declares_no_pair(self, tmp_path: Path) -> None:
        assert read_pair_declaration(tmp_path).pairs == ()

    def test_a_project_declaring_no_block_declares_no_pair(self, tmp_path: Path) -> None:
        (tmp_path / ".beadloom").mkdir()
        (tmp_path / ".beadloom" / "config.yml").write_text("languages:\n- .py\n", encoding="utf-8")
        assert read_pair_declaration(tmp_path).pairs == ()

    def test_a_declared_pair_resolves_against_the_project_root(self, tmp_path: Path) -> None:
        _declare(tmp_path, ("README.ru.md", "README.md"))
        pairs = read_pair_declaration(tmp_path).pairs
        assert [(p.source, p.follower) for p in pairs] == [
            (tmp_path / "README.ru.md", tmp_path / "README.md")
        ]

    def test_a_half_written_declaration_is_refused(self, tmp_path: Path) -> None:
        (tmp_path / ".beadloom").mkdir()
        (tmp_path / ".beadloom" / "config.yml").write_text(
            "document_pairs:\n  - source: README.ru.md\n", encoding="utf-8"
        )
        assert read_pair_declaration(tmp_path).pairs == ()

    def test_a_path_escaping_the_project_root_is_refused(self, tmp_path: Path) -> None:
        _declare(tmp_path, ("../outside.md", "README.md"))
        assert read_pair_declaration(tmp_path).pairs == ()

    def test_unreadable_config_declares_no_pair(self, tmp_path: Path) -> None:
        (tmp_path / ".beadloom").mkdir()
        (tmp_path / ".beadloom" / "config.yml").write_text("document_pairs: [\n", encoding="utf-8")
        assert read_pair_declaration(tmp_path).pairs == ()


class TestCheckDocumentPairs:
    def test_a_project_that_declares_nothing_is_not_judged(self, tmp_path: Path) -> None:
        report = check_document_pairs(tmp_path)
        assert not report.declared
        assert report.findings == ()
        assert report.compared == 0

    def test_a_missing_file_is_reported_as_unreadable_and_not_compared(
        self, tmp_path: Path
    ) -> None:
        (tmp_path / "SOURCE.md").write_text("# T\n", encoding="utf-8")
        _declare(tmp_path, ("SOURCE.md", "GONE.md"))
        report = check_document_pairs(tmp_path)
        assert report.declared
        assert report.comparisons[0].unreadable == ("GONE.md",)
        assert report.comparisons[0].findings == ()

    def test_the_report_sums_the_blocks_every_pair_compared(self, tmp_path: Path) -> None:
        (tmp_path / "A.md").write_text("# T\n\na\n", encoding="utf-8")
        (tmp_path / "B.md").write_text("# T\n\nb\n", encoding="utf-8")
        (tmp_path / "C.md").write_text("# T\n\nc\n", encoding="utf-8")
        _declare(tmp_path, ("A.md", "B.md"), ("A.md", "C.md"))
        report = check_document_pairs(tmp_path)
        assert report.compared == 4
        assert len(report.comparisons) == 2


# ---------------------------------------------------------------------------
# The reproduction
# ---------------------------------------------------------------------------


class TestTheReadmePairOf20260910:
    """The red case: the files as they stood before commit 97fafca5."""

    @pytest.fixture()
    def report(self, tmp_path: Path) -> PairReport:
        shutil.copy(FIXTURE_PAIR / "README.ru.md", tmp_path / "README.ru.md")
        shutil.copy(FIXTURE_PAIR / "README.md", tmp_path / "README.md")
        _declare(tmp_path, ("README.ru.md", "README.md"))
        return check_document_pairs(tmp_path)

    def test_the_only_number_that_differed_that_day_was_a_line_count(self) -> None:
        english = (FIXTURE_PAIR / "README.md").read_text(encoding="utf-8").splitlines()
        russian = (FIXTURE_PAIR / "README.ru.md").read_text(encoding="utf-8").splitlines()
        assert (len(russian), len(english)) == (362, 360)

    def test_the_comparison_finds_the_paragraph_the_english_file_lacked(
        self, report: PairReport
    ) -> None:
        findings = report.findings
        unpaired = [
            f for f in findings if f.check == UNPAIRED_BLOCK and f.source_line is not None
        ]
        assert unpaired, f"the 2026-09-10 divergence went unreported: {findings}"
        assert [f.kind for f in unpaired] == [PARAGRAPH]
        assert unpaired[0].section.startswith("«Проверка прошла»")

    def test_the_comparison_reports_the_population_it_read(self, report: PairReport) -> None:
        comparison = report.comparisons[0]
        assert comparison.source_blocks == 109
        assert comparison.follower_blocks == 108
        assert comparison.compared == 108
