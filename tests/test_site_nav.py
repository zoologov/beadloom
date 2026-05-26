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
    render_nav,
    render_nav_config,
    render_sidebar,
    render_sidebar_ru,
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


def test_documentation_group_prunes_empty_dirs(tmp_path: Path) -> None:
    """A docs subdir with no markdown (directly or nested) emits no group."""
    (tmp_path / "docs" / "empty" / "deeper").mkdir(parents=True)
    (tmp_path / "docs" / "guides").mkdir()
    (tmp_path / "docs" / "guides" / "intro.md").write_text("# Intro\n", encoding="utf-8")
    js = render_documentation_group(tmp_path)
    # The non-empty dir is a group; the empty dir tree is pruned (no dead group).
    assert '"Guides"' in js
    assert '"Empty"' not in js
    assert '"Deeper"' not in js


def test_documentation_group_skips_dotfiles_and_dotdirs(tmp_path: Path) -> None:
    """Hidden ``.md`` files and hidden subdirectories are excluded from nav."""
    (tmp_path / "docs" / ".hidden").mkdir(parents=True)
    (tmp_path / "docs" / ".hidden" / "secret.md").write_text("# x\n", encoding="utf-8")
    (tmp_path / "docs" / ".dotfile.md").write_text("# x\n", encoding="utf-8")
    (tmp_path / "docs" / "visible.md").write_text("# Visible\n", encoding="utf-8")
    js = render_documentation_group(tmp_path)
    assert 'link: "/docs/visible"' in js
    assert "dotfile" not in js
    assert "secret" not in js
    assert "Hidden" not in js


def test_documentation_links_resolve_to_existing_docs(tmp_path: Path) -> None:
    """Every emitted doc nav link maps to a real ``.md`` under docs/ (no dead nav)."""
    _seed_docs(tmp_path)
    js = render_documentation_group(tmp_path)
    docs_dir = tmp_path / "docs"
    for line in js.splitlines():
        stripped = line.strip()
        if 'link: "/docs/' not in stripped:
            continue
        url = stripped.split('link: "', 1)[1].split('"', 1)[0]
        rel = url[len("/docs/") :]
        if not rel:  # the /docs/ landing link has no backing .md
            continue
        assert (docs_dir / f"{rel}.md").is_file(), f"dead doc nav link: {url}"


def test_architecture_links_resolve_to_existing_nodes(conn: sqlite3.Connection) -> None:
    """Every emitted Architecture nav link targets a real node page kind (no dead nav)."""
    js = render_architecture_group(conn)
    node_kinds = {
        str(row["ref_id"]): str(row["kind"])
        for row in conn.execute("SELECT ref_id, kind FROM nodes").fetchall()
    }
    kind_dir = {"service": "services", "domain": "domains", "feature": "features"}
    for line in js.splitlines():
        stripped = line.strip()
        if "link:" not in stripped or "/architecture" in stripped:
            continue
        url = stripped.split('link: "', 1)[1].split('"', 1)[0]
        parts = url.strip("/").split("/")
        assert len(parts) == 2, url
        directory, ref = parts
        assert ref in node_kinds, f"dead arch nav link to unknown node: {url}"
        assert kind_dir[node_kinds[ref]] == directory, f"wrong dir for {ref}: {url}"


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


# ---------------------------------------------------------------------------
# BDL-046 BEAD-02 — restructured ordered sidebar + empty top nav
# ---------------------------------------------------------------------------


def _top_level_texts(js: str) -> list[str]:
    """The ``text:`` labels of the top-level sidebar entries, in document order.

    Each top-level entry opens with ``  {`` (exactly two-space indentation). For a
    flat entry the ``text:`` key is inline on that line; for a group it is on the
    next line at four-space indentation. We capture the first ``text:`` per entry.
    """
    texts: list[str] = []
    lines = js.splitlines()
    for idx, line in enumerate(lines):
        if not (line.startswith("  {") and not line.startswith("   ")):
            continue
        head = line if 'text: "' in line else lines[idx + 1]
        texts.append(head.split('text: "', 1)[1].split('"', 1)[0])
    return texts


def test_render_nav_is_empty(conn: sqlite3.Connection) -> None:
    """Top nav is emptied — theme keeps appearance/search/locale regardless."""
    assert render_nav() == "[]"


def test_render_nav_config_top_nav_is_empty(
    conn: sqlite3.Connection, tmp_path: Path
) -> None:
    _seed_docs(tmp_path)
    js = render_nav_config(conn, tmp_path)
    assert re.search(r"export const nav = \[\s*\];", js)


def test_sidebar_top_level_order_with_getting_started(
    conn: sqlite3.Connection, tmp_path: Path
) -> None:
    _seed_docs(tmp_path)
    js = render_sidebar(conn, docs_root=tmp_path / "docs", has_getting_started=True)
    assert _top_level_texts(js) == [
        "About",
        "Getting Started",
        "Dashboard",
        "Architecture",
        "Landscape map",
        "Documentation",
    ]


def test_sidebar_omits_getting_started_when_absent(
    conn: sqlite3.Connection, tmp_path: Path
) -> None:
    _seed_docs(tmp_path)
    js = render_sidebar(conn, docs_root=tmp_path / "docs", has_getting_started=False)
    assert _top_level_texts(js) == [
        "About",
        "Dashboard",
        "Architecture",
        "Landscape map",
        "Documentation",
    ]
    # No top-level Getting Started entry (a docs-tree leaf of the same name may
    # still exist inside the Documentation group — that is fine and unrelated).
    assert "Getting Started" not in _top_level_texts(js)


def test_sidebar_about_first_links_root(
    conn: sqlite3.Connection, tmp_path: Path
) -> None:
    js = render_sidebar(conn, docs_root=tmp_path / "docs", has_getting_started=False)
    assert '{ text: "About", link: "/" }' in js


def test_sidebar_getting_started_links_doc(
    conn: sqlite3.Connection, tmp_path: Path
) -> None:
    js = render_sidebar(conn, docs_root=tmp_path / "docs", has_getting_started=True)
    assert "Getting Started" in _top_level_texts(js)
    assert 'link: "/docs/getting-started" }' in js


def test_sidebar_dashboard_is_flat(
    conn: sqlite3.Connection, tmp_path: Path
) -> None:
    """Dashboard is a plain link, not a one-child 'Metrics' group."""
    js = render_sidebar(conn, docs_root=tmp_path / "docs", has_getting_started=False)
    assert '{ text: "Dashboard", link: "/dashboard" }' in js
    assert "Metrics" not in js


def test_sidebar_landscape_is_flat(
    conn: sqlite3.Connection, tmp_path: Path
) -> None:
    """Landscape map is a plain link, not a one-child 'Map' group."""
    js = render_sidebar(conn, docs_root=tmp_path / "docs", has_getting_started=False)
    assert '{ text: "Landscape map", link: "/landscape" }' in js
    assert '{ text: "Map"' not in js


def test_sidebar_architecture_collapsed_with_overview_link(
    conn: sqlite3.Connection, tmp_path: Path
) -> None:
    js = render_sidebar(conn, docs_root=tmp_path / "docs", has_getting_started=False)
    assert '"Architecture"' in js
    assert "collapsed: true" in js
    # Overview entry now points at the dedicated /architecture page (BEAD-03),
    # not the former /index landing.
    assert '{ text: "Architecture overview", link: "/architecture" }' in js
    assert 'link: "/index"' not in js


def test_sidebar_documentation_expanded_overview_led(
    conn: sqlite3.Connection, tmp_path: Path
) -> None:
    _seed_docs(tmp_path)
    js = render_sidebar(conn, docs_root=tmp_path / "docs", has_getting_started=False)
    assert '"Documentation"' in js
    assert "collapsed: false" in js
    overview_pos = js.index('{ text: "Overview", link: "/docs/" }')
    doc_section = js.index('"Documentation"')
    assert overview_pos > doc_section


def test_sidebar_is_deterministic(
    conn: sqlite3.Connection, tmp_path: Path
) -> None:
    _seed_docs(tmp_path)
    a = render_sidebar(conn, docs_root=tmp_path / "docs", has_getting_started=True)
    b = render_sidebar(conn, docs_root=tmp_path / "docs", has_getting_started=True)
    assert a == b


def test_nav_config_auto_detects_getting_started(
    conn: sqlite3.Connection, tmp_path: Path
) -> None:
    """``render_nav_config`` emits the top-level Getting Started entry iff the
    backing page exists under ``docs/`` (link-safe auto-detection)."""
    js_absent = render_nav_config(conn, tmp_path)  # no docs/ dir at all
    assert "Getting Started" not in _top_level_texts(_sidebar_array(js_absent))
    _seed_docs(tmp_path)  # adds docs/getting-started.md
    js_present = render_nav_config(conn, tmp_path)
    assert "Getting Started" in _top_level_texts(_sidebar_array(js_present))


def _sidebar_array(config_js: str) -> str:
    """Extract the ``sidebar`` array body from a generated config module."""
    return config_js.split("export const sidebar = ", 1)[1]


def test_sidebar_balanced_brackets(
    conn: sqlite3.Connection, tmp_path: Path
) -> None:
    _seed_docs(tmp_path)
    js = render_sidebar(conn, docs_root=tmp_path / "docs", has_getting_started=True)
    assert js.count("[") == js.count("]")
    assert js.count("{") == js.count("}")


# ---------------------------------------------------------------------------
# BDL-046 BEAD-04 — RU locale sidebar (curated About-only) + navRu/sidebarRu
# ---------------------------------------------------------------------------


def test_sidebar_ru_about_links_ru_home(
    conn: sqlite3.Connection, tmp_path: Path
) -> None:
    """The only translated page: About points at the RU home ``/ru/``."""
    js = render_sidebar_ru(conn, docs_root=tmp_path / "docs", has_getting_started=False)
    assert '{ text: "О проекте", link: "/ru/" }' in js
    # EN About link must not leak into the RU sidebar's About entry.
    assert '{ text: "About", link: "/" }' not in js


def test_sidebar_ru_top_level_order_matches_en(
    conn: sqlite3.Connection, tmp_path: Path
) -> None:
    """RU sidebar mirrors the EN top-level ORDER exactly (only labels differ)."""
    _seed_docs(tmp_path)
    ru = render_sidebar_ru(
        conn, docs_root=tmp_path / "docs", has_getting_started=True
    )
    assert _top_level_texts(ru) == [
        "О проекте",
        "С чего начать",
        "Дашборд",
        "Архитектура",
        "Карта ландшафта",
        "Документация",
    ]


def test_sidebar_ru_omits_getting_started_when_absent(
    conn: sqlite3.Connection, tmp_path: Path
) -> None:
    _seed_docs(tmp_path)
    ru = render_sidebar_ru(
        conn, docs_root=tmp_path / "docs", has_getting_started=False
    )
    assert _top_level_texts(ru) == [
        "О проекте",
        "Дашборд",
        "Архитектура",
        "Карта ландшафта",
        "Документация",
    ]


def test_sidebar_ru_non_about_links_point_at_en_routes(
    conn: sqlite3.Connection, tmp_path: Path
) -> None:
    """Only About is translated; every other link targets the EN routes."""
    _seed_docs(tmp_path)
    ru = render_sidebar_ru(
        conn, docs_root=tmp_path / "docs", has_getting_started=True
    )
    assert 'link: "/dashboard"' in ru
    assert 'link: "/landscape"' in ru
    assert 'link: "/architecture"' in ru
    assert 'link: "/docs/getting-started"' in ru
    assert 'link: "/docs/"' in ru
    assert 'link: "/services/beadloom"' in ru
    assert 'link: "/domains/context-oracle"' in ru
    # No non-About link is rebased under /ru/.
    for line in ru.splitlines():
        stripped = line.strip()
        if "link:" not in stripped:
            continue
        url = stripped.split('link: "', 1)[1].split('"', 1)[0]
        if url == "/ru/":
            continue
        assert not url.startswith("/ru/"), f"non-About link rebased to RU: {url}"


def test_sidebar_ru_is_deterministic(
    conn: sqlite3.Connection, tmp_path: Path
) -> None:
    _seed_docs(tmp_path)
    a = render_sidebar_ru(conn, docs_root=tmp_path / "docs", has_getting_started=True)
    b = render_sidebar_ru(conn, docs_root=tmp_path / "docs", has_getting_started=True)
    assert a == b


def test_sidebar_ru_balanced_brackets(
    conn: sqlite3.Connection, tmp_path: Path
) -> None:
    _seed_docs(tmp_path)
    ru = render_sidebar_ru(conn, docs_root=tmp_path / "docs", has_getting_started=True)
    assert ru.count("[") == ru.count("]")
    assert ru.count("{") == ru.count("}")


def test_render_nav_config_exports_ru_locale(
    conn: sqlite3.Connection, tmp_path: Path
) -> None:
    """config.generated.mjs additionally exports navRu + sidebarRu."""
    _seed_docs(tmp_path)
    js = render_nav_config(conn, tmp_path)
    assert re.search(r"export const navRu = \[\s*\];", js)
    assert re.search(r"export const sidebarRu = \[", js)
    # The RU About link is present in the module.
    assert '{ text: "О проекте", link: "/ru/" }' in js
    # Existing EN exports remain.
    assert re.search(r"export const nav = \[", js)
    assert re.search(r"export const sidebar = \[", js)


def test_render_nav_config_ru_section_is_deterministic(
    conn: sqlite3.Connection, tmp_path: Path
) -> None:
    _seed_docs(tmp_path)
    assert render_nav_config(conn, tmp_path) == render_nav_config(conn, tmp_path)


# ---------------------------------------------------------------------------
# BDL-046 BEAD-06 — holistic edge cases (empty graph, no docs dir, RU mirror)
# ---------------------------------------------------------------------------


def test_architecture_group_empty_graph_keeps_overview_entry() -> None:
    """An empty graph still emits the Architecture group with its overview link.

    No nodes -> no part_of tree, but the group is never empty: the
    ``/architecture`` overview entry is always present (link-safe, no crash).
    """
    db = sqlite3.connect(":memory:")
    db.row_factory = sqlite3.Row
    create_schema(db)
    js = render_architecture_group(db)
    db.close()
    assert '"Architecture"' in js
    assert '{ text: "Architecture overview", link: "/architecture" }' in js


def test_render_nav_config_no_docs_dir_still_emits_all_exports(
    conn: sqlite3.Connection, tmp_path: Path
) -> None:
    """With no docs/ directory the config still exports all four arrays.

    Documentation group degrades to just its Overview link; Getting Started is
    omitted (no backing page); the module stays valid (balanced brackets).
    """
    js = render_nav_config(conn, tmp_path)  # tmp_path has no docs/
    for export in ("export const nav = ", "export const sidebar = ",
                   "export const navRu = ", "export const sidebarRu = "):
        assert export in js
    assert '{ text: "Overview", link: "/docs/" }' in js
    assert "Getting Started" not in _top_level_texts(_sidebar_array(js))
    assert js.count("{") == js.count("}")
    assert js.count("[") == js.count("]")


def test_sidebar_ru_reuses_en_architecture_subtree_labels(
    conn: sqlite3.Connection, tmp_path: Path
) -> None:
    """Only the group HEADER is Russian; interior node labels stay English.

    The RU sidebar reuses the EN Architecture/Documentation subtrees verbatim
    (same links + nesting), swapping only the top-level header label. So the
    header is 'Архитектура' but the interior 'Context Oracle' / 'Cache' node
    labels remain English (every interior link is an EN route anyway).
    """
    ru = render_sidebar_ru(conn, docs_root=tmp_path / "docs", has_getting_started=False)
    assert '"Архитектура"' in ru
    assert '"Context Oracle"' in ru  # interior node label stays EN
    assert '"Cache"' in ru
    # The EN top-level header label must not leak as a top-level entry.
    assert "Architecture" not in _top_level_texts(ru)


def test_sidebar_ru_documentation_header_is_russian(
    conn: sqlite3.Connection, tmp_path: Path
) -> None:
    _seed_docs(tmp_path)
    ru = render_sidebar_ru(conn, docs_root=tmp_path / "docs", has_getting_started=False)
    assert '"Документация"' in ru
    # Overview leaf link unchanged (EN route).
    assert '{ text: "Overview", link: "/docs/" }' in ru
