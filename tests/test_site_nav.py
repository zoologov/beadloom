"""Tests for beadloom.application.site_nav — VitePress nav/sidebar trees.

BDL-041 F4.4 BEAD-11: the Architecture sidebar group is a collapsed, ``part_of``-
nested 3-level tree with human-readable labels; the Documentation group mirrors
the ``docs/`` directory structure as a nested, collapsible tree. Both stay
deterministic (sorted, byte-stable) and emit no dead links.
"""

from __future__ import annotations

import re
import sqlite3
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pathlib import Path

from beadloom.application.site_nav import (
    human_label,
    render_architecture_group,
    render_documentation_group,
    render_nav_config,
)
from beadloom.infrastructure.db import create_schema


def _seed(conn: sqlite3.Connection) -> None:
    """A service -> domains -> features part_of hierarchy (owner's example shape)."""
    nodes = [
        ("beadloom", "service", "Beadloom CLI service.", None),
        ("context-oracle", "domain", "Context bundle building.", "src/beadloom/context_oracle"),
        ("doc-sync", "domain", "Doc-code sync tracking.", "src/beadloom/doc_sync"),
        ("cache", "feature", "Context cache.", "src/beadloom/context_oracle/cache.py"),
        ("docs-audit", "feature", "Docs audit.", "src/beadloom/doc_sync/audit.py"),
    ]
    for ref_id, kind, summary, source in nodes:
        conn.execute(
            "INSERT INTO nodes (ref_id, kind, summary, source) VALUES (?, ?, ?, ?)",
            (ref_id, kind, summary, source),
        )
    edges = [
        ("context-oracle", "beadloom", "part_of"),
        ("doc-sync", "beadloom", "part_of"),
        ("cache", "context-oracle", "part_of"),
        ("docs-audit", "doc-sync", "part_of"),
    ]
    for src, dst, kind in edges:
        conn.execute(
            "INSERT INTO edges (src_ref_id, dst_ref_id, kind) VALUES (?, ?, ?)",
            (src, dst, kind),
        )
    conn.commit()


@pytest.fixture()
def conn() -> sqlite3.Connection:
    db = sqlite3.connect(":memory:")
    db.row_factory = sqlite3.Row
    create_schema(db)
    _seed(db)
    return db


# ---------------------------------------------------------------------------
# human labels
# ---------------------------------------------------------------------------


def test_human_label_title_cases_ref() -> None:
    assert human_label("context-oracle") == "Context Oracle"
    assert human_label("cache") == "Cache"
    assert human_label("doc-sync") == "Doc Sync"
    assert human_label("beadloom") == "Beadloom"


# ---------------------------------------------------------------------------
# Architecture group — collapsed + part_of-nested + human labels
# ---------------------------------------------------------------------------


def test_architecture_group_is_collapsed(conn: sqlite3.Connection) -> None:
    js = render_architecture_group(conn)
    assert '"Architecture"' in js
    assert "collapsed: true" in js


def test_architecture_group_overview_first(conn: sqlite3.Connection) -> None:
    js = render_architecture_group(conn)
    overview_pos = js.index("Architecture overview")
    root_pos = js.index('"Beadloom"')
    assert overview_pos < root_pos


def test_architecture_group_uses_human_labels(conn: sqlite3.Connection) -> None:
    js = render_architecture_group(conn)
    assert '"Context Oracle"' in js
    assert '"Cache"' in js
    assert '"Doc Sync"' in js
    # No raw kind-suffixed labels.
    assert "Kind:" not in js
    assert '"context-oracle"' not in js.replace('link: "/domains/context-oracle"', "")


def test_architecture_group_is_part_of_nested(conn: sqlite3.Connection) -> None:
    """A feature appears under its domain, under the service root (3 levels)."""
    js = render_architecture_group(conn)
    root = js.index('"Beadloom"')
    domain = js.index('"Context Oracle"', root)
    feature = js.index('"Cache"', domain)
    # Order in the serialized tree reflects nesting: root then domain then feature.
    assert root < domain < feature
    # The feature's items live in a nested items: block (deeper than the domain).

    def _indent(token: str) -> int:
        line_start = js.rfind("\n", 0, js.index(token)) + 1
        return len(js[line_start : js.index(token)]) - len(
            js[line_start : js.index(token)].lstrip()
        )

    assert _indent('"Cache"') > _indent('"Context Oracle"') > _indent('"Beadloom"')


def test_architecture_self_edge_root_still_renders(conn: sqlite3.Connection) -> None:
    """A ``root part_of root`` self-edge must not collapse the tree to empty.

    The real dogfood graph has ``beadloom -> beadloom``; if treated as a real
    parent the service root is dropped and the whole Architecture tree vanishes.
    """
    conn.execute(
        "INSERT INTO edges (src_ref_id, dst_ref_id, kind) VALUES (?, ?, ?)",
        ("beadloom", "beadloom", "part_of"),
    )
    conn.commit()
    js = render_architecture_group(conn)
    assert '"Beadloom"' in js
    assert '"Context Oracle"' in js  # children still nested under the root


def test_architecture_links_resolve_to_node_pages(conn: sqlite3.Connection) -> None:
    js = render_architecture_group(conn)
    assert 'link: "/services/beadloom"' in js
    assert 'link: "/domains/context-oracle"' in js
    assert 'link: "/features/cache"' in js


# ---------------------------------------------------------------------------
# Documentation group — mirrors docs/ tree
# ---------------------------------------------------------------------------


def _seed_docs(root: Path) -> None:
    (root / "docs" / "domains" / "context-oracle" / "features" / "cache").mkdir(
        parents=True
    )
    (root / "docs" / "domains" / "context-oracle" / "README.md").write_text(
        "# Context Oracle\n", encoding="utf-8"
    )
    (
        root / "docs" / "domains" / "context-oracle" / "features" / "cache" / "SPEC.md"
    ).write_text("# Cache\n", encoding="utf-8")
    (root / "docs" / "getting-started.md").write_text("# Start\n", encoding="utf-8")


def test_documentation_group_is_nested_tree(tmp_path: Path) -> None:
    _seed_docs(tmp_path)
    js = render_documentation_group(tmp_path)
    assert '"Documentation"' in js
    assert "collapsed: true" in js
    # Directory becomes a nested group; its child docs nest under it.

    def _indent(token: str) -> int:
        i = js.index(token)
        line_start = js.rfind("\n", 0, i) + 1
        return len(js[line_start:i]) - len(js[line_start:i].lstrip())

    # domains group exists and the cache SPEC nests deeper than its dir labels.
    assert '"Domains"' in js
    assert _indent('"Context Oracle"') > _indent('"Domains"')


def test_documentation_links_resolve_to_published_docs(tmp_path: Path) -> None:
    _seed_docs(tmp_path)
    js = render_documentation_group(tmp_path)
    # Links are rooted at /docs/ (the published copy) and keep the path.
    assert 'link: "/docs/domains/context-oracle/README"' in js
    assert (
        'link: "/docs/domains/context-oracle/features/cache/SPEC"' in js
    )
    assert 'link: "/docs/getting-started"' in js


def test_documentation_group_empty_when_no_docs(tmp_path: Path) -> None:
    js = render_documentation_group(tmp_path)
    # Still a valid group (the /docs/ landing link), never crashes.
    assert '"Documentation"' in js


# ---------------------------------------------------------------------------
# Full config — deterministic, all sections present
# ---------------------------------------------------------------------------


def test_render_nav_config_has_all_sections(
    conn: sqlite3.Connection, tmp_path: Path
) -> None:
    _seed_docs(tmp_path)
    js = render_nav_config(conn, tmp_path)
    for section in ("Dashboard", "Architecture", "Landscape", "Documentation"):
        assert section in js
    # Dashboard + Landscape unchanged (flat).
    assert 'link: "/dashboard"' in js
    assert 'link: "/landscape"' in js


def test_render_nav_config_is_deterministic(
    conn: sqlite3.Connection, tmp_path: Path
) -> None:
    _seed_docs(tmp_path)
    assert render_nav_config(conn, tmp_path) == render_nav_config(conn, tmp_path)


def test_render_nav_config_is_valid_js_structure(
    conn: sqlite3.Connection, tmp_path: Path
) -> None:
    _seed_docs(tmp_path)
    js = render_nav_config(conn, tmp_path)
    # Balanced brackets — cheap structural guard (no node).
    assert js.count("[") == js.count("]")
    assert js.count("{") == js.count("}")
    assert re.search(r"export const nav = \[", js)
    assert re.search(r"export const sidebar = \[", js)
