"""A row names the files its node owns that `impact` did not read (BDL-UX #284).

BDL-069 ruled `onboarding` out of scope as blast radius: it surfaced in the axes
as a caller, and a `callers` row was read as "calls into the change, is not
changed". The fix had to reach that node's `templates/docs/core/*.md.txt`, and
nothing in the section could have said so — `impact` reads Python, the templates
are not Python, and the one place a derivation names what it could not read was
the section's `Unresolved` line, which named nothing about them either.

So the answer carries, per node it names, the files that node OWNS — by the one
most-specific-wins rule the linter and `sync-check` use — that this derivation
does not read, and the `## Axes` section writes that fact on the node's own row.

Every case builds a project that is not this repository, indexes it with the
real `reindex`, and runs the real derivation. Reproduced red first on the same
shape, with the tree's `beadloom` at `7eadb4b4`: `callers | skel | 1 —
src/app/skel/generator.py:8 | ? |` and `Unresolved: 1 no-seed`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
import yaml

from beadloom.application.impact import answer_to_dict, impact_of
from beadloom.application.impact.section import render_axes_section
from beadloom.application.reindex import reindex
from beadloom.doc_sync.axes_section import OWNS_UNREAD_COLUMN, read_axes_section

if TYPE_CHECKING:
    from pathlib import Path

    from beadloom.application.impact import ImpactAnswer

_MANIFEST = """\
def read_manifest(root):
    return (root / "manifest.txt").read_text()
"""

_GENERATOR = """\
from pathlib import Path

from app.manifest import read_manifest

TEMPLATES = Path(__file__).parent / "templates"


def render_domain(root):
    name = read_manifest(root)
    return (TEMPLATES / "domain.md.txt").read_text().format(name=name)
"""

_TEMPLATE = "app/skel/templates/domain.md.txt"
_TARGET = "src/app/manifest.py"


def _node(ref_id: str, source: str) -> dict[str, object]:
    return {
        "ref_id": ref_id,
        "kind": "feature",
        "summary": f"the {ref_id} node",
        "source": source,
        "docs": [f"{ref_id}.md"],
    }


def _write(root: Path, relative: str, text: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _project(root: Path, nodes: list[dict[str, object]]) -> Path:
    """The shape `onboarding` had: a caller whose node owns a template it reads."""
    _write(root, "pyproject.toml", '[project]\nname = "app"\nversion = "0.1.0"\n')
    _write(root, "src/app/__init__.py", "")
    _write(root, "src/app/skel/__init__.py", "")
    _write(root, "src/app/manifest.py", _MANIFEST)
    _write(root, "src/app/skel/generator.py", _GENERATOR)
    _write(root, f"src/{_TEMPLATE}", "# {name}\n\n## Source\n")
    for node in nodes:
        _write(root, f"docs/{node['ref_id']}.md", f"# {node['ref_id']}\n\nWhat it does.\n")
    graph = {"nodes": nodes}
    _write(root, ".beadloom/_graph/graph.yml", yaml.safe_dump(graph))
    return root


@pytest.fixture
def project(tmp_path: Path) -> Path:
    root = _project(
        tmp_path / "proj",
        [_node("manifest", "src/app/manifest.py"), _node("skel", "src/app/skel/")],
    )
    reindex(root)
    return root


def _row(section_text: str, axis: str, node: str) -> str:
    return next(
        line
        for line in section_text.splitlines()
        if line.startswith(f"| {axis} | {node} |")
    )


def _unread(answer: ImpactAnswer) -> dict[str, tuple[str, ...]]:
    return {owned.node: owned.files for owned in answer.unread_ownership}


class TestTheAnswerCarriesWhatEachNodeOwnsAndWasNotRead:
    def test_a_caller_whose_node_owns_a_template_names_that_template(
        self, project: Path
    ) -> None:
        answer = impact_of(_TARGET, project_root=project)
        assert _unread(answer) == {"skel": (f"src/{_TEMPLATE}",)}

    def test_a_node_owning_only_python_is_not_listed(self, project: Path) -> None:
        answer = impact_of(_TARGET, project_root=project)
        assert "manifest" not in _unread(answer)

    def test_a_file_a_more_specific_node_owns_is_not_counted_against_its_parent(
        self, tmp_path: Path
    ) -> None:
        """Most specific wins, as it does for the linter and `sync-check`.

        Counting a child's files against its parent too would name `skel` as
        the owner of a template another node owns, and send the ruling to the
        wrong row.
        """
        root = _project(
            tmp_path / "proj",
            [
                _node("manifest", "src/app/manifest.py"),
                _node("skel", "src/app/skel/"),
                _node("skel-templates", "src/app/skel/templates/"),
            ],
        )
        reindex(root)
        answer = impact_of(_TARGET, project_root=root)
        assert "skel" not in _unread(answer)

    def test_a_compiled_cache_is_not_a_file_the_node_owns(self, project: Path) -> None:
        _write(project, "src/app/skel/__pycache__/generator.cpython-313.pyc", "bytes")
        answer = impact_of(_TARGET, project_root=project)
        assert _unread(answer) == {"skel": (f"src/{_TEMPLATE}",)}

    def test_the_unresolved_population_names_the_node_and_the_file(
        self, project: Path
    ) -> None:
        answer = impact_of(_TARGET, project_root=project)
        gaps = [gap for gap in answer.unresolved if gap.kind == "node-owns-unread-files"]
        assert len(gaps) == 1
        assert "skel" in gaps[0].detail
        assert gaps[0].where == f"src/{_TEMPLATE}"

    def test_without_an_index_no_ownership_is_claimed(self, tmp_path: Path) -> None:
        """No index, no owner — so nothing is claimed as owned, and `no-graph-index` says why."""
        root = _project(
            tmp_path / "proj",
            [_node("manifest", "src/app/manifest.py"), _node("skel", "src/app/skel/")],
        )
        answer = impact_of(_TARGET, project_root=root)
        assert answer.unread_ownership == ()
        assert "node-owns-unread-files" not in {gap.kind for gap in answer.unresolved}

    def test_the_json_carries_every_file_per_node(self, project: Path) -> None:
        payload = answer_to_dict(impact_of(_TARGET, project_root=project))
        assert payload["unread_ownership"] == [
            {"node": "skel", "files": [f"src/{_TEMPLATE}"]}
        ]


class TestTheSectionWritesItOnTheRow:
    def test_the_callers_row_names_the_template_its_node_owns(self, project: Path) -> None:
        rendered = render_axes_section(impact_of(_TARGET, project_root=project))
        row = _row(rendered, "callers", "skel")
        assert f"1 — `src/{_TEMPLATE}`" in row

    def test_a_row_whose_node_owns_nothing_unread_says_none(self, project: Path) -> None:
        """A measured absence is written, so it cannot read as a column nobody filled."""
        rendered = render_axes_section(impact_of(_TARGET, project_root=project))
        cells = [cell.strip() for cell in _row(rendered, "branches", "manifest").split("|")]
        header_line = next(line for line in rendered.splitlines() if line.startswith("| Axis |"))
        header = [cell.strip() for cell in header_line.split("|")]
        assert cells[header.index(OWNS_UNREAD_COLUMN)] == "none"

    def test_the_row_reads_back_with_its_count(self, project: Path) -> None:
        rendered = render_axes_section(impact_of(_TARGET, project_root=project))
        section = read_axes_section(rendered)
        assert section is not None
        by_node = {(axis.axis, axis.node): axis for axis in section.axes}
        assert by_node[("callers", "skel")].unread_count == 1
        assert by_node[("branches", "manifest")].unread_count == 0

    def test_a_row_naming_no_node_claims_nothing_about_ownership(
        self, project: Path
    ) -> None:
        rendered = render_axes_section(impact_of(_TARGET, project_root=project))
        section = read_axes_section(rendered)
        assert section is not None
        unowned = [axis for axis in section.axes if not axis.node]
        assert unowned, rendered
        assert all(axis.unread_count is None for axis in unowned)

    def test_the_unresolved_field_counts_the_new_kind(self, project: Path) -> None:
        rendered = render_axes_section(impact_of(_TARGET, project_root=project))
        section = read_axes_section(rendered)
        assert section is not None
        assert "1 node-owns-unread-files" in section.unresolved
