"""VitePress nav/sidebar tree builders (BDL-041 F4.4 BEAD-11).

The Architecture sidebar group is a collapsed, ``part_of``-nested tree with
human-readable labels (service root -> domains -> features); the Documentation
group mirrors the ``docs/`` directory structure as a nested, collapsible tree.
Both are pure + deterministic (sorted, byte-stable) and emit only links that
resolve to a generated page (no dead nav entries).

Output is a fragment of the generated ``.vitepress/config.generated.mjs`` module
(see :mod:`beadloom.application.site`). Kept here so ``site.py`` stays small.
"""

# beadloom:domain=application

from __future__ import annotations

import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import sqlite3
    from pathlib import Path

# Node kind -> generated page sub-directory (mirrors site_pages._KIND_DIR; the
# nav links are extension-less — VitePress rewrites to clean URLs).
_KIND_DIR: dict[str, str] = {
    "domain": "domains",
    "service": "services",
    "feature": "features",
}

_INDENT = "  "


def human_label(ref_id: str) -> str:
    """A human-readable label for *ref_id* (title-cased, hyphens -> spaces).

    ``context-oracle`` -> ``Context Oracle``; ``cache`` -> ``Cache``. Matches the
    owner's example tree (``Beadloom`` / ``Context Oracle`` / ``Cache``), never the
    raw ref or a ``Kind:``-suffixed label.
    """
    words = ref_id.replace("_", "-").replace("-", " ").split()
    return " ".join(word[:1].upper() + word[1:] for word in words if word)


def _js_str(value: str) -> str:
    """A JSON-/JS-safe double-quoted string literal."""
    return json.dumps(value, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Architecture group — part_of-nested tree
# ---------------------------------------------------------------------------


def _load_arch_nodes(conn: sqlite3.Connection) -> dict[str, str]:
    """ref_id -> kind for every node we can place on an architecture page."""
    rows = conn.execute("SELECT ref_id, kind FROM nodes ORDER BY ref_id").fetchall()
    return {
        str(row["ref_id"]): str(row["kind"])
        for row in rows
        if str(row["kind"]) in _KIND_DIR
    }


def _load_part_of_children(
    conn: sqlite3.Connection, kinds: dict[str, str]
) -> dict[str, list[str]]:
    """parent ref_id -> sorted child ref_ids, from ``part_of`` edges (child -> parent)."""
    children: dict[str, list[str]] = {}
    rows = conn.execute(
        "SELECT src_ref_id, dst_ref_id FROM edges "
        "WHERE kind = 'part_of' ORDER BY dst_ref_id, src_ref_id"
    ).fetchall()
    for row in rows:
        child = str(row["src_ref_id"])
        parent = str(row["dst_ref_id"])
        if child == parent or child not in kinds or parent not in kinds:
            continue
        children.setdefault(parent, []).append(child)
    for kids in children.values():
        kids.sort()
    return children


def _arch_link(ref_id: str, kinds: dict[str, str]) -> str:
    """Extension-less nav link to a node's generated page."""
    return f"/{_KIND_DIR[kinds[ref_id]]}/{ref_id}"


def _arch_node_js(
    ref_id: str,
    kinds: dict[str, str],
    children: dict[str, list[str]],
    depth: int,
    seen: frozenset[str],
) -> list[str]:
    """Serialize one architecture node (label + link) and its nested children."""
    pad = _INDENT * depth
    label = _js_str(human_label(ref_id))
    link = _js_str(_arch_link(ref_id, kinds))
    kids = [c for c in children.get(ref_id, []) if c not in seen]
    if not kids:
        return [f"{pad}{{ text: {label}, link: {link} }}"]
    lines = [f"{pad}{{", f"{pad}{_INDENT}text: {label},", f"{pad}{_INDENT}link: {link},"]
    lines.append(f"{pad}{_INDENT}items: [")
    next_seen = seen | {ref_id}
    child_blocks = [
        _arch_node_js(child, kinds, children, depth + 2, next_seen) for child in kids
    ]
    lines.append(",\n".join("\n".join(block) for block in child_blocks))
    lines.append(f"{pad}{_INDENT}],")
    lines.append(f"{pad}}}")
    return lines


def render_architecture_group(conn: sqlite3.Connection) -> str:
    """The collapsed, ``part_of``-nested Architecture sidebar group (JS fragment).

    Roots are nodes with no ``part_of`` parent (the service root); each root nests
    its domains, which nest their features — all with human-readable labels. An
    "Architecture overview" entry (the ``/architecture`` page) stays at the top.
    """
    kinds = _load_arch_nodes(conn)
    children = _load_part_of_children(conn, kinds)
    has_parent = {
        str(row["src_ref_id"])
        for row in conn.execute(
            "SELECT src_ref_id, dst_ref_id FROM edges WHERE kind = 'part_of'"
        ).fetchall()
        # A self-edge (ref part_of itself) is not a real parent link — without
        # this the root service (e.g. ``beadloom -> beadloom``) is misread as
        # having a parent and the whole architecture tree collapses to empty.
        if str(row["src_ref_id"]) != str(row["dst_ref_id"])
    }
    roots = sorted(ref for ref in kinds if ref not in has_parent)

    items: list[str] = [
        f'{_INDENT * 3}{{ text: "Architecture overview", link: "/architecture" }}'
    ]
    for root in roots:
        items.append("\n".join(_arch_node_js(root, kinds, children, 3, frozenset())))
    return (
        f"{_INDENT}{{\n"
        f'{_INDENT * 2}text: "Architecture",\n'
        f"{_INDENT * 2}collapsed: true,\n"
        f"{_INDENT * 2}items: [\n"
        + ",\n".join(items)
        + f",\n{_INDENT * 2}],\n"
        f"{_INDENT}}}"
    )


# ---------------------------------------------------------------------------
# Documentation group — mirrors the docs/ directory tree
# ---------------------------------------------------------------------------


def _doc_link(rel: Path) -> str:
    """Extension-less ``/docs/``-rooted link to a published doc page."""
    posix = rel.as_posix()
    stem = posix[: -len(".md")] if posix.endswith(".md") else posix
    return f"/docs/{stem}"


def _doc_dir_js(directory: Path, base: Path, depth: int) -> list[str]:
    """Serialize a docs/ subdirectory as a nested, collapsible group."""
    pad = _INDENT * depth
    rel_dir = directory.relative_to(base)
    label = _js_str(human_label(rel_dir.name))
    child_lines = _doc_children_js(directory, base, depth + 2)
    if not child_lines:
        return []
    lines = [
        f"{pad}{{",
        f"{pad}{_INDENT}text: {label},",
        f"{pad}{_INDENT}collapsed: true,",
        f"{pad}{_INDENT}items: [",
    ]
    lines.append(",\n".join(child_lines))
    lines.append(f"{pad}{_INDENT}],")
    lines.append(f"{pad}}}")
    return ["\n".join(lines)]


def _doc_children_js(directory: Path, base: Path, depth: int) -> list[str]:
    """Serialized child blocks of *directory*: markdown leaves then subdirs (sorted)."""
    blocks: list[str] = []
    pad = _INDENT * depth
    for md in sorted(p for p in directory.iterdir() if p.is_file() and p.suffix == ".md"):
        if md.name.startswith("."):
            continue
        rel = md.relative_to(base)
        label = _js_str(human_label(md.stem))
        link = _js_str(_doc_link(rel))
        blocks.append(f"{pad}{{ text: {label}, link: {link} }}")
    for sub in sorted(p for p in directory.iterdir() if p.is_dir()):
        if sub.name.startswith("."):
            continue
        blocks.extend(_doc_dir_js(sub, base, depth))
    return blocks


def render_documentation_group_from_dir(docs_dir: Path, *, collapsed: bool) -> str:
    """The Documentation sidebar group built from a docs directory (JS fragment).

    Each docs subdirectory becomes a nested, collapsible group; ``.md`` files
    become leaf links rooted at ``/docs/`` (the published copy). An "Overview"
    link to ``/docs/`` is always first so the group is never empty and leads with
    a real landing page.
    """
    collapsed_js = "true" if collapsed else "false"
    items: list[str] = [f'{_INDENT * 3}{{ text: "Overview", link: "/docs/" }}']
    if docs_dir.is_dir():
        items.extend(_doc_children_js(docs_dir, docs_dir, 3))
    return (
        f"{_INDENT}{{\n"
        f'{_INDENT * 2}text: "Documentation",\n'
        f"{_INDENT * 2}collapsed: {collapsed_js},\n"
        f"{_INDENT * 2}items: [\n"
        + ",\n".join(items)
        + f",\n{_INDENT * 2}],\n"
        f"{_INDENT}}}"
    )


def render_documentation_group(project_root: Path) -> str:
    """Collapsed Documentation group rooted at ``project_root / "docs"``.

    Backward-compatible wrapper around :func:`render_documentation_group_from_dir`.
    """
    return render_documentation_group_from_dir(project_root / "docs", collapsed=True)


# ---------------------------------------------------------------------------
# Full config module
# ---------------------------------------------------------------------------


def render_nav() -> str:
    """The top-nav JS array — intentionally empty (JS fragment).

    BDL-046: top-nav items are removed; the VitePress default theme still renders
    the appearance (light/dark) toggle, local search, and the locale switcher in
    the nav bar regardless of ``nav`` entries.
    """
    return "[]"


def render_sidebar(
    conn: sqlite3.Connection,
    *,
    docs_root: Path,
    has_getting_started: bool,
) -> str:
    """The full ordered EN sidebar JS array (deterministic, link-safe).

    Order: About · Getting Started (only if its page exists) · Dashboard (flat) ·
    Architecture (collapsed ``part_of`` tree, overview -> ``/architecture``) ·
    Landscape map (flat) · Documentation (expanded, Overview-led). Dashboard and
    Landscape are plain ``{ text, link }`` entries, not one-child groups.
    """
    arch_group = render_architecture_group(conn)
    docs_group = render_documentation_group_from_dir(docs_root, collapsed=False)
    entries: list[str] = [f'{_INDENT}{{ text: "About", link: "/" }}']
    if has_getting_started:
        entries.append(
            f'{_INDENT}{{ text: "Getting Started", link: "/docs/getting-started" }}'
        )
    entries.append(f'{_INDENT}{{ text: "Dashboard", link: "/dashboard" }}')
    entries.append(arch_group)
    entries.append(f'{_INDENT}{{ text: "Landscape map", link: "/landscape" }}')
    entries.append(docs_group)
    return "[\n" + ",\n".join(entries) + ",\n]"


def render_nav_config(conn: sqlite3.Connection, project_root: Path) -> str:
    """The full generated VitePress nav/sidebar config module (deterministic).

    Top nav is empty (``render_nav``); the single shared EN sidebar is the
    ordered, link-safe tree from :func:`render_sidebar` (About / Getting Started /
    Dashboard / Architecture / Landscape map / Documentation). BDL-046 BEAD-11
    dropped VitePress ``locales`` (the switcher translated the whole menu and
    404'd off ``/ru/``): the module exports only ``nav`` + ``sidebar``; the
    bilingual About is now an in-page cross-link emitted by ``render_about``.
    """
    docs_root = project_root / "docs"
    has_getting_started = _getting_started_exists(docs_root)
    nav = render_nav()
    sidebar = render_sidebar(
        conn, docs_root=docs_root, has_getting_started=has_getting_started
    )
    return (
        "// GENERATED by `beadloom docs site` — do not edit by hand.\n"
        "// Imported by .vitepress/config.mjs; regenerated deterministically.\n"
        f"export const nav = {nav};\n\n"
        f"export const sidebar = {sidebar};\n"
    )


def _getting_started_exists(docs_root: Path) -> bool:
    """True if a ``getting-started.*`` page is published under *docs_root*.

    Link-safe: the sidebar only emits the Getting Started entry when a backing
    page exists (any markdown extension), never a dead link.
    """
    if not docs_root.is_dir():
        return False
    return any(
        p.is_file() and p.stem == "getting-started" and p.suffix == ".md"
        for p in docs_root.iterdir()
    )
