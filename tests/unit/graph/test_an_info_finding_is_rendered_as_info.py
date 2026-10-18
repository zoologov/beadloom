"""A finding at ``info`` is said as information in every rendering (BDL-083 D2, #328).

The one ``info`` finding the rule engine produces is the statement that an import rule is
live with nothing to ban. Before it existed the same fact was a ``warn`` that read "cannot
fire". Rendering it as ``[WARN]``, counting it as a warning or exiting 1 on it under
``--fail-on-warn`` would put the false signal back in another place.
"""

from __future__ import annotations

from beadloom.graph.linter import LintResult, format_github, format_rich
from beadloom.graph.rules.import_glob import nothing_to_ban_finding


def _result() -> LintResult:
    statement = nothing_to_ban_finding(
        rule_name="digest-no-os",
        rule_description="the digest domain does no I/O",
        glob="os/**",
        example="os",
        searched="0 of 16 indexed import paths",
    )
    return LintResult(
        violations=[statement], rules_evaluated=1, files_scanned=5, imports_resolved=16
    )


def test_the_text_rendering_marks_it_info_and_never_warn() -> None:
    text = format_rich(_result())

    assert "[INFO] digest-no-os" in text
    assert "[WARN]" not in text


def test_it_is_neither_an_error_nor_a_warning() -> None:
    result = _result()

    assert (result.error_count, result.warning_count, result.has_errors) == (0, 0, False)


def test_fail_on_warn_does_not_exit_on_it() -> None:
    assert _result().fails_on_warn is False


def test_the_github_rendering_is_a_notice() -> None:
    (line,) = format_github(_result()).splitlines()

    assert line.startswith("::notice::nothing_to_ban digest-no-os: 0 imports of `os/**`")
