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
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from beadloom.application.site_dashboard import (
    build_dashboard_data,
    render_dashboard_md,
    serialize_dashboard_data,
)
from beadloom.application.site_landscape import (
    build_landscape_data,
    existing_page_urls,
    render_landscape_md,
)
from beadloom.application.site_mermaid_guard import MermaidIssue, validate_mermaid
from beadloom.application.site_metrics_history import (
    MetricsPoint,
    append_metrics_point,
    backfill_structural_history,
)
from beadloom.application.site_nav import render_nav_config
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


def _to_int(value: object) -> int:
    """Coerce an honest numeric dashboard value to int (0 on a non-number)."""
    return int(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else 0


def _to_float(value: object) -> float:
    """Coerce an honest numeric dashboard value to float (0.0 on a non-number)."""
    if isinstance(value, bool):
        return 0.0
    return float(value) if isinstance(value, (int, float)) else 0.0


def _scalar_metrics(
    conn: sqlite3.Connection, project_root: Path, federated: Path | None
) -> dict[str, object]:
    """Build the dashboard data once to source this run's honest scalar metrics."""
    return build_dashboard_data(conn, project_root=project_root, federated=federated)


def _record_metrics_point(
    conn: sqlite3.Connection,
    project_root: Path,
    *,
    federated: Path | None,
    now_ts: str | None,
) -> None:
    """Append this run's honest metrics point (injected/now ts) to the history.

    The scalar metrics are taken from the SAME dashboard data the page emits
    (honest by construction); structural ``edges``/``symbols`` come from the DB.
    The point's ts is the only wall-clock read and lands solely in the
    append-only history store — never in the diffed dashboard fields.
    """
    ts = now_ts or datetime.now(timezone.utc).isoformat()
    data = _scalar_metrics(conn, project_root, federated)
    lint_obj = data["lint"]
    debt_obj = data["debt"]
    docs_obj = data["docs"]
    assert isinstance(lint_obj, dict)
    assert isinstance(debt_obj, dict)
    assert isinstance(docs_obj, dict)
    edges = int(conn.execute("SELECT count(*) FROM edges").fetchone()[0])
    symbols = int(conn.execute("SELECT count(*) FROM code_symbols").fetchone()[0])
    point = MetricsPoint(
        ts=ts,
        lint_violations=_to_int(lint_obj["violations"]),
        debt_score=_to_float(debt_obj["debt_score"]),
        coverage_pct=_to_float(docs_obj["coverage_pct"]),
        sync_pct=_to_float(docs_obj["freshness_pct"]),
        nodes=_to_int(docs_obj["nodes"]),
        edges=edges,
        symbols=symbols,
    )
    append_metrics_point(project_root, point)


def generate_site(
    conn: sqlite3.Connection,
    out_dir: Path,
    *,
    project_root: Path,
    federated: Path | None = None,
    now_ts: str | None = None,
) -> SiteResult:
    """Generate the VitePress content tree under *out_dir* (deterministic).

    Args:
        conn: An open, read-only connection to the indexed graph DB.
        out_dir: The output directory (``--out``); never the source ``docs/``.
        project_root: The project root (for resolving relative paths; the source
            ``docs/`` is never written).
        federated: Optional federated.json for the landscape map (later beads).
        now_ts: ISO-8601 timestamp for the metrics-history point recorded this
            run. Injected in tests for determinism; defaults to the current UTC
            instant in production (the only wall-clock read, and only into the
            append-only history store — never into the diffed dashboard fields).

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
    # Record this run's honest point first (backfill structural history once so
    # the trend isn't empty on day one), so the emitted series includes "now".
    backfill_structural_history(conn, project_root)
    _record_metrics_point(conn, project_root, federated=federated, now_ts=now_ts)
    dashboard_data = build_dashboard_data(
        conn, project_root=project_root, federated=federated
    )
    # NOTE: the data file goes under `public/` so VitePress copies it verbatim
    # into the built `dist/` root (it does NOT copy arbitrary srcDir files), so
    # the widgets' runtime `withBase("/dashboard.data.json")` fetch resolves in
    # the static build — not just under the dev server (BDL-043).
    _write(
        out_dir / "public" / "dashboard.data.json",
        serialize_dashboard_data(dashboard_data),
        written,
    )
    _write(out_dir / "dashboard.md", render_dashboard_md(dashboard_data), written)

    # Showcase B — the 🌟 cross-repo landscape map (Mermaid, generated from the
    # federate hub output when given, else a degenerate single-repo map).
    landscape_data = build_landscape_data(conn, federated=federated)
    landscape_pages = existing_page_urls(conn)
    _write(
        out_dir / "landscape.md",
        render_landscape_md(landscape_data, pages=landscape_pages),
        written,
    )

    # Showcase C — the published validated docs. Copy the REAL docs/ tree into
    # site/docs/ preserving structure (source never mutated) and inject a
    # per-doc validation badge from the doc_sync engine (same source as
    # sync-check). Badges land only in the copy under out_dir.
    written.extend(publish_docs(conn, out_dir, project_root=project_root))

    _write(
        out_dir / ".vitepress" / "config.generated.mjs",
        render_nav_config(conn, project_root),
        written,
    )

    return SiteResult(out_dir=out_dir, written=tuple(sorted(written)))
