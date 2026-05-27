"""Tests for beadloom.application.site — the `docs site` generator (BDL-040 BEAD-01).

Asserts the generator emits the expected files deterministically (re-generate ->
byte-identical), node pages contain summary/symbols/edges-as-links + an embedded
diagram, and nothing is written outside ``--out``.
"""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path, PurePosixPath

import pytest

from beadloom.application.site import generate_site
from beadloom.infrastructure.db import create_schema

# Markdown inline links: capture the URL inside (...). Excludes images is not
# needed here (the generator emits no images).
_LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _seed(conn: sqlite3.Connection) -> None:
    """Insert a small but representative graph (service/domain/feature + edges)."""
    nodes = [
        ("beadloom", "service", "Beadloom CLI service.", None),
        ("application", "domain", "Use-case orchestration.", "src/beadloom/application"),
        ("graph", "domain", "YAML graph format and loader.", "src/beadloom/graph"),
        ("reindex", "feature", "Full reindex pipeline.", "src/beadloom/application/reindex.py"),
    ]
    for ref_id, kind, summary, source in nodes:
        conn.execute(
            "INSERT INTO nodes (ref_id, kind, summary, source) VALUES (?, ?, ?, ?)",
            (ref_id, kind, summary, source),
        )
    edges = [
        ("application", "beadloom", "part_of"),
        ("graph", "beadloom", "part_of"),
        ("reindex", "application", "part_of"),
        ("application", "graph", "depends_on"),
        ("application", "graph", "uses"),
    ]
    for src, dst, kind in edges:
        conn.execute(
            "INSERT INTO edges (src_ref_id, dst_ref_id, kind) VALUES (?, ?, ?)",
            (src, dst, kind),
        )
    # A public symbol attached to the application source dir.
    conn.execute(
        "INSERT INTO code_symbols "
        "(file_path, symbol_name, kind, line_start, line_end, file_hash) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        ("src/beadloom/application/reindex.py", "do_reindex", "function", 1, 10, "h"),
    )
    # A linked hand-written doc for the application node. Paths in the `docs`
    # table are stored RELATIVE to the source `docs/` dir (no `docs/` prefix) —
    # the published copy lives under `site/docs/<path>`, so the generated link
    # must be rooted at `/docs/` (see test_node_page_doc_links_resolve).
    conn.execute(
        "INSERT INTO docs (path, kind, ref_id, hash) VALUES (?, ?, ?, ?)",
        ("domains/application/README.md", "domain", "application", "dh"),
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
# Structure / emitted files
# ---------------------------------------------------------------------------


def test_emits_index_and_per_node_pages(conn: sqlite3.Connection, tmp_path: Path) -> None:
    out = tmp_path / "site"
    result = generate_site(conn, out, project_root=tmp_path)

    assert (out / "index.md").exists()
    assert (out / "services" / "beadloom.md").exists()
    assert (out / "domains" / "application.md").exists()
    assert (out / "domains" / "graph.md").exists()
    assert (out / "features" / "reindex.md").exists()
    # The result reports every written path.
    assert (out / "index.md") in result.written
    assert (out / "domains" / "application.md") in result.written


def test_emits_vitepress_config(conn: sqlite3.Connection, tmp_path: Path) -> None:
    out = tmp_path / "site"
    generate_site(conn, out, project_root=tmp_path)
    cfg = out / ".vitepress" / "config.generated.mjs"
    assert cfg.exists()
    text = cfg.read_text(encoding="utf-8")
    # nav/sidebar sections present (later beads fill Dashboard/Landscape/Documentation).
    assert "Dashboard" in text
    assert "Architecture" in text
    assert "Landscape" in text
    assert "Documentation" in text


def test_architecture_page_has_counts_and_diagram_and_health(
    conn: sqlite3.Connection, tmp_path: Path
) -> None:
    # BDL-046: the architecture overview moved off the landing to /architecture.
    out = tmp_path / "site"
    generate_site(conn, out, project_root=tmp_path)
    text = (out / "architecture.md").read_text(encoding="utf-8")
    assert "1 service" in text or "1 services" in text
    assert "2 domains" in text
    assert "1 feature" in text or "1 features" in text
    # Embedded top-level diagram (mermaid C4).
    assert "```mermaid" in text
    assert "C4Container" in text
    # Health summary line (coverage).
    assert "coverage" in text.lower()
    assert (out / "architecture.md") in result_written(conn, out, tmp_path)


def result_written(
    conn: sqlite3.Connection, out: Path, project_root: Path
) -> tuple[Path, ...]:
    """Re-run the generator (idempotent) to read the returned written tuple."""
    return generate_site(conn, out, project_root=project_root).written


# ---------------------------------------------------------------------------
# BDL-046: About home (EN + RU), architecture page, docs overview
# ---------------------------------------------------------------------------


def test_index_is_readme_about_not_architecture_overview(
    conn: sqlite3.Connection, tmp_path: Path
) -> None:
    # README at the project root becomes the About home page.
    (tmp_path / "README.md").write_text(
        "# Beadloom\n\nKEEP YOUR ARCHITECTURE ACCURATE marker.\n", encoding="utf-8"
    )
    out = tmp_path / "site"
    result = generate_site(conn, out, project_root=tmp_path)
    text = (out / "index.md").read_text(encoding="utf-8")
    # README marker present; the C4 architecture overview is NOT on the home page.
    assert "KEEP YOUR ARCHITECTURE ACCURATE marker." in text
    assert "C4Container" not in text
    assert "Architecture overview" not in text
    assert (out / "index.md") in result.written


def test_index_falls_back_to_overview_without_readme(
    conn: sqlite3.Connection, tmp_path: Path
) -> None:
    # No README.md -> robust fallback to the former architecture overview body.
    out = tmp_path / "site"
    generate_site(conn, out, project_root=tmp_path)
    text = (out / "index.md").read_text(encoding="utf-8")
    assert "C4Container" in text


def test_ru_index_from_readme_ru(conn: sqlite3.Connection, tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("# Beadloom\n\nEN home.\n", encoding="utf-8")
    (tmp_path / "README.ru.md").write_text(
        "# Beadloom\n\nRU_HOME_MARKER (russian about).\n", encoding="utf-8"
    )
    out = tmp_path / "site"
    result = generate_site(conn, out, project_root=tmp_path)
    ru = (out / "ru" / "index.md").read_text(encoding="utf-8")
    assert "RU_HOME_MARKER (russian about)." in ru
    assert (out / "ru" / "index.md") in result.written


def test_ru_index_skipped_without_readme_ru(
    conn: sqlite3.Connection, tmp_path: Path
) -> None:
    (tmp_path / "README.md").write_text("# Beadloom\n\nEN home.\n", encoding="utf-8")
    out = tmp_path / "site"
    generate_site(conn, out, project_root=tmp_path)
    assert not (out / "ru" / "index.md").exists()


def test_docs_index_loose_docs_under_general_section(
    conn: sqlite3.Connection, tmp_path: Path
) -> None:
    """Top-level (un-sectioned) docs are described under a 'General' heading.

    A doc with no leading directory segment (e.g. ``getting-started.md``) has no
    section, so the overview names it as inline TEXT under a synthetic 'General'
    heading (human-labelled, no link).
    """
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "getting-started.md").write_text("# GS\n", encoding="utf-8")
    out = tmp_path / "site"
    generate_site(conn, out, project_root=tmp_path)
    text = (out / "docs" / "index.md").read_text(encoding="utf-8")
    assert "## General" in text
    assert "Getting Started" in text
    # Named as text, never as a link.
    assert "](/docs/" not in text


def test_architecture_page_is_not_the_about_home(
    conn: sqlite3.Connection, tmp_path: Path
) -> None:
    """With a README, the overview lives ONLY at /architecture, not at /index."""
    (tmp_path / "README.md").write_text(
        "# Beadloom\n\nABOUT_MARKER body.\n", encoding="utf-8"
    )
    out = tmp_path / "site"
    generate_site(conn, out, project_root=tmp_path)
    index = (out / "index.md").read_text(encoding="utf-8")
    arch = (out / "architecture.md").read_text(encoding="utf-8")
    assert "ABOUT_MARKER body." in index
    assert "Architecture overview" not in index
    assert "Architecture overview" in arch
    assert "ABOUT_MARKER" not in arch


def test_written_tuple_is_sorted_and_contains_new_paths(
    conn: sqlite3.Connection, tmp_path: Path
) -> None:
    """SiteResult.written is sorted and lists the BDL-046 pages.

    index.md (About), architecture.md (moved overview), ru/index.md (RU About),
    docs/index.md (grouped overview) all appear, and the tuple is sorted.
    """
    (tmp_path / "README.md").write_text("# B\n\nEN.\n", encoding="utf-8")
    (tmp_path / "README.ru.md").write_text("# B\n\nRU.\n", encoding="utf-8")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "getting-started.md").write_text("# GS\n", encoding="utf-8")
    out = tmp_path / "site"
    result = generate_site(conn, out, project_root=tmp_path)
    assert list(result.written) == sorted(result.written)
    for rel in ("index.md", "architecture.md", "ru/index.md", "docs/index.md"):
        assert out / rel in result.written


def test_exactly_one_docs_index_when_source_has_root_index(
    conn: sqlite3.Connection, tmp_path: Path
) -> None:
    """A source docs/index.md does not create a duplicate landing page.

    The grouped overview overwrites the single published docs/index.md in
    place — there is exactly one, even when the source tree ships its own.
    """
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "index.md").write_text("# Source landing\n", encoding="utf-8")
    (docs / "getting-started.md").write_text("# GS\n", encoding="utf-8")
    out = tmp_path / "site"
    generate_site(conn, out, project_root=tmp_path)
    docs_indexes = [p for p in out.rglob("index.md") if p.parent.name == "docs"]
    assert len(docs_indexes) == 1
    # The grouped overview won (intro paragraph present), not the source body.
    text = docs_indexes[0].read_text(encoding="utf-8")
    assert "title: Documentation" in text


def test_docs_index_is_grouped_overview(
    conn: sqlite3.Connection, tmp_path: Path
) -> None:
    # Build a small published docs tree (Domains / Services / Guides + a loose doc).
    docs = tmp_path / "docs"
    (docs / "domains").mkdir(parents=True)
    (docs / "services").mkdir()
    (docs / "guides").mkdir()
    (docs / "getting-started.md").write_text("# GS\n", encoding="utf-8")
    (docs / "domains" / "application.md").write_text("# App\n", encoding="utf-8")
    (docs / "services" / "beadloom.md").write_text("# Svc\n", encoding="utf-8")
    (docs / "guides" / "intro.md").write_text("# Intro\n", encoding="utf-8")

    out = tmp_path / "site"
    generate_site(conn, out, project_root=tmp_path)
    text = (out / "docs" / "index.md").read_text(encoding="utf-8")
    # Grouped section headings, not a flat link wall.
    assert "## Domains" in text
    assert "## Services" in text
    assert "## Guides" in text
    # Members are named as inline TEXT, human-labelled (no link wall).
    assert "Application" in text
    assert "Beadloom" in text
    # NO links in the body — the navigable tree is the expanded sidebar.
    assert "](/docs/" not in text
    # Exactly one docs index page.
    docs_indexes = [p for p in out.rglob("index.md") if p.parent.name == "docs"]
    assert len(docs_indexes) == 1


# ---------------------------------------------------------------------------
# Node-page content: summary / symbols / edges-as-links / diagram
# ---------------------------------------------------------------------------


def test_node_page_has_summary_source_symbols(
    conn: sqlite3.Connection, tmp_path: Path
) -> None:
    out = tmp_path / "site"
    generate_site(conn, out, project_root=tmp_path)
    text = (out / "domains" / "application.md").read_text(encoding="utf-8")
    assert "Use-case orchestration." in text
    assert "src/beadloom/application" in text


def test_node_page_symbols_listed(conn: sqlite3.Connection, tmp_path: Path) -> None:
    out = tmp_path / "site"
    generate_site(conn, out, project_root=tmp_path)
    text = (out / "features" / "reindex.md").read_text(encoding="utf-8")
    assert "do_reindex" in text


def test_node_page_edges_as_links(conn: sqlite3.Connection, tmp_path: Path) -> None:
    out = tmp_path / "site"
    generate_site(conn, out, project_root=tmp_path)
    text = (out / "domains" / "application.md").read_text(encoding="utf-8")
    # depends_on / uses / part_of edges rendered as markdown links to other pages.
    assert "depends_on" in text
    assert "](../domains/graph.md)" in text  # link to the graph domain page
    assert "](../services/beadloom.md)" in text  # part_of -> beadloom service page


def test_node_page_embedded_diagram(conn: sqlite3.Connection, tmp_path: Path) -> None:
    out = tmp_path / "site"
    generate_site(conn, out, project_root=tmp_path)
    text = (out / "domains" / "application.md").read_text(encoding="utf-8")
    assert "```mermaid" in text


def test_node_page_linked_docs_as_links(conn: sqlite3.Connection, tmp_path: Path) -> None:
    out = tmp_path / "site"
    generate_site(conn, out, project_root=tmp_path)
    text = (out / "domains" / "application.md").read_text(encoding="utf-8")
    # The doc link is rooted at /docs/ — the published copy lives under site/docs/.
    assert "](/docs/domains/application/README.md)" in text


# ---------------------------------------------------------------------------
# Internal link resolution (catches dead links WITHOUT needing node/VitePress)
# ---------------------------------------------------------------------------


def _is_external(url: str) -> bool:
    """A link VitePress does not resolve against the emitted tree."""
    return (
        "://" in url
        or url.startswith(("#", "mailto:", "tel:"))
        or url.strip() == ""
    )


def _resolve_target(out: Path, page: Path, url: str) -> Path | None:
    """The file a markdown *url* on *page* should resolve to in the site tree.

    Mirrors VitePress link resolution: absolute (`/foo`) roots at the site root,
    relative resolves against the page's directory, a trailing `/` means the
    directory's `index.md`, and the `.md` suffix is optional (clean URLs).
    Returns ``None`` for external/anchor links (not our concern).
    """
    raw = url.split("#", 1)[0].split("?", 1)[0]
    if _is_external(raw):
        return None
    base = PurePosixPath(page.relative_to(out).as_posix()).parent
    target = (
        PurePosixPath(raw.lstrip("/"))
        if raw.startswith("/")
        else base / raw
    )
    # Directory link -> index page.
    if raw.endswith("/"):
        target = target / "index"
    # Try the path as-is, with .md, and as a dir index (clean-URL forms).
    candidates = [target, target.with_suffix(".md")]
    if target.suffix == "":
        candidates.append(target / "index.md")
    for cand in candidates:
        resolved = out / PurePosixPath(*cand.parts)
        if resolved.exists():
            return resolved
    return out / PurePosixPath(*target.parts)  # report the primary miss


# Directories VitePress does not render (so they are not part of the content
# tree whose links must resolve): the node toolchain and build/config dirs.
_NON_CONTENT_DIRS = frozenset({"node_modules", ".vitepress", "dist"})


def _dead_links(out: Path) -> list[tuple[str, str]]:
    """Every internal markdown link in the *content* tree whose target is missing.

    Only the rendered content tree is walked (``node_modules`` / ``.vitepress``
    are excluded — VitePress does not render them). Links inside fenced code
    blocks (e.g. Mermaid ``click`` directives) are ignored — not markdown links.
    """
    dead: list[tuple[str, str]] = []
    for md in sorted(out.rglob("*.md")):
        if any(part in _NON_CONTENT_DIRS for part in md.relative_to(out).parts):
            continue
        body = md.read_text(encoding="utf-8")
        in_fence = False
        for line in body.splitlines():
            if line.lstrip().startswith("```"):
                in_fence = not in_fence
                continue
            if in_fence:
                continue
            for url in _LINK_RE.findall(line):
                resolved = _resolve_target(out, md, url)
                if resolved is not None and not resolved.exists():
                    dead.append((str(md.relative_to(out)), url))
    return dead


def test_generated_internal_links_resolve(
    conn: sqlite3.Connection, tmp_path: Path
) -> None:
    """Every internal markdown link in the generated tree resolves to a file.

    This is the node-free guard for the VitePress dead-link failure surfaced by
    the F4 dogfood: node pages used to link hand-written docs at ``/<path>`` even
    though the published copy lives under ``/docs/<path>``.
    """
    # The published doc must exist on disk for its link to resolve.
    docs = tmp_path / "docs" / "domains" / "application"
    docs.mkdir(parents=True)
    (docs / "README.md").write_text("# Application\n", encoding="utf-8")

    out = tmp_path / "site"
    generate_site(conn, out, project_root=tmp_path)

    assert not _dead_links(out), f"dead internal links: {_dead_links(out)}"


def test_committed_site_tree_has_no_dead_links() -> None:
    """The committed dogfood ``site/`` tree (if present) has no dead links.

    Validates the real generated output `npm run docs:build` consumes, so the
    VitePress dead-link regression is caught without needing node. Skipped on a
    checkout where the dogfood site has not been generated.
    """
    repo_root = Path(__file__).resolve().parents[1]
    site = repo_root / "site"
    if not (site / "index.md").exists():
        pytest.skip("dogfood site/ not generated in this checkout")
    assert not _dead_links(site), f"dead internal links in committed site/: {_dead_links(site)}"


# ---------------------------------------------------------------------------
# Determinism + no source mutation
# ---------------------------------------------------------------------------


_FIXED_TS = "2026-06-05T00:00:00+00:00"


def test_regenerate_is_byte_identical(conn: sqlite3.Connection, tmp_path: Path) -> None:
    out = tmp_path / "site"
    # Inject a fixed metrics-history ts: the only wall-clock read is the trend
    # point; dedup-by-ts keeps the diffed output byte-stable for a fixed history.
    generate_site(conn, out, project_root=tmp_path, now_ts=_FIXED_TS)
    first = {
        p.relative_to(out): p.read_bytes()
        for p in sorted(out.rglob("*"))
        if p.is_file()
    }
    # Regenerate into the same dir; output must be byte-identical.
    generate_site(conn, out, project_root=tmp_path, now_ts=_FIXED_TS)
    second = {
        p.relative_to(out): p.read_bytes()
        for p in sorted(out.rglob("*"))
        if p.is_file()
    }
    assert first == second


def test_no_wall_clock_in_output(conn: sqlite3.Connection, tmp_path: Path) -> None:
    """Two generations of the same graph produce identical bytes (fixed ts)."""
    out_a = tmp_path / "a"
    out_b = tmp_path / "b"
    generate_site(conn, out_a, project_root=tmp_path, now_ts=_FIXED_TS)
    generate_site(conn, out_b, project_root=tmp_path, now_ts=_FIXED_TS)
    a = {p.relative_to(out_a): p.read_bytes() for p in sorted(out_a.rglob("*")) if p.is_file()}
    b = {p.relative_to(out_b): p.read_bytes() for p in sorted(out_b.rglob("*")) if p.is_file()}
    assert a == b


def test_never_writes_into_source_docs(conn: sqlite3.Connection, tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    docs.mkdir()
    sentinel = docs / "README.md"
    sentinel.write_text("ORIGINAL", encoding="utf-8")
    out = tmp_path / "site"
    result = generate_site(conn, out, project_root=tmp_path)
    # Source docs untouched.
    assert sentinel.read_text(encoding="utf-8") == "ORIGINAL"
    # Every written path is under out/.
    for p in result.written:
        assert out in p.parents or p == out


def test_empty_graph_still_emits_index(tmp_path: Path) -> None:
    db = sqlite3.connect(":memory:")
    db.row_factory = sqlite3.Row
    create_schema(db)
    out = tmp_path / "site"
    generate_site(db, out, project_root=tmp_path)
    assert (out / "index.md").exists()


# ---------------------------------------------------------------------------
# CLI: `beadloom docs site`
# ---------------------------------------------------------------------------


def _cli_project(tmp_path: Path) -> Path:
    import yaml

    from beadloom.application.reindex import reindex

    project = tmp_path / "proj"
    project.mkdir()
    graph_dir = project / ".beadloom" / "_graph"
    graph_dir.mkdir(parents=True)
    (graph_dir / "graph.yml").write_text(
        yaml.dump(
            {
                "nodes": [
                    {"ref_id": "api-gw", "kind": "service", "summary": "API Gateway"},
                    {"ref_id": "routing", "kind": "domain", "summary": "Routing domain"},
                    {"ref_id": "FEAT-1", "kind": "feature", "summary": "Feature one"},
                ],
                "edges": [
                    {"src": "routing", "dst": "api-gw", "kind": "part_of"},
                    {"src": "FEAT-1", "dst": "routing", "kind": "part_of"},
                ],
            }
        ),
        encoding="utf-8",
    )
    (project / "docs").mkdir()
    (project / "src").mkdir()
    reindex(project)
    return project


def test_cli_docs_site_default_out(tmp_path: Path) -> None:
    from click.testing import CliRunner

    from beadloom.services.cli import main

    project = _cli_project(tmp_path)
    runner = CliRunner()
    result = runner.invoke(main, ["docs", "site", "--project", str(project)])
    assert result.exit_code == 0, result.output
    assert (project / "site" / "index.md").exists()
    assert (project / "site" / "services" / "api-gw.md").exists()


def test_cli_docs_site_custom_out(tmp_path: Path) -> None:
    from click.testing import CliRunner

    from beadloom.services.cli import main

    project = _cli_project(tmp_path)
    out = tmp_path / "custom-site"
    runner = CliRunner()
    result = runner.invoke(
        main, ["docs", "site", "--project", str(project), "--out", str(out)]
    )
    assert result.exit_code == 0, result.output
    assert (out / "index.md").exists()


def test_cli_docs_site_no_db(tmp_path: Path) -> None:
    from click.testing import CliRunner

    from beadloom.services.cli import main

    project = tmp_path / "empty"
    project.mkdir()
    runner = CliRunner()
    result = runner.invoke(main, ["docs", "site", "--project", str(project)])
    assert result.exit_code == 1
    assert "database not found" in result.output
