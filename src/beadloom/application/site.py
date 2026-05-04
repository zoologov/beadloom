"""The `docs site` use-case: generate a VitePress content tree from the graph.

Reads the indexed graph read-only and emits, under ``--out`` (default ``site/``):
- ``index.md`` — architecture overview (domain/service/feature counts, the
  top-level C4/Mermaid diagram, a health summary line).
- per-node pages (``domains/<ref>.md`` / ``services/<ref>.md`` /
  ``features/<ref>.md``) — see :mod:`beadloom.application.site_pages`.
- ``dashboard.md`` + ``dashboard.data.json`` — Showcase A, the AaC/DocAsCode
  metrics dashboard (see :mod:`beadloom.application.site_dashboard`); every
  number comes from the same code path as its gate (honest by construction).
- ``landscape.md`` — Showcase B, the 🌟 cross-repo landscape map (see
  :mod:`beadloom.application.site_landscape`); a Mermaid diagram generated from
  the ``federate`` hub output (or a degenerate single-repo map), with edges
  labelled by ``ContractVerdict``, a health overlay, and clickable nodes.
- ``docs/…`` — Showcase C, the published validated documentation (see
  :mod:`beadloom.application.site_published`): the REAL ``docs/**`` tree copied
  in (source never mutated) with a per-doc ``doc_sync`` validation badge (same
  source as ``sync-check``).
- ``.vitepress/config.generated.mjs`` — nav/sidebar config consumed by the
  committed VitePress scaffold (sections: Dashboard / Architecture / Landscape /
  Documentation).

Beadloom produces, VitePress renders. Output is deterministic (sorted, stable
frontmatter, NO wall-clock in the diffed output) and is NEVER written into the
source ``docs/`` tree — only under ``--out``.
"""

# beadloom:domain=application

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from beadloom.application.site_dashboard import (
    build_dashboard_data,
    render_dashboard_md,
    serialize_dashboard_data,
)
from beadloom.application.site_landscape import (
    build_landscape_data,
    render_landscape_md,
)
from beadloom.application.site_mermaid_guard import MermaidIssue, validate_mermaid
from beadloom.application.site_pages import NodeRow, load_nodes, render_all_pages
from beadloom.application.site_published import publish_docs
from beadloom.graph.c4 import filter_c4_nodes, map_to_c4, render_c4_mermaid

if TYPE_CHECKING:
    import sqlite3
    from pathlib import Path

logger = logging.getLogger(__name__)


class MermaidValidationError(RuntimeError):
    """A generated diagram failed the structural Mermaid guard.

    Raised by :func:`generate_site` so a broken diagram fails ``docs site`` (in
    pytest/CI) instead of silently shipping a page that crashes the browser
    render. Carries the offending page path and the structural issues found.
    """

    def __init__(self, page: str, issues: list[MermaidIssue]) -> None:
        detail = "; ".join(f"[{i.kind}] {i.message}" for i in issues)
        super().__init__(f"Mermaid guard rejected {page}: {detail}")
        self.page = page
        self.issues = issues


@dataclass(frozen=True)
class SiteResult:
    """The outcome of a site generation: every file written, sorted."""

    out_dir: Path
    written: tuple[Path, ...]


@dataclass(frozen=True)
class _HealthSummary:
    """Read-only health snapshot (no DB writes, no wall-clock)."""

    nodes: int
    edges: int
    docs: int
    coverage_pct: float
    stale: int


def _count_kinds(nodes: list[NodeRow]) -> dict[str, int]:
    """Count nodes by kind."""
    counts: dict[str, int] = {}
    for node in nodes:
        counts[node.kind] = counts.get(node.kind, 0) + 1
    return counts


def _compute_health(conn: sqlite3.Connection) -> _HealthSummary:
    """Compute a health summary read-only (mirrors the metrics `status` shows)."""
    nodes = int(conn.execute("SELECT count(*) FROM nodes").fetchone()[0])
    edges = int(conn.execute("SELECT count(*) FROM edges").fetchone()[0])
    docs = int(conn.execute("SELECT count(*) FROM docs").fetchone()[0])
    covered = int(
        conn.execute(
            "SELECT count(DISTINCT n.ref_id) FROM nodes n "
            "JOIN docs d ON d.ref_id = n.ref_id"
        ).fetchone()[0]
    )
    coverage = (covered / nodes * 100.0) if nodes > 0 else 0.0
    stale = int(
        conn.execute("SELECT count(*) FROM sync_state WHERE status = 'stale'").fetchone()[0]
    )
    return _HealthSummary(
        nodes=nodes, edges=edges, docs=docs, coverage_pct=coverage, stale=stale
    )


def _plural(count: int, singular: str) -> str:
    """``1 service`` / ``2 services`` (deterministic, no locale)."""
    return f"{count} {singular}" if count == 1 else f"{count} {singular}s"


def _top_level_diagram(conn: sqlite3.Connection) -> str:
    """The top-level (container) C4/Mermaid diagram for the overview page."""
    nodes, rels = map_to_c4(conn)
    nodes, rels = filter_c4_nodes(nodes, rels, level="container")
    return render_c4_mermaid(nodes, rels)


def _render_index(conn: sqlite3.Connection, nodes: list[NodeRow]) -> str:
    """The architecture overview page (counts + diagram + health line)."""
    counts = _count_kinds(nodes)
    health = _compute_health(conn)
    diagram = _top_level_diagram(conn)

    summary_parts = [
        _plural(counts.get("domain", 0), "domain"),
        _plural(counts.get("service", 0), "service"),
        _plural(counts.get("feature", 0), "feature"),
    ]
    lines = [
        "---",
        "title: Architecture",
        "---",
        "",
        "# Architecture overview",
        "",
        "Generated by `beadloom docs site` — Beadloom produces, VitePress renders.",
        "",
        "## At a glance",
        "",
        "- " + ", ".join(summary_parts),
        "",
        "## Health",
        "",
        (
            f"- {health.nodes} nodes, {health.edges} edges, {health.docs} docs "
            f"— coverage {health.coverage_pct:.0f}%, {health.stale} stale"
        ),
        "",
        "## Top-level diagram",
        "",
        "```mermaid",
        diagram.rstrip("\n"),
        "```",
        "",
    ]
    return "\n".join(lines) + "\n"


def _render_nav_config(nodes: list[NodeRow]) -> str:
    """The generated VitePress nav/sidebar config (consumed by the scaffold).

    Sections: Dashboard / Architecture / Landscape / Documentation. The
    architecture section lists every node page; the other three are placeholders
    the later beads (BEAD-02/03/04) fill.
    """
    arch_items: list[str] = ['        { text: "Overview", link: "/index" }']
    dir_for = {"domain": "domains", "service": "services", "feature": "features"}
    for node in nodes:
        sub = dir_for.get(node.kind)
        if sub is None:
            continue
        arch_items.append(
            f'        {{ text: "{node.ref_id}", link: "/{sub}/{node.ref_id}" }}'
        )
    items_block = ",\n".join(arch_items)
    return (
        "// GENERATED by `beadloom docs site` — do not edit by hand.\n"
        "// Imported by .vitepress/config.mjs; regenerated deterministically.\n"
        "export const nav = [\n"
        '  { text: "Dashboard", link: "/dashboard" },\n'
        '  { text: "Architecture", link: "/index" },\n'
        '  { text: "Landscape", link: "/landscape" },\n'
        '  { text: "Documentation", link: "/docs/" },\n'
        "];\n\n"
        "export const sidebar = [\n"
        '  { text: "Dashboard", items: [{ text: "Metrics", link: "/dashboard" }] },\n'
        '  {\n'
        '    text: "Architecture",\n'
        "    items: [\n"
        f"{items_block},\n"
        "    ],\n"
        "  },\n"
        '  { text: "Landscape", items: [{ text: "Map", link: "/landscape" }] },\n'
        '  { text: "Documentation", items: [{ text: "Docs", link: "/docs/" }] },\n'
        "];\n"
    )


def _extract_mermaid_blocks(content: str) -> list[str]:
    """Return the body of every ```` ```mermaid ```` fenced block in *content*."""
    blocks: list[str] = []
    lines = content.splitlines()
    inside = False
    current: list[str] = []
    for line in lines:
        stripped = line.strip()
        if not inside and stripped.startswith("```mermaid"):
            inside = True
            current = []
            continue
        if inside and stripped.startswith("```"):
            inside = False
            blocks.append("\n".join(current))
            continue
        if inside:
            current.append(line)
    return blocks


def _guard_diagrams(path: Path, content: str) -> None:
    """Validate every Mermaid diagram in *content*; raise on any structural issue.

    Closes the F4 "build green != renders ok" gap: a reserved-keyword flowchart
    id or a C4 Rel to an undeclared node fails ``docs site`` here (pytest/CI),
    not in the browser.
    """
    if path.suffix != ".md":
        return
    issues: list[MermaidIssue] = []
    for block in _extract_mermaid_blocks(content):
        issues.extend(validate_mermaid(block))
    if issues:
        raise MermaidValidationError(path.name, issues)


def _write(path: Path, content: str, written: list[Path]) -> None:
    """Write *content* to *path* (creating parents) and record it.

    Every Markdown page is run through the Mermaid structural guard first, so a
    diagram that would crash the VitePress render fails generation instead.
    """
    _guard_diagrams(path, content)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    written.append(path)


def generate_site(
    conn: sqlite3.Connection,
    out_dir: Path,
    *,
    project_root: Path,
    federated: Path | None = None,
) -> SiteResult:
    """Generate the VitePress content tree under *out_dir* (deterministic).

    Args:
        conn: An open, read-only connection to the indexed graph DB.
        out_dir: The output directory (``--out``); never the source ``docs/``.
        project_root: The project root (for resolving relative paths; the source
            ``docs/`` is never written).
        federated: Optional federated.json for the landscape map (later beads).

    Returns:
        A :class:`SiteResult` listing every written file (sorted).
    """
    nodes = load_nodes(conn)
    written: list[Path] = []

    _write(out_dir / "index.md", _render_index(conn, nodes), written)

    for page in render_all_pages(conn):
        _write(out_dir / page.rel_path, page.body, written)

    # Showcase A — the metrics dashboard (machine data + human page). Numbers
    # come from the same code paths as the gates (honest by construction).
    dashboard_data = build_dashboard_data(
        conn, project_root=project_root, federated=federated
    )
    _write(
        out_dir / "dashboard.data.json",
        serialize_dashboard_data(dashboard_data),
        written,
    )
    _write(out_dir / "dashboard.md", render_dashboard_md(dashboard_data), written)

    # Showcase B — the 🌟 cross-repo landscape map (Mermaid, generated from the
    # federate hub output when given, else a degenerate single-repo map).
    landscape_data = build_landscape_data(conn, federated=federated)
    _write(out_dir / "landscape.md", render_landscape_md(landscape_data), written)

    # Showcase C — the published validated docs. Copy the REAL docs/ tree into
    # site/docs/ preserving structure (source never mutated) and inject a
    # per-doc validation badge from the doc_sync engine (same source as
    # sync-check). Badges land only in the copy under out_dir.
    written.extend(publish_docs(conn, out_dir, project_root=project_root))

    _write(
        out_dir / ".vitepress" / "config.generated.mjs",
        _render_nav_config(nodes),
        written,
    )

    return SiteResult(out_dir=out_dir, written=tuple(sorted(written)))
