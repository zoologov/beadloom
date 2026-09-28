"""Incremental reindex falls back to a full one when a graph file's hash moved.

``_graph_yaml_changed`` compares the graph files of two file indexes by hash: an
added, removed or edited ``.beadloom/_graph/*.yml`` means the incremental path
cannot patch the index and must rebuild it. Split out of ``tests/test_reindex.py``
(BDL-074 ``beadloom-2mj3.7``): pure dictionaries in, a boolean out, so unit.
"""

from __future__ import annotations


class TestGraphYamlChanged:
    """Unit tests for the _graph_yaml_changed helper."""

    def test_no_graph_files_returns_false(self) -> None:
        from beadloom.application.reindex import _graph_yaml_changed

        current: dict[str, tuple[str, str]] = {
            "docs/a.md": ("abc", "doc"),
            "src/b.py": ("def", "code"),
        }
        stored: dict[str, tuple[str, str]] = {
            "docs/a.md": ("abc", "doc"),
            "src/b.py": ("def", "code"),
        }
        assert _graph_yaml_changed(current, stored) is False

    def test_same_graph_returns_false(self) -> None:
        from beadloom.application.reindex import _graph_yaml_changed

        current: dict[str, tuple[str, str]] = {
            ".beadloom/_graph/g.yml": ("aaa", "graph"),
            "docs/a.md": ("bbb", "doc"),
        }
        stored: dict[str, tuple[str, str]] = {
            ".beadloom/_graph/g.yml": ("aaa", "graph"),
            "docs/a.md": ("bbb", "doc"),
        }
        assert _graph_yaml_changed(current, stored) is False

    def test_changed_hash_returns_true(self) -> None:
        from beadloom.application.reindex import _graph_yaml_changed

        current: dict[str, tuple[str, str]] = {
            ".beadloom/_graph/g.yml": ("new_hash", "graph"),
        }
        stored: dict[str, tuple[str, str]] = {
            ".beadloom/_graph/g.yml": ("old_hash", "graph"),
        }
        assert _graph_yaml_changed(current, stored) is True

    def test_added_graph_returns_true(self) -> None:
        from beadloom.application.reindex import _graph_yaml_changed

        current: dict[str, tuple[str, str]] = {
            ".beadloom/_graph/g.yml": ("aaa", "graph"),
            ".beadloom/_graph/extra.yml": ("bbb", "graph"),
        }
        stored: dict[str, tuple[str, str]] = {
            ".beadloom/_graph/g.yml": ("aaa", "graph"),
        }
        assert _graph_yaml_changed(current, stored) is True

    def test_deleted_graph_returns_true(self) -> None:
        from beadloom.application.reindex import _graph_yaml_changed

        current: dict[str, tuple[str, str]] = {}
        stored: dict[str, tuple[str, str]] = {
            ".beadloom/_graph/g.yml": ("aaa", "graph"),
        }
        assert _graph_yaml_changed(current, stored) is True
