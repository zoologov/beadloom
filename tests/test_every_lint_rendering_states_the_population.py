"""Every rendering of a lint result states the population the layer rule judged.

BDL-070 A3 (`beadloom-2dgz`). A2 made the layer rule state its reach as a
FINDING, which is what the two readers that call the evaluators without
`lint()` receive. A finding is not what a person reads first, though: the line
they read is the summary, and `0 violations, 16 rules evaluated` says the same
words whether the rule judged 16 edges of 363 or all 363. This module holds the
other half — the same fact on `LintResult` itself, as data, and in each of the
four renderings that carry a result out of the process.

Three properties are held here, and the third is the one that is easy to lose:

- **Every rendering carries it.** `format_rich`, `format_json`,
  `format_github`, `format_porcelain`, and `beadloom lint`'s own clean line.
- **`format_json` is additive.** Its existing keys are asserted by name, so a
  consumer that reads the summary keeps reading it.
- **The GREEN line carries it too.** A population is not a consolation offered
  beside a failure: a clean result is exactly where a reader most needs to know
  how much of the graph the result covers. Held by a fixture whose layer rule
  reaches every edge it is handed — the rule emits no finding there (it has
  nothing it could not see), so the summary clause is the ONLY place the
  denominator is stated.

One thing this module does not assert is a verdict. Nothing here decides; the
renderings read a result they did not produce. That the DECISIONS are unchanged
is A2's property and A7's proof, and repeating it here would be a second copy
of a claim rather than a second check of it.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

from beadloom.application.reindex import incremental_reindex
from beadloom.graph.linter import (
    POPULATION_MARKER,
    LintResult,
    format_github,
    format_json,
    format_porcelain,
    format_rich,
    lint,
)
from beadloom.graph.rules.layer_reach import (
    LAYER_POPULATION_RULE_TYPE,
    layer_rule_reach,
    layer_rule_reaches,
)

if TYPE_CHECKING:
    from pathlib import Path

#: The summary keys `format_json` carried before this bead. Named one by one
#: rather than counted: "additive only" is a promise to a consumer that reads a
#: key by name, and a length check keeps passing while a rename breaks it.
_SUMMARY_KEYS_BEFORE_A3 = frozenset(
    {
        "rules_evaluated",
        "rules_inert",
        "violations_suppressed",
        "violations_count",
        "error_count",
        "warning_count",
        "files_scanned",
        "files_unattributed",
        "imports_resolved",
        "elapsed_ms",
    }
)

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


def _project(tmp_path: Path, *, nodes: str, edges: str) -> Path:
    """A project whose only rule is the layer rule, over the given graph."""
    graph_dir = tmp_path / ".beadloom" / "_graph"
    graph_dir.mkdir(parents=True)
    (graph_dir / "services.yml").write_text(f"nodes:\n{nodes}edges:\n{edges}")
    (graph_dir / "rules.yml").write_text(f"version: 1\nrules:\n{_LAYER_RULE}")
    (tmp_path / "docs").mkdir()
    return tmp_path


@pytest.fixture()
def partly_layered_project(tmp_path: Path) -> Path:
    """Two `depends_on` edges, one of which the rule can judge.

    `svc -> dom` carries a declared tag at both ends. `widget -> helper` carries
    none, so the rule passes over it — the shape this epic exists to make
    visible, at a size the numbers can be read at: 1 of 2.
    """
    return _project(
        tmp_path,
        nodes=(
            "  - ref_id: svc\n    kind: service\n    summary: A service\n"
            "    tags: [layer-service]\n"
            "  - ref_id: dom\n    kind: domain\n    summary: A domain\n"
            "    tags: [layer-domain]\n"
            "  - ref_id: widget\n    kind: feature\n    summary: An untagged feature\n"
            "  - ref_id: helper\n    kind: feature\n    summary: Another untagged feature\n"
        ),
        edges=(
            "  - src: svc\n    dst: dom\n    kind: depends_on\n"
            "  - src: widget\n    dst: helper\n    kind: depends_on\n"
        ),
    )


@pytest.fixture()
def fully_layered_project(tmp_path: Path) -> Path:
    """One `depends_on` edge, tagged at both ends and in the declared direction.

    The rule reaches everything it was handed and finds nothing wrong, so this
    is the green line — and the only place the population appears is the clause
    this bead adds.
    """
    return _project(
        tmp_path,
        nodes=(
            "  - ref_id: svc\n    kind: service\n    summary: A service\n"
            "    tags: [layer-service]\n"
            "  - ref_id: dom\n    kind: domain\n    summary: A domain\n"
            "    tags: [layer-domain]\n"
        ),
        edges="  - src: svc\n    dst: dom\n    kind: depends_on\n",
    )


@pytest.fixture()
def unlayered_project(tmp_path: Path) -> Path:
    """A project that declares no layer rule at all — nothing to state."""
    graph_dir = tmp_path / ".beadloom" / "_graph"
    graph_dir.mkdir(parents=True)
    (graph_dir / "services.yml").write_text(
        "nodes:\n"
        "  - ref_id: billing\n    kind: domain\n    summary: Billing\n"
        "  - ref_id: auth\n    kind: domain\n    summary: Auth\n"
        "edges: []\n"
    )
    (graph_dir / "rules.yml").write_text(
        "version: 1\n"
        "rules:\n"
        "  - name: billing-no-auth\n"
        '    description: "Billing must not import auth"\n'
        "    deny:\n"
        "      from: { ref_id: billing }\n"
        "      to: { ref_id: auth }\n"
    )
    (tmp_path / "docs").mkdir()
    return tmp_path


def _run(project: Path) -> LintResult:
    return lint(project, reindex=incremental_reindex)


# ---------------------------------------------------------------------------
# The result carries it
# ---------------------------------------------------------------------------


class TestTheResultCarriesThePopulation:
    """`LintResult` holds the numbers, so no rendering has to re-derive them."""

    def test_one_population_per_layer_rule(self, partly_layered_project: Path) -> None:
        result = _run(partly_layered_project)

        assert [p.rule_name for p in result.layer_populations] == ["architecture-layers"]
        population = result.layer_populations[0]
        assert population.edge_kind == "depends_on"
        assert (population.own_tags.evaluated, population.own_tags.total) == (1, 2)
        assert population.own_tags.skipped_untagged == 1

    def test_a_project_with_no_layer_rule_carries_none(self, unlayered_project: Path) -> None:
        assert _run(unlayered_project).layer_populations == []

    def test_the_numbers_agree_with_the_finding_the_evaluator_emitted(
        self, partly_layered_project: Path
    ) -> None:
        """The two answers to one question, held against each other.

        `lint` counts the population beside `inert_rule_names` and
        `suppressed_crossings`, while `evaluate_all` counts it again inside the
        evaluator. Both call `reach_of` over one index, so they cannot differ in
        logic — and this is what would fail if one of them later stopped doing
        that, which is the whole subject of this epic.
        """
        result = _run(partly_layered_project)
        population = result.layer_populations[0]
        statements = [
            v for v in result.violations if v.rule_type == LAYER_POPULATION_RULE_TYPE
        ]

        assert len(statements) == 1
        message = statements[0].message
        assert f"{population.own_tags.evaluated} of {population.own_tags.total}" in message
        assert str(population.own_tags.skipped_untagged) in message


class TestOneReadPerRun:
    """`layer_rule_reaches` answers for every rule over one read of the graph."""

    def test_it_agrees_rule_by_rule_with_the_single_rule_entry_point(
        self, partly_layered_project: Path
    ) -> None:
        from beadloom.graph.rules.loader import load_rules
        from beadloom.graph.rules.types import LayerRule
        from beadloom.infrastructure.db import readonly_connection

        _run(partly_layered_project)
        rules = load_rules(partly_layered_project / ".beadloom" / "_graph" / "rules.yml")
        layer_rules = [rule for rule in rules if isinstance(rule, LayerRule)]

        with readonly_connection(partly_layered_project / ".beadloom" / "beadloom.db") as conn:
            assert layer_rule_reaches(conn, layer_rules) == [
                layer_rule_reach(conn, rule) for rule in layer_rules
            ]

    def test_no_rules_reads_nothing(self, partly_layered_project: Path) -> None:
        from beadloom.infrastructure.db import readonly_connection

        _run(partly_layered_project)
        with readonly_connection(partly_layered_project / ".beadloom" / "beadloom.db") as conn:
            assert layer_rule_reaches(conn, []) == []


# ---------------------------------------------------------------------------
# The four renderings
# ---------------------------------------------------------------------------


class TestTheRichRendering:
    """The line a person reads states the denominator of the verdict above it."""

    def test_the_red_line_carries_it(self, partly_layered_project: Path) -> None:
        text = format_rich(_run(partly_layered_project))

        summary = next(line for line in text.splitlines() if line.startswith("Errors:"))
        assert "architecture-layers judged 1 of 2 live depends_on edge(s)" in summary

    def test_the_green_line_carries_it(self, fully_layered_project: Path) -> None:
        """A population is not a consolation for a failure.

        The rule reached every edge here, so it emits no finding: if the green
        line stayed silent too, `1 of 1` and `1 of 400` would again be the same
        output.
        """
        result = _run(fully_layered_project)
        text = format_rich(result)

        assert result.violations == []
        summary = next(line for line in text.splitlines() if "No violations found" in line)
        assert "architecture-layers judged 1 of 1 live depends_on edge(s)" in summary

    def test_a_project_with_no_layer_rule_keeps_the_line_it_had(
        self, unlayered_project: Path
    ) -> None:
        summary = next(
            line
            for line in format_rich(_run(unlayered_project)).splitlines()
            if "No violations found" in line
        )
        assert "judged" not in summary

    def test_a_rule_handed_no_edge_states_no_population(self, tmp_path: Path) -> None:
        """A rule with an empty edge set has no denominator to report.

        Liveness already says that rule could not fire, and this project has
        filed the affirm-it-twice shape before. Silence here is the same
        decision `population_statement` makes, taken for the same reason.
        """
        project = _project(
            tmp_path,
            nodes="  - ref_id: svc\n    kind: service\n    summary: A service\n"
            "    tags: [layer-service]\n",
            edges=" []\n",
        )
        result = _run(project)

        assert result.layer_populations[0].own_tags.total == 0
        assert "judged" not in format_rich(result)


class TestTheJsonRendering:
    """Structured output gains a key and loses none."""

    def test_the_summary_carries_the_population(self, partly_layered_project: Path) -> None:
        summary = json.loads(format_json(_run(partly_layered_project)))["summary"]

        assert summary["layer_populations"] == [
            {
                "rule": "architecture-layers",
                "edge_kind": "depends_on",
                "evaluated": 1,
                "total": 2,
                "skipped_untagged": 1,
                "inherited_evaluated": 1,
                "inherited_total": 2,
                "unjudged": 0,
            }
        ]

    def test_the_existing_keys_are_unchanged(self, partly_layered_project: Path) -> None:
        payload = json.loads(format_json(_run(partly_layered_project)))

        assert set(payload) == {"violations", "findings", "suppressed", "summary"}
        assert set(payload["summary"]) >= _SUMMARY_KEYS_BEFORE_A3
        assert set(payload["summary"]) - _SUMMARY_KEYS_BEFORE_A3 == {"layer_populations"}

    def test_a_clean_run_carries_it_too(self, fully_layered_project: Path) -> None:
        payload = json.loads(format_json(_run(fully_layered_project)))

        assert payload["violations"] == []
        assert payload["summary"]["layer_populations"][0]["total"] == 1

    def test_inheritance_is_reported_beside_own_tags(self, tmp_path: Path) -> None:
        """The second pair of numbers is what Release B will move.

        A component inside a tagged domain is the shape an adopter has and this
        repository hides. Own tags reach 1 of 2 edges here; membership inherited
        through `part_of` reaches both.
        """
        project = _project(
            tmp_path,
            nodes=(
                "  - ref_id: svc\n    kind: service\n    summary: A service\n"
                "    tags: [layer-service]\n"
                "  - ref_id: dom\n    kind: domain\n    summary: A domain\n"
                "    tags: [layer-domain]\n"
                "  - ref_id: inner\n    kind: feature\n    summary: Inside the domain\n"
            ),
            edges=(
                "  - src: svc\n    dst: dom\n    kind: depends_on\n"
                "  - src: inner\n    dst: dom\n    kind: part_of\n"
                "  - src: svc\n    dst: inner\n    kind: depends_on\n"
            ),
        )
        entry = json.loads(format_json(_run(project)))["summary"]["layer_populations"][0]

        assert (entry["evaluated"], entry["total"]) == (1, 2)
        assert (entry["inherited_evaluated"], entry["unjudged"]) == (2, 1)


class TestTheGithubRendering:
    """The CI annotation stream states the population as a notice."""

    def test_a_notice_carries_it(self, partly_layered_project: Path) -> None:
        lines = format_github(_run(partly_layered_project)).splitlines()

        assert lines[0] == (
            "::notice::architecture-layers judged 1 of 2 live depends_on edge(s)"
        )

    def test_a_clean_run_is_no_longer_silent(self, fully_layered_project: Path) -> None:
        result = _run(fully_layered_project)

        assert result.violations == []
        assert format_github(result) == (
            "::notice::architecture-layers judged 1 of 1 live depends_on edge(s)"
        )

    def test_a_project_with_no_layer_rule_stays_silent(self, unlayered_project: Path) -> None:
        assert format_github(_run(unlayered_project)) == ""


class TestThePorcelainRendering:
    """A hook reads the population without parsing a violation record."""

    def test_a_marked_line_carries_it(self, partly_layered_project: Path) -> None:
        lines = format_porcelain(_run(partly_layered_project)).splitlines()

        assert lines[0] == (
            f"{POPULATION_MARKER}layer_population:architecture-layers:depends_on:1:2:1:1"
        )

    def test_the_violation_records_are_untouched(self, partly_layered_project: Path) -> None:
        """The marker is what separates the two shapes, so records keep theirs.

        A rule name cannot begin with `# `, which is why the same marker
        `scope-check` uses is the split here: a consumer drops the marked lines
        and reads exactly the seven-field records it read before.
        """
        records = [
            line
            for line in format_porcelain(_run(partly_layered_project)).splitlines()
            if not line.startswith(POPULATION_MARKER)
        ]

        assert records
        assert all(len(record.split(":")) == 7 for record in records)
        assert all(
            record.startswith("architecture-layers:") and POPULATION_MARKER not in record
            for record in records
        )

    def test_a_clean_run_is_no_longer_silent(self, fully_layered_project: Path) -> None:
        result = _run(fully_layered_project)

        assert result.violations == []
        assert format_porcelain(result) == (
            f"{POPULATION_MARKER}layer_population:architecture-layers:depends_on:1:1:0:1"
        )

    def test_a_project_with_no_layer_rule_stays_silent(self, unlayered_project: Path) -> None:
        assert format_porcelain(_run(unlayered_project)) == ""


# ---------------------------------------------------------------------------
# `beadloom lint`'s own line
# ---------------------------------------------------------------------------


class TestTheCleanLineTheCommandPrints:
    """The line `beadloom lint` writes when a formatter reports nothing."""

    def _run_cli(self, project: Path, fmt: str) -> str:
        from click.testing import CliRunner

        from beadloom.services.cli import main

        result = CliRunner().invoke(
            main, ["lint", "--project", str(project), "--format", fmt]
        )
        assert result.exit_code == 0, result.output
        return result.output

    def test_the_clean_line_carries_the_population(self, fully_layered_project: Path) -> None:
        output = self._run_cli(fully_layered_project, "porcelain")

        clean = next(line for line in output.splitlines() if line.startswith("0 violations"))
        assert "architecture-layers judged 1 of 1 live depends_on edge(s)" in clean

    def test_the_clean_line_still_prints_beside_the_marked_line(
        self, fully_layered_project: Path
    ) -> None:
        """The population line does not evict the verdict it qualifies.

        Before this bead the clean line was printed because the porcelain
        formatter produced nothing at all. It now produces the population, so a
        branch keyed on "no output" would have dropped the one sentence saying
        there were no violations.
        """
        lines = self._run_cli(fully_layered_project, "porcelain").splitlines()

        assert any(line.startswith(POPULATION_MARKER) for line in lines)
        assert any(line.startswith("0 violations") for line in lines)

    def test_a_project_with_no_layer_rule_keeps_the_line_it_had(
        self, unlayered_project: Path
    ) -> None:
        output = self._run_cli(unlayered_project, "porcelain").strip()

        assert output == "0 violations, 1 rules evaluated"
