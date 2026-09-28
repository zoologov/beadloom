"""The debt report states the population its rule counts were taken over.

`application/debt_report/collect.py` calls `evaluate_all` directly and never sees
a `LintResult`; the population reaches the report as data, through scoring, into
both renderings. One defect this surface carries is held here as well: it reads
`rules.yml` from a place nobody writes it.

Split out of ``tests/test_every_surface_past_lint_states_the_population.py``
by node (BDL-074 E1); the behaviour is BDL-070 A4's (`beadloom-q6jh`). A4 is
additive at every surface: nothing here changes a count, and whether an advisory
statement counts as a violation is decided once, on `LintResult`.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

import pytest

from beadloom.application.debt_report.collect import collect_debt_data
from beadloom.application.debt_report.render import format_debt_json, format_debt_report
from beadloom.application.debt_report.scoring import compute_debt_score
from beadloom.application.reindex import incremental_reindex
from beadloom.infrastructure.db import connection
from tests.support.layer_population_projects import (
    LAYER_RULE,
    THE_PHRASE,
    write_partly_layered_project,
    write_unlayered_project,
)

if TYPE_CHECKING:
    from pathlib import Path

#: Rich colours numbers by default, so `1 of 2` arrives in the debt report's
#: terminal output with escape sequences between its characters. The assertions
#: below are about the words, not about the colouring.
_ANSI = re.compile(r"\x1b\[[0-9;]*m")


def _plain(rendered: str) -> str:
    return _ANSI.sub("", rendered)


@pytest.fixture()
def partly_layered_project(tmp_path: Path) -> Path:
    """A project whose layer rule reaches half the edges it is handed."""
    return write_partly_layered_project(tmp_path)


@pytest.fixture()
def unlayered_project(tmp_path: Path) -> Path:
    """A project that declares no layer rule."""
    return write_unlayered_project(tmp_path)


class TestTheDebtReportStatesThePopulation:
    """The score is a count; the population is what it was counted over."""

    def test_the_collected_data_carries_the_phrase(self, partly_layered_project: Path) -> None:
        with connection(partly_layered_project / ".beadloom" / "beadloom.db") as conn:
            data = collect_debt_data(conn, partly_layered_project)
        assert data.layer_populations == [THE_PHRASE]

    def test_the_report_carries_it_through_scoring(self, partly_layered_project: Path) -> None:
        with connection(partly_layered_project / ".beadloom" / "beadloom.db") as conn:
            report = compute_debt_score(collect_debt_data(conn, partly_layered_project))
        assert report.layer_populations == [THE_PHRASE]

    def test_the_json_form_carries_it(self, partly_layered_project: Path) -> None:
        with connection(partly_layered_project / ".beadloom" / "beadloom.db") as conn:
            report = compute_debt_score(collect_debt_data(conn, partly_layered_project))
        assert format_debt_json(report)["layer_populations"] == [THE_PHRASE]

    def test_the_rich_report_prints_it(self, partly_layered_project: Path) -> None:
        with connection(partly_layered_project / ".beadloom" / "beadloom.db") as conn:
            report = compute_debt_score(collect_debt_data(conn, partly_layered_project))
        assert THE_PHRASE in _plain(format_debt_report(report))

    def test_a_project_with_no_layer_rule_prints_nothing(self, unlayered_project: Path) -> None:
        with connection(unlayered_project / ".beadloom" / "beadloom.db") as conn:
            report = compute_debt_score(collect_debt_data(conn, unlayered_project))
        assert report.layer_populations == []
        assert "judged" not in _plain(format_debt_report(report))

    def test_the_score_is_unchanged(self, partly_layered_project: Path) -> None:
        """The advisory is counted exactly as A2 left it counted."""
        with connection(partly_layered_project / ".beadloom" / "beadloom.db") as conn:
            data = collect_debt_data(conn, partly_layered_project)
        assert (data.error_count, data.warning_count) == (0, 1)


class TestTheDebtReportReadsRulesFromAPlaceNobodyWritesThem:
    """A defect this bead found, held so that fixing it fails here first.

    ``collect.py`` resolves ``<root>/rules.yml`` and then
    ``<root>/.beadloom/rules.yml``. The canonical location — the one ``lint``,
    the TUI, the MCP server, ``reindex`` and ``prime`` all use — is
    ``<root>/.beadloom/_graph/rules.yml``. A project with the standard layout
    therefore scores zero rule violations however many it has. Measured on this
    repository: 0 errors and 0 warnings against the 0 errors and 71 warnings
    ``lint --strict`` reports over the same index.

    Not fixed here: the one-line repair moves this repository's raw
    rule-violations score from 0 to 71 points at the default ``rule_warning``
    weight, and Release A's constraint is that no number moves on upgrade. When
    it is fixed, this case fails and names the bead that fixed it.
    """

    def test_the_canonical_location_alone_is_not_read(self, tmp_path: Path) -> None:
        graph_dir = tmp_path / ".beadloom" / "_graph"
        graph_dir.mkdir(parents=True)
        (graph_dir / "services.yml").write_text(
            "nodes:\n"
            "  - ref_id: svc\n    kind: service\n    summary: A service\n"
            "    tags: [layer-service]\n"
            "  - ref_id: dom\n    kind: domain\n    summary: A domain\n"
            "    tags: [layer-domain]\n"
            "  - ref_id: widget\n    kind: feature\n    summary: Untagged\n"
            "  - ref_id: helper\n    kind: feature\n    summary: Untagged\n"
            "edges:\n"
            "  - src: svc\n    dst: dom\n    kind: depends_on\n"
            "  - src: widget\n    dst: helper\n    kind: depends_on\n"
        )
        (graph_dir / "rules.yml").write_text(f"version: 1\nrules:\n{LAYER_RULE}")
        (tmp_path / "docs").mkdir()
        incremental_reindex(tmp_path)

        with connection(tmp_path / ".beadloom" / "beadloom.db") as conn:
            data = collect_debt_data(conn, tmp_path)

        assert data.layer_populations == []
        assert (data.error_count, data.warning_count) == (0, 0)
