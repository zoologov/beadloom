"""`beadloom reindex` states its test files by placement and each other kind by name.

BDL-074 F1. The `Tests:` line said "174 bound by other means" of acceptance step
files and self-checks. The first bind through their scenarios' tags and the second
bind to no node by design, so one phrase over both was true of neither. The line
now names each kind by its recorded count, as the lint population does.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from click.testing import CliRunner

from beadloom.services.cli import main

if TYPE_CHECKING:
    from pathlib import Path

_GRAPH = """\
version: 1
nodes:
  - ref_id: ledger
    kind: service
    summary: the ledger
  - ref_id: posting
    kind: domain
    summary: posting entries
    source: src/ledger/
edges:
  - src: posting
    dst: ledger
    kind: part_of
"""

_TEST = "def test_one() -> None:\n    assert True\n"

#: One mirrored file, one unplaced, one acceptance step file and two self-checks.
_TEST_FILES = (
    "tests/unit/ledger/test_posting.py",
    "tests/test_flat.py",
    "tests/acceptance/steps/test_posting_steps.py",
    "tests/self_check/docs/test_readme.py",
    "tests/self_check/config/test_flow.py",
)


def _project(root: Path) -> Path:
    project = root / "ledger-project"
    graph = project / ".beadloom" / "_graph"
    graph.mkdir(parents=True)
    (graph / "services.yml").write_text(_GRAPH, encoding="utf-8")
    source = project / "src" / "ledger"
    source.mkdir(parents=True)
    (source / "__init__.py").write_text("", encoding="utf-8")
    (source / "posting.py").write_text(
        "# beadloom:domain=posting\ndef post() -> int:\n    return 1\n", encoding="utf-8"
    )
    for relative in _TEST_FILES:
        path = project / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(_TEST, encoding="utf-8")
    return project


def _tests_line(project: Path) -> str:
    result = CliRunner().invoke(main, ["reindex", "--full", "--project", str(project)])
    assert result.exit_code == 0, result.output
    (line,) = [line for line in result.output.splitlines() if line.startswith("Tests:")]
    return line


class TestTheReindexTestsLine:
    def test_each_other_kind_is_named_by_its_count(self, tmp_path: Path) -> None:
        # Act
        line = _tests_line(_project(tmp_path))

        # Assert
        assert line.split(maxsplit=1)[1] == (
            "5 files (1 bound to a node, 1 unplaced, 1 acceptance step, 2 self-check)"
        )

    def test_no_phrase_folds_the_kinds_together(self, tmp_path: Path) -> None:
        line = _tests_line(_project(tmp_path))

        assert "by other means" not in line
