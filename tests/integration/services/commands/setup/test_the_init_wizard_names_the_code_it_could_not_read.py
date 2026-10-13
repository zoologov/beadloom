"""The ``init`` wizard names the code files no installed parser read, as ``--yes`` does.

BDL-082 S2a wired the line ``<N> <Language> files, no parser installed — install with:
uv tool install "beadloom[languages]"`` into every branch of ``init`` and both branches of
``reindex``; the ``--yes`` and ``--bootstrap`` branches and the reindex have cases, and the
wizard, the branch a human adopter meets first, had none. Without the line, a project of TypeScript
files read with no grammar prints 0 symbols and every FSD rule passes with no input.

The wizard's answers are patched at ``rich.prompt``, its one input boundary: "bootstrap"
for the mode, then the graph review's answer.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from beadloom.services.cli import main
from tests.support.fsd_spec_examples import GROUP, write_example
from tests.support.missing_grammar import grammars_missing

if TYPE_CHECKING:
    from pathlib import Path

#: The specification's slice group holds 8 TypeScript files; the wizard indents its lines.
UNREAD_LINE = (
    "  8 TypeScript files, no parser installed — "
    'install with: uv tool install "beadloom[languages]"'
)


def _wizard(root: Path, review: str) -> tuple[int, str]:
    with (
        patch("rich.prompt.Prompt.ask", side_effect=["bootstrap", review]),
        patch("rich.prompt.Confirm.ask", return_value=False),
    ):
        result = CliRunner().invoke(main, ["init", "--project", str(root)])
    assert result.exception is None or isinstance(result.exception, SystemExit), result.output
    return result.exit_code, result.output


def test_the_wizard_names_the_typescript_files_it_read_no_symbol_from(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = write_example(tmp_path / "probe", GROUP)

    with grammars_missing(monkeypatch):
        _, output = _wizard(root, "yes")

    assert UNREAD_LINE in output.splitlines()


def test_the_wizards_exit_code_does_not_move_on_the_unread_line(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = write_example(tmp_path / "probe", GROUP)

    with grammars_missing(monkeypatch):
        code, output = _wizard(root, "yes")

    assert code == 0, output


def test_the_wizard_prints_no_such_line_when_every_file_was_read(tmp_path: Path) -> None:
    pytest.importorskip("tree_sitter_typescript")
    root = write_example(tmp_path / "probe", GROUP)

    _, output = _wizard(root, "yes")

    assert "no parser installed" not in output


def test_the_wizard_left_for_an_edit_reads_no_index_and_prints_no_such_line(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # "edit" hands the graph to the adopter before any reindex: there is no index to
    # count from, and the wizard tells them to run `beadloom reindex`, which says it.
    root = write_example(tmp_path / "probe", GROUP)

    with grammars_missing(monkeypatch):
        _, output = _wizard(root, "edit")

    assert "no parser installed" not in output
