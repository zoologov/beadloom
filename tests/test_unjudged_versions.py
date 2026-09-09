"""A version token the audit declined to judge is reported, in every surface.

BDL-068 S6, `beadloom-0mdo.81`, closing BDL-UX #266.

`git` enters the subject vocabulary from `(project_root / ".git").exists()`,
and the absent case was read as the assertion that this project has nothing to
do with git.  A directory built by `git archive HEAD` -- every clean room this
repository measures in -- carries no `.git`, so "Measured on git 2.49.0" was
compared against this project's own version and every clean-room Gate run on
this repository was rc 1 for that line.

The vocabulary now calls such a name UNRESOLVED, and this module holds the half
that keeps the fix from being a silencer: a declined token is COUNTED and NAMED
wherever the audit reports, so a reader can see the exemption applied.  An
exemption nobody can see is the failure mode `version_subjects.py`'s own design
notes rank below a false positive.
"""

from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from beadloom.doc_sync.audit import AuditResult, compare_facts
from beadloom.doc_sync.scanner import Mention
from beadloom.doc_sync.version_subjects import VersionSubjects
from beadloom.infrastructure.db import create_schema, open_db
from beadloom.services.cli import main

#: A vocabulary with one confirmed foreign name and one the environment could
#: not confirm, so every assertion below can tell the two populations apart.
SUBJECTS = VersionSubjects(
    names=frozenset({"bd"}),
    project=frozenset({"invoice-svc"}),
    origins=(("bd", "docs_audit.subjects"),),
    unresolved=frozenset({"git"}),
    unresolved_origins=(("git", "no .git here"),),
)


def _mention(value: str, subject: str | None) -> Mention:
    return Mention(
        fact_name="version",
        value=value,
        file=Path("README.md"),
        line=1,
        context=f"Measured on {subject} {value}.",
        subject=subject,
    )


def _project(tmp_path: Path, readme: str) -> Path:
    """An adopter project with no ``.git``, which is what a clean room is."""
    proj = tmp_path / "adopter"
    (proj / ".beadloom").mkdir(parents=True)
    (proj / "pyproject.toml").write_text(
        '[project]\nname = "invoice-svc"\nversion = "3.7.0"\n', encoding="utf-8"
    )
    (proj / "README.md").write_text(f"# invoice-svc\n\n{readme}\n", encoding="utf-8")
    conn = open_db(proj / ".beadloom" / "beadloom.db")
    create_schema(conn)
    conn.close()
    return proj


class TestTheTwoExemptPopulationsStaySeparate:
    """Attributed and unjudged are exempt for different reasons."""

    def test_a_confirmed_subject_is_attributed(self) -> None:
        result = compare_facts({}, [_mention("1.0.4", "bd")], subjects=SUBJECTS)
        assert [m.value for m in result.attributed] == ["1.0.4"]
        assert result.unjudged == []

    def test_an_unresolved_subject_is_unjudged(self) -> None:
        result = compare_facts({}, [_mention("2.49.0", "git")], subjects=SUBJECTS)
        assert [m.value for m in result.unjudged] == ["2.49.0"]
        assert result.attributed == []

    def test_the_spelling_in_the_document_does_not_decide_it(self) -> None:
        """``Git 2.49.0`` names the same subject as ``git 2.49.0``."""
        result = compare_facts({}, [_mention("2.49.0", "Git")], subjects=SUBJECTS)
        assert [m.value for m in result.unjudged] == ["2.49.0"]

    def test_a_token_with_no_subject_is_still_judged(self) -> None:
        facts_result = compare_facts(
            {}, [_mention("3.1.0", None)], subjects=SUBJECTS
        )
        assert facts_result.unjudged == []
        assert facts_result.attributed == []
        assert [m.value for m in facts_result.unmatched] == ["3.1.0"]


class TestTheGateLineNamesIt:
    """`beadloom ci`'s docs-audit line says what it declined to judge."""

    def test_the_line_names_the_subject_and_the_count(self) -> None:
        from beadloom.application.gate import _audit_summary

        result = AuditResult(
            facts={},
            findings=[],
            unmatched=[],
            coverage={},
            unjudged=[_mention("2.49.0", "git")],
            subjects=SUBJECTS,
        )

        line = _audit_summary(result, [])
        assert "git" in line, line
        assert "could not judge" in line.lower(), line

    def test_the_line_is_unchanged_when_nothing_was_declined(self) -> None:
        from beadloom.application.gate import _audit_summary

        result = AuditResult(facts={}, findings=[], unmatched=[], coverage={})

        assert "could not judge" not in _audit_summary(result, []).lower()


class TestTheReportNamesIt:
    """`beadloom docs audit` reports the population in both its renderings."""

    def test_the_human_report_names_the_subject_and_the_reason(
        self, tmp_path: Path
    ) -> None:
        project = _project(tmp_path, "Measured on git 2.49.0 in two rigs.")

        invocation = CliRunner().invoke(
            main, ["docs", "audit", "--project", str(project)]
        )

        assert invocation.exit_code == 0, invocation.output
        assert "could not judge" in invocation.output.lower(), invocation.output
        assert "git" in invocation.output

    def test_the_json_carries_the_tokens_the_count_and_the_vocabulary(
        self, tmp_path: Path
    ) -> None:
        project = _project(tmp_path, "Measured on git 2.49.0 in two rigs.")

        invocation = CliRunner().invoke(
            main, ["docs", "audit", "--json", "--project", str(project)]
        )
        payload = json.loads(invocation.stdout)

        assert payload["unjudged_versions"] == [
            {
                "file": "README.md",
                "line": 3,
                "value": "2.49.0",
                "subject": "git",
            }
        ]
        assert payload["summary"]["unjudged_version_count"] == 1
        reasons = {
            entry["name"]: entry["reason"]
            for entry in payload["unresolved_version_subjects"]
        }
        assert ".git" in reasons["git"]


class TestTheDefectVerbatim:
    """The line that reddened every clean-room Gate run on this repository."""

    def test_a_dependency_release_in_a_directory_with_no_git_is_not_stale(
        self, tmp_path: Path
    ) -> None:
        project = _project(
            tmp_path, "Measured on git 2.49.0 in two isolated rigs."
        )

        invocation = CliRunner().invoke(
            main, ["docs", "audit", "--json", "--project", str(project)]
        )
        payload = json.loads(invocation.stdout)

        assert payload["stale"] == []
        assert invocation.exit_code == 0

    def test_this_projects_own_version_is_still_judged_in_that_directory(
        self, tmp_path: Path
    ) -> None:
        """The fix must not buy the room's green with the tree's blindness."""
        project = _project(tmp_path, "The current release is 9.9.9.")

        invocation = CliRunner().invoke(
            main, ["docs", "audit", "--json", "--project", str(project)]
        )
        payload = json.loads(invocation.stdout)

        assert [entry["mentioned"] for entry in payload["stale"]] == ["9.9.9"]
