"""The Gate's lint line counts the statements the linter made at info.

BDL-083 S1 fix 1 (``beadloom-4m0w``, S1R Minor 5). S1b added ``info`` as the severity of
a live rule with nothing to ban. The lint step's summary counted errors and warnings
only, so a lint whose only findings were statements at info read
"0 error(s), 0 warning(s)" and named no count for what it had found.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from beadloom.application.gate import lint_step
from beadloom.graph import linter
from beadloom.graph.linter import LintResult
from beadloom.graph.rules.types import INFO_SEVERITY, Violation

if TYPE_CHECKING:
    from pathlib import Path

    import pytest


def _violation(severity: str) -> Violation:
    return Violation(
        rule_name="a-rule",
        rule_description="a rule",
        rule_type="forbid_import",
        severity=severity,
        file_path=None,
        line_number=None,
        from_ref_id=None,
        to_ref_id=None,
        message="a finding",
    )


def _lint_returning(monkeypatch: pytest.MonkeyPatch, *severities: str) -> None:
    result = LintResult(violations=[_violation(s) for s in severities], rules_evaluated=3)
    monkeypatch.setattr(linter, "lint", lambda _root: result)


def test_a_lint_of_info_statements_only_counts_them(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _lint_returning(monkeypatch, INFO_SEVERITY, INFO_SEVERITY)

    step = lint_step(tmp_path)

    assert step.passed
    assert step.summary.startswith("0 error(s), 0 warning(s), 2 statement(s) at info")


def test_the_info_count_follows_the_error_and_warning_counts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _lint_returning(monkeypatch, "error", "warn", INFO_SEVERITY)

    step = lint_step(tmp_path)

    assert not step.passed
    assert step.summary.startswith("1 error(s), 1 warning(s), 1 statement(s) at info")


def test_a_lint_with_no_info_statement_keeps_its_line(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _lint_returning(monkeypatch, "warn")

    step = lint_step(tmp_path)

    assert step.summary.startswith("0 error(s), 1 warning(s)")
    assert "at info" not in step.summary
