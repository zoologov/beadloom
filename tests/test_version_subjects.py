"""The subject vocabulary a version token can be attributed to (BDL-UX #253).

BDL-068 S6, `beadloom-0mdo.63`. The unit level of what
`tests/acceptance/features/version_subject.feature` states as behaviour: where
each name in the vocabulary comes from, and which names must never enter it.

The over-collection cases are the ones that matter most. A stray word in the
vocabulary silences every version standing beside it, which is a false NEGATIVE
-- the outcome `scanner.py`'s own design notes call worse than a false positive
-- and the first draft of this module put the word ``an`` into this repository's
own vocabulary by reading a TOML comment's apostrophes as a quoted string.
"""

from __future__ import annotations

from pathlib import Path

from beadloom.doc_sync.scanner import DocScanner
from beadloom.doc_sync.version_subjects import (
    VersionSubjects,
    derive_version_subjects,
)


def _project(root: Path, pyproject: str) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    (root / "pyproject.toml").write_text(pyproject, encoding="utf-8")
    return root


class TestWhatEntersTheVocabulary:
    """Every name the derivation admits, and the source that admitted it."""

    def test_a_declared_dependency_is_a_subject(self, tmp_path: Path) -> None:
        root = _project(
            tmp_path / "p",
            '[project]\nname = "svc"\ndependencies = ["click>=8.1", "rich"]\n',
        )
        subjects = derive_version_subjects(root)
        assert "click" in subjects.names
        assert "rich" in subjects.names

    def test_an_optional_dependency_is_a_subject(self, tmp_path: Path) -> None:
        root = _project(
            tmp_path / "p",
            '[project]\nname = "svc"\n\n'
            "[project.optional-dependencies]\n"
            'watch = ["watchfiles>=0.20"]\n',
        )
        assert "watchfiles" in derive_version_subjects(root).names

    def test_a_dependency_group_is_a_subject(self, tmp_path: Path) -> None:
        root = _project(
            tmp_path / "p",
            '[project]\nname = "svc"\n\n'
            "[dependency-groups]\n"
            'dev = ["pytest>=8", "mypy"]\n',
        )
        names = derive_version_subjects(root).names
        assert {"pytest", "mypy"} <= names

    def test_requires_python_names_the_interpreter_family(
        self, tmp_path: Path
    ) -> None:
        root = _project(
            tmp_path / "p",
            '[project]\nname = "svc"\nrequires-python = ">=3.10"\n',
        )
        names = derive_version_subjects(root).names
        assert {"python", "cpython", "pypy"} <= names

    def test_a_git_repository_names_git(self, tmp_path: Path) -> None:
        root = _project(tmp_path / "p", '[project]\nname = "svc"\n')
        (root / ".git").mkdir()
        subjects = derive_version_subjects(root)
        assert "git" in subjects.names
        assert ("git", "the project is a git repository") in subjects.origins

    def test_a_configured_subject_needs_no_manifest(self, tmp_path: Path) -> None:
        root = _project(tmp_path / "p", '[project]\nname = "svc"\n')
        (root / ".beadloom").mkdir()
        (root / ".beadloom" / "config.yml").write_text(
            "docs_audit:\n  subjects:\n    - bd\n    - PostgreSQL\n",
            encoding="utf-8",
        )
        subjects = derive_version_subjects(root)
        assert {"bd", "postgresql"} <= subjects.names
        assert ("bd", "docs_audit.subjects") in subjects.origins

    def test_a_package_json_declares_dependencies_and_its_runtime(
        self, tmp_path: Path
    ) -> None:
        root = tmp_path / "p"
        root.mkdir()
        (root / "package.json").write_text(
            '{"name": "web", "dependencies": {"react": "^18.0.0"},'
            ' "engines": {"node": ">=20"}}',
            encoding="utf-8",
        )
        names = derive_version_subjects(root).names
        assert {"react", "node", "nodejs"} <= names

    def test_a_cargo_manifest_declares_crates_and_its_toolchain(
        self, tmp_path: Path
    ) -> None:
        root = tmp_path / "p"
        root.mkdir()
        (root / "Cargo.toml").write_text(
            '[package]\nname = "svc"\nrust-version = "1.74"\n\n'
            '[dependencies]\nserde = "1.0"\n',
            encoding="utf-8",
        )
        names = derive_version_subjects(root).names
        assert {"serde", "rust", "rustc"} <= names


class TestWhatMustNeverEnterTheVocabulary:
    """A stray name silences a real claim, so over-collection is the defect."""

    def test_prose_in_a_comment_is_not_a_dependency(self, tmp_path: Path) -> None:
        """A comment inside a dependency array is prose, and prose has quotes.

        Measured on this repository's own manifest: reading the comment put the
        word ``an`` into the vocabulary, out of a quoted phrase, and would have
        silenced any version standing beside that word.
        """
        comment_with_quotes = '    # the rule ("an executable artifact cannot lie")'
        comment_with_apostrophes = "    # holds for the project's manifest, not the reader's"
        root = _project(
            tmp_path / "p",
            "[project]\n"
            'name = "svc"\n'
            "dependencies = [\n"
            f"{comment_with_quotes}\n"
            f"{comment_with_apostrophes}\n"
            '    "tree-sitter>=0.25",\n'
            "]\n",
        )
        names = derive_version_subjects(root).names
        assert names == frozenset({"tree-sitter"}), (
            "a comment's quoted prose and its apostrophes are not dependencies"
        )


    def test_keywords_and_classifiers_are_not_dependencies(
        self, tmp_path: Path
    ) -> None:
        root = _project(
            tmp_path / "p",
            "[project]\n"
            'name = "svc"\n'
            'keywords = ["documentation", "graph"]\n'
            'classifiers = ["Programming Language :: Python :: 3.10"]\n'
            'dependencies = ["click"]\n',
        )
        names = derive_version_subjects(root).names
        assert "click" in names
        assert "documentation" not in names
        assert "graph" not in names

    def test_the_project_never_cites_itself_as_another_product(
        self, tmp_path: Path
    ) -> None:
        root = _project(
            tmp_path / "p",
            '[project]\nname = "click"\ndependencies = ["click"]\n',
        )
        subjects = derive_version_subjects(root)
        assert "click" not in subjects.names
        assert "click" in subjects.project

    def test_a_project_with_no_manifest_declares_no_subject(
        self, tmp_path: Path
    ) -> None:
        """Nothing declared means nothing CONFIRMED, not nothing at all.

        ``git`` is still unresolved here: an empty directory cannot confirm a
        git tree and cannot deny one either (BDL-UX #266). The vocabulary a
        caller passes explicitly is the only genuinely empty one, and
        ``test_an_empty_vocabulary_attributes_nothing`` holds that case.
        """
        root = tmp_path / "p"
        root.mkdir()
        subjects = derive_version_subjects(root)
        assert subjects.names == frozenset()
        assert subjects.unresolved == frozenset({"git"})

    def test_an_unparsable_config_leaves_the_derivation_standing(
        self, tmp_path: Path
    ) -> None:
        root = _project(
            tmp_path / "p", '[project]\nname = "svc"\ndependencies = ["click"]\n'
        )
        (root / ".beadloom").mkdir()
        (root / ".beadloom" / "config.yml").write_text(
            "docs_audit:\n  subjects: not-a-list\n", encoding="utf-8"
        )
        assert "click" in derive_version_subjects(root).names


class TestWhichTokenAVersionIsGivenTo:
    """The walk: the nearest name to the left, inside the version's clause."""

    SUBJECTS = VersionSubjects(
        names=frozenset({"bd", "git", "cpython"}),
        project=frozenset({"beadloom"}),
    )

    def _scan(self, line: str) -> list[tuple[str, str | None]]:
        scanner = DocScanner(self.SUBJECTS)
        return [
            (str(m.value), m.subject)
            for m in scanner.scan_line(line, origin=Path("doc.md"))
            if m.fact_name == "version"
        ]

    def test_the_name_beside_the_number_owns_it(self) -> None:
        assert self._scan("Measured on bd 1.0.4 in an isolated rig.") == [
            ("1.0.4", "bd")
        ]

    def test_markdown_emphasis_around_the_name_is_stripped(self) -> None:
        assert self._scan("Measured against **bd 1.0.4**:") == [("1.0.4", "bd")]

    def test_a_version_with_no_name_beside_it_stays_this_projects(self) -> None:
        assert self._scan("The current release is 3.1.0.") == [("3.1.0", None)]

    def test_a_name_the_project_never_declared_is_not_a_subject(self) -> None:
        assert self._scan("The rig ran on PostgreSQL 16.2.1.") == [
            ("16.2.1", None)
        ]

    def test_each_number_goes_to_the_name_beside_it(self) -> None:
        """The project's own name stops the walk as firmly as a foreign one.

        The foreign name is placed to the LEFT of the project's here on
        purpose. With the two the other way round the assertion passes whether
        or not the walk stops at ``beadloom``, because the walk would find no
        foreign name to its left either way -- a scenario that cannot fail is
        not a check.
        """
        assert self._scan("bd 1.0.4 answers and beadloom 3.1.0 asks.") == [
            ("1.0.4", "bd"),
            ("3.1.0", None),
        ]

    def test_a_name_beyond_a_clause_separator_does_not_reach(self) -> None:
        line = "`BD_MEASURED_VERSION` names bd, and the release is `1.0.4`."
        assert self._scan(line) == [("1.0.4", None)]

    def test_an_empty_vocabulary_attributes_nothing(self) -> None:
        scanner = DocScanner()
        found = scanner.scan_line(
            "Measured on bd 1.0.4.", origin=Path("doc.md")
        )
        assert [(str(m.value), m.subject) for m in found] == [("1.0.4", None)]


class TestASourceTheEnvironmentCannotConfirm:
    """A probe of the environment answers "yes" or "cannot tell", never "no".

    BDL-068 S6, `beadloom-0mdo.81`, closing BDL-UX #266. ``git`` entered the
    vocabulary from ``(project_root / ".git").exists()``, and the absent case
    was read as the assertion that this project has nothing to do with git. A
    directory built by ``git archive HEAD`` carries no ``.git`` by
    construction, so the derivation answered "no" to a question it could not
    see -- and every clean-room Gate run on this repository was rc 1 for one
    line reading "Measured on git 2.49.0".
    """

    def test_a_git_repository_resolves_git(self, tmp_path: Path) -> None:
        root = _project(tmp_path / "p", '[project]\nname = "svc"\n')
        (root / ".git").mkdir()
        subjects = derive_version_subjects(root)
        assert "git" in subjects.names
        assert "git" not in subjects.unresolved

    def test_no_git_leaves_git_unresolved_rather_than_absent(
        self, tmp_path: Path
    ) -> None:
        root = _project(tmp_path / "p", '[project]\nname = "svc"\n')
        subjects = derive_version_subjects(root)
        assert "git" in subjects.unresolved
        assert "git" not in subjects.names

    def test_an_unresolved_name_carries_the_reason_it_is_unresolved(
        self, tmp_path: Path
    ) -> None:
        root = _project(tmp_path / "p", '[project]\nname = "svc"\n')
        reasons = dict(derive_version_subjects(root).unresolved_origins)
        assert ".git" in reasons["git"]

    def test_a_declared_subject_resolves_what_the_environment_cannot(
        self, tmp_path: Path
    ) -> None:
        """A project that names ``git`` itself has answered the question."""
        root = _project(tmp_path / "p", '[project]\nname = "svc"\n')
        (root / ".beadloom").mkdir()
        (root / ".beadloom" / "config.yml").write_text(
            "docs_audit:\n  subjects:\n    - git\n", encoding="utf-8"
        )
        subjects = derive_version_subjects(root)
        assert "git" in subjects.names
        assert "git" not in subjects.unresolved

    def test_a_project_named_git_never_becomes_its_own_foreign_subject(
        self, tmp_path: Path
    ) -> None:
        root = _project(tmp_path / "p", '[project]\nname = "git"\n')
        subjects = derive_version_subjects(root)
        assert "git" not in subjects.names
        assert "git" not in subjects.unresolved

    def test_an_unresolved_name_alone_is_still_a_vocabulary(self) -> None:
        """``__bool__`` gates the whole attribution walk in the scanner.

        A vocabulary holding only unresolved names must not read as empty, or
        the walk returns ``None`` and the token is judged against this project
        -- which is the defect verbatim.
        """
        assert bool(VersionSubjects(unresolved=frozenset({"git"})))

    def test_an_unresolved_name_is_still_the_subject_beside_the_number(
        self,
    ) -> None:
        scanner = DocScanner(
            VersionSubjects(
                names=frozenset({"bd"}),
                project=frozenset({"beadloom"}),
                unresolved=frozenset({"git"}),
            )
        )
        found = [
            (str(m.value), m.subject)
            for m in scanner.scan_line(
                "Measured on git 2.49.0.", origin=Path("doc.md")
            )
            if m.fact_name == "version"
        ]
        assert found == [("2.49.0", "git")]
