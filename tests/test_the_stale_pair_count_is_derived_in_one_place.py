"""One computation answers "how many stale pairs", and it carries the noun.

BDL-069 `beadloom-rqma.5`. Three beads fixed this label surface by surface:
`beadloom-h7b3` changed one place and found three, `beadloom-yn6i` changed those
three and found four more. The cause is not the wording — it is that every call
site computes the number itself and is therefore free to name it itself. Nineteen
sites read `sync_state` and report a number, under FOUR different populations.

So the claim these tests hold is not "four more places were corrected" but "the
count is derived in one place, and the place that derives it says what it
counted". `StaleCount.of_pairs(n).phrase` is the one spelling of `N stale
pair(s)`, `count_stale_pairs` is the one query for it, and `stale_node_refs` is
a DIFFERENT function for the DIFFERENT population, so no caller can reach for
one and get the other.

The populations that are still in question — the `status` trend row, the debt
report, the doc-status screen — are NOT decided here. They are recorded on
`beadloom-r9t5`.
"""

from __future__ import annotations

import ast
import io
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from beadloom.application.graph_reads import (
    StaleCount,
    count_stale_pairs,
    stale_node_refs,
)
from beadloom.infrastructure.db import open_db
from tests import stale_pair_project as project

if TYPE_CHECKING:
    import sqlite3
    from collections.abc import Iterator

SRC = Path(__file__).resolve().parents[1] / "src" / "beadloom"


@pytest.fixture()
def two_stale_pairs_over_one_document(tmp_path: Path) -> Iterator[sqlite3.Connection]:
    """One document, two code files, both pairs stale — the shape of the defect.

    The staleness is produced by doing what an adopter does and read back through
    ``check_sync``, which is what writes the ``sync_state`` rows every surface
    under test then counts.
    """
    root = project.build(tmp_path / "adopter")
    project.add_an_unannotated_module(root)
    assert len(project.stale(root)) == 2
    conn = open_db(root / ".beadloom" / "beadloom.db")
    try:
        yield conn
    finally:
        conn.close()


class TestTheCountCarriesItsNoun:
    def test_a_pair_count_says_pairs(self) -> None:
        assert StaleCount.of_pairs(3).phrase == "3 stale pair(s)"

    def test_the_noun_is_available_on_its_own_for_a_label(self) -> None:
        """`why` writes `Stale pairs:`; the word comes from the count, not the site."""
        assert StaleCount.of_pairs(0).noun == "pair"

    def test_a_count_of_none_is_still_a_count_of_pairs(self) -> None:
        assert StaleCount.of_pairs(0).phrase == "0 stale pair(s)"


class TestTheTwoPopulationsAreTwoFunctions:
    def test_the_pair_count_counts_one_row_per_document_and_code_file(
        self, two_stale_pairs_over_one_document: sqlite3.Connection
    ) -> None:
        tally = count_stale_pairs(two_stale_pairs_over_one_document)
        assert (tally.count, tally.noun) == (2, "pair")

    def test_the_node_reader_returns_the_one_node_those_two_pairs_belong_to(
        self, two_stale_pairs_over_one_document: sqlite3.Connection
    ) -> None:
        assert stale_node_refs(two_stale_pairs_over_one_document) == ["widgets"]

    def test_a_named_node_narrows_the_pair_count(
        self, two_stale_pairs_over_one_document: sqlite3.Connection
    ) -> None:
        tally = count_stale_pairs(two_stale_pairs_over_one_document, ref_ids={"widgets"})
        assert tally.count == 2

    def test_no_node_named_counts_nothing_rather_than_everything(
        self, two_stale_pairs_over_one_document: sqlite3.Connection
    ) -> None:
        """`why` over a node with no dependents asks about an EMPTY set of refs."""
        assert count_stale_pairs(two_stale_pairs_over_one_document, ref_ids=set()).count == 0


def _phrase_sites() -> dict[str, list[int]]:
    """Every module under `src/` that spells `stale pair(s)` in a literal."""
    found: dict[str, list[int]] = {}
    for path in sorted(SRC.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        lines = [
            node.lineno
            for node in ast.walk(tree)
            if isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and "stale pair(s)" in node.value
        ]
        if lines:
            found[str(path.relative_to(SRC))] = lines
    return found


def _pair_count_query_sites() -> dict[str, list[int]]:
    """Every module under `src/` that counts the STALE rows with its own SQL.

    The population is the one `count_stale_pairs` owns — rows whose status is
    `stale` — so a query over `status IN ('stale', 'missing')` is a different
    population and is not one of these sites. `application/status.py` and
    `application/site.py` ask that wider question and are held on
    `beadloom-r9t5`, which is where the decision about it lives.
    """
    found: dict[str, list[int]] = {}
    for path in sorted(SRC.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        lines = [
            node.lineno
            for node in ast.walk(tree)
            if isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and "count(*) FROM sync_state" in node.value
            and "status = 'stale'" in node.value
        ]
        if lines:
            found[str(path.relative_to(SRC))] = lines
    return found


class TestNoSiteQueriesThePairCountItself:
    """The count has one query as well as one noun (BDL-069 review, Minor 2).

    `infrastructure/health.py` kept its own `SELECT count(*) FROM sync_state
    WHERE status = 'stale'` through `beadloom-rqma.5` — the identical population,
    in the same layer as the function that now owns it, with no boundary between
    them. A second copy of the query is what lets a second answer to "how many
    stale pairs" be born, which is the defect this bead's own name is about.

    The reads that are NOT this population are not in scope here and stay where
    they are: `context_oracle/builder.py` selects the stale ROWS of a subgraph,
    `onboarding/scanner/prime.py` selects their paths, and
    `application/debt_report/collect.py` counts NODES rather than pairs — that
    last one is a fourth copy of `stale_node_refs` and is recorded on
    `beadloom-r9t5`, where the decision about its population is already held.
    """

    def test_only_the_computation_carries_the_query(self) -> None:
        assert sorted(_pair_count_query_sites()) == ["infrastructure/repository.py"]


class TestNoSiteSpellsThePhraseItself:
    """The guard that makes a fifth site unable to be born mislabelled.

    A site that writes `N stale pair(s)` by hand is a site free to write
    `N stale doc(s)` instead, which is how this defect reached nineteen places.
    """

    def test_only_the_computation_and_the_one_site_it_cannot_reach_spell_it(
        self,
    ) -> None:
        assert sorted(_phrase_sites()) == [
            # The computation itself, and the only place the sentence is built.
            "infrastructure/repository.py",
            # `onboarding-no-direct-infra` forbids onboarding -> infrastructure,
            # and its exemption list names `infrastructure/db`, not
            # `infrastructure/repository`. Routing `prime` here needs a new
            # exemption for one sentence; the existing `db` entry already says
            # `prime_context()` should move to the repository seam whole
            # (BDL-UX #150). Until then this is the one copy, and it is stated.
            "onboarding/scanner/prime.py",
        ]


class TestTheSurfacesThatReportThatCount:
    """Every reachable surface renders the shared noun, not a word of its own.

    Each one was READ before it was changed: all four below count one
    ``sync_state`` row per document AND code file, so their population was
    already right and the noun was the whole defect.
    """

    def test_why_says_pairs_in_its_plain_impact_summary(
        self, two_stale_pairs_over_one_document: sqlite3.Connection
    ) -> None:
        from beadloom.context_oracle.why import analyze_node, render_why_tree

        text = render_why_tree(analyze_node(two_stale_pairs_over_one_document, "widgets"))
        assert "Stale pairs:" in text
        assert "Stale docs" not in text

    def test_why_says_pairs_in_its_rich_impact_summary(
        self, two_stale_pairs_over_one_document: sqlite3.Connection
    ) -> None:
        from rich.console import Console

        from beadloom.context_oracle.why import analyze_node, render_why

        console = Console(file=io.StringIO(), width=100, no_color=True)
        render_why(analyze_node(two_stale_pairs_over_one_document, "widgets"), console)
        rendered = console.file.getvalue()  # type: ignore[attr-defined]
        assert "Stale pairs:" in rendered
        assert "Stale docs" not in rendered

    def test_the_context_bundle_heading_names_the_pairs_listed_under_it(
        self, two_stale_pairs_over_one_document: sqlite3.Connection
    ) -> None:
        """`beadloom ctx` lists one entry per pair; `mcp.md` already says pairs."""
        from beadloom.context_oracle.builder import build_context
        from beadloom.services.commands.query import _format_markdown

        bundle = build_context(two_stale_pairs_over_one_document, ["widgets"])
        markdown = _format_markdown(bundle)
        assert "## Stale Pairs" in markdown
        assert "## Stale Docs" not in markdown

    def test_the_mcp_status_tool_counts_pairs_and_says_pairs(
        self, two_stale_pairs_over_one_document: sqlite3.Connection
    ) -> None:
        from beadloom.services.mcp_server import _TOOLS, handle_get_status

        assert handle_get_status(two_stale_pairs_over_one_document)["stale_count"] == 2
        description = next(t.description for t in _TOOLS if t.name == "get_status")
        assert "stale pair count" in description

    def test_the_sync_report_table_names_the_pairs_it_lists(self) -> None:
        """The authority every other surface restates: one row per pair."""
        from beadloom.services.commands.docsync import _build_sync_report

        report = _build_sync_report(
            [
                {"status": "stale", "ref_id": "widgets", "doc_path": d, "code_path": c}
                for d, c in (("widgets.md", "src/widgets/alpha.py"),
                             ("widgets.md", "src/widgets/beta.py"))
            ]
        )
        assert "### Stale Pairs" in report
        assert "### Stale Documents" not in report

    def test_the_dashboard_docs_card_names_what_it_counted(self) -> None:
        from beadloom.application.site_dashboard import _docs_card

        card = _docs_card({"stale": 2, "tracked_pairs": 5, "coverage_pct": 80.0})
        assert card["detail"] == "2 stale of 5 tracked pair(s)"


class TestTheTuiSurfaces:
    def test_the_status_bar_number_has_a_noun(self) -> None:
        """It printed `  2 stale` — a number with nothing saying what it counted."""
        pytest.importorskip("textual", reason="the terminal dashboard needs the `tui` extra")
        from beadloom.tui.widgets.status_bar import StatusBarWidget

        bar = StatusBarWidget()
        bar.refresh_data(node_count=1, edge_count=0, doc_count=1, stale_count=2)
        assert "2 stale pair(s)" in bar.render().plain

    def test_a_clean_status_bar_still_names_the_population(self) -> None:
        pytest.importorskip("textual", reason="the terminal dashboard needs the `tui` extra")
        from beadloom.tui.widgets.status_bar import StatusBarWidget

        assert "0 stale pair(s)" in StatusBarWidget().render().plain

    def test_the_dependency_path_label_moves_with_why(self) -> None:
        """It renders `why`'s number, so one number cannot carry two nouns."""
        pytest.importorskip("textual", reason="the terminal dashboard needs the `tui` extra")
        from beadloom.context_oracle.why import (
            ImpactSummary,
            NodeInfo,
            TreeNode,
            WhyResult,
        )
        from beadloom.tui.widgets.dependency_path import _render_dependency_tree

        class OneDependentWithTwoStalePairs:
            """The impact summary renders only when a dependent exists."""

            def analyze(self, ref_id: str, *, reverse: bool = False) -> WhyResult:
                return WhyResult(
                    node=NodeInfo(ref_id=ref_id, kind="domain", summary="widgets"),
                    upstream=(),
                    downstream=(
                        TreeNode(
                            ref_id="ledger",
                            kind="domain",
                            summary="ledger",
                            edge_kind="depends_on",
                        ),
                    ),
                    impact=ImpactSummary(
                        downstream_direct=1,
                        downstream_transitive=1,
                        doc_coverage=100.0,
                        stale=StaleCount.of_pairs(2),
                    ),
                )

        text = _render_dependency_tree("widgets", OneDependentWithTwoStalePairs()).plain
        assert "Stale pairs: " in text
        assert "Stale docs" not in text
