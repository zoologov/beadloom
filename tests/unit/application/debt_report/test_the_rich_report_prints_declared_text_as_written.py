"""The Rich debt report prints the patterns, rules and nodes it names as they were written.

Fourth review of ``beadloom-b9ll``, m-4-1 (``beadloom-2mj3.19``): the report passed its
population lines to Rich as markup. Rich read the ``[jt]`` of the default Jest patterns as
a style tag and dropped it, so every JavaScript or TypeScript project on the defaults was
told its tests were read by ``__tests__/**/*.s`` while ``ctx`` and the JSON said
``__tests__/**/*.[jt]s``. A declared pattern that Rich parses as a closing tag, ``[/x]``,
crashed the report with a ``MarkupError``.
"""

from __future__ import annotations

import re

from beadloom.application.debt_report import CategoryScore, DebtReport, NodeDebt
from beadloom.application.debt_report.render import format_debt_report
from beadloom.context_oracle.test_binding import describe_test_file_recognition
from beadloom.context_oracle.test_layout import layout_from_config

_ANSI = re.compile(r"\x1b\[[0-9;]*m")


def _plain(rendered: str) -> str:
    """The report as a reader sees it, with the terminal's colour codes removed."""
    return _ANSI.sub("", rendered)


def _report(
    *,
    test_population: str = "",
    layer_populations: tuple[str, ...] = (),
    offenders: tuple[NodeDebt, ...] = (),
) -> DebtReport:
    return DebtReport(
        debt_score=0.0,
        severity="clean",
        categories=[
            CategoryScore(name="rule_violations", score=0.0, details={"errors": 0}),
            CategoryScore(name="test_gaps", score=0.0, details={"untested": 0}),
        ],
        top_offenders=list(offenders),
        trend=None,
        layer_populations=list(layer_populations),
        test_population=test_population,
    )


def _population_under(config: dict[str, object]) -> str:
    layout, problems = layout_from_config(config)
    assert problems == []
    return describe_test_file_recognition(layout.recorded(present_roots=("__tests__",)))


class TestTheTestPopulation:
    def test_the_jest_defaults_keep_their_brackets(self) -> None:
        population = _population_under({})
        assert "__tests__/**/*.[jt]s" in population

        rendered = _plain(format_debt_report(_report(test_population=population)))

        assert "__tests__/**/*.[jt]s" in rendered
        assert "__tests__/**/*.[jt]sx" in rendered

    def test_a_pattern_rich_reads_as_a_closing_tag_is_printed_not_raised(self) -> None:
        population = _population_under(
            {"tests": {"patterns": {"jest": ["*.test.ts", "[/x]*.ts"]}}}
        )

        rendered = _plain(format_debt_report(_report(test_population=population)))

        assert "[/x]*.ts" in rendered


class TestTheOtherDeclaredText:
    def test_a_layer_population_is_printed_as_written(self) -> None:
        phrase = "layers [domain] judged 3 of 5 edge(s) [/x]"

        rendered = _plain(format_debt_report(_report(layer_populations=(phrase,))))

        assert f"counted over: {phrase}" in rendered

    def test_an_offender_and_its_rule_are_printed_as_written(self) -> None:
        offender = NodeDebt(ref_id="app-[slug]", score=3.0, reasons=["violation:error:[/x]"])

        rendered = _plain(format_debt_report(_report(offenders=(offender,))))

        assert "app-[slug]" in rendered
        assert "violation:error:[/x]" in rendered
