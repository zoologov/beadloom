"""Every surface that reports a lint result states the population it was taken over.

BDL-070 A4 (`beadloom-q6jh`). A3 put the population on `LintResult` and into the
four renderings `beadloom lint` itself produces. Five other surfaces report a
lint result, and **two of them never see a `LintResult` at all**:
`tui/data_providers.py` and `application/debt_report/collect.py` call
`evaluate_all` directly, which is why A2 emitted the population as a FINDING
rather than as a clause in the summary line. This module holds all five.

**Nothing here changes a count.** Whether an advisory statement counts as a
violation is one question with one answer, and it belongs in one place —
`LintResult`'s counting properties — not in five leaves. A4 is additive at every
surface, so every number these surfaces printed before it, they print after it.

**One phrase, one place.** `population_phrase` is the single wording; the Gate
line, the GitHub notice, `prime`'s health line and the debt report all call it.
Five surfaces phrasing one fact five ways is the defect this epic is about, in
miniature, so it is asserted rather than reviewed.

**What this module cannot see.** The caller-set derivation follows `import` and
`from ... import` by name (including `as`), so a module that reaches
`evaluate_all` through `importlib` or an attribute chain is outside it. It is a
guard, not a proof, and the limit is stated in the case that depends on it.
"""

from __future__ import annotations

import ast
import inspect
import re
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

import beadloom
from beadloom.application.debt_report.collect import collect_debt_data
from beadloom.application.debt_report.render import format_debt_json, format_debt_report
from beadloom.application.debt_report.scoring import compute_debt_score
from beadloom.application.gate import lint_step
from beadloom.application.reindex import incremental_reindex
from beadloom.graph.linter import format_github, lint
from beadloom.graph.rules.layer_reach import (
    LAYER_POPULATION_RULE_TYPE,
    layer_rule_reaches,
    population_phrase,
    stated_populations,
)
from beadloom.infrastructure.db import connection
from beadloom.onboarding.scanner.prime import prime_context
from beadloom.services.mcp_server import handle_lint
from beadloom.tui.data_providers import LintDataProvider
from beadloom.tui.widgets.lint_panel import LintPanelWidget

if TYPE_CHECKING:
    from collections.abc import Iterator

# ---------------------------------------------------------------------------
# The fixture: a graph small enough that the numbers can be read
# ---------------------------------------------------------------------------

_LAYER_RULE = (
    "  - name: architecture-layers\n"
    '    description: "Services -> domains, not the reverse"\n'
    "    severity: error\n"
    "    layers:\n"
    "      - name: services\n"
    "        tag: layer-service\n"
    "      - name: domains\n"
    "        tag: layer-domain\n"
    "    enforce: top-down\n"
    "    allow_skip: true\n"
    "    edge_kind: depends_on\n"
)

#: What the rule judged on the fixture below, spelled once. `svc -> dom` carries
#: a declared tag at both ends; `widget -> helper` carries none, so the rule
#: passes over it. 1 of 2 is the whole point of this epic at a size a reader can
#: hold.
THE_PHRASE = "architecture-layers judged 1 of 2 live depends_on edge(s)"


@pytest.fixture()
def partly_layered_project(tmp_path: Path) -> Path:
    """A project whose layer rule reaches half the edges it is handed.

    ``rules.yml`` is written TWICE, and the duplicate is a defect this bead
    found rather than a convenience. Every reader in the product resolves
    ``.beadloom/_graph/rules.yml``; ``debt_report/collect.py`` resolves
    ``<root>/rules.yml`` and then ``<root>/.beadloom/rules.yml``, neither of
    which exists in a standard layout, so its rule-violation counts are zero on
    every project — measured on this repository: 0 errors and 0 warnings against
    the 0 errors and 71 warnings ``lint --strict`` reports over the same index. The
    second copy is what makes the debt surface reachable at all in this module.
    :class:`TestTheDebtReportReadsRulesFromAPlaceNobodyWritesThem` holds the
    defect so it fails loudly when it is fixed.
    """
    graph_dir = tmp_path / ".beadloom" / "_graph"
    graph_dir.mkdir(parents=True)
    (graph_dir / "services.yml").write_text(
        "nodes:\n"
        "  - ref_id: svc\n    kind: service\n    summary: A service\n"
        "    tags: [layer-service]\n"
        "  - ref_id: dom\n    kind: domain\n    summary: A domain\n"
        "    tags: [layer-domain]\n"
        "  - ref_id: widget\n    kind: feature\n    summary: An untagged feature\n"
        "  - ref_id: helper\n    kind: feature\n    summary: Another untagged feature\n"
        "edges:\n"
        "  - src: svc\n    dst: dom\n    kind: depends_on\n"
        "  - src: widget\n    dst: helper\n    kind: depends_on\n"
    )
    rules = f"version: 1\nrules:\n{_LAYER_RULE}"
    (graph_dir / "rules.yml").write_text(rules)
    (tmp_path / "rules.yml").write_text(rules)
    (tmp_path / "docs").mkdir()
    incremental_reindex(tmp_path)
    return tmp_path


@pytest.fixture()
def unlayered_project(tmp_path: Path) -> Path:
    """A project that declares no layer rule — every surface stays silent."""
    graph_dir = tmp_path / ".beadloom" / "_graph"
    graph_dir.mkdir(parents=True)
    (graph_dir / "services.yml").write_text(
        "nodes:\n"
        "  - ref_id: billing\n    kind: domain\n    summary: Billing\n"
        "  - ref_id: auth\n    kind: domain\n    summary: Auth\n"
        "edges: []\n"
    )
    rules = (
        "version: 1\n"
        "rules:\n"
        "  - name: billing-no-auth\n"
        '    description: "Billing must not import auth"\n'
        "    deny:\n"
        "      from: { ref_id: billing }\n"
        "      to: { ref_id: auth }\n"
    )
    (graph_dir / "rules.yml").write_text(rules)
    (tmp_path / "rules.yml").write_text(rules)
    (tmp_path / "docs").mkdir()
    incremental_reindex(tmp_path)
    return tmp_path


# ---------------------------------------------------------------------------
# One phrasing, shared
# ---------------------------------------------------------------------------


class TestOnePhrasingServesEverySurface:
    """The wording lives once, so five surfaces cannot drift into five wordings."""

    def test_the_phrase_names_the_rule_the_fraction_and_the_edge_kind(
        self, partly_layered_project: Path
    ) -> None:
        with connection(partly_layered_project / ".beadloom" / "beadloom.db") as conn:
            from beadloom.graph.rules import LayerRule, load_rules

            rules = load_rules(partly_layered_project / ".beadloom" / "_graph" / "rules.yml")
            reaches = layer_rule_reaches(
                conn, [r for r in rules if isinstance(r, LayerRule)]
            )

        assert [population_phrase(reach) for reach in reaches] == [THE_PHRASE]

    def test_a_rule_handed_no_edge_of_its_kind_is_not_stated(
        self, unlayered_project: Path
    ) -> None:
        """No denominator, nothing to say — and liveness already says the rest."""
        assert stated_populations(lint(unlayered_project).layer_populations) == []

    def test_the_github_notice_carries_the_shared_phrase(
        self, partly_layered_project: Path
    ) -> None:
        """A3's rendering is now the shared phrase rather than its own copy."""
        assert f"::notice::{THE_PHRASE}" in format_github(lint(partly_layered_project))


# ---------------------------------------------------------------------------
# Surface 1 — the Gate
# ---------------------------------------------------------------------------


class TestTheGateLineStatesThePopulation:
    """`beadloom ci`'s lint step is the line a push is judged by."""

    def test_the_summary_carries_the_phrase(self, partly_layered_project: Path) -> None:
        assert THE_PHRASE in lint_step(partly_layered_project).summary

    def test_a_project_with_no_layer_rule_gets_no_clause(
        self, unlayered_project: Path
    ) -> None:
        assert "judged" not in lint_step(unlayered_project).summary

    def test_the_verdict_is_unchanged(self, partly_layered_project: Path) -> None:
        """The clause qualifies the line; it decides nothing on it."""
        step = lint_step(partly_layered_project)
        assert step.passed is True


# ---------------------------------------------------------------------------
# Surface 2 — the MCP lint tool
# ---------------------------------------------------------------------------

#: The summary keys `handle_lint` carried before this bead, named one by one.
#: "Additive only" is a promise to a consumer that reads a key by name, and a
#: length check keeps passing while a rename breaks it.
_MCP_SUMMARY_KEYS_BEFORE_A4 = frozenset({"errors", "warnings", "rules_evaluated"})


class TestTheMcpLintToolStatesThePopulation:
    """An agent reading the tool's JSON gets the denominator with the counts."""

    def test_the_summary_carries_one_entry_per_layer_rule(
        self, partly_layered_project: Path
    ) -> None:
        summary = handle_lint(partly_layered_project)["summary"]

        assert [entry["rule"] for entry in summary["layer_populations"]] == [
            "architecture-layers"
        ]
        entry = summary["layer_populations"][0]
        assert (entry["evaluated"], entry["total"]) == (1, 2)
        assert entry["edge_kind"] == "depends_on"

    def test_the_keys_that_were_there_are_still_there(
        self, partly_layered_project: Path
    ) -> None:
        summary = handle_lint(partly_layered_project)["summary"]
        assert set(summary) >= _MCP_SUMMARY_KEYS_BEFORE_A4

    def test_a_severity_filter_does_not_filter_the_population(
        self, partly_layered_project: Path
    ) -> None:
        """The population is not a finding, so a finding filter cannot hide it."""
        summary = handle_lint(partly_layered_project, severity="error")["summary"]
        assert len(summary["layer_populations"]) == 1

    def test_a_project_with_no_layer_rule_carries_an_empty_list(
        self, unlayered_project: Path
    ) -> None:
        assert handle_lint(unlayered_project)["summary"]["layer_populations"] == []


# ---------------------------------------------------------------------------
# Surface 3 — the TUI lint panel (past `lint()`)
# ---------------------------------------------------------------------------


@contextmanager
def _provider(project_root: Path) -> Iterator[LintDataProvider]:
    """The TUI's lint provider over the fixture's index."""
    with connection(project_root / ".beadloom" / "beadloom.db") as conn:
        yield LintDataProvider(conn=conn, project_root=project_root)


class TestTheTuiPanelStatesThePopulation:
    """The panel never sees a `LintResult`; it takes the population from the finding."""

    def test_the_provider_carries_the_rule_type_and_the_message(
        self, partly_layered_project: Path
    ) -> None:
        """Both were dropped: the numbers live in the message and nowhere else."""
        with _provider(partly_layered_project) as provider:
            rows = provider.get_violations()

        population = [r for r in rows if r["rule_type"] == LAYER_POPULATION_RULE_TYPE]
        assert len(population) == 1
        assert "1 of 2" in (population[0]["message"] or "")

    def test_the_panel_renders_the_numbers(self, partly_layered_project: Path) -> None:
        with _provider(partly_layered_project) as provider:
            rows = provider.get_violations()
        panel = LintPanelWidget(violations=rows)

        rendered = panel.render().plain
        assert "1 of 2" in rendered

    def test_the_population_leads_the_list(self, partly_layered_project: Path) -> None:
        """The reach of a check is what the findings under it are true of."""
        with _provider(partly_layered_project) as provider:
            rows = provider.get_violations()
        panel = LintPanelWidget(violations=rows)

        body = panel.render().plain.splitlines()[1:]
        assert "1 of 2" in body[0]

    def test_the_count_is_unchanged(self, partly_layered_project: Path) -> None:
        """A4 states; it does not re-count. The open item is recorded on A7."""
        with _provider(partly_layered_project) as provider:
            assert provider.get_violation_count() == len(provider.get_violations())

    def test_a_panel_with_no_population_renders_as_before(self) -> None:
        panel = LintPanelWidget(
            violations=[
                {
                    "rule_name": "billing-no-auth",
                    "severity": "error",
                    "from_ref_id": "billing",
                    "to_ref_id": "auth",
                    "description": "Billing must not import auth",
                    "rule_type": "deny",
                    "message": "billing depends on auth",
                }
            ]
        )
        rendered = panel.render().plain
        assert "billing-no-auth" in rendered
        assert "judged" not in rendered


# ---------------------------------------------------------------------------
# Surface 4 — the debt report (past `lint()`)
# ---------------------------------------------------------------------------


#: Rich colours numbers by default, so `1 of 2` arrives in the debt report's
#: terminal output with escape sequences between its characters. The assertions
#: below are about the words, not about the colouring.
_ANSI = re.compile(r"\x1b\[[0-9;]*m")


def _plain(rendered: str) -> str:
    return _ANSI.sub("", rendered)


class TestTheDebtReportStatesThePopulation:
    """The score is a count; the population is what it was counted over."""

    def test_the_collected_data_carries_the_phrase(
        self, partly_layered_project: Path
    ) -> None:
        with connection(partly_layered_project / ".beadloom" / "beadloom.db") as conn:
            data = collect_debt_data(conn, partly_layered_project)
        assert data.layer_populations == [THE_PHRASE]

    def test_the_report_carries_it_through_scoring(
        self, partly_layered_project: Path
    ) -> None:
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

    def test_a_project_with_no_layer_rule_prints_nothing(
        self, unlayered_project: Path
    ) -> None:
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
        (graph_dir / "rules.yml").write_text(f"version: 1\nrules:\n{_LAYER_RULE}")
        (tmp_path / "docs").mkdir()
        incremental_reindex(tmp_path)

        with connection(tmp_path / ".beadloom" / "beadloom.db") as conn:
            data = collect_debt_data(conn, tmp_path)

        assert data.layer_populations == []
        assert (data.error_count, data.warning_count) == (0, 0)


# ---------------------------------------------------------------------------
# Surface 5 — `prime`
# ---------------------------------------------------------------------------


class TestPrimeStatesThePopulation:
    """The context an agent is primed with states what its health line covers."""

    def test_the_health_line_carries_the_phrase(
        self, partly_layered_project: Path
    ) -> None:
        text = prime_context(partly_layered_project)
        assert isinstance(text, str)
        health = next(line for line in text.splitlines() if line.startswith("Health:"))
        assert THE_PHRASE in health

    def test_the_json_form_carries_it(self, partly_layered_project: Path) -> None:
        payload = prime_context(partly_layered_project, fmt="json")
        assert isinstance(payload, dict)
        assert payload["health"]["layer_populations"] == [THE_PHRASE]

    def test_a_project_with_no_layer_rule_gets_no_clause(
        self, unlayered_project: Path
    ) -> None:
        text = prime_context(unlayered_project)
        assert isinstance(text, str)
        assert "judged" not in text

    def test_the_clause_is_per_rule_not_per_finding(
        self, partly_layered_project: Path
    ) -> None:
        """The budget survives because the clause does not grow with the graph.

        ``prime``'s list is capped at ten findings; the population is one line
        per DECLARED layer rule, so a repository with a thousand findings adds
        the same one clause a repository with none does.
        """
        text = prime_context(partly_layered_project)
        assert isinstance(text, str)
        assert text.count("judged") == 1
        assert len(text.encode("utf-8")) < 8000


# ---------------------------------------------------------------------------
# The caller set
# ---------------------------------------------------------------------------

#: The name the evaluator is called by. Read off the function object so a rename
#: fails at import here rather than leaving a scan that finds no call site and
#: reports every claim below as satisfied.
THE_EVALUATOR = "evaluate_all"

#: The modules `evaluate_all` can be imported from: the one it is defined in and
#: the two that re-export it. Every caller in the product names one of them.
THE_EVALUATOR_MODULES = frozenset(
    {"beadloom.graph.rules", "beadloom.graph.rule_engine", "beadloom.graph"}
)

#: Every function in `src/` that calls the evaluator, mapped to the name in its
#: own module that carries the population onward. Compared for EQUALITY, so a
#: FOURTH call site fails here and is asked the question this bead exists to
#: ask: what does this surface tell its reader about how much of the graph its
#: answer covers?
#:
#: `linter._evaluate` and `debt_report._count_violations` count the reaches
#: themselves, from the same `reach_of` the evaluator uses, so they name the
#: counter. `tui.data_providers.refresh` does neither: it hands the finding on
#: whole, and the population travels as a FIELD of it, so the name is the field.
#: That token is weak evidence on its own, which is why it is evidence and not
#: the check — `TestTheTuiPanelStatesThePopulation` is what holds the behaviour.
THE_CALLERS: dict[str, str] = {
    "beadloom/graph/linter.py::_evaluate": "layer_rule_reaches",
    "beadloom/tui/data_providers.py::refresh": "rule_type",
    "beadloom/application/debt_report/collect.py::_count_violations": (
        "layer_rule_reaches"
    ),
}


def _package_root() -> Path:
    return Path(inspect.getfile(beadloom)).parent


def _evaluator_names_in(tree: ast.Module) -> set[str]:
    """The local names bound to the evaluator in this file, `as` included."""
    return {
        alias.asname or alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module in THE_EVALUATOR_MODULES
        for alias in node.names
        if alias.name == THE_EVALUATOR
    }


def _callers_in(path: Path, relative: str) -> dict[str, str]:
    """`module::function` for every function in *path* that calls the evaluator."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    names = _evaluator_names_in(tree)
    if not names:
        return {}
    source = path.read_text(encoding="utf-8")
    found: dict[str, str] = {}
    for function in ast.walk(tree):
        if not isinstance(function, ast.FunctionDef | ast.AsyncFunctionDef):
            continue
        calls = any(
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id in names
            for node in ast.walk(function)
        )
        if calls:
            found[f"{relative}::{function.name}"] = source
    return found


def _derived_callers() -> dict[str, str]:
    root = _package_root()
    callers: dict[str, str] = {}
    for path in sorted(root.rglob("*.py")):
        relative = f"beadloom/{path.relative_to(root).as_posix()}"
        callers.update(_callers_in(path, relative))
    return callers


class TestEveryCallerOfTheEvaluatorIsNamed:
    """A new caller of `evaluate_all` is a new surface, and it fails here first."""

    def test_the_derived_set_is_the_named_set(self) -> None:
        assert set(_derived_callers()) == set(THE_CALLERS)

    def test_each_caller_names_what_carries_the_population(self) -> None:
        """Evidence, not proof: the module names the thing that carries the reach."""
        unhandled = [
            caller
            for caller, source in _derived_callers().items()
            if THE_CALLERS.get(caller, "\0") not in source
        ]
        assert unhandled == []

    def test_a_caller_reached_under_a_name_this_scan_cannot_see(self) -> None:
        """The stated ceiling: an attribute call binds no name this scan reads."""
        tree = ast.parse(
            "from beadloom.graph import rule_engine\n"
            "def surface(conn, rules):\n"
            "    return rule_engine.evaluate_all(conn, rules)\n"
        )
        assert _evaluator_names_in(tree) == set()
