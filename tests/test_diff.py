"""Tests for beadloom.diff — Graph delta: compare current graph YAML with state at a git ref."""

from __future__ import annotations

import json
import os
import subprocess
from typing import TYPE_CHECKING

import pytest
import yaml

from beadloom.graph.diff import (
    EdgeChange,
    GraphDiff,
    NodeChange,
    compute_diff,
    diff_to_dict,
    render_diff,
)

if TYPE_CHECKING:
    from pathlib import Path

_GIT_ENV = {
    **os.environ,
    "GIT_AUTHOR_NAME": "test",
    "GIT_AUTHOR_EMAIL": "t@t",
    "GIT_COMMITTER_NAME": "test",
    "GIT_COMMITTER_EMAIL": "t@t",
}


def _git(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    """Run a git command in the given directory."""
    return subprocess.run(  # noqa: S603
        ["git", *args],  # noqa: S607
        cwd=cwd,
        capture_output=True,
        text=True,
        env=_GIT_ENV,
    )


@pytest.fixture()
def git_project(tmp_path: Path) -> Path:
    """Create a git repo with initial graph YAML committed."""
    graph_dir = tmp_path / ".beadloom" / "_graph"
    graph_dir.mkdir(parents=True)

    yaml_content = yaml.dump(
        {
            "nodes": [
                {"ref_id": "auth-login", "kind": "feature", "summary": "User authentication"},
                {"ref_id": "user-service", "kind": "service", "summary": "User management"},
            ],
            "edges": [
                {"src": "auth-login", "dst": "user-service", "kind": "uses"},
            ],
        }
    )
    (graph_dir / "test.yml").write_text(yaml_content)

    _git(tmp_path, "init")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-m", "initial")

    return tmp_path


class TestDiffNoChanges:
    def test_diff_no_changes(self, git_project: Path) -> None:
        """Same YAML at HEAD -> empty diff."""
        result = compute_diff(git_project, since="HEAD")
        assert not result.has_changes
        assert result.nodes == ()
        assert result.edges == ()


class TestDiffAddedNode:
    def test_diff_added_node(self, git_project: Path) -> None:
        """New node added -> detected as 'added'."""
        graph_dir = git_project / ".beadloom" / "_graph"
        yaml_content = yaml.dump(
            {
                "nodes": [
                    {"ref_id": "auth-login", "kind": "feature", "summary": "User authentication"},
                    {"ref_id": "user-service", "kind": "service", "summary": "User management"},
                    {"ref_id": "payment", "kind": "service", "summary": "Payment processing"},
                ],
                "edges": [
                    {"src": "auth-login", "dst": "user-service", "kind": "uses"},
                ],
            }
        )
        (graph_dir / "test.yml").write_text(yaml_content)

        result = compute_diff(git_project, since="HEAD")
        assert result.has_changes
        added_nodes = [n for n in result.nodes if n.change_type == "added"]
        assert len(added_nodes) == 1
        assert added_nodes[0].ref_id == "payment"
        assert added_nodes[0].kind == "service"


class TestDiffRemovedNode:
    def test_diff_removed_node(self, git_project: Path) -> None:
        """Node removed -> detected as 'removed'."""
        graph_dir = git_project / ".beadloom" / "_graph"
        yaml_content = yaml.dump(
            {
                "nodes": [
                    {"ref_id": "auth-login", "kind": "feature", "summary": "User authentication"},
                ],
                "edges": [],
            }
        )
        (graph_dir / "test.yml").write_text(yaml_content)

        result = compute_diff(git_project, since="HEAD")
        assert result.has_changes
        removed_nodes = [n for n in result.nodes if n.change_type == "removed"]
        assert len(removed_nodes) == 1
        assert removed_nodes[0].ref_id == "user-service"


class TestDiffChangedSummary:
    def test_diff_changed_summary(self, git_project: Path) -> None:
        """Summary changed -> detected as 'changed' with old/new."""
        graph_dir = git_project / ".beadloom" / "_graph"
        yaml_content = yaml.dump(
            {
                "nodes": [
                    {"ref_id": "auth-login", "kind": "feature", "summary": "Updated auth flow"},
                    {"ref_id": "user-service", "kind": "service", "summary": "User management"},
                ],
                "edges": [
                    {"src": "auth-login", "dst": "user-service", "kind": "uses"},
                ],
            }
        )
        (graph_dir / "test.yml").write_text(yaml_content)

        result = compute_diff(git_project, since="HEAD")
        assert result.has_changes
        changed_nodes = [n for n in result.nodes if n.change_type == "changed"]
        assert len(changed_nodes) == 1
        assert changed_nodes[0].ref_id == "auth-login"
        assert changed_nodes[0].old_summary == "User authentication"
        assert changed_nodes[0].new_summary == "Updated auth flow"


class TestDiffChangedKind:
    def test_diff_changed_kind(self, git_project: Path) -> None:
        """Node kind changed -> detected as 'changed'."""
        graph_dir = git_project / ".beadloom" / "_graph"
        yaml_content = yaml.dump(
            {
                "nodes": [
                    {"ref_id": "auth-login", "kind": "domain", "summary": "User authentication"},
                    {"ref_id": "user-service", "kind": "service", "summary": "User management"},
                ],
                "edges": [
                    {"src": "auth-login", "dst": "user-service", "kind": "uses"},
                ],
            }
        )
        (graph_dir / "test.yml").write_text(yaml_content)

        result = compute_diff(git_project, since="HEAD")
        assert result.has_changes
        changed_nodes = [n for n in result.nodes if n.change_type == "changed"]
        assert len(changed_nodes) == 1
        assert changed_nodes[0].ref_id == "auth-login"
        assert changed_nodes[0].kind == "domain"


class TestDiffAddedEdge:
    def test_diff_added_edge(self, git_project: Path) -> None:
        """New edge -> detected as 'added'."""
        graph_dir = git_project / ".beadloom" / "_graph"
        yaml_content = yaml.dump(
            {
                "nodes": [
                    {"ref_id": "auth-login", "kind": "feature", "summary": "User authentication"},
                    {"ref_id": "user-service", "kind": "service", "summary": "User management"},
                ],
                "edges": [
                    {"src": "auth-login", "dst": "user-service", "kind": "uses"},
                    {"src": "user-service", "dst": "auth-login", "kind": "provides"},
                ],
            }
        )
        (graph_dir / "test.yml").write_text(yaml_content)

        result = compute_diff(git_project, since="HEAD")
        assert result.has_changes
        added_edges = [e for e in result.edges if e.change_type == "added"]
        assert len(added_edges) == 1
        assert added_edges[0].src == "user-service"
        assert added_edges[0].dst == "auth-login"
        assert added_edges[0].kind == "provides"


class TestDiffRemovedEdge:
    def test_diff_removed_edge(self, git_project: Path) -> None:
        """Edge removed -> detected as 'removed'."""
        graph_dir = git_project / ".beadloom" / "_graph"
        yaml_content = yaml.dump(
            {
                "nodes": [
                    {"ref_id": "auth-login", "kind": "feature", "summary": "User authentication"},
                    {"ref_id": "user-service", "kind": "service", "summary": "User management"},
                ],
                "edges": [],
            }
        )
        (graph_dir / "test.yml").write_text(yaml_content)

        result = compute_diff(git_project, since="HEAD")
        assert result.has_changes
        removed_edges = [e for e in result.edges if e.change_type == "removed"]
        assert len(removed_edges) == 1
        assert removed_edges[0].src == "auth-login"
        assert removed_edges[0].dst == "user-service"
        assert removed_edges[0].kind == "uses"


class TestDiffNewFile:
    def test_diff_new_file(self, git_project: Path) -> None:
        """New YAML file not in git -> all its nodes 'added'."""
        graph_dir = git_project / ".beadloom" / "_graph"
        new_yaml = yaml.dump(
            {
                "nodes": [
                    {"ref_id": "billing", "kind": "domain", "summary": "Billing domain"},
                ],
                "edges": [],
            }
        )
        (graph_dir / "billing.yml").write_text(new_yaml)

        result = compute_diff(git_project, since="HEAD")
        assert result.has_changes
        added_nodes = [n for n in result.nodes if n.change_type == "added"]
        added_ids = {n.ref_id for n in added_nodes}
        assert "billing" in added_ids


class TestDiffDeletedFile:
    def test_diff_deleted_file(self, git_project: Path) -> None:
        """YAML file removed since ref -> all its nodes 'removed'."""
        graph_dir = git_project / ".beadloom" / "_graph"
        (graph_dir / "test.yml").unlink()

        result = compute_diff(git_project, since="HEAD")
        assert result.has_changes
        removed_nodes = [n for n in result.nodes if n.change_type == "removed"]
        removed_ids = {n.ref_id for n in removed_nodes}
        assert "auth-login" in removed_ids
        assert "user-service" in removed_ids

        removed_edges = [e for e in result.edges if e.change_type == "removed"]
        assert len(removed_edges) == 1
        assert removed_edges[0].src == "auth-login"


class TestDiffInvalidRef:
    def test_diff_invalid_ref(self, git_project: Path) -> None:
        """Bad git ref -> ValueError with clear message."""
        with pytest.raises(ValueError, match="Invalid git ref"):
            compute_diff(git_project, since="nonexistent-ref-abc123")


class TestHasChangesProperty:
    def test_has_changes_true(self) -> None:
        diff = GraphDiff(
            since_ref="HEAD",
            nodes=(NodeChange(ref_id="x", kind="feature", change_type="added"),),
            edges=(),
        )
        assert diff.has_changes is True

    def test_has_changes_false(self) -> None:
        diff = GraphDiff(since_ref="HEAD", nodes=(), edges=())
        assert diff.has_changes is False

    def test_has_changes_edges_only(self) -> None:
        diff = GraphDiff(
            since_ref="HEAD",
            nodes=(),
            edges=(EdgeChange(src="a", dst="b", kind="uses", change_type="added"),),
        )
        assert diff.has_changes is True


class TestRenderNoChanges:
    def test_render_no_changes(self) -> None:
        """render shows 'No graph changes' message."""
        from io import StringIO

        from rich.console import Console

        diff = GraphDiff(since_ref="HEAD", nodes=(), edges=())
        output = StringIO()
        console = Console(file=output, force_terminal=False)
        render_diff(diff, console)
        text = output.getvalue()
        assert "No graph changes since HEAD" in text


class TestRenderWithChanges:
    def test_render_with_changes(self) -> None:
        """render output contains expected markers."""
        from io import StringIO

        from rich.console import Console

        diff = GraphDiff(
            since_ref="HEAD~1",
            nodes=(
                NodeChange(ref_id="new-feat", kind="feature", change_type="added"),
                NodeChange(
                    ref_id="old-feat",
                    kind="feature",
                    change_type="changed",
                    old_summary="Old",
                    new_summary="New",
                ),
                NodeChange(ref_id="gone-feat", kind="feature", change_type="removed"),
            ),
            edges=(
                EdgeChange(src="a", dst="b", kind="uses", change_type="added"),
                EdgeChange(src="c", dst="d", kind="depends", change_type="removed"),
            ),
        )
        output = StringIO()
        console = Console(file=output, force_terminal=False)
        render_diff(diff, console)
        text = output.getvalue()

        assert "Graph diff (since HEAD~1)" in text
        assert "+" in text  # added marker
        assert "~" in text  # changed marker
        assert "-" in text  # removed marker
        assert "new-feat" in text
        assert "old-feat" in text
        assert "gone-feat" in text


class TestDiffToDict:
    def test_diff_to_dict(self) -> None:
        """JSON serialization structure."""
        diff = GraphDiff(
            since_ref="HEAD",
            nodes=(
                NodeChange(ref_id="feat-1", kind="feature", change_type="added"),
                NodeChange(
                    ref_id="feat-2",
                    kind="service",
                    change_type="changed",
                    old_summary="Old summary",
                    new_summary="New summary",
                ),
            ),
            edges=(EdgeChange(src="a", dst="b", kind="uses", change_type="removed"),),
        )
        result = diff_to_dict(diff)

        # Verify structure
        assert result["since_ref"] == "HEAD"
        assert result["has_changes"] is True
        assert len(result["nodes"]) == 2
        assert len(result["edges"]) == 1

        # Verify node serialization
        added_node = result["nodes"][0]
        assert added_node["ref_id"] == "feat-1"
        assert added_node["change_type"] == "added"
        assert added_node["old_summary"] is None
        assert added_node["new_summary"] is None

        changed_node = result["nodes"][1]
        assert changed_node["old_summary"] == "Old summary"
        assert changed_node["new_summary"] == "New summary"

        # Verify edge serialization
        edge = result["edges"][0]
        assert edge["src"] == "a"
        assert edge["dst"] == "b"
        assert edge["kind"] == "uses"
        assert edge["change_type"] == "removed"

        # Verify JSON serializable
        json_str = json.dumps(result)
        assert json_str  # non-empty
