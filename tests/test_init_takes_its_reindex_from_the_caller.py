# beadloom:domain=onboarding
"""`init` re-indexes with the callable it is handed, not one it imports.

BDL-070 `beadloom-46am`. ``onboarding/scanner/init_flow.py`` imported
``beadloom.application.reindex`` twice, function-locally. Onboarding is a domain
and the re-index is an application use case, so that import ran against the
declared direction ``services -> application -> domains -> infrastructure``; it
was the only reverse-direction edge of the 357 that inheritance through
``part_of`` brings into the layer check's scope on this repository.

The direction was inverted rather than excused. What this file holds is the
three properties that inversion could have broken:

- the injected callable is the one that runs, once, on the project root;
- it still runs AFTER every block that writes a graph file, which is the
  ordering BDL-067 `.14` and `.18` established and the reason `init`'s verdict
  can be taken over the index at all;
- omitting it fails loudly at the call site instead of silently not indexing.

``tests/test_no_domain_package_imports_application.py`` holds the import itself.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

from beadloom.onboarding.scanner import interactive_init, non_interactive_init

if TYPE_CHECKING:
    from pathlib import Path


@dataclass
class FakeIndex:
    """The four counts `init` reads off a re-index, and nothing else."""

    symbols_indexed: int = 7
    imports_indexed: int = 5
    edges_loaded: int = 3
    docs_indexed: int = 2


@dataclass
class RecordingReindexer:
    """Records each call and what the graph directory held at that moment."""

    roots: list[Path] = field(default_factory=list)
    graph_files_at_call: list[frozenset[str]] = field(default_factory=list)

    def __call__(self, project_root: Path) -> FakeIndex:
        self.roots.append(project_root)
        graph_dir = project_root / ".beadloom" / "_graph"
        self.graph_files_at_call.append(
            frozenset(path.name for path in graph_dir.glob("*.yml")) if graph_dir.is_dir()
            else frozenset()
        )
        return FakeIndex()


def _a_project_with_source_and_a_document(root: Path) -> None:
    """The smallest tree both `bootstrap` and `import` have something to do with."""
    package = root / "src" / "api"
    package.mkdir(parents=True)
    (package / "app.py").write_text("def main():\n    pass\n", encoding="utf-8")
    docs = root / "docs"
    docs.mkdir()
    (docs / "readme.md").write_text("# Hello\n\nWorld.\n", encoding="utf-8")


class TestTheInjectedCallableIsTheOneThatRuns:
    def test_non_interactive_init_calls_it_once_on_the_project_root(
        self, tmp_path: Path
    ) -> None:
        reindexer = RecordingReindexer()

        non_interactive_init(tmp_path, reindex=reindexer, mode="bootstrap")

        assert reindexer.roots == [tmp_path]

    def test_non_interactive_init_reports_the_counts_it_was_given(
        self, tmp_path: Path
    ) -> None:
        """Nothing re-reads the index: the three counts come off the returned object."""
        result = non_interactive_init(tmp_path, reindex=RecordingReindexer(), mode="bootstrap")

        assert result["reindex"] == {"symbols": 7, "imports": 5, "edges": 3}

    def test_the_wizard_calls_it_too(self, tmp_path: Path) -> None:
        _a_project_with_source_and_a_document(tmp_path)
        reindexer = RecordingReindexer()

        with patch("rich.prompt.Prompt.ask", side_effect=["bootstrap", "accept"]), patch(
            "rich.prompt.Confirm.ask", return_value=False
        ):
            interactive_init(tmp_path, reindex=reindexer)

        assert reindexer.roots == [tmp_path]


class TestItStillRunsAfterEveryGraphFileIsWritten:
    """The ordering BDL-067 `.14` and `.18` established, pinned at the seam.

    `init` takes its verdict through the Gate's `lint_step`, which reads the
    index without re-indexing. A re-index that ran before the last graph file
    was written made that verdict a judgement of a graph the command had not
    finished writing: rc 0 from `init`, rc 1 from the adopter's next
    `lint --strict`. Moving where the callable comes from must not move when it
    is called, so the assertion is on what was ON DISK at the moment of the call.
    """

    def test_mode_both_has_written_the_imported_graph_before_the_call(
        self, tmp_path: Path
    ) -> None:
        _a_project_with_source_and_a_document(tmp_path)
        reindexer = RecordingReindexer()

        non_interactive_init(tmp_path, reindex=reindexer, mode="both")

        assert len(reindexer.graph_files_at_call) == 1
        written = reindexer.graph_files_at_call[0]
        assert "imported.yml" in written, (
            "the import step writes `imported.yml`; a re-index that runs before it "
            f"judges a graph the command had not finished writing. On disk: {sorted(written)}"
        )
        assert "services.yml" in written


class TestOmittingItFailsLoudly:
    """A default would be a silent 'do not re-index', which is the .14 defect."""

    def test_non_interactive_init_requires_the_reindexer(self, tmp_path: Path) -> None:
        with pytest.raises(TypeError, match="reindex"):
            non_interactive_init(tmp_path, mode="bootstrap")  # type: ignore[call-arg]

    def test_interactive_init_requires_the_reindexer(self, tmp_path: Path) -> None:
        with pytest.raises(TypeError, match="reindex"):
            interactive_init(tmp_path)  # type: ignore[call-arg]


def test_the_application_result_satisfies_the_port_onboarding_declares() -> None:
    """The port is only worth having if the real re-index still fits through it.

    Structural, at runtime: `IndexCounts` is not `@runtime_checkable`, so this
    reads the four member names off the port and asserts a real `ReindexResult`
    carries each. A member added to the port and not to the result would fail
    here rather than at an adopter's first `beadloom init`.
    """
    from beadloom.application.reindex.models import ReindexResult
    from beadloom.onboarding.scanner.reindex_port import IndexCounts

    declared = [name for name in IndexCounts.__annotations__] + [
        name
        for name, value in vars(IndexCounts).items()
        if isinstance(value, property)
    ]
    assert declared, "the port declares no member, so this test would assert nothing"

    result = ReindexResult()
    for name in declared:
        assert hasattr(result, name), f"ReindexResult has no `{name}`"
