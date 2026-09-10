"""Step implementations for BDL-069 S4 — the declared document pair.

Thin by design: every step writes real markdown to a real project root and calls
the real comparison. The reproduction step spends the two READMEs as they stood
on 2026-09-10, kept in ``tests/fixtures/readme_pair_2026_09_10/`` — a check whose
red case is a hand-written approximation of the defect proves the approximation.
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest
from pytest_bdd import given, scenarios, then, when

from beadloom.doc_sync.document_pairs import UNPAIRED_BLOCK, check_document_pairs

if TYPE_CHECKING:
    from beadloom.doc_sync.document_pairs import PairReport

scenarios("../features/document_pairs.feature")

#: The pair as it stood on 2026-09-10 at commit 31f8c9cb, the parent of the
#: commit that brought the English file back into line with the Russian one.
#:
#: It lives INSIDE ``tests/acceptance/`` because the suite is copied out of the
#: repository and run on its own by the sabotage test in
#: ``tests/test_bead14_s4_binding.py``. A step reaching for a path above the
#: suite fails in that copy for a reason that is not the sabotage, which is
#: exactly the collateral that test refuses.
FIXTURE_PAIR = Path(__file__).resolve().parents[1] / "fixtures" / "readme_pair_2026_09_10"


@pytest.fixture()
def world() -> dict[str, Any]:
    """The one mutable bag the steps share, kept explicit rather than global."""
    return {}


def _declare(root: Path, source: str, follower: str) -> None:
    """Write the ``document_pairs:`` block that opts the project in."""
    (root / ".beadloom").mkdir(parents=True, exist_ok=True)
    (root / ".beadloom" / "config.yml").write_text(
        f"document_pairs:\n  - source: {source}\n    follower: {follower}\n",
        encoding="utf-8",
    )


@given("a declared pair whose follower is missing a paragraph the source has")
def _pair_missing_paragraph(tmp_path: Path, world: dict[str, Any]) -> None:
    (tmp_path / "SOURCE.md").write_text(
        "# Title\n\nFirst paragraph.\n\nSecond paragraph.\n\nThird paragraph.\n",
        encoding="utf-8",
    )
    (tmp_path / "FOLLOWER.md").write_text(
        "# Title\n\nFirst paragraph.\n\nThird paragraph.\n",
        encoding="utf-8",
    )
    _declare(tmp_path, "SOURCE.md", "FOLLOWER.md")
    world["root"] = tmp_path


@given("the README pair as it stood on 2026-09-10")
def _readme_pair_of_the_day(tmp_path: Path, world: dict[str, Any]) -> None:
    shutil.copy(FIXTURE_PAIR / "README.ru.md", tmp_path / "README.ru.md")
    shutil.copy(FIXTURE_PAIR / "README.md", tmp_path / "README.md")
    _declare(tmp_path, "README.ru.md", "README.md")
    world["root"] = tmp_path


@given("a declared pair whose two files carry the same blocks in the same order")
def _pair_that_corresponds(tmp_path: Path, world: dict[str, Any]) -> None:
    (tmp_path / "SOURCE.md").write_text(
        # The pair standing in two scripts is the point of the check; ruff flags the Cyrillic.
        "# Заголовок\n\nАбзац.\n\n- один\n- два\n\n```\nout\n```\n",  # noqa: RUF001
        encoding="utf-8",
    )
    (tmp_path / "FOLLOWER.md").write_text(
        "# Title\n\nA paragraph, wrapped\nover two lines.\n\n- one\n- two\n\n```\nout\n```\n",
        encoding="utf-8",
    )
    _declare(tmp_path, "SOURCE.md", "FOLLOWER.md")
    world["root"] = tmp_path


@given("a declared pair whose follower's list carries one row fewer")
def _pair_with_a_shorter_list(tmp_path: Path, world: dict[str, Any]) -> None:
    (tmp_path / "SOURCE.md").write_text(
        "# Заголовок\n\n- один\n- два\n- три\n",
        encoding="utf-8",
    )
    (tmp_path / "FOLLOWER.md").write_text(
        "# Title\n\n- one\n- two\n",
        encoding="utf-8",
    )
    _declare(tmp_path, "SOURCE.md", "FOLLOWER.md")
    world["root"] = tmp_path


@given("a project that declares no document pair")
def _project_without_a_pair(tmp_path: Path, world: dict[str, Any]) -> None:
    (tmp_path / ".beadloom").mkdir(parents=True, exist_ok=True)
    (tmp_path / ".beadloom" / "config.yml").write_text("languages:\n- .py\n", encoding="utf-8")
    world["root"] = tmp_path


@when("the document pairs are compared")
def _compare(world: dict[str, Any]) -> None:
    world["report"] = check_document_pairs(world["root"])


def _report(world: dict[str, Any]) -> PairReport:
    report: PairReport = world["report"]
    return report


@then("the missing paragraph is reported against the heading it stands under")
def _missing_paragraph_named(world: dict[str, Any]) -> None:
    report = _report(world)
    unpaired = [f for f in report.findings if f.check == UNPAIRED_BLOCK]
    assert unpaired, f"no unpaired block reported: {report.findings}"
    assert [(f.kind, f.section, f.follower_line) for f in unpaired] == [
        ("paragraph", "Title", None)
    ], f"the source-only paragraph is not named under its heading: {unpaired}"


@then("the comparison reports how many blocks it compared")
def _population_named(world: dict[str, Any]) -> None:
    report = _report(world)
    assert report.compared > 0
    for comparison in report.comparisons:
        assert comparison.compared <= min(comparison.source_blocks, comparison.follower_blocks)


@then("a block present in the Russian file and absent in the English one is reported")
def _russian_only_block(world: dict[str, Any]) -> None:
    report = _report(world)
    unpaired = [
        f for f in report.findings if f.check == UNPAIRED_BLOCK and f.source_line is not None
    ]
    assert unpaired, f"the 2026-09-10 divergence was not found: {report.findings}"


@then("the row count difference is reported against both files")
def _row_count_reported(world: dict[str, Any]) -> None:
    report = _report(world)
    rows = [f for f in report.findings if f.check == "row-count"]
    assert rows, f"no row-count finding: {report.findings}"
    assert rows[0].source_line is not None
    assert rows[0].follower_line is not None


@then("no finding is reported")
def _no_finding(world: dict[str, Any]) -> None:
    report = _report(world)
    assert report.findings == (), f"unexpected findings: {report.findings}"


@then("the comparison reports that no pair is declared")
def _no_pair_declared(world: dict[str, Any]) -> None:
    report = _report(world)
    assert not report.declared
