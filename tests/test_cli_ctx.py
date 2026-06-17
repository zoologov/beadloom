"""Tests for `beadloom ctx` CLI command."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from click.testing import CliRunner

from beadloom.services.cli import main

if TYPE_CHECKING:
    from pathlib import Path


def _setup_project(tmp_path: Path) -> Path:
    """Create a minimal project with graph, docs, and code for ctx testing."""
    import yaml

    project = tmp_path / "proj"
    project.mkdir()

    # Graph.
    graph_dir = project / ".beadloom" / "_graph"
    graph_dir.mkdir(parents=True)
    (graph_dir / "features.yml").write_text(
        yaml.dump(
            {
                "nodes": [
                    {"ref_id": "PROJ-1", "kind": "feature", "summary": "Track filtering"},
                    {"ref_id": "routing", "kind": "domain", "summary": "Routing domain"},
                ],
                "edges": [
                    {"src": "PROJ-1", "dst": "routing", "kind": "part_of"},
                ],
            }
        )
    )

    # Docs.
    docs_dir = project / "docs"
    docs_dir.mkdir()
    (docs_dir / "spec.md").write_text("## Specification\n\nTrack filtering rules.\n")

    # Source.
    src_dir = project / "src"
    src_dir.mkdir()
    (src_dir / "api.py").write_text("# beadloom:feature=PROJ-1\ndef list_tracks():\n    pass\n")

    # Reindex to populate DB.
    from beadloom.application.reindex import reindex

    reindex(project)
    return project


class TestCtxCommand:
    def test_ctx_json_output(self, tmp_path: Path) -> None:
        project = _setup_project(tmp_path)
        runner = CliRunner()
        result = runner.invoke(main, ["ctx", "PROJ-1", "--json", "--project", str(project)])
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data["version"] == 2
        assert data["focus"]["ref_id"] == "PROJ-1"

    def test_ctx_markdown_output(self, tmp_path: Path) -> None:
        project = _setup_project(tmp_path)
        runner = CliRunner()
        result = runner.invoke(main, ["ctx", "PROJ-1", "--project", str(project)])
        assert result.exit_code == 0, result.output
        # Should contain focus node info.
        assert "PROJ-1" in result.output

    def test_ctx_multiple_ref_ids(self, tmp_path: Path) -> None:
        project = _setup_project(tmp_path)
        runner = CliRunner()
        result = runner.invoke(
            main, ["ctx", "PROJ-1", "routing", "--json", "--project", str(project)]
        )
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        node_ids = {n["ref_id"] for n in data["graph"]["nodes"]}
        assert "PROJ-1" in node_ids
        assert "routing" in node_ids

    def test_ctx_depth_flag(self, tmp_path: Path) -> None:
        project = _setup_project(tmp_path)
        runner = CliRunner()
        result = runner.invoke(
            main, ["ctx", "PROJ-1", "--depth", "1", "--json", "--project", str(project)]
        )
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data["version"] == 2

    def test_ctx_max_nodes_flag(self, tmp_path: Path) -> None:
        project = _setup_project(tmp_path)
        runner = CliRunner()
        result = runner.invoke(
            main, ["ctx", "PROJ-1", "--max-nodes", "5", "--json", "--project", str(project)]
        )
        assert result.exit_code == 0, result.output

    def test_ctx_max_chunks_flag(self, tmp_path: Path) -> None:
        project = _setup_project(tmp_path)
        runner = CliRunner()
        result = runner.invoke(
            main, ["ctx", "PROJ-1", "--max-chunks", "3", "--json", "--project", str(project)]
        )
        assert result.exit_code == 0, result.output

    def test_ctx_not_found(self, tmp_path: Path) -> None:
        project = _setup_project(tmp_path)
        runner = CliRunner()
        result = runner.invoke(main, ["ctx", "NONEXISTENT", "--project", str(project)])
        assert result.exit_code != 0
        assert "not found" in result.output.lower()

    def test_ctx_no_db(self, tmp_path: Path) -> None:
        """Running ctx without reindex should produce an error."""
        project = tmp_path / "empty"
        project.mkdir()
        runner = CliRunner()
        result = runner.invoke(main, ["ctx", "PROJ-1", "--project", str(project)])
        assert result.exit_code != 0

    def test_ctx_markdown_flag_explicit(self, tmp_path: Path) -> None:
        project = _setup_project(tmp_path)
        runner = CliRunner()
        result = runner.invoke(main, ["ctx", "PROJ-1", "--markdown", "--project", str(project)])
        assert result.exit_code == 0, result.output
        assert "PROJ-1" in result.output

    def test_ctx_markdown_no_h3_chunk_headers(self, tmp_path: Path) -> None:
        """Chunk boundaries must NOT use ### heading format."""
        project = _setup_project(tmp_path)
        runner = CliRunner()
        result = runner.invoke(main, ["ctx", "PROJ-1", "--project", str(project)])
        assert result.exit_code == 0, result.output
        # Old format (### heading with section in parens) must not appear.
        assert "### Specification (spec)" not in result.output


class TestCtxCacheTransparency:
    """`beadloom ctx` now routes through SqliteCache (S5 .22).

    The cache must be invisible at the CLI boundary: the same invocation
    must yield a semantically-identical bundle whether freshly built (first
    call, cache miss) or served from the persisted L2 cache (second call,
    hit). Note the *bundle* is identical; the L2 hit path round-trips through
    canonical (sort_keys) JSON, so the pretty-printed CLI key ORDER may differ
    while the parsed object and its etag are stable — that is the transparency
    contract being asserted.
    """

    def test_repeated_json_invocations_yield_equal_bundles(
        self, tmp_path: Path
    ) -> None:
        from beadloom.context_oracle.cache import compute_etag

        project = _setup_project(tmp_path)
        runner = CliRunner()

        first = runner.invoke(
            main, ["ctx", "PROJ-1", "--json", "--project", str(project)]
        )
        assert first.exit_code == 0, first.output

        # Second call hits the L2 cache populated by the first.
        second = runner.invoke(
            main, ["ctx", "PROJ-1", "--json", "--project", str(project)]
        )
        assert second.exit_code == 0, second.output

        first_bundle = json.loads(first.output)
        second_bundle = json.loads(second.output)
        # Parsed bundles are equal (transparent cache).
        assert second_bundle == first_bundle
        # Etag (canonical serialization) is identical → byte-stable payload.
        assert compute_etag(second_bundle) == compute_etag(first_bundle)

    def test_cache_hit_persisted_in_bundle_cache_table(
        self, tmp_path: Path
    ) -> None:
        """After a ctx call the L2 bundle_cache table holds the bundle."""
        from beadloom.context_oracle.cache import bundle_cache_key
        from beadloom.infrastructure.db import open_db

        project = _setup_project(tmp_path)
        runner = CliRunner()
        result = runner.invoke(
            main, ["ctx", "PROJ-1", "--json", "--project", str(project)]
        )
        assert result.exit_code == 0, result.output

        conn = open_db(project / ".beadloom" / "beadloom.db")
        try:
            row = conn.execute(
                "SELECT cache_key FROM bundle_cache WHERE cache_key = ?",
                (bundle_cache_key(["PROJ-1"], 2, 20, 10),),
            ).fetchone()
        finally:
            conn.close()
        assert row is not None


class TestFormatMarkdownUnit:
    """Unit tests for _format_markdown chunk separator format."""

    def test_chunk_separator_uses_hr(self) -> None:
        """Chunk headers use --- separator instead of ### heading."""
        # Arrange
        from beadloom.services.cli import _format_markdown

        bundle: dict[str, object] = {
            "focus": {"ref_id": "X-1", "kind": "feature", "summary": "Test"},
            "graph": {"nodes": [], "edges": []},
            "text_chunks": [
                {
                    "heading": "Overview",
                    "section": "spec",
                    "doc_path": "overview.md",
                    "content": "Some content here.",
                },
            ],
            "code_symbols": [],
            "sync_status": {},
        }

        # Act
        output = _format_markdown(bundle)

        # Assert
        assert "---" in output
        assert "**Overview** | `spec` | _overview.md_" in output
        assert "### Overview" not in output

    def test_multiple_chunks_each_have_hr(self) -> None:
        """Each chunk boundary gets its own --- separator."""
        # Arrange
        from beadloom.services.cli import _format_markdown

        bundle: dict[str, object] = {
            "focus": {"ref_id": "X-1", "kind": "feature", "summary": "Test"},
            "graph": {"nodes": [], "edges": []},
            "text_chunks": [
                {
                    "heading": "First",
                    "section": "spec",
                    "doc_path": "first.md",
                    "content": "First content.",
                },
                {
                    "heading": "Second",
                    "section": "guide",
                    "doc_path": "second.md",
                    "content": "Second content.",
                },
            ],
            "code_symbols": [],
            "sync_status": {},
        }

        # Act
        output = _format_markdown(bundle)

        # Assert
        assert output.count("---") == 2
        assert "**First** | `spec` | _first.md_" in output
        assert "**Second** | `guide` | _second.md_" in output

    def test_no_heading_collision_with_content(self) -> None:
        """Content with ### headings does not collide with chunk boundaries."""
        # Arrange
        from beadloom.services.cli import _format_markdown

        bundle: dict[str, object] = {
            "focus": {"ref_id": "X-1", "kind": "feature", "summary": "Test"},
            "graph": {"nodes": [], "edges": []},
            "text_chunks": [
                {
                    "heading": "BFS Algorithm",
                    "section": "spec",
                    "doc_path": "bfs.md",
                    "content": "### BFS Algorithm\nBFS traverses the graph...",
                },
            ],
            "code_symbols": [],
            "sync_status": {},
        }

        # Act
        output = _format_markdown(bundle)

        # Assert — the ### in content is the only ### heading
        lines = output.split("\n")
        h3_lines = [line for line in lines if line.startswith("### ")]
        assert len(h3_lines) == 1
        assert h3_lines[0] == "### BFS Algorithm"
        # The chunk boundary uses --- not ###
        assert "---" in output
        assert "**BFS Algorithm** | `spec` | _bfs.md_" in output
