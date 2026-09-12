"""BDL-069 S3 (``beadloom-jtcx``) — the report over the version surface.

The derivation is ``beadloom-w4cd``'s and is tested in
``tests/test_version_surface.py``. What is tested here is the report: whether a
person cutting a release can read every place, what checks each one, and which
ones nothing checks, out of one run.

:class:`TestTheNinePlacesTheReleaseHadToEdit` is the binding case. The release
commit ``f3b5593e`` added 23 lines carrying the new literal, across 13 files.
Nine of those files are the version's homes BDL-UX #281 records -- the
manifest's assignment, the graph node summary, the agent-instruction region, the
getting-started guide, the CLI reference, the integration test, and three files
no instrument reads (the changelog, the roadmap and the audit's own SPEC). The
other four are the tracker's export and three records written about the release.
The nine are written down HERE, in the expectation, and nowhere in the module
under test: the argument of BDL-UX #281 is that a derivation beats a checklist,
and a test that asserts the derivation finds the checklist's entries is how the
two are kept apart.

The fixture projects declare ``7.3.1`` rather than this project's version, for
the reason ``beadloom-w4cd`` measured: a fixture equal to the real literal puts
its own rows into the sweep of the repository it is run beside.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from click.testing import CliRunner

from beadloom.services.cli import main

if TYPE_CHECKING:
    from collections.abc import Iterator

REPO_ROOT = Path(__file__).resolve().parent.parent

_VERSION = "7.3.1"

_MANIFEST = f"""\
[project]
name = "widget"
version = "{_VERSION}"

[tool.pytest.ini_options]
testpaths = ["tests"]
"""


def _run(project: Path, *extra: str) -> tuple[int, str]:
    result = CliRunner().invoke(main, ["version-surface", "--project", str(project), *extra])
    if result.exception is not None and not isinstance(result.exception, SystemExit):
        raise result.exception
    return result.exit_code, result.output


def _write(root: Path, relative: str, text: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _project(tmp_path: Path) -> Path:
    """A project with one place an instrument holds and one it does not."""
    project = tmp_path / "widget"
    project.mkdir()
    _write(project, "pyproject.toml", _MANIFEST)
    _write(
        project,
        "docs/getting-started.md",
        f"# Widget\n\nNothing here.\n\nThe current release is {_VERSION}.\n",
    )
    _write(project, "CHANGELOG.md", f"# Changelog\n\n## [{_VERSION}] - 2026-01-01\n")
    return project


def _project_citing_a_dependency(tmp_path: Path, *, fenced: bool) -> Path:
    """A guide the audit reads, whose version token it gives to a declared dependency.

    With *fenced*, a second line states the version inside a code block, which the
    audit does not read: two lines, one file, two different reasons.
    """
    project = _project(tmp_path)
    _write(
        project,
        "pyproject.toml",
        _MANIFEST.replace('version = "', 'dependencies = ["click>=8"]\nversion = "'),
    )
    fence = f"\n```\nwidget {_VERSION}\n```\n" if fenced else ""
    _write(
        project,
        "docs/getting-started.md",
        f"# Widget\n\nMeasured with click {_VERSION} before anything else.\n{fence}",
    )
    return project


def _block(output: str, heading: str) -> str:
    return next((block for block in output.split("\n\n") if heading in block), "")


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip())


class TestEveryPlaceIsNamedWithItsChecker:
    """The three things the report exists to say, on a project of three places."""

    def test_the_source_of_truth_is_named_with_the_chain_it_was_derived_through(
        self, tmp_path: Path
    ) -> None:
        code, output = _run(_project(tmp_path))

        assert code == 0
        assert _VERSION in output
        assert "pyproject.toml" in output
        assert "[project] version" in output

    def test_a_judged_place_carries_its_instrument_on_its_own_row(self, tmp_path: Path) -> None:
        _, output = _run(_project(tmp_path))
        checked = _block(output, "Checked (")

        assert "docs/getting-started.md" in checked
        assert "docs-audit" in checked
        assert "5" in checked

    def test_an_unjudged_place_is_under_the_gap_with_the_reason_it_falls_outside(
        self, tmp_path: Path
    ) -> None:
        _, output = _run(_project(tmp_path))
        gap = _block(output, "Checked by nothing")

        assert "CHANGELOG.md" in gap
        assert "excluded" in gap

    def test_the_counts_name_places_and_files_separately(self, tmp_path: Path) -> None:
        """Two lines in one file are two places, which is what a release edits."""
        project = _project(tmp_path)
        _write(
            project,
            "CHANGELOG.md",
            f"# Changelog\n\n## [{_VERSION}] - 2026-01-01\n\nReleased {_VERSION} today.\n",
        )

        _, output = _run(project)

        assert "Checked by nothing (2 place(s) in 1 file(s))" in output

    def test_places_in_one_file_are_grouped_under_one_header(self, tmp_path: Path) -> None:
        """A per-line list without grouping is a report nobody finishes."""
        project = _project(tmp_path)
        _write(
            project,
            "CHANGELOG.md",
            "# Changelog\n\n" + "".join(f"## [{_VERSION}] - 2026-01-0{n}\n" for n in range(1, 6)),
        )

        _, output = _run(project)

        headers = [line for line in output.splitlines() if line.startswith("    CHANGELOG.md")]
        assert headers == [
            "    CHANGELOG.md (5)    — docs audit does not read it: CHANGELOG.md is excluded "
            "by default"
        ]

    def test_two_reasons_in_one_file_are_two_groups_rather_than_one_averaged_reason(
        self, tmp_path: Path
    ) -> None:
        """A document the audit reads, stating the version twice and judged on neither.

        One line gives the token to another product, the other sits in a fenced
        block. Those are two different edits to a release and two different gaps
        in the audit, so they are two headers over one file.
        """
        project = _project_citing_a_dependency(tmp_path, fenced=True)

        code, output = _run(project)
        gap = _block(output, "Checked by nothing")
        headers = [
            line for line in gap.splitlines() if line.startswith("    docs/getting-started.md")
        ]

        assert code == 0
        assert len(headers) == 2, gap
        assert all("(1)" in header for header in headers), gap

    def test_a_wrapped_group_header_does_not_align_with_the_rows_under_it(
        self, tmp_path: Path
    ) -> None:
        """A reason's second line at a row's indent reads as a place with no line number."""
        _, output = _run(_project_citing_a_dependency(tmp_path, fenced=False))
        body = _block(output, "Checked by nothing").splitlines()[1:]
        rows = [line for line in body if line.lstrip()[:1].isdigit()]
        headers = [line for line in body if _indent(line) == len("    ")]
        continuations = [line for line in body if line not in rows and line not in headers]

        assert continuations, f"the fixture's reason no longer wraps:\n{output}"
        assert {_indent(line) for line in rows}.isdisjoint(
            {_indent(line) for line in continuations}
        ), "\n".join(body)

    def test_a_long_line_is_truncated_rather_than_wrapped_by_the_terminal(
        self, tmp_path: Path
    ) -> None:
        project = _project(tmp_path)
        _write(project, "CHANGELOG.md", f"# Changelog\n\n## [{_VERSION}] {'x' * 400}\n")

        _, output = _run(project)

        assert "…" in output
        assert max(len(line) for line in output.splitlines()) <= 100


class TestTheReportStatesItsOwnPopulation:
    """A report that does not say what it read is a claim about everything."""

    def test_it_names_the_files_it_read(self, tmp_path: Path) -> None:
        _, output = _run(_project(tmp_path))

        assert "file(s) read" in _block(output, "Population")

    def test_it_names_the_suffixes_it_did_not_read_with_a_count_each(self, tmp_path: Path) -> None:
        project = _project(tmp_path)
        _write(project, "data.json", '{"version": "7.3.1"}\n')

        _, output = _run(project)
        population = _block(output, "Population")

        assert ".json (1)" in population

    def test_it_names_the_directories_it_pruned(self, tmp_path: Path) -> None:
        _, output = _run(_project(tmp_path))

        assert ".git" in _block(output, "Population")

    def test_an_unreadable_file_is_named_with_its_reason(self, tmp_path: Path) -> None:
        project = _project(tmp_path)
        (project / "broken.md").write_bytes(b"\xff\xfe version 7.3.1\n")

        _, output = _run(project)

        assert "broken.md" in _block(output, "Population")

    def test_no_unreadable_file_reads_as_none_rather_than_as_silence(self, tmp_path: Path) -> None:
        _, output = _run(_project(tmp_path))

        assert "Unreadable: none" in _block(output, "Population")

    def test_the_instruments_are_listed_with_the_population_each_holds(
        self, tmp_path: Path
    ) -> None:
        _, output = _run(_project(tmp_path))
        instruments = _block(output, "Instruments")

        for name in ("packaging-manifest", "docs-audit", "graph-summary-facts", "doctor"):
            assert name in instruments

    def test_an_instrument_the_project_declares_nothing_for_carries_its_reason(
        self, tmp_path: Path
    ) -> None:
        project = tmp_path / "bare"
        project.mkdir()
        _write(project, "pyproject.toml", f'[project]\nname = "w"\nversion = "{_VERSION}"\n')

        _, output = _run(project)
        instruments = _block(output, "Instruments")

        assert "NOT RESOLVED" in instruments

    def test_the_limit_of_the_sweep_is_stated_with_the_literal_it_swept_for(
        self, tmp_path: Path
    ) -> None:
        _, output = _run(_project(tmp_path))

        assert "current literal" in output
        assert "before the bump" in output


class TestAVersionThatCannotBeDerived:
    """An empty answer and an empty answer with a reason are different answers."""

    def test_it_exits_two_with_the_reason_on_standard_output(self, tmp_path: Path) -> None:
        project = tmp_path / "bare"
        project.mkdir()
        _write(project, "pyproject.toml", '[project]\nname = "widget"\n')

        code, output = _run(project)

        assert code == 2
        assert "NOT DERIVED" in output
        assert "declares no version" in output

    def test_it_does_not_print_a_population_it_never_swept(self, tmp_path: Path) -> None:
        project = tmp_path / "bare"
        project.mkdir()
        _write(project, "pyproject.toml", '[project]\nname = "widget"\n')

        _, output = _run(project)

        assert "Population" not in output


class TestTheJsonPayload:
    """The same facts, in the shape a release script reads."""

    def test_every_place_carries_its_line_its_checkers_and_its_reason(
        self, tmp_path: Path
    ) -> None:
        _, output = _run(_project(tmp_path), "--json")
        payload = json.loads(output)

        guide = next(p for p in payload["places"] if p["path"] == "docs/getting-started.md")
        assert guide["line"] == 5
        assert guide["checkers"] == ["docs-audit"]
        assert guide["reason"]

    def test_the_gap_is_its_own_key_rather_than_a_filter_the_caller_repeats(
        self, tmp_path: Path
    ) -> None:
        _, output = _run(_project(tmp_path), "--json")
        payload = json.loads(output)

        assert [p["path"] for p in payload["unchecked"]] == ["CHANGELOG.md"]

    def test_it_carries_the_source_of_truth_the_instruments_and_the_population(
        self, tmp_path: Path
    ) -> None:
        _, output = _run(_project(tmp_path), "--json")
        payload = json.loads(output)

        assert payload["source_of_truth"]["value"] == _VERSION
        assert {i["name"] for i in payload["instruments"]} >= {"docs-audit", "doctor"}
        assert payload["population"]["files_read"] >= 3

    def test_a_project_with_no_derivable_version_answers_the_reason_in_json_too(
        self, tmp_path: Path
    ) -> None:
        project = tmp_path / "bare"
        project.mkdir()
        _write(project, "pyproject.toml", '[project]\nname = "widget"\n')

        code, output = _run(project, "--json")
        payload = json.loads(output)

        assert code == 2
        assert payload["source_of_truth"] is None
        assert "declares no version" in payload["unresolved"]


@pytest.fixture(scope="module")
def repository_report() -> Iterator[str]:
    """One sweep of this repository, shared — it reads over a thousand files."""
    _, output = _run(REPO_ROOT)
    yield output


class TestTheNinePlacesTheReleaseHadToEdit:
    """The answer, checked against what cutting 4.0.0 actually edited.

    Commit ``f3b5593e`` is the record: nine files carrying a version literal that
    had to move, plus ``.beads/issues.jsonl``, which is the tracker's own export
    and is pruned by the sweep because no release edits it by hand.
    """

    @pytest.mark.parametrize(
        ("relative", "checker"),
        [
            ("src/beadloom/__init__.py", "packaging-manifest"),
            (".beadloom/_graph/beadloom.yml", "graph-summary-facts"),
            (".claude/CLAUDE.md", "doctor"),
            ("docs/getting-started.md", "docs-audit"),
            ("docs/services/cli.md", "docs-audit"),
            ("tests/test_integration_v1.py", "test-suite"),
        ],
    )
    def test_a_place_an_instrument_holds_is_reported_under_that_instrument(
        self, repository_report: str, relative: str, checker: str
    ) -> None:
        checked = _block(repository_report, "Checked (")

        assert relative in checked, checked
        group = next(line for line in checked.splitlines() if relative in line)
        assert checker in group, group

    @pytest.mark.parametrize(
        "relative",
        [
            "CHANGELOG.md",
            ".claude/development/ROADMAP.md",
            "docs/domains/doc-sync/features/docs-audit/SPEC.md",
        ],
    )
    def test_a_place_the_release_met_one_at_a_time_is_reported_as_checked_by_nothing(
        self, repository_report: str, relative: str
    ) -> None:
        assert relative in _block(repository_report, "Checked by nothing"), repository_report

    def test_the_tracker_export_is_not_a_place_because_no_release_edits_it(
        self, repository_report: str
    ) -> None:
        assert ".beads/issues.jsonl" not in repository_report
