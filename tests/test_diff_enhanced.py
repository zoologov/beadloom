"""Tests for enhanced graph diff — source, tags, and snapshot integration."""

from __future__ import annotations

import json
import sqlite3
import textwrap
from io import StringIO
from unittest.mock import patch

import pytest

from beadloom.graph.diff import (
    GraphDiff,
    NodeChange,
    _parse_yaml_content,
    compute_diff_from_snapshot,
    diff_to_dict,
    render_diff,
)
from beadloom.graph.snapshot import save_snapshot
from beadloom.infrastructure.db import create_schema


@pytest.fixture()
def conn() -> sqlite3.Connection:
    """Create an in-memory DB with full schema."""
    db = sqlite3.connect(":memory:")
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys=ON")
    create_schema(db)
    return db


@pytest.fixture()
def populated_conn(conn: sqlite3.Connection) -> sqlite3.Connection:
    """DB with sample nodes, edges, and symbols."""
    conn.execute(
        "INSERT INTO nodes (ref_id, kind, summary, source, extra) VALUES (?, ?, ?, ?, ?)",
        ("auth", "domain", "Authentication", "src/auth/", json.dumps({"tags": ["core"]})),
    )
    conn.execute(
        "INSERT INTO nodes (ref_id, kind, summary, source, extra) VALUES (?, ?, ?, ?, ?)",
        ("billing", "domain", "Billing system", "src/billing/", json.dumps({"tags": ["feature"]})),
    )
    conn.execute(
        "INSERT INTO edges (src_ref_id, dst_ref_id, kind) VALUES (?, ?, ?)",
        ("billing", "auth", "uses"),
    )
    conn.commit()
    return conn


class TestNodeChangeNewFields:
    """Test NodeChange dataclass with new source/tags/symbols fields."""

    def test_default_values(self) -> None:
        nc = NodeChange(ref_id="x", kind="domain", change_type="added")
        assert nc.old_source is None
        assert nc.new_source is None
        assert nc.old_tags == ()
        assert nc.new_tags == ()
        assert nc.symbols_added == 0
        assert nc.symbols_removed == 0

    def test_with_source_and_tags(self) -> None:
        nc = NodeChange(
            ref_id="auth",
            kind="domain",
            change_type="changed",
            old_source="src/auth/",
            new_source="src/auth-v2/",
            old_tags=("core",),
            new_tags=("core", "v2"),
        )
        assert nc.old_source == "src/auth/"
        assert nc.new_source == "src/auth-v2/"
        assert nc.old_tags == ("core",)
        assert nc.new_tags == ("core", "v2")

    def test_with_symbols(self) -> None:
        nc = NodeChange(
            ref_id="auth",
            kind="domain",
            change_type="changed",
            symbols_added=5,
            symbols_removed=2,
        )
        assert nc.symbols_added == 5
        assert nc.symbols_removed == 2


class TestParseYamlContentEnhanced:
    """Test that _parse_yaml_content extracts source and tags."""

    def test_extracts_source(self) -> None:
        yaml_content = textwrap.dedent("""\
            nodes:
              - ref_id: auth
                kind: domain
                summary: Auth module
                source: src/auth/
        """)
        nodes, _ = _parse_yaml_content(yaml_content)
        assert nodes["auth"]["source"] == "src/auth/"

    def test_extracts_tags(self) -> None:
        yaml_content = textwrap.dedent("""\
            nodes:
              - ref_id: auth
                kind: domain
                summary: Auth module
                tags: [core, security]
        """)
        nodes, _ = _parse_yaml_content(yaml_content)
        assert nodes["auth"]["tags"] == ("core", "security")

    def test_missing_source_defaults_empty(self) -> None:
        yaml_content = textwrap.dedent("""\
            nodes:
              - ref_id: auth
                kind: domain
                summary: Auth module
        """)
        nodes, _ = _parse_yaml_content(yaml_content)
        assert nodes["auth"]["source"] == ""

    def test_missing_tags_defaults_empty_tuple(self) -> None:
        yaml_content = textwrap.dedent("""\
            nodes:
              - ref_id: auth
                kind: domain
                summary: Auth module
        """)
        nodes, _ = _parse_yaml_content(yaml_content)
        assert nodes["auth"]["tags"] == ()

    def test_tags_sorted(self) -> None:
        yaml_content = textwrap.dedent("""\
            nodes:
              - ref_id: auth
                kind: domain
                summary: Auth module
                tags: [zebra, alpha]
        """)
        nodes, _ = _parse_yaml_content(yaml_content)
        assert nodes["auth"]["tags"] == ("alpha", "zebra")


class TestComputeDiffSourceChanges:
    """Test that compute_diff detects source path changes."""

    def test_source_change_detected(self, tmp_path: pytest.TempPathFactory) -> None:
        """Source path change is detected as a 'changed' node."""
        # We test via _parse_yaml_content comparison logic directly
        # since compute_diff needs a git repo. Test node comparison inline.
        old_yaml = textwrap.dedent("""\
            nodes:
              - ref_id: auth
                kind: domain
                summary: Auth
                source: src/auth/
        """)
        new_yaml = textwrap.dedent("""\
            nodes:
              - ref_id: auth
                kind: domain
                summary: Auth
                source: src/auth-v2/
        """)
        old_nodes, _ = _parse_yaml_content(old_yaml)
        new_nodes, _ = _parse_yaml_content(new_yaml)

        # source differs -> should be "changed"
        assert old_nodes["auth"]["source"] != new_nodes["auth"]["source"]

    def test_tag_change_detected(self) -> None:
        old_yaml = textwrap.dedent("""\
            nodes:
              - ref_id: auth
                kind: domain
                summary: Auth
                tags: [core]
        """)
        new_yaml = textwrap.dedent("""\
            nodes:
              - ref_id: auth
                kind: domain
                summary: Auth
                tags: [core, v2]
        """)
        old_nodes, _ = _parse_yaml_content(old_yaml)
        new_nodes, _ = _parse_yaml_content(new_yaml)

        assert old_nodes["auth"]["tags"] != new_nodes["auth"]["tags"]


class TestComputeDiffFromSnapshot:
    """Test compute_diff_from_snapshot integration with snapshot storage."""

    def test_no_changes(self, populated_conn: sqlite3.Connection) -> None:
        snap_id = save_snapshot(populated_conn)
        diff = compute_diff_from_snapshot(populated_conn, snap_id)
        assert not diff.has_changes
        assert diff.since_ref == f"snapshot:{snap_id}"

    def test_added_node(self, populated_conn: sqlite3.Connection) -> None:
        snap_id = save_snapshot(populated_conn)
        populated_conn.execute(
            "INSERT INTO nodes (ref_id, kind, summary) VALUES (?, ?, ?)",
            ("payments", "domain", "Payment processing"),
        )
        populated_conn.commit()

        diff = compute_diff_from_snapshot(populated_conn, snap_id)
        assert diff.has_changes
        added = [n for n in diff.nodes if n.change_type == "added"]
        assert len(added) == 1
        assert added[0].ref_id == "payments"

    def test_removed_node(self, populated_conn: sqlite3.Connection) -> None:
        snap_id = save_snapshot(populated_conn)
        populated_conn.execute("DELETE FROM edges WHERE src_ref_id = ?", ("billing",))
        populated_conn.execute("DELETE FROM nodes WHERE ref_id = ?", ("billing",))
        populated_conn.commit()

        diff = compute_diff_from_snapshot(populated_conn, snap_id)
        assert diff.has_changes
        removed = [n for n in diff.nodes if n.change_type == "removed"]
        assert len(removed) == 1
        assert removed[0].ref_id == "billing"

    def test_changed_summary(self, populated_conn: sqlite3.Connection) -> None:
        snap_id = save_snapshot(populated_conn)
        populated_conn.execute(
            "UPDATE nodes SET summary = ? WHERE ref_id = ?",
            ("Updated auth", "auth"),
        )
        populated_conn.commit()

        diff = compute_diff_from_snapshot(populated_conn, snap_id)
        assert diff.has_changes
        changed = [n for n in diff.nodes if n.change_type == "changed"]
        assert len(changed) == 1
        assert changed[0].old_summary == "Authentication"
        assert changed[0].new_summary == "Updated auth"

    def test_changed_source(self, populated_conn: sqlite3.Connection) -> None:
        snap_id = save_snapshot(populated_conn)
        populated_conn.execute(
            "UPDATE nodes SET source = ? WHERE ref_id = ?",
            ("src/auth-v2/", "auth"),
        )
        populated_conn.commit()

        diff = compute_diff_from_snapshot(populated_conn, snap_id)
        changed = [n for n in diff.nodes if n.change_type == "changed"]
        assert len(changed) == 1
        assert changed[0].old_source == "src/auth/"
        assert changed[0].new_source == "src/auth-v2/"

    def test_changed_tags(self, populated_conn: sqlite3.Connection) -> None:
        snap_id = save_snapshot(populated_conn)
        populated_conn.execute(
            "UPDATE nodes SET extra = ? WHERE ref_id = ?",
            (json.dumps({"tags": ["core", "security"]}), "auth"),
        )
        populated_conn.commit()

        diff = compute_diff_from_snapshot(populated_conn, snap_id)
        changed = [n for n in diff.nodes if n.change_type == "changed"]
        assert len(changed) == 1
        assert changed[0].old_tags == ("core",)
        assert changed[0].new_tags == ("core", "security")

    def test_added_edge(self, populated_conn: sqlite3.Connection) -> None:
        snap_id = save_snapshot(populated_conn)
        populated_conn.execute(
            "INSERT INTO edges (src_ref_id, dst_ref_id, kind) VALUES (?, ?, ?)",
            ("auth", "billing", "depends_on"),
        )
        populated_conn.commit()

        diff = compute_diff_from_snapshot(populated_conn, snap_id)
        assert diff.has_changes
        added_edges = [e for e in diff.edges if e.change_type == "added"]
        assert len(added_edges) == 1

    def test_removed_edge(self, populated_conn: sqlite3.Connection) -> None:
        snap_id = save_snapshot(populated_conn)
        populated_conn.execute(
            "DELETE FROM edges WHERE src_ref_id = ? AND dst_ref_id = ?",
            ("billing", "auth"),
        )
        populated_conn.commit()

        diff = compute_diff_from_snapshot(populated_conn, snap_id)
        removed_edges = [e for e in diff.edges if e.change_type == "removed"]
        assert len(removed_edges) == 1

    def test_snapshot_not_found(self, conn: sqlite3.Connection) -> None:
        with pytest.raises(ValueError, match="not found"):
            compute_diff_from_snapshot(conn, 9999)


class TestRenderDiffEnhanced:
    """Test render_diff shows source/tag/symbol changes."""

    def test_shows_source_change(self) -> None:
        diff = GraphDiff(
            since_ref="test",
            nodes=(
                NodeChange(
                    ref_id="auth",
                    kind="domain",
                    change_type="changed",
                    old_source="src/auth/",
                    new_source="src/auth-v2/",
                ),
            ),
            edges=(),
        )
        from rich.console import Console

        buf = StringIO()
        console = Console(file=buf, force_terminal=False, no_color=True)
        render_diff(diff, console)
        output = buf.getvalue()
        assert "src/auth/" in output
        assert "src/auth-v2/" in output

    def test_shows_tag_change(self) -> None:
        diff = GraphDiff(
            since_ref="test",
            nodes=(
                NodeChange(
                    ref_id="auth",
                    kind="domain",
                    change_type="changed",
                    old_tags=("core",),
                    new_tags=("core", "v2"),
                ),
            ),
            edges=(),
        )
        from rich.console import Console

        buf = StringIO()
        console = Console(file=buf, force_terminal=False, no_color=True)
        render_diff(diff, console)
        output = buf.getvalue()
        assert "['core']" in output
        assert "['core', 'v2']" in output

    def test_shows_symbols_change(self) -> None:
        diff = GraphDiff(
            since_ref="test",
            nodes=(
                NodeChange(
                    ref_id="auth",
                    kind="domain",
                    change_type="changed",
                    symbols_added=5,
                    symbols_removed=2,
                ),
            ),
            edges=(),
        )
        from rich.console import Console

        buf = StringIO()
        console = Console(file=buf, force_terminal=False, no_color=True)
        render_diff(diff, console)
        output = buf.getvalue()
        assert "+5" in output
        assert "-2" in output


class TestDiffToDictEnhanced:
    """Test diff_to_dict includes new fields."""

    def test_includes_source_and_tags(self) -> None:
        diff = GraphDiff(
            since_ref="test",
            nodes=(
                NodeChange(
                    ref_id="auth",
                    kind="domain",
                    change_type="changed",
                    old_source="src/auth/",
                    new_source="src/auth-v2/",
                    old_tags=("core",),
                    new_tags=("core", "v2"),
                    symbols_added=3,
                    symbols_removed=1,
                ),
            ),
            edges=(),
        )
        result = diff_to_dict(diff)
        node = result["nodes"][0]  # type: ignore[index]
        assert node["old_source"] == "src/auth/"
        assert node["new_source"] == "src/auth-v2/"
        assert node["old_tags"] == ("core",)
        assert node["new_tags"] == ("core", "v2")
        assert node["symbols_added"] == 3
        assert node["symbols_removed"] == 1


class TestBackwardCompatibility:
    """Test that old YAML without source/tags still works."""

    def test_old_yaml_no_source_no_tags(self) -> None:
        yaml_content = textwrap.dedent("""\
            nodes:
              - ref_id: auth
                kind: domain
                summary: Auth module
        """)
        nodes, _ = _parse_yaml_content(yaml_content)
        assert nodes["auth"]["source"] == ""
        assert nodes["auth"]["tags"] == ()
        assert nodes["auth"]["kind"] == "domain"
        assert nodes["auth"]["summary"] == "Auth module"
