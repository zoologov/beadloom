"""Whether a ``to:`` glob can match an import path at all (BDL-083 D2, BDL-UX #328).

The verdict is decided by the matcher the rule fires with,
:func:`~beadloom.graph.rules.types.matches_import_target`, run on a path built from the
glob — never by a second reading of the glob. That is the property #328 was missing:
liveness counted ``fnmatch('os', 'os/**') == False`` while the matcher's appended "/"
fired ``os/**`` on ``import os``.
"""

from __future__ import annotations

import pytest

from beadloom.graph.rules.import_glob import source_roots, to_glob_reach
from beadloom.graph.rules.types import matches_import_target


class TestAGlobThatCanMatch:
    @pytest.mark.parametrize(
        ("glob", "example"),
        [
            pytest.param("os/**", "os", id="package glob covers the bare module"),
            pytest.param("bcrypt*", "bcrypt", id="trailing star"),
            pytest.param("bcrypt/**", "bcrypt", id="package glob of a library"),
            pytest.param("pkg/infrastructure/**", "pkg/infrastructure", id="a layer"),
            pytest.param("pkg/infrastructure/db", "pkg/infrastructure/db", id="literal"),
        ],
    )
    def test_the_example_is_the_literal_prefix_the_matcher_accepts(
        self, glob: str, example: str
    ) -> None:
        reach = to_glob_reach(glob, source_roots=frozenset())

        assert (reach.example, reach.unmatchable) == (example, None)

    @pytest.mark.parametrize(
        "glob",
        ["**/infrastructure/**", "os/*/path", "[!a]*", "pkg/[a-c]ore/**", "?s"],
    )
    def test_a_glob_whose_prefix_alone_does_not_match_is_filled_in(self, glob: str) -> None:
        reach = to_glob_reach(glob, source_roots=frozenset())

        assert reach.unmatchable is None
        assert reach.example is not None

    @pytest.mark.parametrize(
        "glob",
        ["os/**", "bcrypt*", "**/infrastructure/**", "os/*/path", "[!a]*", "?s", "x/[b-d]"],
    )
    def test_the_matcher_itself_accepts_every_example(self, glob: str) -> None:
        reach = to_glob_reach(glob, source_roots=frozenset())

        assert reach.example is not None
        assert matches_import_target(reach.example, glob)


class TestAGlobThatCannotMatch:
    def test_a_glob_beginning_with_a_source_root_names_it(self) -> None:
        reach = to_glob_reach("src/pkg/infrastructure/**", source_roots=frozenset({"src"}))

        assert reach.example is None
        assert reach.unmatchable is not None
        assert "begins with 'src'" in reach.unmatchable

    def test_the_source_root_reason_says_it_is_inferred_from_the_index(self) -> None:
        """S1R Minor 4 (``beadloom-7kas``): a source root is an inference, and says so.

        A directory no indexed import begins with can still be an importable package —
        ``tests`` on a project that scans it and imports nothing from it — so the sentence
        names what it rests on and the one import that would prove it wrong.
        """
        reach = to_glob_reach("tests/**", source_roots=frozenset({"tests"}))

        assert reach.unmatchable is not None
        assert "inferred from the index" in reach.unmatchable
        assert "an importable package named 'tests' would still fire it" in reach.unmatchable

    def test_a_glob_that_is_the_source_root_itself_names_it(self) -> None:
        reach = to_glob_reach("backend", source_roots=frozenset({"backend"}))

        assert reach.unmatchable is not None
        assert "begins with 'backend'" in reach.unmatchable

    def test_a_partial_first_segment_is_not_a_source_root(self) -> None:
        """``sr*`` does not name the directory ``src``: it is not judged by the root."""
        reach = to_glob_reach("sr*/x/**", source_roots=frozenset({"src"}))

        assert reach.unmatchable is None

    @pytest.mark.parametrize("glob", ["pkg.infrastructure.*", "pkg/db.py", "os.path"])
    def test_a_dot_in_the_glob_never_matches_an_import_path(self, glob: str) -> None:
        reach = to_glob_reach(glob, source_roots=frozenset())

        assert reach.example is None
        assert reach.unmatchable is not None
        assert "'.'" in reach.unmatchable

    def test_a_dot_inside_a_class_is_not_a_literal_dot(self) -> None:
        reach = to_glob_reach("pkg/[._]x/**", source_roots=frozenset())

        assert reach.unmatchable is None


class TestTheSourceRoots:
    def test_a_directory_no_import_path_begins_with_is_a_source_root(self) -> None:
        roots = source_roots(
            ["src/pkg/tui/app.py", "backend/src/digest/sections.py"],
            ["pkg/infrastructure", "digest/sections", "os"],
        )

        assert roots == frozenset({"src", "backend"})

    def test_a_flat_layout_has_no_source_root(self) -> None:
        """``pkg/a.py`` imported as ``pkg.a``: the directory IS the import path's first part."""
        roots = source_roots(["pkg/a.py", "pkg/b/c.py"], ["pkg/a", "os"])

        assert roots == frozenset()

    def test_a_file_at_the_root_of_the_project_names_no_directory(self) -> None:
        assert source_roots(["setup.py"], ["os"]) == frozenset()
