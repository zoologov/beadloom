# beadloom:domain=application
"""A machine-readable stream stays machine-readable while the human one warns.

BDL-062 `.5`. Two dev agents in this feature diagnosed the same symptom as
"``lint --format json`` pollutes stdout", and both were wrong: the CLI writes
the JSON document to stdout and the ``warning: N error-severity violation(s)``
line to stderr, so ``beadloom lint --format json | jq`` has always worked. The
defect is in the harness. Click 8.4's ``CliRunner`` merges stderr into
``result.output``, so ``json.loads(result.output)`` parses only while nothing
warns.

Measured on this branch before it was fixed, a tmp project with one
error-severity violation and no ``--strict``::

    result.output  len=1385  -> JSONDecodeError: Extra data: line 44 column 1
    result.stdout  len=1295  -> PARSES
    result.stderr  len=  90  -> 'warning: 1 error-severity violation(s) found, ...'

Those parses went green on their own once `.4` corrected the four drifting
nodes and the warning stopped firing, which is the reason they could not be
left alone: **the fragility outlived the symptom**. Every JSON parse in this
suite now reads ``result.stdout``, and
:class:`TestNoTestParsesJsonFromTheMergedStream` is what stops one drifting
back.

The tests below are split by what they hold:

* :class:`TestTheWarningNeverReachesTheMachineStream` — the CLI's own contract,
  asserted while the warning is actually firing rather than while it is quiet.
* :class:`TestNoTestParsesJsonFromTheMergedStream` — the harness rule, read out
  of this suite's own source, so a re-introduced ``.output`` parse fails here
  rather than in whichever unrelated test the next warning happens to reach.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from click.testing import CliRunner

from beadloom.services.cli import main

if TYPE_CHECKING:
    from click.testing import Result

#: This repository's root — the live graph the self-lint tests read.
REPO_ROOT = Path(__file__).resolve().parents[1]

#: The directory whose ``test_*.py`` the harness rule is read out of.
TESTS_ROOT = Path(__file__).resolve().parent

#: The exact sentence the CLI writes to stderr when errors were found without
#: ``--strict``. Spelled here so a reword that moved it to stdout fails loudly.
WARNING_MARKER = "error-severity violation(s) found"


# --------------------------------------------------------------------------- #
# a project the warning actually fires on
# --------------------------------------------------------------------------- #


def _project_with_an_error_violation(tmp_path: Path) -> Path:
    """A project whose graph forbids an import its code makes.

    ``deny`` rules default to ``error``, so linting this project without
    ``--strict`` exits 0 *and* writes the warning — the one combination under
    which the merged stream is not valid JSON.
    """
    project = tmp_path / "proj"
    graph_dir = project / ".beadloom" / "_graph"
    graph_dir.mkdir(parents=True)
    (project / "docs").mkdir()
    (graph_dir / "services.yml").write_text(
        "nodes:\n"
        "  - ref_id: billing\n"
        "    kind: domain\n"
        "    summary: Billing domain\n"
        "  - ref_id: auth\n"
        "    kind: domain\n"
        "    summary: Auth domain\n"
        "edges: []\n",
        encoding="utf-8",
    )
    (graph_dir / "rules.yml").write_text(
        "version: 1\n"
        "rules:\n"
        "  - name: billing-no-auth\n"
        '    description: "Billing must not import auth"\n'
        "    deny:\n"
        "      from: { ref_id: billing }\n"
        "      to: { ref_id: auth }\n",
        encoding="utf-8",
    )
    billing = project / "src" / "billing"
    billing.mkdir(parents=True)
    (billing / "invoice.py").write_text(
        "# beadloom:domain=billing\nimport auth.tokens\n\n\ndef process() -> None:\n    pass\n",
        encoding="utf-8",
    )
    auth = project / "src" / "auth"
    auth.mkdir(parents=True)
    (auth / "tokens.py").write_text(
        "# beadloom:domain=auth\n\n\ndef verify() -> None:\n    pass\n",
        encoding="utf-8",
    )
    return project


def _resolve_the_import(project: Path) -> None:
    """Record the cross-boundary import as resolved so the rule engine sees it.

    The reindexer leaves ``resolved_ref_id`` unset for a package that is not on
    the import path, and an unresolved import is not a boundary crossing. This
    is the same seam ``tests/test_cli_lint.py`` uses.
    """
    from beadloom.infrastructure.db import open_db

    conn = open_db(project / ".beadloom" / "beadloom.db")
    conn.execute(
        "INSERT OR REPLACE INTO code_imports"
        " (file_path, line_number, import_path, resolved_ref_id, file_hash)"
        " VALUES (?, ?, ?, ?, ?)",
        ("src/billing/invoice.py", 2, "auth.tokens", "auth", "test"),
    )
    conn.commit()
    conn.close()


@pytest.fixture()
def warning_lint(tmp_path: Path) -> Result:
    """One ``lint --format json`` run whose stderr carries the warning."""
    project = _project_with_an_error_violation(tmp_path)
    runner = CliRunner()
    runner.invoke(main, ["lint", "--project", str(project)])
    _resolve_the_import(project)
    return runner.invoke(
        main, ["lint", "--project", str(project), "--no-reindex", "--format", "json"]
    )


# --------------------------------------------------------------------------- #
# the CLI's contract, asserted while the warning is firing
# --------------------------------------------------------------------------- #


class TestTheWarningNeverReachesTheMachineStream:
    """The JSON document and the human warning travel on different streams."""

    def test_the_run_under_test_really_does_warn(self, warning_lint: Result) -> None:
        """The fixture is only evidence while it exhibits the condition.

        A contract asserted on a run that never warned would pass on the defect
        it was written for — the exact way these parses went green in `.4`.
        """
        assert WARNING_MARKER in warning_lint.stderr, warning_lint.stderr
        assert warning_lint.exit_code == 0, warning_lint.output

    def test_stdout_parses_as_json_while_the_warning_fires(self, warning_lint: Result) -> None:
        payload = json.loads(warning_lint.stdout)

        assert payload["summary"]["error_count"] >= 1, payload["summary"]

    def test_the_warning_is_absent_from_stdout(self, warning_lint: Result) -> None:
        assert WARNING_MARKER not in warning_lint.stdout

    def test_the_merged_stream_is_the_only_one_that_is_not_json(
        self, warning_lint: Result
    ) -> None:
        """Why the harness rule exists, stated as an executable measurement.

        This asserts a property of ``CliRunner``, not of Beadloom: if a future
        Click stops merging the streams the assertion is simply no longer true
        and the rule below becomes belt-and-braces rather than load-bearing.
        Recorded so a reader can tell which of the two changed.
        """
        assert warning_lint.output != warning_lint.stdout
        assert warning_lint.stderr in warning_lint.output

    def test_this_repository_lints_to_a_parsable_document_on_stdout(
        self, live_repo_reindexed: Path
    ) -> None:
        """The live-repo self-lint, which is where the fragility was measured."""
        result = CliRunner().invoke(
            main,
            ["lint", "--format", "json", "--project", str(live_repo_reindexed), "--no-reindex"],
        )

        payload = json.loads(result.stdout)

        assert "violations" in payload
        assert "summary" in payload


# --------------------------------------------------------------------------- #
# the harness rule, read out of this suite's own source
# --------------------------------------------------------------------------- #


def _json_parses_of_a_merged_stream(source: str) -> list[str]:
    """Every ``…loads(… .output …)`` in *source*, as ``"line N"`` strings.

    Matches on the callee's ``loads`` and on the attribute name anywhere inside
    the argument, rather than on a variable name. That covers ``result``,
    ``machine``, ``world["result"]``, ``_cli(...)`` and the
    ``result.output.split(marker)[1]`` form without enumerating any of them, and
    it does not care whether the module was imported as ``json`` or ``_json``.
    """
    offenders: list[str] = []
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.Call) or not node.args:
            continue
        callee = node.func
        if not isinstance(callee, ast.Attribute) or callee.attr != "loads":
            continue
        for inner in ast.walk(node.args[0]):
            if isinstance(inner, ast.Attribute) and inner.attr == "output":
                offenders.append(f"line {inner.lineno}")
    return offenders


class TestNoTestParsesJsonFromTheMergedStream:
    """No test in this suite reads a JSON payload out of ``result.output``."""

    @pytest.mark.parametrize(
        "snippet",
        [
            "payload = json.loads(result.output)",
            'payload = json.loads(result.output.split("x", 1)[1])',
            'payload = json.loads(world["result"].output)',
            "payload = json.loads(_cli(project).output)",
            "payload = _json.loads(str(result.output))",
        ],
        ids=["plain", "sliced", "subscripted", "call", "aliased-and-stringified"],
    )
    def test_the_detector_sees_every_spelling_it_forbids(self, snippet: str) -> None:
        """The rule is only a rule if it recognises its own violation.

        Each spelling here occurred in this suite before the sweep, so the list
        is a record of what was actually written, not of what could be.
        """
        assert _json_parses_of_a_merged_stream(snippet) == ["line 1"]

    @pytest.mark.parametrize(
        "snippet",
        [
            "payload = json.loads(result.stdout)",
            'payload = json.loads(result.stdout.split("x", 1)[1])',
            "assert result.output.count('x') == 1",
        ],
        ids=["plain", "sliced", "not-a-parse-at-all"],
    )
    def test_the_detector_passes_what_is_correct(self, snippet: str) -> None:
        assert _json_parses_of_a_merged_stream(snippet) == []

    def test_no_test_module_parses_json_from_the_merged_stream(self) -> None:
        offenders: dict[str, list[str]] = {}
        for path in sorted(TESTS_ROOT.rglob("*.py")):
            if path == Path(__file__):
                continue
            found = _json_parses_of_a_merged_stream(path.read_text(encoding="utf-8"))
            if found:
                offenders[str(path.relative_to(TESTS_ROOT))] = found
        assert offenders == {}, (
            "these parse a JSON payload out of the stream Click merges stderr "
            f"into; read `.stdout` instead: {offenders}"
        )
