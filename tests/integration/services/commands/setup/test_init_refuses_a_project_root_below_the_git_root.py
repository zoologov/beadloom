"""``init`` refuses a project root below the git root in every mode (BDL-083 S2e, #325).

``beadloom-7pd6``. The refusal comes before any writer runs, so no mode leaves a
``.beadloom/`` behind in the subfolder: the non-interactive one, ``--bootstrap``, ``--import``
and the wizard. At the git root the same command initialises, which is the control.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from click.testing import CliRunner

from beadloom.services.cli import main
from tests.support.committed_project import commit_project

if TYPE_CHECKING:
    from pathlib import Path

#: Every way of entering ``init``; the wizard is answered with an empty input it never reads.
_MODES = (["--yes"], ["--bootstrap"], ["--import", "docs"], [])


def _project(root: Path) -> Path:
    (root / "src" / "app").mkdir(parents=True)
    (root / "src" / "app" / "__init__.py").write_text("x = 1\n", encoding="utf-8")
    (root / "docs").mkdir()
    (root / "docs" / "README.md").write_text("# App\n", encoding="utf-8")
    return root


@pytest.mark.parametrize("mode", _MODES, ids=["yes", "bootstrap", "import", "wizard"])
def test_every_mode_refuses_and_writes_nothing(tmp_path: Path, mode: list[str]) -> None:
    repository = tmp_path / "repository"
    project = _project(repository / "app")
    commit_project(repository)
    args = [str(project / a) if a == "docs" else a for a in mode]

    result = CliRunner().invoke(main, ["init", *args, "--project", str(project)], input="")

    assert result.exit_code == 1, result.output
    assert "the git root is above the project root" in " ".join(result.output.split())
    assert not (project / ".beadloom").exists()


def test_at_the_git_root_init_runs(tmp_path: Path) -> None:
    project = _project(tmp_path / "repository")
    commit_project(project)

    result = CliRunner().invoke(main, ["init", "--yes", "--project", str(project)])

    assert result.exit_code == 0, result.output
    assert (project / ".beadloom").is_dir()
