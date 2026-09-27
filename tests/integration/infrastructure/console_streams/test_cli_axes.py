"""`beadloom axes` — the command that reads a work item's `## Axes` section back.

The section is where a work item records what a change ranges over and how much
of it this item takes, and the rows it keeps are the list `scope-check` compares
every commit against. Three renderings read it: the human table, `--refs` (the
line a bead's own scope is written from) and `--json`.

**Why this module exists.** Measured on 2026-09-09 over BDL-068 S6's forty-nine
changed source files, `services/commands/impact.py` was the one below the slice's
coverage floor at 51 %, and `beadloom axes` — its second command — was reached by
no test at all. A rendering nothing exercises is a rendering that can lose a row
silently, and the row it would lose is an approved node.

Written after the behaviour, so these are boundary guards. What they guard is the
three renderings agreeing about one section: a node kept by the table is a node in
`--refs` and in `--json`, and a row that decides nothing is `UNDECIDED` in all
three rather than absent from one.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest
from click.testing import CliRunner

from beadloom.services.cli import main

if TYPE_CHECKING:
    from pathlib import Path

    from click.testing import Result

#: A section with one kept row, one ruled out, one undecided and one naming no
#: node — the four states `axes_section` distinguishes, in one document.
SECTION = """\
# BRIEF: ORD-1

## Axes

> **Derived by:** `beadloom impact` over `src/orders.py`
> **Seed:** `place_order`, under the rule `reaches-an-effect-sink`
> **Unresolved:** co-writers, on one target

| Axis | Node | Sites | In scope | Why |
| ------ | ------ | ------ | ------ | ------ |
| callers | orders | 12 | yes | the change ranges over it |
| callers | billing | 3 | no | the contract is unchanged |
| co-writers | ledger | 1 |  | nobody has decided |
| branches | — | 4 | yes | the count is a fact about the body |
"""


def _document(tmp_path: Path, text: str = SECTION) -> Path:
    path = tmp_path / "BRIEF.md"
    path.write_text(text, encoding="utf-8")
    return path


def _run(*args: str) -> Result:
    return CliRunner().invoke(main, ["axes", *args])


class TestTheThreeRenderingsOfOneSection:
    """One section, read three ways, and the three answers must be one answer."""

    def test_the_human_rendering_names_the_seed_and_every_row(self, tmp_path: Path) -> None:
        result = _run(str(_document(tmp_path)))
        assert result.exit_code == 0
        assert "Seed: `place_order`, under the rule `reaches-an-effect-sink`" in result.stdout
        assert "Unresolved: co-writers, on one target" in result.stdout
        assert "[in] callers — orders: 12" in result.stdout
        assert "[out] callers — billing: 3" in result.stdout
        assert "[UNDECIDED] co-writers — ledger: 1" in result.stdout

    def test_a_row_naming_no_node_is_rendered_with_the_dash_it_carries(
        self, tmp_path: Path
    ) -> None:
        """An em dash in the node cell names nothing, and the row is still a row."""
        result = _run(str(_document(tmp_path)))
        assert result.exit_code == 0
        assert "[in] branches — —: 4" in result.stdout

    def test_refs_carries_only_the_nodes_a_row_kept(self, tmp_path: Path) -> None:
        result = _run("--refs", str(_document(tmp_path)))
        assert result.exit_code == 0
        assert result.stdout.strip() == "refs: orders"

    def test_the_human_rendering_ends_with_the_same_refs_line(self, tmp_path: Path) -> None:
        """Two renderings of one fact, held together so they cannot drift apart."""
        human = _run(str(_document(tmp_path)))
        refs = _run("--refs", str(_document(tmp_path)))
        assert refs.stdout.strip() in human.stdout

    def test_json_states_every_row_and_the_kept_nodes_apart(self, tmp_path: Path) -> None:
        result = _run("--json", str(_document(tmp_path)))
        assert result.exit_code == 0
        payload = json.loads(result.stdout)
        assert payload["refs"] == ["orders"]
        assert payload["seed"].startswith("`place_order`")
        assert payload["unresolved"] == "co-writers, on one target"
        assert [row["axis"] for row in payload["axes"]] == [
            "callers",
            "callers",
            "co-writers",
            "branches",
        ]
        assert [row["in_scope"] for row in payload["axes"]] == [True, False, None, True]

    def test_json_gives_every_row_the_line_a_reader_opens(self, tmp_path: Path) -> None:
        result = _run("--json", str(_document(tmp_path)))
        payload = json.loads(result.stdout)
        lines = [row["line"] for row in payload["axes"]]
        assert lines == sorted(lines)
        assert all(line > 0 for line in lines)

    def test_json_is_read_off_stdout_alone(self, tmp_path: Path) -> None:
        """The guard this project's own suite added: Click merges the streams by default."""
        result = CliRunner().invoke(main, ["axes", "--json", str(_document(tmp_path))])
        assert json.loads(result.stdout)["refs"] == ["orders"]


class TestADocumentThatCarriesNoSection:
    """The refusal, and that it names the command that produces what is missing."""

    def test_a_document_with_no_axes_section_exits_one_and_says_what_to_run(
        self, tmp_path: Path
    ) -> None:
        document = _document(tmp_path, "# BRIEF: ORD-1\n\n## Problem\n\nNothing here.\n")
        result = _run(str(document))
        assert result.exit_code == 1
        assert "carries no `## Axes` section" in result.output
        assert "beadloom impact <path|symbol> --section" in result.output

    @pytest.mark.parametrize("flag", ["--refs", "--json"])
    def test_the_refusal_is_the_same_under_every_rendering(
        self, tmp_path: Path, flag: str
    ) -> None:
        """The section is read before the rendering is chosen, so one refusal serves all."""
        document = _document(tmp_path, "# BRIEF: ORD-1\n\nNothing here.\n")
        result = _run(flag, str(document))
        assert result.exit_code == 1
        assert "carries no `## Axes` section" in result.output

    def test_a_path_that_is_not_a_file_is_refused_by_click(self, tmp_path: Path) -> None:
        result = _run(str(tmp_path / "absent.md"))
        assert result.exit_code == 2
        assert "does not exist" in result.output


class TestASectionWithAHeadingAndNoRows:
    """An empty section and a missing one are different answers and stay different.

    `read_axes_section` returns `None` for a document with no heading and an empty
    `AxesSection` for one with a heading and nothing under it. The command refuses
    only the first, so a work item that has started its section reads back as
    started.
    """

    def test_a_heading_with_no_table_renders_the_fields_and_no_row(self, tmp_path: Path) -> None:
        document = _document(
            tmp_path,
            "# BRIEF: ORD-1\n\n## Axes\n\n> **Seed:** `none`\n\nNot derived yet.\n",
        )
        result = _run(str(document))
        assert result.exit_code == 0
        assert "Seed: `none`" in result.stdout
        assert "Unresolved: NOT STATED" in result.stdout

    def test_a_section_with_no_kept_row_produces_an_empty_refs_line(self, tmp_path: Path) -> None:
        """An empty `refs:` is the honest answer: nothing was ruled in, not nothing was asked."""
        document = _document(
            tmp_path,
            "# BRIEF: ORD-1\n\n## Axes\n\n> **Seed:** `none`\n\n"
            "| Axis | Node | Sites | In scope | Why |\n"
            "| ------ | ------ | ------ | ------ | ------ |\n"
            "| callers | orders | 2 | no | out of this slice |\n",
        )
        result = _run("--refs", str(document))
        assert result.exit_code == 0
        assert result.stdout.strip() == "refs:"
