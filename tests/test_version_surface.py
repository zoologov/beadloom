"""BDL-069 S3 (``beadloom-w4cd``) — every place this project states its version.

The measurement this module is built against was taken on 2026-09-10, cutting
the release that preceded this epic (BDL-UX #281): the version is stated in nine
places, judged by four
instruments over disjoint populations, and three of the nine by nothing. The
list was first derived BY HAND and was wrong by two — ``docs audit`` reported a
line in ``docs/services/cli.md`` its own author had classified as an example
rather than a claim, and grepping for its twin found the same sentence in a
document no check reads.

So the binding test here is :class:`TestThisRepositoryIsFoundByDerivation`: the
nine are asserted as an expectation of the DERIVATION, and no path of the nine
appears in the module's source. :meth:`TestTheDerivationHoldsNoList` is what
checks the second half, by parsing the module and stripping its docstrings.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from beadloom.doc_sync.version_surface import (
    DOCS_AUDIT,
    DOCTOR,
    GRAPH_SUMMARY_FACTS,
    PACKAGING_MANIFEST,
    TEST_SUITE,
    VersionSurface,
    read_version_surface,
)

REPO_ROOT = Path(__file__).resolve().parent.parent


def _manifest(root: Path, *, dynamic: bool = True, version: str = "1.2.3") -> None:
    """A project whose manifest declares *version*, statically or through hatch."""
    if dynamic:
        body = (
            '[project]\nname = "widget"\ndynamic = ["version"]\n\n'
            '[tool.hatch.version]\npath = "src/widget/__init__.py"\n'
        )
        package = root / "src" / "widget"
        package.mkdir(parents=True, exist_ok=True)
        (package / "__init__.py").write_text(
            f'"""Widget."""\n\n__version__ = "{version}"\n', encoding="utf-8"
        )
    else:
        body = f'[project]\nname = "widget"\nversion = "{version}"\n'
    (root / "pyproject.toml").write_text(body, encoding="utf-8")


def _write(root: Path, relative: str, text: str) -> Path:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _place(surface: VersionSurface, relative: str) -> list[object]:
    wanted = Path(relative)
    return [place for place in surface.places if place.path == wanted]


def _one(surface: VersionSurface, relative: str) -> object:
    found = _place(surface, relative)
    assert len(found) == 1, f"{relative}: {found}"
    return found[0]


class TestTheSourceOfTruth:
    """The version is taken from the manifest, and an unreadable one says so."""

    def test_a_dynamic_version_is_followed_to_the_file_that_assigns_it(
        self, tmp_path: Path
    ) -> None:
        _manifest(tmp_path, version="7.3.1")

        surface = read_version_surface(tmp_path)

        assert surface.source_of_truth is not None
        assert surface.source_of_truth.value == "7.3.1"
        assert surface.source_of_truth.path == Path("src/widget/__init__.py")
        assert surface.source_of_truth.line == 3
        assert "hatch" in surface.source_of_truth.derived_from

    def test_a_static_version_is_the_manifest_line_itself(self, tmp_path: Path) -> None:
        _manifest(tmp_path, dynamic=False, version="2.5.1")

        surface = read_version_surface(tmp_path)

        assert surface.source_of_truth is not None
        assert surface.source_of_truth.value == "2.5.1"
        assert surface.source_of_truth.path == Path("pyproject.toml")

    def test_the_manifest_place_carries_the_packaging_instrument(self, tmp_path: Path) -> None:
        _manifest(tmp_path, version="7.3.1")

        surface = read_version_surface(tmp_path)

        assert _one(surface, "src/widget/__init__.py").checkers == (PACKAGING_MANIFEST,)

    def test_a_project_declaring_no_version_answers_a_reason_not_an_empty_list(
        self, tmp_path: Path
    ) -> None:
        (tmp_path / "pyproject.toml").write_text('[project]\nname = "widget"\n', "utf-8")

        surface = read_version_surface(tmp_path)

        assert surface.source_of_truth is None
        assert surface.places == ()
        assert "declares no version" in surface.unresolved

    def test_a_dynamic_version_whose_file_is_missing_is_unresolved_with_the_path(
        self, tmp_path: Path
    ) -> None:
        (tmp_path / "pyproject.toml").write_text(
            '[project]\nname = "widget"\ndynamic = ["version"]\n\n'
            '[tool.hatch.version]\npath = "src/widget/__init__.py"\n',
            encoding="utf-8",
        )

        surface = read_version_surface(tmp_path)

        assert surface.source_of_truth is None
        assert "src/widget/__init__.py" in surface.unresolved


class TestTheDocsAuditPopulation:
    """The audit's population is the audit's own surface, reasons included."""

    def test_a_document_the_audit_reads_carries_the_audit_as_its_checker(
        self, tmp_path: Path
    ) -> None:
        _manifest(tmp_path, version="7.3.1")
        _write(tmp_path, "docs/getting-started.md", "The current release is 7.3.1.\n")

        surface = read_version_surface(tmp_path)

        assert _one(surface, "docs/getting-started.md").checkers == (DOCS_AUDIT,)

    def test_a_document_the_audit_excludes_carries_the_audits_own_reason(
        self, tmp_path: Path
    ) -> None:
        _manifest(tmp_path, version="7.3.1")
        _write(tmp_path, "CHANGELOG.md", "## [7.3.1] - 2026-09-10\n")

        place = _one(read_version_surface(tmp_path), "CHANGELOG.md")

        assert place.checkers == ()
        assert "CHANGELOG.md is excluded by default" in place.reason

    def test_a_spec_under_the_built_in_exclude_pattern_is_checked_by_nothing(
        self, tmp_path: Path
    ) -> None:
        _manifest(tmp_path, version="7.3.1")
        _write(
            tmp_path,
            "docs/domains/doc-sync/features/docs-audit/SPEC.md",
            "| `The current release is 7.3.1` | none | this project's version |\n",
        )

        place = _one(
            read_version_surface(tmp_path),
            "docs/domains/doc-sync/features/docs-audit/SPEC.md",
        )

        assert place.checkers == ()
        assert "exclude pattern" in place.reason

    def test_a_token_the_audit_attributes_to_another_subject_is_not_ours(
        self, tmp_path: Path
    ) -> None:
        _manifest(tmp_path, version="1.0.4")
        _write(tmp_path, ".beadloom/config.yml", "docs_audit:\n  subjects:\n    - bd\n")
        _write(tmp_path, "docs/guides/tracker.md", "Measured on bd 1.0.4.\n")

        place = _one(read_version_surface(tmp_path), "docs/guides/tracker.md")

        assert place.checkers == ()
        assert "bd" in place.reason

    def test_a_line_outside_every_scan_glob_says_so(self, tmp_path: Path) -> None:
        _manifest(tmp_path, version="7.3.1")
        _write(tmp_path, ".claude/development/ROADMAP.md", "> **Current version: 7.3.1**\n")

        place = _one(read_version_surface(tmp_path), ".claude/development/ROADMAP.md")

        assert place.checkers == ()
        assert "scan glob" in place.reason


class TestTheGraphSummaryPopulation:
    """A node summary is judged only where the project declares the rule."""

    def _graph(self, root: Path, *, declared: bool) -> None:
        _write(
            root,
            ".beadloom/_graph/widget.yml",
            'nodes:\n  - ref_id: widget\n    summary: "Widget CLI (v7.3.1)"\n',
        )
        rules = "version: 3\nrules:\n"
        if declared:
            rules += "  - name: graph-summary-facts\n    severity: error\n    summary_facts: {}\n"
        else:
            rules += "  - name: domain-needs-parent\n"
        _write(root, ".beadloom/_graph/rules.yml", rules)

    def test_a_declared_rule_names_itself_and_its_severity(self, tmp_path: Path) -> None:
        _manifest(tmp_path, version="7.3.1")
        self._graph(tmp_path, declared=True)

        place = _one(read_version_surface(tmp_path), ".beadloom/_graph/widget.yml")

        assert place.checkers == (GRAPH_SUMMARY_FACTS,)
        assert "error" in place.reason

    def test_an_undeclared_rule_leaves_the_summary_checked_by_nothing(
        self, tmp_path: Path
    ) -> None:
        _manifest(tmp_path, version="7.3.1")
        self._graph(tmp_path, declared=False)

        place = _one(read_version_surface(tmp_path), ".beadloom/_graph/widget.yml")

        assert place.checkers == ()
        assert "not declared" in place.reason

    def test_a_version_beside_a_node_rather_than_in_its_summary_is_not_judged(
        self, tmp_path: Path
    ) -> None:
        _manifest(tmp_path, version="7.3.1")
        self._graph(tmp_path, declared=True)
        _write(
            tmp_path,
            ".beadloom/_graph/other.yml",
            '# written for 7.3.1\nnodes:\n  - ref_id: other\n    summary: "Other"\n',
        )

        place = _one(read_version_surface(tmp_path), ".beadloom/_graph/other.yml")

        assert place.checkers == ()
        assert "summary" in place.reason


class TestTheTestSuitePopulation:
    """A literal the suite asserts is checked; one it merely prints is not."""

    def test_an_assert_under_testpaths_is_checked_by_the_suite(self, tmp_path: Path) -> None:
        _manifest(tmp_path, version="7.3.1")
        (tmp_path / "pyproject.toml").write_text(
            (tmp_path / "pyproject.toml").read_text(encoding="utf-8")
            + '\n[tool.pytest.ini_options]\ntestpaths = ["tests"]\n',
            encoding="utf-8",
        )
        _write(
            tmp_path,
            "tests/test_release.py",
            "from widget import __version__\n\n\ndef test_it() -> None:\n"
            '    assert __version__ == "7.3.1"\n',
        )

        place = _one(read_version_surface(tmp_path), "tests/test_release.py")

        assert place.checkers == (TEST_SUITE,)

    def test_a_docstring_under_testpaths_is_checked_by_nothing(self, tmp_path: Path) -> None:
        _manifest(tmp_path, version="7.3.1")
        (tmp_path / "pyproject.toml").write_text(
            (tmp_path / "pyproject.toml").read_text(encoding="utf-8")
            + '\n[tool.pytest.ini_options]\ntestpaths = ["tests"]\n',
            encoding="utf-8",
        )
        _write(
            tmp_path,
            "tests/test_note.py",
            '"""Measured on the published 7.3.1 wheel."""\n',
        )

        place = _one(read_version_surface(tmp_path), "tests/test_note.py")

        assert place.checkers == ()
        assert "assert" in place.reason

    def test_a_python_file_outside_testpaths_is_checked_by_nothing(self, tmp_path: Path) -> None:
        _manifest(tmp_path, version="7.3.1")
        _write(tmp_path, "src/widget/notes.py", '"""Shipped in 7.3.1."""\n')

        place = _one(read_version_surface(tmp_path), "src/widget/notes.py")

        assert place.checkers == ()
        assert "testpaths" in place.reason


class TestTheDoctorPopulation:
    """The agent-instruction claim is the auto-region, not the whole file."""

    def _adapter(self, root: Path, body: str) -> None:
        _write(root, ".claude/CLAUDE.md", body)
        _write(
            root,
            ".beadloom/flow-manifest.json",
            '{"version": 1, "written": {".claude/CLAUDE.md": "abc"}}',
        )

    def test_a_claim_inside_the_project_info_region_is_checked_by_doctor(
        self, tmp_path: Path
    ) -> None:
        _manifest(tmp_path, version="7.3.1")
        self._adapter(
            tmp_path,
            "# Core\n\n<!-- beadloom:auto-start project-info -->\n"
            "- **Current version:** 7.3.1\n<!-- beadloom:auto-end -->\n",
        )

        place = _one(read_version_surface(tmp_path), ".claude/CLAUDE.md")

        assert place.checkers == (DOCTOR,)

    def test_prose_outside_the_region_in_the_same_file_is_checked_by_nothing(
        self, tmp_path: Path
    ) -> None:
        _manifest(tmp_path, version="7.3.1")
        self._adapter(
            tmp_path,
            "# Core\n\n<!-- beadloom:auto-start project-info -->\n"
            "- **Current version:** 7.3.1\n<!-- beadloom:auto-end -->\n\n"
            "The gap is closed as of 7.3.1.\n",
        )

        places = _place(read_version_surface(tmp_path), ".claude/CLAUDE.md")

        assert [place.checkers for place in places] == [(DOCTOR,), ()]
        assert "project-info" in places[1].reason

    def test_an_adapter_the_flow_manifest_does_not_record_is_checked_by_nothing(
        self, tmp_path: Path
    ) -> None:
        _manifest(tmp_path, version="7.3.1")
        _write(
            tmp_path,
            ".beadloom/flow/claude/CLAUDE.md",
            "<!-- beadloom:auto-start project-info -->\n"
            "- **Current version:** 7.3.1\n<!-- beadloom:auto-end -->\n",
        )

        place = _one(read_version_surface(tmp_path), ".beadloom/flow/claude/CLAUDE.md")

        assert place.checkers == ()


class TestThePopulationItSearched:
    """A sweep that does not say what it skipped is a list with a clean face."""

    def test_the_kinds_it_did_not_read_are_counted_by_suffix(self, tmp_path: Path) -> None:
        _manifest(tmp_path, version="7.3.1")
        _write(tmp_path, "package-lock.json", '{"widget": "7.3.1"}')
        _write(tmp_path, "notes.html", "<p>7.3.1</p>\n")

        population = read_version_surface(tmp_path).population

        assert dict(population.not_read)[".json"] == 1
        assert dict(population.not_read)[".html"] == 1
        assert _place(read_version_surface(tmp_path), "package-lock.json") == []

    def test_a_skipped_directory_is_named_and_its_files_are_not_places(
        self, tmp_path: Path
    ) -> None:
        _manifest(tmp_path, version="7.3.1")
        _write(tmp_path, ".venv/lib/widget.py", '__version__ = "7.3.1"\n')

        surface = read_version_surface(tmp_path)

        assert _place(surface, ".venv/lib/widget.py") == []
        assert ".venv" in surface.population.directories_skipped

    def test_a_file_it_could_not_decode_is_reported_with_its_reason(self, tmp_path: Path) -> None:
        _manifest(tmp_path, version="7.3.1")
        (tmp_path / "broken.md").write_bytes(b"\xff\xfe not text 7.3.1")

        population = read_version_surface(tmp_path).population

        assert [str(path) for path, _ in population.unreadable] == ["broken.md"]

    def test_it_counts_the_files_it_read(self, tmp_path: Path) -> None:
        _manifest(tmp_path, version="7.3.1")

        population = read_version_surface(tmp_path).population

        assert population.files_read == 2  # pyproject.toml + src/widget/__init__.py

    def test_every_instrument_states_the_population_it_holds(self, tmp_path: Path) -> None:
        _manifest(tmp_path, version="7.3.1")

        instruments = read_version_surface(tmp_path).instruments

        assert {instrument.name for instrument in instruments} == {
            PACKAGING_MANIFEST,
            DOCS_AUDIT,
            GRAPH_SUMMARY_FACTS,
            DOCTOR,
            TEST_SUITE,
        }
        assert all(instrument.population for instrument in instruments)
        assert all(instrument.resolved or instrument.reason for instrument in instruments)


class TestEveryPlaceIsAnswerable:
    """A place with no reason is a row a reader cannot act on."""

    def test_a_token_inside_a_longer_number_is_not_a_place(self, tmp_path: Path) -> None:
        _manifest(tmp_path, version="7.3.1")
        _write(tmp_path, "docs/sizes.md", "The file is 17.3.111 megabytes.\n")

        assert _place(read_version_surface(tmp_path), "docs/sizes.md") == []

    def test_every_place_carries_a_reason_and_an_excerpt(self, tmp_path: Path) -> None:
        _manifest(tmp_path, version="7.3.1")
        _write(tmp_path, "docs/getting-started.md", "The current release is 7.3.1.\n")
        _write(tmp_path, "CHANGELOG.md", "## [7.3.1] - 2026-09-10\n")

        for place in read_version_surface(tmp_path).places:
            assert place.reason, place
            assert place.excerpt, place
            assert place.line > 0, place

    def test_the_unchecked_projection_is_the_places_no_instrument_holds(
        self, tmp_path: Path
    ) -> None:
        _manifest(tmp_path, version="7.3.1")
        _write(tmp_path, "CHANGELOG.md", "## [7.3.1] - 2026-09-10\n")

        surface = read_version_surface(tmp_path)

        assert [place.path for place in surface.unchecked] == [Path("CHANGELOG.md")]

    def test_places_are_ordered_by_path_then_line(self, tmp_path: Path) -> None:
        _manifest(tmp_path, version="7.3.1")
        _write(tmp_path, "docs/b.md", "7.3.1\n")
        _write(tmp_path, "docs/a.md", "7.3.1\n\n7.3.1\n")

        surface = read_version_surface(tmp_path)

        assert [(str(p.path), p.line) for p in surface.places] == [
            ("docs/a.md", 1),
            ("docs/a.md", 3),
            ("docs/b.md", 1),
            ("src/widget/__init__.py", 3),
        ]


class TestTheDerivationHoldsNoList:
    """The places are derived. A list of them in the source is the defect."""

    def test_the_module_names_none_of_the_places_it_must_find(self) -> None:
        source = (REPO_ROOT / "src" / "beadloom" / "doc_sync" / "version_surface.py").read_text(
            encoding="utf-8"
        )
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef)):
                first = node.body[0] if node.body else None
                if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant):
                    first.value.value = ""
        code = ast.unparse(tree)

        for place in (
            "CHANGELOG",
            "ROADMAP",
            "getting-started",
            "cli.md",
            "SPEC.md",
            "test_integration_v1",
            "beadloom.yml",
        ):
            assert place not in code, f"the source names the place {place!r}"


@pytest.fixture(scope="module")
def surface() -> VersionSurface:
    """This repository's own surface, read once for the class below."""
    return read_version_surface(REPO_ROOT)


@pytest.mark.skipif(
    not (REPO_ROOT / "src" / "beadloom" / "__init__.py").is_file(),
    reason="the nine places are this repository's own measurement",
)
class TestThisRepositoryIsFoundByDerivation:
    """The nine of 2026-09-10, found without any of them being written down.

    The count is the floor and not the ceiling: this epic's own waves 1 and 2
    added documents stating the current release, and the command is the answer
    to the question the hand-written list of nine kept getting wrong.

    The fixture projects above declare a version of their own for a reason. A
    fixture that happened to equal this project's real one put 50 rows of its
    own data into the first run of the command it feeds, which is the limit the
    module states wearing a different coat: a literal used as data and a literal
    used as a statement are told apart by no structure either of them carries.
    """

    def test_the_source_of_truth_is_this_project_s_own_manifest_chain(
        self, surface: VersionSurface
    ) -> None:
        assert surface.source_of_truth is not None
        assert surface.source_of_truth.path == Path("src/beadloom/__init__.py")

    @pytest.mark.parametrize(
        ("relative", "checkers"),
        [
            ("src/beadloom/__init__.py", (PACKAGING_MANIFEST,)),
            (".beadloom/_graph/beadloom.yml", (GRAPH_SUMMARY_FACTS,)),
            (".claude/CLAUDE.md", (DOCTOR,)),
            ("docs/getting-started.md", (DOCS_AUDIT,)),
            ("docs/services/cli.md", (DOCS_AUDIT,)),
            ("tests/test_integration_v1.py", (TEST_SUITE,)),
            ("CHANGELOG.md", ()),
            (".claude/development/ROADMAP.md", ()),
            ("docs/domains/doc-sync/features/docs-audit/SPEC.md", ()),
        ],
    )
    def test_each_of_the_nine_is_found_with_its_checker(
        self, surface: VersionSurface, relative: str, checkers: tuple[str, ...]
    ) -> None:
        found = _place(surface, relative)

        assert found, f"{relative} was not derived"
        assert checkers in {place.checkers for place in found}

    def test_the_three_nothing_checks_are_named_as_such(self, surface: VersionSurface) -> None:
        unchecked = {str(place.path) for place in surface.unchecked}

        assert {
            "CHANGELOG.md",
            ".claude/development/ROADMAP.md",
            "docs/domains/doc-sync/features/docs-audit/SPEC.md",
        } <= unchecked

    def test_it_reports_the_population_it_swept(self, surface: VersionSurface) -> None:
        assert surface.population.files_read > 100
        assert surface.population.not_read
