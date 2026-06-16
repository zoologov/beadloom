# beadloom:domain=graph
# beadloom:feature=federation
"""Satellite export: the deterministic, self-describing JSON artifact (BEAD-03).

A satellite repo emits :func:`build_export` / :func:`serialize_export`: a
deterministic JSON artifact that a hub aggregates (BEAD-04). Determinism (sorted
keys + sorted node/edge arrays) keeps exports reviewable as diffs. The export
envelope records ``commit_sha`` and ``exported_at`` so the hub can report
staleness it cannot otherwise verify, plus the resolved ``repo`` / ``landscape``
provenance (:func:`resolve_repo_name` / :func:`resolve_landscape`).
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import sqlite3

# Export artifact schema version (bumped on breaking shape changes; the hub
# tolerates/reports mismatches).
#
# v2 (BDL-038 BEAD-03): adds the ``protocol: graphql`` contract wire — a producer
# edge carries ``contract.exposed`` (parsed SDL surface) and a consumer edge
# carries ``contract.references``. The change is purely additive: v1 exports
# (AMQP-only / no GraphQL fields) still read without error — ``aggregate_exports``
# never requires the new fields (missing -> empty surface).
EXPORT_SCHEMA_VERSION = 2


def _export_node(row: sqlite3.Row) -> dict[str, object]:
    """Serialize one ``nodes`` row into a deterministic node dict."""
    return {
        "ref_id": row["ref_id"],
        "kind": row["kind"],
        "summary": row["summary"],
        "lifecycle": row["lifecycle"],
        "source": row["source"],
    }


def _export_edge(row: sqlite3.Row) -> dict[str, object]:
    """Serialize one ``edges`` row into a deterministic edge dict.

    AMQP/contract metadata (when present under the ``contract`` key of the
    edge's ``extra`` JSON) is surfaced as a top-level ``contract`` field;
    edges without it omit the key entirely (smaller, stable diffs).
    """
    edge: dict[str, object] = {
        "src": row["src_ref_id"],
        "dst": row["dst_ref_id"],
        "kind": row["kind"],
        "lifecycle": row["lifecycle"],
    }
    contract = _edge_contract(row["extra"])
    if contract is not None:
        edge["contract"] = contract
    return edge


def _edge_contract(raw_extra: str | None) -> dict[str, object] | None:
    """Extract the optional ``contract`` payload from an edge's ``extra`` JSON."""
    if not raw_extra:
        return None
    try:
        extra = json.loads(raw_extra)
    except json.JSONDecodeError:
        return None
    if not isinstance(extra, dict):
        return None
    contract = extra.get("contract")
    return contract if isinstance(contract, dict) else None


def build_export(
    conn: sqlite3.Connection,
    *,
    repo: str,
    commit_sha: str | None,
    exported_at: str,
    generator: str,
    landscape: str | None = None,
) -> dict[str, object]:
    """Build the satellite export artifact from the indexed graph.

    Pure with respect to its inputs: ``exported_at`` and ``commit_sha`` are
    injected so the output is deterministic (tests pass fixed values; the CLI
    passes wall-clock UTC + git HEAD). Nodes are sorted by ``ref_id`` and edges
    by ``(src, dst, kind)`` so identical graphs serialize byte-identically.

    ``landscape`` (BEAD-06, U5) names the *product* a satellite belongs to. It
    is emitted ONLY when explicitly resolved (config ``landscape:`` key); a
    landscape-less export is the F1 back-compat shape — the hub then treats the
    whole ``federate`` run as one landscape, so single-product reconciliation is
    byte-identical to F1. A genuine cross-product link is still expressed with an
    explicit ``@repo:`` ref, which resolves regardless of landscape.
    """
    node_rows = conn.execute(
        "SELECT ref_id, kind, summary, source, lifecycle FROM nodes ORDER BY ref_id"
    ).fetchall()
    edges = [_export_edge(r) for r in _edge_rows(conn)]
    edges.sort(key=lambda e: (str(e["src"]), str(e["dst"]), str(e["kind"])))
    export: dict[str, object] = {
        "schema_version": EXPORT_SCHEMA_VERSION,
        "repo": repo,
        "commit_sha": commit_sha,
        "exported_at": exported_at,
        "generator": generator,
        "nodes": [_export_node(r) for r in node_rows],
        "edges": edges,
    }
    if landscape is not None:
        export["landscape"] = landscape
    return export


def _edge_rows(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    """Union local ``edges`` with cross-repo ``foreign_edges`` (#100).

    Declared ``@repo:`` edges live in ``foreign_edges`` (their endpoint cannot
    satisfy the local FK) and would otherwise never reach the artifact, so the
    hub could not see intent-declared cross-repo links. Both tables expose the
    same columns; sorting happens in :func:`build_export`.
    """
    rows = list(
        conn.execute(
            "SELECT src_ref_id, dst_ref_id, kind, extra, lifecycle FROM edges"
        ).fetchall()
    )
    if _has_foreign_edges_table(conn):
        rows.extend(
            conn.execute(
                "SELECT src_ref_id, dst_ref_id, kind, extra, lifecycle FROM foreign_edges"
            ).fetchall()
        )
    return rows


def _has_foreign_edges_table(conn: sqlite3.Connection) -> bool:
    """True when the ``foreign_edges`` table exists (older DBs may lack it)."""
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='foreign_edges'"
    ).fetchone()
    return row is not None


def serialize_export(export: dict[str, object]) -> str:
    """Serialize an export dict to deterministic JSON (sorted keys, 2-space)."""
    return json.dumps(export, sort_keys=True, indent=2, ensure_ascii=False)


def resolve_repo_name(project_root: Path) -> str:
    """Resolve the repo name for an export (Q3).

    Precedence: ``.beadloom/config.yml`` ``repo:`` key > git remote basename >
    project directory name. Deterministic and overridable.
    """
    from_config = _repo_from_config(project_root)
    if from_config:
        return from_config
    from_git = _repo_from_git_remote(project_root)
    if from_git:
        return from_git
    return project_root.resolve().name


def resolve_landscape(project_root: Path) -> str:
    """Resolve the landscape (product) name for an export (BEAD-06, U5).

    Precedence: ``.beadloom/config.yml`` ``landscape:`` key > the resolved repo
    name. A satellite that does not declare a landscape belongs to a product
    named after its repo — so a single-product run (every satellite its own
    landscape, or none declared) reconciles exactly as F1. Distinct declared
    landscapes scope implicit contract matching, so unrelated products in a
    company-landscape never cross-pollute (the CLI omits the value from the
    export when it equals the repo default, preserving the F1 wire shape).
    """
    from_config = _landscape_from_config(project_root)
    if from_config:
        return from_config
    return resolve_repo_name(project_root)


def _landscape_from_config(project_root: Path) -> str | None:
    """Read the ``landscape:`` key from ``.beadloom/config.yml`` if present."""
    config_path = project_root / ".beadloom" / "config.yml"
    if not config_path.exists():
        return None
    import yaml

    config = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    landscape = config.get("landscape")
    return landscape if isinstance(landscape, str) and landscape else None


def _repo_from_config(project_root: Path) -> str | None:
    """Read the ``repo:`` key from ``.beadloom/config.yml`` if present."""
    config_path = project_root / ".beadloom" / "config.yml"
    if not config_path.exists():
        return None
    import yaml

    config = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    repo = config.get("repo")
    return repo if isinstance(repo, str) and repo else None


def _repo_from_git_remote(project_root: Path) -> str | None:
    """Derive the repo name from the ``origin`` git remote URL basename."""
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],  # noqa: S607
            cwd=project_root,
            capture_output=True,
            text=True,
        )
    except (FileNotFoundError, OSError):
        return None
    if result.returncode != 0:
        return None
    url = result.stdout.strip()
    if not url:
        return None
    basename = url.rstrip("/").rsplit("/", 1)[-1].rsplit(":", 1)[-1]
    if basename.endswith(".git"):
        basename = basename[: -len(".git")]
    return basename or None


def current_commit_sha(project_root: Path) -> str | None:
    """Return the current git HEAD sha, or ``None`` outside a git repo (Q4).

    Returns ``None`` when *project_root* is not itself the git toplevel (#103):
    ``git`` walks UP to the enclosing repo for a nested non-repo dir, which
    would otherwise leak an unrelated (host) repo's HEAD into the export. An
    honest "unknown HEAD" beats a misleading provenance sha.
    """
    if not _is_git_toplevel(project_root):
        return None
    sha = _run_git(project_root, "rev-parse", "HEAD")
    return sha or None


def _is_git_toplevel(project_root: Path) -> bool:
    """True when *project_root* is the toplevel of its own git repository."""
    toplevel = _run_git(project_root, "rev-parse", "--show-toplevel")
    if toplevel is None:
        return False
    try:
        return Path(toplevel).resolve() == project_root.resolve()
    except OSError:
        return False


def _run_git(cwd: Path, *args: str) -> str | None:
    """Run ``git <args>`` in *cwd*; return stripped stdout, or ``None`` on failure."""
    try:
        result = subprocess.run(  # noqa: S603
            ["git", *args],  # noqa: S607
            cwd=cwd,
            capture_output=True,
            text=True,
        )
    except (FileNotFoundError, OSError):
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip()
