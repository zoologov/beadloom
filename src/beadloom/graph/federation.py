"""Cross-repo node identity + satellite export for federation (BDL-037).

A graph ref may name a node in *another* repo using the ``@<repo>:<ref_id>``
form (e.g. ``@integration-service:plans``). A plain ref (no leading ``@``) is
local, exactly as before — federation is purely additive.

This module owns the :class:`FederatedRef` value type and the :func:`parse_ref`
parser. Malformed foreign refs raise :class:`FederationRefError` so the loader
can record them in ``result.errors`` instead of silently dropping them.

It also owns the **satellite export** (:func:`build_export` /
:func:`serialize_export`): a deterministic, self-describing JSON artifact that a
hub aggregates (BEAD-04). Determinism (sorted keys + sorted node/edge arrays)
keeps exports reviewable as diffs. The export envelope records ``commit_sha``
and ``exported_at`` so the hub can report staleness it cannot otherwise verify.
"""

# beadloom:domain=graph

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import sqlite3
    from pathlib import Path

# Marker that introduces a foreign (cross-repo) reference.
_FOREIGN_MARKER = "@"

# Export artifact schema version (bumped on breaking shape changes; the hub
# tolerates/reports mismatches).
EXPORT_SCHEMA_VERSION = 1


class FederationRefError(ValueError):
    """Raised when a ``@...`` foreign ref is malformed.

    A leading ``@`` signals the author intended a cross-repo reference, so a
    broken shape is an error to surface — never a silently-accepted local ref.
    Malformed examples: ``@:x`` (empty repo), ``@repo:`` (empty ref_id),
    ``@repo`` (no separator), ``@``.
    """


@dataclass(frozen=True)
class FederatedRef:
    """A graph reference that may point at another repo.

    ``repo is None`` means a local reference (the common case). Otherwise the
    ref names node ``ref_id`` in satellite repo ``repo``; it resolves against
    the federated union at the hub, not during a single-repo load.
    """

    repo: str | None
    ref_id: str

    @property
    def is_foreign(self) -> bool:
        """True when this ref targets another repo."""
        return self.repo is not None

    @property
    def qualified(self) -> str:
        """Canonical string form: ``@repo:ref_id`` (foreign) or ``ref_id`` (local)."""
        if self.repo is None:
            return self.ref_id
        return f"{_FOREIGN_MARKER}{self.repo}:{self.ref_id}"


def is_foreign_ref(raw: str) -> bool:
    """Cheap check: does *raw* look like a foreign ref (leading ``@``)?

    Does not validate the shape — use :func:`parse_ref` for that.
    """
    return raw.startswith(_FOREIGN_MARKER)


def parse_ref(raw: str) -> FederatedRef:
    """Parse a graph ref into a :class:`FederatedRef`.

    - ``"routing"``            -> local ``FederatedRef(None, "routing")``
    - ``"@repo:plans"``        -> foreign ``FederatedRef("repo", "plans")``
    - malformed ``@...``       -> :class:`FederationRefError`

    Only the first ``:`` after the marker separates repo from ref_id, so a
    foreign ref_id may itself contain colons (``@repo:ns:thing``). A plain ref
    with a colon and no leading ``@`` stays local untouched.
    """
    if not raw.startswith(_FOREIGN_MARKER):
        if not raw:
            raise FederationRefError("Empty ref is not a valid node reference.")
        return FederatedRef(repo=None, ref_id=raw)

    body = raw[len(_FOREIGN_MARKER) :]
    repo, sep, ref_id = body.partition(":")
    if not sep or not repo or not ref_id:
        raise FederationRefError(
            f"Malformed foreign ref '{raw}': expected '@<repo>:<ref_id>' "
            f"with non-empty repo and ref_id."
        )
    return FederatedRef(repo=repo, ref_id=ref_id)


# --- Satellite export (BEAD-03) ---------------------------------------------


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
) -> dict[str, object]:
    """Build the satellite export artifact from the indexed graph.

    Pure with respect to its inputs: ``exported_at`` and ``commit_sha`` are
    injected so the output is deterministic (tests pass fixed values; the CLI
    passes wall-clock UTC + git HEAD). Nodes are sorted by ``ref_id`` and edges
    by ``(src, dst, kind)`` so identical graphs serialize byte-identically.
    """
    node_rows = conn.execute(
        "SELECT ref_id, kind, summary, source, lifecycle FROM nodes ORDER BY ref_id"
    ).fetchall()
    edge_rows = conn.execute(
        "SELECT src_ref_id, dst_ref_id, kind, extra, lifecycle FROM edges "
        "ORDER BY src_ref_id, dst_ref_id, kind"
    ).fetchall()
    return {
        "schema_version": EXPORT_SCHEMA_VERSION,
        "repo": repo,
        "commit_sha": commit_sha,
        "exported_at": exported_at,
        "generator": generator,
        "nodes": [_export_node(r) for r in node_rows],
        "edges": [_export_edge(r) for r in edge_rows],
    }


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
    """Return the current git HEAD sha, or ``None`` outside a git repo (Q4)."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],  # noqa: S607
            cwd=project_root,
            capture_output=True,
            text=True,
        )
    except (FileNotFoundError, OSError):
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None
