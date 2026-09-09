"""`beadloom impact` — the two renderings a work item's document is written from.

`--section` renders the `## Axes` section an author pastes into a BRIEF or an RFC,
and `beadloom axes` reads that section back. The two are one round trip through a
markdown table, and this module holds it closed: what the renderer writes, the
reader must return, row for row and decision for decision. `beadloom-0mdo.46` and
`beadloom-0mdo.77` both moved the reader's half of that boundary, and nothing
compared the two halves against each other.

**Why this module exists.** Measured on 2026-09-09 over BDL-068 S6's forty-nine
changed source files, `services/commands/impact.py` was the one below the slice's
coverage floor. `--section` and the refusal for a target no rule can find were
reached by no test; the acceptance suite invokes `--json` and the human form only.

Written after the behaviour, so these are boundary guards.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

import pytest
import yaml
from click.testing import CliRunner

from beadloom.doc_sync.axes_section import read_axes_section
from beadloom.services.cli import main

if TYPE_CHECKING:
    from pathlib import Path

    from click.testing import Result

_ORDERS = """\
def place_order(item):
    return record(item)


def record(item):
    return item
"""

_BILLING = """\
from pkg.orders import place_order


def charge(item):
    if item:
        return place_order(item)
    return None
"""


@pytest.fixture
def project(tmp_path: Path) -> Path:
    """A two-module source tree with a graph node over each module."""
    root = tmp_path / "proj"
    (root / "src" / "pkg").mkdir(parents=True)
    (root / "src" / "pkg" / "__init__.py").write_text("", encoding="utf-8")
    (root / "src" / "pkg" / "orders.py").write_text(_ORDERS, encoding="utf-8")
    (root / "src" / "pkg" / "billing.py").write_text(_BILLING, encoding="utf-8")
    (root / "docs").mkdir()
    nodes: list[dict[str, Any]] = []
    for name in ("orders", "billing"):
        (root / "docs" / f"{name}.md").write_text(f"# {name}\n\nWhat it does.\n", "utf-8")
        nodes.append(
            {
                "ref_id": name,
                "kind": "feature",
                "summary": f"the {name} module",
                "source": f"src/pkg/{name}.py",
                "docs": [f"{name}.md"],
            }
        )
    graph = root / ".beadloom" / "_graph"
    graph.mkdir(parents=True)
    (graph / "graph.yml").write_text(yaml.dump({"nodes": nodes}), encoding="utf-8")
    return root


def _run(project: Path, *args: str) -> Result:
    return CliRunner().invoke(main, ["impact", *args, "--project", str(project)])


class TestTheSectionRenderingRoundTrips:
    """What `--section` writes, `beadloom axes` must read back unchanged.

    The two halves live in different domains — the renderer in `application`, the
    reader in `doc-sync` — and a work item's approved-node list is whatever the
    second returns about what the first wrote.
    """

    def test_the_rendered_section_is_read_back_as_a_section(self, project: Path) -> None:
        result = _run(project, "src/pkg/orders.py", "--section")
        assert result.exit_code == 0
        section = read_axes_section(result.stdout)
        assert section is not None
        assert section.axes, result.stdout

    def test_every_rendered_row_survives_the_reader(self, project: Path) -> None:
        """The row count is the fact a table-boundary defect destroys first."""
        result = _run(project, "src/pkg/orders.py", "--section")
        section = read_axes_section(result.stdout)
        assert section is not None
        rendered = [
            line
            for line in result.stdout.splitlines()
            if line.startswith("|") and not set(line) <= set("| -:")
        ]
        # One header row plus one row per axis.
        assert len(section.axes) == len(rendered) - 1

    def test_the_rendered_section_states_the_seed_the_answer_was_derived_from(
        self, project: Path
    ) -> None:
        result = _run(project, "src/pkg/orders.py", "--section")
        section = read_axes_section(result.stdout)
        assert section is not None
        assert section.names_a_seed is True
        assert section.derived_by

    def test_a_freshly_rendered_section_keeps_nothing_in_scope(self, project: Path) -> None:
        """The state the section is born in: the derivation ran, nobody has decided.

        `axis-without-a-scope-decision` exists to report exactly this, so a rendered
        section that arrived with decisions already made would be a check that
        cannot fire.
        """
        result = _run(project, "src/pkg/orders.py", "--section")
        section = read_axes_section(result.stdout)
        assert section is not None
        assert section.kept == ()
        assert all(axis.in_scope is None for axis in section.axes)

    def test_the_alignment_row_it_writes_is_one_both_readers_accept(self, project: Path) -> None:
        """Held because the two separator predicates disagree (BDL-UX #269).

        The renderer chooses the spelling, so a change to that choice decides
        whether every rendered section reads back correctly.
        """
        from beadloom.application.active_table.table import is_separator_cells
        from beadloom.doc_sync.tables import cells_of, is_separator

        result = _run(project, "src/pkg/orders.py", "--section")
        alignment = [
            cells
            for line in result.stdout.splitlines()
            if (cells := cells_of(line)) and set("".join(cells)) <= set("-:")
        ]
        assert alignment, result.stdout
        for cells in alignment:
            assert is_separator(cells) is True
            assert is_separator_cells(cells) is True


class TestTheOtherTwoRenderings:
    """`--json` and the human form, on the same answer."""

    def test_json_and_the_human_form_answer_about_the_same_target(self, project: Path) -> None:
        structured = _run(project, "src/pkg/orders.py", "--json")
        human = _run(project, "src/pkg/orders.py")
        assert structured.exit_code == 0
        assert human.exit_code == 0
        payload = json.loads(structured.stdout)
        assert payload["target"] == "src/pkg/orders.py"
        assert payload["seed_rule"]["name"] == "reaches-an-effect-sink"
        assert "src/pkg/orders.py" in human.stdout

    def test_json_is_read_off_stdout_alone(self, project: Path) -> None:
        """Click merges the streams by default; the payload is stdout's."""
        result = _run(project, "src/pkg/orders.py", "--json")
        assert isinstance(json.loads(result.stdout), dict)


class TestATargetNoRuleCanFind:
    """The refusal, and that it is a refusal rather than an answer over nothing."""

    def test_a_target_that_is_neither_a_path_nor_a_symbol_exits_one(self, project: Path) -> None:
        result = _run(project, "there_is_no_such_thing")
        assert result.exit_code == 1
        assert "no file and no symbol named" in result.output

    def test_the_refusal_goes_to_stderr_and_stdout_stays_empty(self, project: Path) -> None:
        """A consumer that pipes stdout gets nothing rather than a half answer."""
        result = CliRunner().invoke(
            main,
            ["impact", "there_is_no_such_thing", "--project", str(project), "--json"],
        )
        assert result.exit_code == 1
        assert result.stdout == ""
