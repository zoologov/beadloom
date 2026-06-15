"""Sync engine: doc-code synchronization state management."""

# beadloom:domain=doc-sync
# beadloom:feature=sync-check

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import sqlite3


def _compute_symbols_hash(conn: sqlite3.Connection, ref_id: str) -> str:
    """Compute SHA-256 of sorted code_symbols for a *ref_id*.

    Returns an empty string when no symbols are annotated with the given
    ref_id, allowing callers to skip drift checks for unlinked nodes.
    """
    rows = conn.execute(
        "SELECT file_path, symbol_name, kind FROM code_symbols "
        "WHERE annotations LIKE ? ORDER BY file_path, symbol_name",
        (f'%"{ref_id}"%',),
    ).fetchall()
    if not rows:
        return ""
    data = "|".join(f"{r['file_path']}:{r['symbol_name']}:{r['kind']}" for r in rows)
    return hashlib.sha256(data.encode()).hexdigest()


@dataclass
class SyncPair:
    """A doc-code pair linked through a shared ref_id."""

    ref_id: str
    doc_path: str
    code_path: str
    doc_hash: str
    code_hash: str


# beadloom:domain=doc-sync
def build_sync_state(conn: sqlite3.Connection) -> list[SyncPair]:
    """Build sync pairs from docs and code_symbols sharing a ref_id.

    For each ref_id that has both a doc and at least one code symbol,
    creates a SyncPair with current hashes.
    """
    # Find ref_ids that have linked docs.
    doc_rows = conn.execute(
        "SELECT ref_id, path, hash FROM docs WHERE ref_id IS NOT NULL"
    ).fetchall()

    if not doc_rows:
        return []

    pairs: list[SyncPair] = []

    for doc_row in doc_rows:
        ref_id = doc_row["ref_id"]
        doc_path = doc_row["path"]
        doc_hash = doc_row["hash"]

        # Find code symbols annotated with this ref_id.
        sym_rows = conn.execute("SELECT * FROM code_symbols").fetchall()
        seen_files: set[str] = set()

        for sym in sym_rows:
            annotations: dict[str, Any] = json.loads(sym["annotations"])
            for _key, val in annotations.items():
                if val == ref_id and sym["file_path"] not in seen_files:
                    seen_files.add(sym["file_path"])
                    pairs.append(
                        SyncPair(
                            ref_id=ref_id,
                            doc_path=doc_path,
                            code_path=sym["file_path"],
                            doc_hash=doc_hash,
                            code_hash=sym["file_hash"],
                        )
                    )
                    break

    return pairs


def _file_hash(path: Path) -> str | None:
    """Compute SHA-256 hash of a file, or None if file doesn't exist."""
    if not path.is_file():
        return None
    content = path.read_text(encoding="utf-8")
    return hashlib.sha256(content.encode()).hexdigest()


def check_sync(
    conn: sqlite3.Connection,
    project_root: Path | None = None,
) -> list[dict[str, Any]]:
    """Check sync_state entries against actual file hashes on disk.

    Reads files directly from disk to detect changes since last sync,
    independent of whether reindex has been run.  Also runs source
    coverage and doc coverage checks to catch untracked files and
    missing module mentions.

    Parameters
    ----------
    conn:
        Open SQLite connection.
    project_root:
        Project root directory. If None, inferred from DB path.

    Returns list of dicts with doc_path, code_path, ref_id, status,
    reason, and optional details.
    """
    sync_rows = conn.execute("SELECT * FROM sync_state").fetchall()
    if not sync_rows:
        return []

    # Infer project root from database path if not provided.
    if project_root is None:
        db_path = conn.execute("PRAGMA database_list").fetchone()[2]
        project_root = Path(db_path).parent.parent  # .beadloom/beadloom.db → project

    results: list[dict[str, Any]] = []

    for row in sync_rows:
        doc_path = row["doc_path"]
        code_path = row["code_path"]
        ref_id = row["ref_id"]
        stored_code_hash = row["code_hash_at_sync"]
        stored_doc_hash = row["doc_hash_at_sync"]
        doc_hash_at_last_edit: str = (
            row["doc_hash_at_last_edit"]
            if "doc_hash_at_last_edit" in row.keys()  # noqa: SIM118 - sqlite3.Row `in` checks values, not keys
            else ""
        )

        # Hash actual files on disk.
        current_doc_hash = _file_hash(project_root / "docs" / doc_path)
        current_code_hash = _file_hash(project_root / code_path)

        status = "ok"
        reason = "ok"

        # --- Two-phase sync detection ---
        # When doc_hash_at_last_edit is set, use it to detect code drift
        # that survives reindex (which resets code_hash_at_sync).
        doc_edited = (
            bool(current_doc_hash)
            and bool(doc_hash_at_last_edit)
            and current_doc_hash != doc_hash_at_last_edit
        )

        if current_code_hash and current_code_hash != stored_code_hash:
            status = "stale"
            reason = "hash_changed"
        if current_doc_hash and current_doc_hash != stored_doc_hash:
            status = "stale"
            reason = "hash_changed"

        # Update doc_hash_at_last_edit when doc changes.
        if doc_edited and current_doc_hash:
            # Doc was edited: record new doc hash and reset code
            # baseline so future checks measure drift from here.
            conn.execute(
                "UPDATE sync_state "
                "SET doc_hash_at_last_edit = ?, "
                "code_hash_at_sync = ? "
                "WHERE doc_path = ? AND code_path = ?",
                (
                    current_doc_hash,
                    current_code_hash or stored_code_hash,
                    doc_path,
                    code_path,
                ),
            )
        elif not doc_hash_at_last_edit and current_doc_hash:
            # Legacy/first run: initialize doc_hash_at_last_edit.
            conn.execute(
                "UPDATE sync_state "
                "SET doc_hash_at_last_edit = ? "
                "WHERE doc_path = ? AND code_path = ?",
                (current_doc_hash, doc_path, code_path),
            )

        # Symbol-level drift detection.
        stored_symbols_hash = row["symbols_hash"] if "symbols_hash" in row.keys() else ""  # noqa: SIM118 - sqlite3.Row `in` checks values, not keys
        if stored_symbols_hash:
            current_symbols_hash = _compute_symbols_hash(conn, ref_id)
            if current_symbols_hash != stored_symbols_hash and status == "ok":
                # Code symbols changed but doc hash is same -> semantic drift.
                status = "stale"
                reason = "symbols_changed"

        # Update status in DB.
        conn.execute(
            "UPDATE sync_state SET status = ? WHERE doc_path = ? AND code_path = ?",
            (status, doc_path, code_path),
        )

        results.append(
            {
                "doc_path": doc_path,
                "code_path": code_path,
                "ref_id": ref_id,
                "status": status,
                "reason": reason,
            }
        )

    conn.commit()

    # --- Phase 2: Source coverage checks ---
    source_gaps = check_source_coverage(conn, project_root)

    # Build a lookup of ref_ids already in results and their indices.
    ref_id_indices: dict[str, list[int]] = {}
    for i, r in enumerate(results):
        ref_id_indices.setdefault(r["ref_id"], []).append(i)

    for gap in source_gaps:
        gap_ref_id: str = gap["ref_id"]
        gap_doc_path: str = gap["doc_path"]
        untracked: list[str] = gap["untracked_files"]
        details = ", ".join(Path(f).name for f in untracked)

        if gap_ref_id in ref_id_indices:
            # Update existing results: if any are "ok", change to "stale"
            for idx in ref_id_indices[gap_ref_id]:
                if results[idx]["status"] == "ok":
                    results[idx]["status"] = "stale"
                    results[idx]["reason"] = "untracked_files"
                    results[idx]["details"] = details
                    # Update DB status
                    conn.execute(
                        "UPDATE sync_state SET status = 'stale' "
                        "WHERE doc_path = ? AND code_path = ?",
                        (results[idx]["doc_path"], results[idx]["code_path"]),
                    )
        else:
            # Add new result for ref_id not yet in sync_state
            results.append(
                {
                    "doc_path": gap_doc_path,
                    "code_path": "",
                    "ref_id": gap_ref_id,
                    "status": "stale",
                    "reason": "untracked_files",
                    "details": details,
                }
            )

    # --- Phase 3: Doc coverage checks ---
    doc_gaps = check_doc_coverage(conn, project_root)
    # Rebuild index since source coverage may have added entries.
    ref_id_indices = {}
    for i, r in enumerate(results):
        ref_id_indices.setdefault(r["ref_id"], []).append(i)

    for gap in doc_gaps:
        gap_ref_id = gap["ref_id"]
        gap_doc_path = gap["doc_path"]
        missing: list[str] = gap["missing_modules"]
        details = ", ".join(missing)

        if gap_ref_id in ref_id_indices:
            for idx in ref_id_indices[gap_ref_id]:
                if results[idx]["status"] == "ok":
                    results[idx]["status"] = "stale"
                    results[idx]["reason"] = "missing_modules"
                    results[idx]["details"] = details
                    conn.execute(
                        "UPDATE sync_state SET status = 'stale' "
                        "WHERE doc_path = ? AND code_path = ?",
                        (results[idx]["doc_path"], results[idx]["code_path"]),
                    )
        else:
            results.append(
                {
                    "doc_path": gap_doc_path,
                    "code_path": "",
                    "ref_id": gap_ref_id,
                    "status": "stale",
                    "reason": "missing_modules",
                    "details": details,
                }
            )

    conn.commit()
    return results


def _validate_git_ref(project_root: Path, ref: str) -> bool:
    """Check a git ref resolves, mirroring ``graph.diff._validate_git_ref``.

    Uses ``git rev-parse --verify <ref>``. An all-zero SHA (force-push /
    first-push sentinel) never resolves, so it is rejected here too.
    """
    result = subprocess.run(  # noqa: S603
        ["git", "rev-parse", "--verify", ref],  # noqa: S607
        cwd=project_root,
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode == 0


def _file_content_at_ref(project_root: Path, rel_path: str, ref: str) -> str | None:
    """Return *rel_path* content at *ref* via ``git show``, or None if absent.

    Non-destructive: reads from the object store, never touches the working
    tree or any beadloom DB.
    """
    result = subprocess.run(  # noqa: S603
        ["git", "show", f"{ref}:{rel_path}"],  # noqa: S607
        cwd=project_root,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return None
    return result.stdout


def _hash_text(text: str) -> str:
    """SHA-256 of *text* (UTF-8), matching :func:`_file_hash`'s digest."""
    return hashlib.sha256(text.encode()).hexdigest()


def check_sync_since(
    conn: sqlite3.Connection,
    *,
    project_root: Path,
    since: str,
) -> list[dict[str, Any]]:
    """Report doc-code pairs that drifted **relative to a git ref baseline**.

    Unlike :func:`check_sync` (which compares against the stored ``sync_state``
    baseline), this compares the *current* working tree against the code state
    captured at ``since``. A fresh CI checkout re-baselines ``sync_state`` to
    the just-pushed code, masking per-push drift; the ref baseline is immune to
    that because it reads the parent commit straight from git history.

    A tracked pair is **stale-since-ref** iff:

    * its code file changed between ``since`` and the working tree, **and**
    * its linked doc was *not* correspondingly updated since ``since``.

    If the doc *also* changed since ``since`` the dev already touched it, so the
    pair is reported ``ok`` (we never re-flag a doc the dev just updated).

    Pure and deterministic (no wall-clock); reads git + disk only, mutates
    neither ``sync_state`` nor the working tree. The result list mirrors
    :func:`check_sync`'s shape so the JSON/porcelain renderers are shared.
    """
    sync_rows = conn.execute(
        "SELECT doc_path, code_path, ref_id FROM sync_state"
    ).fetchall()

    results: list[dict[str, Any]] = []
    for row in sync_rows:
        doc_path = row["doc_path"]
        code_path = row["code_path"]
        ref_id = row["ref_id"]
        if not code_path:
            continue

        code_at_ref = _file_content_at_ref(project_root, code_path, since)
        current_code_hash = _file_hash(project_root / code_path)
        ref_code_hash = _hash_text(code_at_ref) if code_at_ref is not None else None
        code_drifted = ref_code_hash != current_code_hash

        doc_rel = str(Path("docs") / doc_path)
        doc_at_ref = _file_content_at_ref(project_root, doc_rel, since)
        current_doc_hash = _file_hash(project_root / "docs" / doc_path)
        ref_doc_hash = _hash_text(doc_at_ref) if doc_at_ref is not None else None
        doc_changed = ref_doc_hash != current_doc_hash

        stale = code_drifted and not doc_changed
        results.append(
            {
                "doc_path": doc_path,
                "code_path": code_path,
                "ref_id": ref_id,
                "status": "stale" if stale else "ok",
                "reason": "hash_changed" if stale else "ok",
            }
        )

    return results


def mark_synced(
    conn: sqlite3.Connection,
    doc_path: str,
    code_path: str,
    project_root: Path,
) -> None:
    """Recompute hashes for a doc-code pair and mark as synced.

    Also updates ``symbols_hash`` to the current value so that future
    :func:`check_sync` calls use this as the new baseline for symbol drift
    detection.
    """
    doc_hash = _file_hash(project_root / "docs" / doc_path)
    code_hash = _file_hash(project_root / code_path)

    # Look up ref_id for this pair to recompute symbols_hash.
    row = conn.execute(
        "SELECT ref_id FROM sync_state WHERE doc_path = ? AND code_path = ?",
        (doc_path, code_path),
    ).fetchone()
    symbols_hash = _compute_symbols_hash(conn, row["ref_id"]) if row else ""

    now = datetime.now(tz=timezone.utc).isoformat()
    conn.execute(
        "UPDATE sync_state SET doc_hash_at_sync = ?, code_hash_at_sync = ?, "
        "symbols_hash = ?, synced_at = ?, status = 'ok', "
        "doc_hash_at_last_edit = ? "
        "WHERE doc_path = ? AND code_path = ?",
        (doc_hash, code_hash, symbols_hash, now, doc_hash, doc_path, code_path),
    )
    conn.commit()


def mark_synced_by_ref(
    conn: sqlite3.Connection,
    ref_id: str,
    project_root: Path,
) -> int:
    """Mark all doc-code pairs for *ref_id* as synced.

    Recomputes current file hashes and ``symbols_hash``, establishing a new
    baseline for symbol drift detection.
    Returns the number of rows updated.
    """
    rows = conn.execute(
        "SELECT doc_path, code_path FROM sync_state WHERE ref_id = ?",
        (ref_id,),
    ).fetchall()

    if not rows:
        return 0

    symbols_hash = _compute_symbols_hash(conn, ref_id)
    now = datetime.now(tz=timezone.utc).isoformat()
    count = 0
    for row in rows:
        doc_hash = _file_hash(project_root / "docs" / row["doc_path"])
        code_hash = _file_hash(project_root / row["code_path"])
        conn.execute(
            "UPDATE sync_state SET doc_hash_at_sync = ?, code_hash_at_sync = ?, "
            "symbols_hash = ?, synced_at = ?, status = 'ok', "
            "doc_hash_at_last_edit = ? "
            "WHERE doc_path = ? AND code_path = ?",
            (doc_hash, code_hash, symbols_hash, now, doc_hash, row["doc_path"], row["code_path"]),
        )
        count += 1

    conn.commit()
    return count


# ---------------------------------------------------------------------------
# BDL-057 Layer 2 — reference doc surface-drift (advisory / warning)
#
# Reference / overview docs opt in with an in-doc annotation
# ``<!-- beadloom:watches=cli,graph,flow.yml -->``. Their coarse aggregate hash
# is baselined on reindex (:func:`build_reference_state`), re-checked on
# sync-check (:func:`check_reference_drift`, severity *warning*), and re-baselined
# on sync-update (:func:`mark_reference_synced`). This lives in the separate
# ``reference_state`` table and never touches the symbol-pair ``sync_state``
# logic or its reason-masking / fixpoint invariant.
# ---------------------------------------------------------------------------


def _resolve_reference_docs_dir(project_root: Path) -> Path:
    """Return the docs directory, honoring ``.beadloom/config.yml`` ``docs_dir``.

    Mirrors the application-layer resolver without importing upward: reads the
    optional ``docs_dir`` key from config, falling back to ``<root>/docs``.
    """
    import yaml

    config_path = project_root / ".beadloom" / "config.yml"
    if config_path.is_file():
        try:
            config = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
        except (OSError, yaml.YAMLError):
            config = {}
        docs_path = config.get("docs_dir") if isinstance(config, dict) else None
        if docs_path:
            return project_root / str(docs_path)
    return project_root / "docs"


def _discover_reference_docs(project_root: Path) -> list[tuple[str, list[str]]]:
    """Find markdown docs declaring a ``watches:`` annotation.

    Scans the top-level ``*.md`` files (e.g. ``README.md``, ``README.ru.md``)
    and every ``*.md`` under the docs directory. Returns a sorted list of
    ``(project-root-relative doc_path, watched surfaces)`` for docs whose
    annotation names at least one known surface.
    """
    from beadloom.doc_sync.surface import parse_watches

    candidates: list[Path] = sorted(project_root.glob("*.md"))
    docs_dir = _resolve_reference_docs_dir(project_root)
    if docs_dir.is_dir():
        candidates += sorted(docs_dir.rglob("*.md"))

    found: list[tuple[str, list[str]]] = []
    for path in candidates:
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        watches = parse_watches(text)
        if watches:
            rel = str(path.relative_to(project_root))
            found.append((rel, watches))
    return found


def build_reference_state(conn: sqlite3.Connection, project_root: Path) -> int:
    """Baseline the aggregate hash of every ``watches``-annotated reference doc.

    Discovers reference docs and records a ``reference_state`` row for each.

    The stored ``aggregate_hash`` baseline is **preserved across reindex** for
    docs already tracked with the *same* ``watches`` set — otherwise a routine
    reindex after a surface change would silently re-baseline and never warn (the
    same fixpoint concern as the symbol-pair ``sync_state``). A fresh baseline at
    the current hash is computed only for newly-discovered docs, or when the
    declared ``watches`` set itself changed (the old baseline no longer applies).
    Docs whose annotation was removed are dropped. Idempotent. Returns the number
    of reference docs recorded.
    """
    from beadloom.doc_sync.surface import aggregate_hash

    discovered = _discover_reference_docs(project_root)
    keep = {doc_path for doc_path, _ in discovered}

    prior: dict[str, tuple[str, str]] = {
        row["doc_path"]: (row["watches"], row["aggregate_hash"])
        for row in conn.execute(
            "SELECT doc_path, watches, aggregate_hash FROM reference_state"
        ).fetchall()
    }

    # Forget docs that no longer declare a watches annotation.
    for doc_path in prior:
        if doc_path not in keep:
            conn.execute(
                "DELETE FROM reference_state WHERE doc_path = ?", (doc_path,)
            )

    for doc_path, watches in discovered:
        watches_csv = ",".join(watches)
        prior_entry = prior.get(doc_path)
        if prior_entry is not None and prior_entry[0] == watches_csv:
            # Already tracked with the same surfaces — keep the existing baseline
            # so a later sync-check still sees drift accrued since it was set.
            continue
        agg = aggregate_hash(watches, conn, project_root)
        conn.execute(
            "INSERT INTO reference_state (doc_path, watches, aggregate_hash, status) "
            "VALUES (?, ?, ?, 'ok') "
            "ON CONFLICT(doc_path) DO UPDATE SET "
            "watches = excluded.watches, aggregate_hash = excluded.aggregate_hash, "
            "status = 'ok'",
            (doc_path, watches_csv, agg),
        )
    conn.commit()
    return len(discovered)


def check_reference_drift(
    conn: sqlite3.Connection,
    project_root: Path,
) -> list[dict[str, Any]]:
    """Recompute each reference doc's aggregate hash and report drift (warning).

    For every ``reference_state`` row, compares the stored baseline against the
    current aggregate hash of its watched surfaces. A mismatch yields
    ``status='surface_drift'`` with ``reason='surface_drift'`` and
    ``severity='warning'`` (never a hard failure); a match yields ``'ok'``. The
    new status is persisted. Returns one result dict per reference doc.
    """
    from beadloom.doc_sync.surface import aggregate_hash

    rows = conn.execute(
        "SELECT doc_path, watches, aggregate_hash FROM reference_state ORDER BY doc_path"
    ).fetchall()
    if not rows:
        return []

    results: list[dict[str, Any]] = []
    for row in rows:
        doc_path = row["doc_path"]
        watches = [s for s in row["watches"].split(",") if s]
        baseline = row["aggregate_hash"]

        current = aggregate_hash(watches, conn, project_root)
        drifted = current != baseline
        status = "surface_drift" if drifted else "ok"

        conn.execute(
            "UPDATE reference_state SET status = ? WHERE doc_path = ?",
            (status, doc_path),
        )
        results.append(
            {
                "doc_path": doc_path,
                "watches": row["watches"],
                "status": status,
                "reason": "surface_drift" if drifted else "ok",
                "severity": "warning",
            }
        )

    conn.commit()
    return results


def mark_reference_synced(
    conn: sqlite3.Connection,
    doc_path: str | None,
    project_root: Path,
    *,
    all_docs: bool = False,
) -> int:
    """Re-baseline a reference doc's aggregate hash, clearing surface drift.

    Recomputes the current aggregate hash for *doc_path* (or every reference doc
    when *all_docs* is set) and stores it with ``status='ok'``. Returns the
    number of rows re-baselined (0 when the doc is not a tracked reference doc).
    """
    from beadloom.doc_sync.surface import aggregate_hash

    if all_docs:
        rows = conn.execute("SELECT doc_path, watches FROM reference_state").fetchall()
    else:
        rows = conn.execute(
            "SELECT doc_path, watches FROM reference_state WHERE doc_path = ?",
            (doc_path,),
        ).fetchall()

    count = 0
    for row in rows:
        watches = [s for s in row["watches"].split(",") if s]
        agg = aggregate_hash(watches, conn, project_root)
        conn.execute(
            "UPDATE reference_state SET aggregate_hash = ?, status = 'ok' "
            "WHERE doc_path = ?",
            (agg, row["doc_path"]),
        )
        count += 1

    conn.commit()
    return count


# Excluded filenames — boilerplate, not doc-worthy
_COVERAGE_EXCLUDE = frozenset({"__init__.py", "conftest.py", "__main__.py"})

# File-level beadloom annotation in a source comment, e.g.
#   # beadloom:domain=core   or   # beadloom:feature=docs-audit
# Captures the ref_id value regardless of the key (domain/feature/...).
_FILE_ANNOTATION_RE = re.compile(
    r"beadloom:(?:domain|feature|service|entity)=([\w.\-]+)"
)

# Doc-side binding marker, e.g. <!-- beadloom:track=src/app/constants.py -->
_TRACK_MARKER_RE = re.compile(r"beadloom:track=([^\s>]+)")


def _file_annotation_ref_ids(path: Path) -> set[str]:
    """Return ref_ids declared by file-level beadloom annotations in *path*.

    Scans the head of the file for ``# beadloom:domain=X`` /
    ``# beadloom:feature=X`` style comments.  These declare node ownership
    even when the file contains no extractable top-level symbol (e.g. a pure
    constants module), so the file is still considered *tracked* (#89).
    """
    if not path.is_file():
        return set()
    try:
        content = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return set()
    return set(_FILE_ANNOTATION_RE.findall(content))


def _tracked_paths_from_doc(doc_file: Path, project_root: Path) -> set[str]:
    """Return code paths bound to a doc via ``beadloom:track`` markers (#90).

    Parses ``<!-- beadloom:track=<path> -->`` comments in *doc_file* and
    normalizes each path relative to *project_root* so it can be compared
    against the on-disk file set.
    """
    if not doc_file.is_file():
        return set()
    try:
        content = doc_file.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return set()

    tracked: set[str] = set()
    for raw in _TRACK_MARKER_RE.findall(content):
        candidate = Path(raw)
        if candidate.is_absolute():
            try:
                tracked.add(str(candidate.relative_to(project_root)))
            except ValueError:
                continue
        else:
            tracked.add(str(candidate))
    return tracked


def check_source_coverage(
    conn: sqlite3.Connection,
    project_root: Path,
) -> list[dict[str, Any]]:
    """Check if all source files in a node's directory are tracked in sync_state.

    For each node with a ``source`` field ending in ``/`` (a directory),
    compares actual Python files on disk against code_paths tracked in
    sync_state for that ref_id.

    Returns list of dicts with ``ref_id``, ``doc_path``, ``untracked_files``
    for nodes that have gaps.
    """
    # 1. Query nodes with directory-based source (ending in /)
    node_rows = conn.execute(
        "SELECT ref_id, source FROM nodes WHERE source IS NOT NULL AND source LIKE '%/'"
    ).fetchall()

    if not node_rows:
        return []

    results: list[dict[str, Any]] = []

    for node in node_rows:
        ref_id: str = node["ref_id"]
        source: str = node["source"]

        # 2. Resolve directory on disk
        source_dir = project_root / source
        if not source_dir.is_dir():
            continue

        # 3. Find doc_path for this ref_id (from sync_state first, then docs table)
        doc_row = conn.execute(
            "SELECT doc_path FROM sync_state WHERE ref_id = ? LIMIT 1",
            (ref_id,),
        ).fetchone()

        if doc_row is None:
            # Fallback to docs table
            doc_row = conn.execute(
                "SELECT path AS doc_path FROM docs WHERE ref_id = ? LIMIT 1",
                (ref_id,),
            ).fetchone()

        if doc_row is None:
            # No linked doc — skip, nothing to mark stale
            continue

        doc_path: str = doc_row["doc_path"]

        # 4. List *.py files on disk (non-recursive), excluding boilerplate
        disk_files: set[str] = set()
        for py_file in source_dir.glob("*.py"):
            if py_file.name in _COVERAGE_EXCLUDE:
                continue
            relative = str(py_file.relative_to(project_root))
            disk_files.add(relative)

        if not disk_files:
            continue

        # 5. Collect tracked code_paths from sync_state for this ref_id
        tracked: set[str] = set()
        sync_rows = conn.execute(
            "SELECT code_path FROM sync_state WHERE ref_id = ?",
            (ref_id,),
        ).fetchall()
        for row in sync_rows:
            tracked.add(row["code_path"])

        # 5b. Also include files tracked under child nodes (part_of this ref_id)
        child_rows = conn.execute(
            "SELECT src_ref_id FROM edges WHERE dst_ref_id = ? AND kind = 'part_of'",
            (ref_id,),
        ).fetchall()
        child_ref_ids = [r["src_ref_id"] for r in child_rows]

        for child_id in child_ref_ids:
            child_sync = conn.execute(
                "SELECT code_path FROM sync_state WHERE ref_id = ?",
                (child_id,),
            ).fetchall()
            for r in child_sync:
                tracked.add(r["code_path"])

        # 6. Also collect file_paths from code_symbols annotated with this ref_id
        #    OR any child ref_id
        all_ref_ids = [ref_id, *child_ref_ids]
        for rid in all_ref_ids:
            sym_rows = conn.execute(
                "SELECT file_path FROM code_symbols WHERE annotations LIKE ?",
                (f'%"{rid}"%',),
            ).fetchall()
            for row in sym_rows:
                tracked.add(row["file_path"])

        # 6b. (#90) Honor explicit `beadloom:track=path` markers in the doc.
        owned_ref_ids = set(all_ref_ids)
        tracked |= _tracked_paths_from_doc(
            project_root / "docs" / doc_path, project_root
        )

        # 6c. (#89) Honor file-level `# beadloom:domain/feature=` annotations.
        #     Symbol-less files (e.g. pure constants modules) produce no
        #     code_symbols rows, so the annotation is the only ownership
        #     signal — count the file as tracked when it declares this node.
        for disk_file in disk_files:
            if disk_file in tracked:
                continue
            if _file_annotation_ref_ids(project_root / disk_file) & owned_ref_ids:
                tracked.add(disk_file)

        # 7. Find untracked files
        untracked = sorted(disk_files - tracked)

        # 8. Report if gaps exist
        if untracked:
            results.append(
                {
                    "ref_id": ref_id,
                    "doc_path": doc_path,
                    "untracked_files": untracked,
                }
            )

    return results


def check_doc_coverage(
    conn: sqlite3.Connection,
    project_root: Path,
) -> list[dict[str, Any]]:
    """Check if documentation mentions module names from the node's source directory.

    For each node with a directory-based ``source``, lists Python file stems
    (without .py) and checks if the linked doc content contains each name.

    Returns list of dicts with ``ref_id``, ``doc_path``, ``missing_modules``
    for nodes where the doc is missing module mentions.
    """
    # 1. Query nodes with directory-based source (ending in /)
    node_rows = conn.execute(
        "SELECT ref_id, source FROM nodes WHERE source IS NOT NULL AND source LIKE '%/'"
    ).fetchall()

    if not node_rows:
        return []

    results: list[dict[str, Any]] = []

    for node in node_rows:
        ref_id: str = node["ref_id"]
        source: str = node["source"]

        # 2. Resolve source dir on disk
        source_dir = project_root / source
        if not source_dir.is_dir():
            continue

        # 3. Get the doc path from docs table for this ref_id
        doc_row = conn.execute(
            "SELECT path FROM docs WHERE ref_id = ? LIMIT 1",
            (ref_id,),
        ).fetchone()

        if doc_row is None:
            continue

        doc_path: str = doc_row["path"]

        # 4. Read the doc file content from disk
        doc_file = project_root / "docs" / doc_path
        if not doc_file.is_file():
            continue

        doc_content = doc_file.read_text(encoding="utf-8")

        # 5. List *.py files on disk (non-recursive), excluding boilerplate
        missing_modules: list[str] = []
        for py_file in sorted(source_dir.glob("*.py")):
            if py_file.name in _COVERAGE_EXCLUDE:
                continue

            # 6. Get stem and check if it appears as a word in doc content
            stem = py_file.stem
            pattern = re.compile(rf"\b{re.escape(stem)}\b", re.IGNORECASE)
            if not pattern.search(doc_content):
                missing_modules.append(stem)

        # 7-8. If any missing, add to results
        if missing_modules:
            results.append(
                {
                    "ref_id": ref_id,
                    "doc_path": doc_path,
                    "missing_modules": missing_modules,
                }
            )

    return results
