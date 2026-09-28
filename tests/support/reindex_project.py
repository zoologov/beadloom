"""An empty project a reindex can run over, built in ``tmp_path``.

Moved out of the reindex test files when BDL-074 ``beadloom-2mj3.7`` split them by
node: the reindex's own tests and the context bundle's tests that read what the
reindex stored build the same project, and a helper several test modules share
lives here rather than in either of them.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


def empty_project(root: Path) -> Path:
    """Create the graph, docs and source folders of a project under *root*, and return it."""
    (root / ".beadloom" / "_graph").mkdir(parents=True)
    (root / "docs").mkdir()
    (root / "src").mkdir()
    return root


def index_path(root: Path) -> Path:
    """Where the reindex writes the index of the project at *root*."""
    return root / ".beadloom" / "beadloom.db"


def write_two_nodes_with_sources(project: Path) -> None:
    """Declare a domain and a service, each owning a source directory."""
    (project / ".beadloom" / "_graph" / "domains.yml").write_text(
        "nodes:\n"
        "  - ref_id: infra\n"
        "    kind: domain\n"
        '    summary: "Infrastructure domain"\n'
        "    source: src/infra\n"
        "  - ref_id: api\n"
        "    kind: service\n"
        '    summary: "API service"\n'
        "    source: src/api\n"
    )
