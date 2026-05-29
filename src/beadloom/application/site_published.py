"""Showcase C — published validated documentation + per-doc badges (BDL-040 BEAD-04).

The REAL root ``docs/`` tree is published as a first-class site section: every
``docs/**`` file is copied into ``site/docs/…`` preserving structure (the docs
are the source of truth, rendered as-is). Into the COPY only, a per-doc
**validation badge** is injected at the top.

Honest by construction
-----------------------
The badge status is derived from the ``doc_sync`` engine via
:func:`beadloom.doc_sync.engine.check_sync` — the SAME code path that
``beadloom sync-check`` runs — so a doc the gate calls stale shows stale on the
site. Per published doc the badge shows:

- ``✅ fresh`` or ``⚠️ stale — <reason>`` (``hash_changed`` / ``symbols_changed``
  / ``untracked_files``), exactly matching ``sync-check`` for that ``doc_path``;
- ``last synced <ts>`` — the stored ``sync_state.synced_at`` (a persisted value,
  NOT wall-clock, so the diffed output stays deterministic);
- the owning node's doc-coverage % (tracked source files / total, read-only) —
  for fresh/stale docs only;
- a doc tracked by NO pair is badged neutrally as a ``reference`` (an
  overview/guide not tied to a code symbol), with no coverage % (that figure is
  the node's source coverage, unrelated to the prose, so it would mislead).

Never mutate the source
-----------------------
Badges are injected ONLY into the copied file under ``site/docs/…``; the source
``docs/`` prose is never rewritten (no AI authoring — that is the deferred
F4.1). The badge is a stable, marker-delimited prefix between
:data:`BADGE_START` / :data:`BADGE_END`, so regeneration overwrites ONLY the
badge region and leaves the authored prose byte-for-byte intact.
"""

# beadloom:domain=application

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import sqlite3
    from pathlib import Path

logger = logging.getLogger(__name__)

#: Stable markers delimiting the injected badge region (so regeneration
#: overwrites only the badge, never the authored prose).
BADGE_START = "<!-- beadloom:badge-start -->"
BADGE_END = "<!-- beadloom:badge-end -->"

#: Boilerplate files excluded from per-node source-coverage counting (mirrors
#: the doc_sync engine's exclusions).
_COVERAGE_EXCLUDE = frozenset({"__init__.py", "__main__.py", "conftest.py"})


@dataclass(frozen=True)
class PublishedDoc:
    """A doc copied into ``site/docs/`` plus its validation badge inputs.

    ``status`` is the literal ``check_sync`` status for ``doc_path`` (``fresh`` /
    ``stale`` / ``untracked``); ``reason`` matches ``sync-check``'s reason for a
    stale doc. All fields are deterministic (``synced_at`` is a stored value).
    """

    doc_path: str
    status: str
    reason: str
    synced_at: str
    ref_id: str
    coverage_pct: float


def inject_badge(prose: str, badge_body: str) -> str:
    """Return *prose* with *badge_body* injected as a marker-delimited prefix.

    The badge is wrapped between :data:`BADGE_START` / :data:`BADGE_END`. If a
    previous badge region is present it is replaced in place; the authored prose
    after the region is preserved byte-for-byte.
    """
    block = f"{BADGE_START}\n{badge_body}\n{BADGE_END}\n\n"
    if BADGE_START in prose and BADGE_END in prose:
        before, _, rest = prose.partition(BADGE_START)
        _, _, after = rest.partition(BADGE_END)
        # Drop the single separating blank line we add after a badge, so
        # re-injection is byte-stable (no accumulating blank lines).
        after = after[2:] if after.startswith("\n\n") else after.lstrip("\n")
        return f"{before}{block}{after}"
    return f"{block}{prose}"


def _node_coverage_pct(
    conn: sqlite3.Connection, ref_id: str, project_root: Path
) -> float:
    """The owning node's doc-coverage %: tracked source files / total (read-only).

    Mirrors the doc_sync engine's source-coverage notion without mutating
    anything. Returns 100.0 when the node has no directory source (nothing to
    track) and it is documented; 0.0 for an untracked / unknown node.
    """
    if not ref_id:
        return 0.0
    row = conn.execute(
        "SELECT source FROM nodes WHERE ref_id = ?", (ref_id,)
    ).fetchone()
    source = row["source"] if row is not None else None
    if not source or not source.endswith("/"):
        # File-level or no source: documented nodes count as fully covered.
        return 100.0
    source_dir = project_root / source
    if not source_dir.is_dir():
        return 100.0
    disk_files = {
        str(p.relative_to(project_root))
        for p in sorted(source_dir.glob("*.py"))
        if p.name not in _COVERAGE_EXCLUDE
    }
    if not disk_files:
        return 100.0
    tracked: set[str] = set()
    for tbl_row in conn.execute(
        "SELECT code_path FROM sync_state WHERE ref_id = ?", (ref_id,)
    ).fetchall():
        tracked.add(tbl_row["code_path"])
    for sym_row in conn.execute(
        "SELECT file_path FROM code_symbols WHERE annotations LIKE ?",
        (f'%"{ref_id}"%',),
    ).fetchall():
        tracked.add(sym_row["file_path"])
    covered = len(disk_files & tracked)
    return round(covered / len(disk_files) * 100.0, 1)


def _synced_at_for(conn: sqlite3.Connection, doc_path: str) -> str:
    """The stored ``sync_state.synced_at`` for *doc_path* (empty if none)."""
    row = conn.execute(
        "SELECT synced_at FROM sync_state WHERE doc_path = ? "
        "ORDER BY synced_at LIMIT 1",
        (doc_path,),
    ).fetchone()
    return str(row["synced_at"]) if row is not None else ""


def build_published_docs(
    conn: sqlite3.Connection, *, project_root: Path
) -> list[PublishedDoc]:
    """Build the per-doc validation inputs for every doc on disk under ``docs/``.

    Status comes from :func:`check_sync` (the sync-check code path); a doc with
    no sync pair is ``untracked``. Sorted by ``doc_path`` (deterministic).
    """
    from beadloom.doc_sync.engine import check_sync

    docs_dir = project_root / "docs"
    if not docs_dir.is_dir():
        return []

    # Authoritative status/reason per doc_path — the literal sync-check path.
    # Extract the primitives we need (status/reason/ref_id) so the rest of the
    # function is free of the engine's ``Any``-typed result dicts.
    results = check_sync(conn, project_root=project_root)
    by_doc: dict[str, tuple[str, str, str]] = {}
    for res in results:
        doc_path = str(res["doc_path"])
        status = str(res["status"])
        # A doc may appear in multiple pairs; stale wins over ok (matches the
        # gate, which fails if any pair is stale).
        prior = by_doc.get(doc_path)
        if prior is None or status == "stale":
            by_doc[doc_path] = (status, str(res.get("reason", "ok")), str(res["ref_id"]))

    # ref_id lookup from the docs table for untracked docs (no sync pair).
    ref_by_doc: dict[str, str] = {}
    for row in conn.execute(
        "SELECT path, ref_id FROM docs WHERE ref_id IS NOT NULL"
    ).fetchall():
        ref_by_doc[str(row["path"])] = str(row["ref_id"])

    published: list[PublishedDoc] = []
    for md in sorted(docs_dir.rglob("*.md")):
        rel_path = md.relative_to(docs_dir)
        if any(part.startswith(".") for part in rel_path.parts):
            continue  # skip hidden docs (consistent with publish_docs)
        rel = str(rel_path)
        entry = by_doc.get(rel)
        if entry is not None and entry[0] in ("ok", "stale"):
            raw_status, reason, ref_id = entry
            status = "fresh" if raw_status == "ok" else "stale"
            synced_at = _synced_at_for(conn, rel)
            coverage = _node_coverage_pct(conn, ref_id, project_root)
        else:
            status, reason, synced_at = "untracked", "untracked", ""
            ref_id = ref_by_doc.get(rel, "")
            coverage = _node_coverage_pct(conn, ref_id, project_root) if ref_id else 0.0
        published.append(
            PublishedDoc(
                doc_path=rel,
                status=status,
                reason=reason,
                synced_at=synced_at,
                ref_id=ref_id,
                coverage_pct=coverage,
            )
        )
    return published


def _badge_body(doc: PublishedDoc) -> str:
    """The human-readable badge body for a published doc (deterministic)."""
    if doc.status == "fresh":
        head = "✅ **fresh**"
    elif doc.status == "stale":
        head = f"⚠️ **stale** — {doc.reason}"
    else:
        # An untracked doc is a guide/overview not tied to a code symbol — not a
        # defect. Use neutral wording and DO NOT print a coverage % (the node's
        # source-coverage is unrelated to this prose and reads as a contradiction).
        head = "📘 **reference** — overview/guide, not tied to a code symbol"

    parts = [f"> {head}"]
    meta: list[str] = []
    if doc.synced_at:
        meta.append(f"last synced {doc.synced_at}")
    if doc.ref_id and doc.status != "untracked":
        meta.append(f"coverage {doc.coverage_pct:.0f}% (`{doc.ref_id}`)")
    if meta:
        parts.append("> ")
        parts.append("> " + " · ".join(meta))
    parts.append(
        "> "
    )
    parts.append(
        "> _Validation by Beadloom `doc_sync` — same source as `sync-check`._"
    )
    return "\n".join(parts)


def render_published_doc(doc: PublishedDoc, prose: str) -> str:
    """Return the published Markdown: badge prefix + the authored prose as-is."""
    return inject_badge(prose, _badge_body(doc))


def _render_docs_index(published: list[str]) -> str:
    """A deterministic landing page for the published-docs section.

    Lists every published doc as a relative link (``.md`` kept — VitePress
    rewrites to a clean URL). Emitted at ``site/docs/index.md`` so the
    Documentation nav target ``/docs/`` resolves (it would 404 otherwise — the
    source ``docs/`` has no root index).
    """
    lines = [
        "---",
        "title: Documentation",
        "---",
        "",
        "# Documentation",
        "",
        "The project's validated documentation, published as-is with a per-doc "
        "`doc_sync` freshness badge (same source as `sync-check`).",
        "",
    ]
    lines.extend(f"- [{path}](./{path})" for path in published)
    lines.append("")
    return "\n".join(lines) + "\n"


def publish_docs(
    conn: sqlite3.Connection,
    out_dir: Path,
    *,
    project_root: Path,
) -> list[Path]:
    """Copy ``docs/**`` into ``out_dir/docs/…`` with badges; return written paths.

    NEVER mutates the source ``docs/`` — badges are injected only into the copy.
    Non-Markdown files are copied verbatim (no badge). A generated
    ``docs/index.md`` landing page is emitted so the ``/docs/`` nav target
    resolves. Deterministic.
    """
    docs_dir = project_root / "docs"
    if not docs_dir.is_dir():
        return []

    badges = {d.doc_path: d for d in build_published_docs(conn, project_root=project_root)}
    written: list[Path] = []
    out_docs = out_dir / "docs"
    published_md: list[str] = []

    for src in sorted(docs_dir.rglob("*")):
        if not src.is_file():
            continue
        rel = src.relative_to(docs_dir)
        # Skip hidden / OS-junk files (e.g. ``.DS_Store``): they are
        # non-deterministic per machine and would pollute the published site.
        if any(part.startswith(".") for part in rel.parts):
            continue
        dst = out_docs / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.suffix == ".md":
            prose = src.read_text(encoding="utf-8")
            doc = badges.get(str(rel))
            content = render_published_doc(doc, prose) if doc is not None else prose
            dst.write_text(content, encoding="utf-8")
            published_md.append(rel.as_posix())
        else:
            dst.write_bytes(src.read_bytes())
        written.append(dst)

    # Landing page so the `/docs/` nav target resolves (the source docs/ tree
    # has no root index). Written last; deterministic (sorted links).
    index = out_docs / "index.md"
    index.parent.mkdir(parents=True, exist_ok=True)
    index.write_text(_render_docs_index(sorted(published_md)), encoding="utf-8")
    written.append(index)

    return written
