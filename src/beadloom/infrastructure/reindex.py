"""Reindex orchestrator: full rebuild and incremental reindex."""

# beadloom:domain=infrastructure

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from beadloom import __version__
from beadloom.context_oracle.code_indexer import extract_symbols, supported_extensions
from beadloom.doc_sync.doc_indexer import chunk_markdown, index_docs
from beadloom.graph.loader import load_graph
from beadloom.infrastructure.db import SCHEMA_VERSION, create_schema, open_db, set_meta
from beadloom.infrastructure.health import take_snapshot

if TYPE_CHECKING:
    import sqlite3
    from pathlib import Path

# Tables to drop on reindex (order matters for FK constraints).
_TABLES_TO_DROP = [
    "search_index",
    "sync_state",
    "code_imports",
    "rules",
    "code_symbols",
    "chunks",
    "docs",
    "edges",
    "nodes",
    "meta",
]

# File extensions to scan for code symbols.
_CODE_EXTENSIONS = frozenset(
    {
        ".py",
        ".ts",
        ".tsx",
        ".js",
        ".jsx",
        ".vue",
        ".go",
        ".rs",
        ".kt",
        ".kts",
        ".java",
        ".swift",
    }
)

# Default scan directories when config.yml has no scan_paths.
_DEFAULT_SCAN_DIRS = ("src", "lib", "app")


@dataclass
class ReindexResult:
    """Summary of a reindex operation."""

    nodes_loaded: int = 0
    edges_loaded: int = 0
    docs_indexed: int = 0
    chunks_indexed: int = 0
    symbols_indexed: int = 0
    imports_indexed: int = 0
    rules_loaded: int = 0
    nothing_changed: bool = False
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def _drop_all_tables(conn: sqlite3.Connection) -> None:
    """Drop all application tables to allow a clean re-create."""
    for table in _TABLES_TO_DROP:
        conn.execute(f"DROP TABLE IF EXISTS {table}")
    conn.commit()


def _build_doc_ref_map(
    graph_dir: Path,
    project_root: Path,
    docs_dir: Path,
) -> tuple[dict[str, str], list[str]]:
    """Build a mapping of relative doc path → ref_id from YAML graph nodes.

    Scans YAML graph files for nodes with ``docs`` lists and maps each
    doc path to the node's ref_id.

    Parameters
    ----------
    graph_dir:
        Path to ``.beadloom/_graph`` directory containing YAML files.
    project_root:
        Root of the project.
    docs_dir:
        Resolved documentation directory (absolute path).

    Returns
    -------
    tuple[dict[str, str], list[str]]
        ``(ref_map, warnings)`` where *warnings* lists any doc path conflicts
        (i.e. a doc referenced by more than one node).
    """
    import yaml

    ref_map: dict[str, str] = {}
    warnings: list[str] = []
    for yml_path in sorted(graph_dir.glob("*.yml")):
        text = yml_path.read_text(encoding="utf-8")
        data = yaml.safe_load(text)
        if data is None:
            continue
        for node in data.get("nodes") or []:
            ref_id = node.get("ref_id", "")
            for doc_path_str in node.get("docs") or []:
                # Normalize: if path starts with docs dir prefix, strip to make it relative.
                abs_path = project_root / doc_path_str
                if abs_path.is_relative_to(docs_dir):
                    rel = str(abs_path.relative_to(docs_dir))
                else:
                    rel = doc_path_str
                if rel in ref_map and ref_map[rel] != ref_id:
                    warnings.append(
                        f"Doc '{rel}' referenced by both '{ref_map[rel]}' and '{ref_id}'; "
                        f"keeping '{ref_map[rel]}'"
                    )
                else:
                    ref_map[rel] = ref_id
    return ref_map, warnings


def _index_code_files(
    project_root: Path,
    conn: sqlite3.Connection,
    seen_ref_ids: set[str],
) -> tuple[int, list[str]]:
    """Scan source files, extract symbols, and insert into SQLite.

    Returns (symbols_indexed, warnings).
    """
    count = 0
    warnings: list[str] = []

    # Scan directories from config.yml (or defaults).
    scan_dirs = [project_root / d for d in resolve_scan_paths(project_root)]
    for scan_dir in scan_dirs:
        if not scan_dir.is_dir():
            continue
        for file_path in sorted(scan_dir.rglob("*")):
            if file_path.suffix not in _CODE_EXTENSIONS:
                continue
            if not file_path.is_file():
                continue

            symbols = extract_symbols(file_path)
            rel_path = str(file_path.relative_to(project_root))

            for sym in symbols:
                conn.execute(
                    "INSERT INTO code_symbols (file_path, symbol_name, kind, "
                    "line_start, line_end, annotations, file_hash) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (
                        rel_path,
                        sym["symbol_name"],
                        sym["kind"],
                        sym["line_start"],
                        sym["line_end"],
                        json.dumps(sym["annotations"], ensure_ascii=False),
                        sym["file_hash"],
                    ),
                )
                count += 1

                # Create touches_code edges for annotated symbols.
                annotations: dict[str, Any] = sym["annotations"]
                for _key, ref_id in annotations.items():
                    if ref_id in seen_ref_ids:
                        conn.execute(
                            "INSERT OR IGNORE INTO edges "
                            "(src_ref_id, dst_ref_id, kind) VALUES (?, ?, ?)",
                            (ref_id, ref_id, "touches_code"),
                        )

    conn.commit()
    return count, warnings


def _build_initial_sync_state(conn: sqlite3.Connection) -> None:
    """Populate sync_state table from docs and code_symbols with shared ref_ids."""
    from beadloom.doc_sync.engine import _compute_symbols_hash, build_sync_state

    now = datetime.now(tz=timezone.utc).isoformat()
    pairs = build_sync_state(conn)
    for pair in pairs:
        conn.execute(
            "INSERT OR IGNORE INTO sync_state "
            "(doc_path, code_path, ref_id, code_hash_at_sync, doc_hash_at_sync, "
            "synced_at, status) VALUES (?, ?, ?, ?, ?, ?, 'ok')",
            (pair.doc_path, pair.code_path, pair.ref_id, pair.code_hash, pair.doc_hash, now),
        )
        # Store symbols hash for symbol-level drift detection.
        symbols_hash = _compute_symbols_hash(conn, pair.ref_id)
        conn.execute(
            "UPDATE sync_state SET symbols_hash = ? WHERE doc_path = ? AND code_path = ?",
            (symbols_hash, pair.doc_path, pair.code_path),
        )
    conn.commit()


def _load_rules_into_db(
    rules_path: Path,
    conn: sqlite3.Connection,
    result: ReindexResult,
) -> None:
    """Load architecture rules from rules.yml into the rules table."""
    from beadloom.graph.rule_engine import DenyRule, RequireRule, load_rules

    try:
        rules = load_rules(rules_path)
    except ValueError as exc:
        result.errors.append(f"Rules loading error: {exc}")
        return

    for rule in rules:
        if isinstance(rule, DenyRule):
            rule_type = "deny"
            rule_def: dict[str, object] = {
                "from": {},
                "to": {},
            }
            from_dict = rule_def["from"]
            assert isinstance(from_dict, dict)
            to_dict = rule_def["to"]
            assert isinstance(to_dict, dict)
            if rule.from_matcher.ref_id is not None:
                from_dict["ref_id"] = rule.from_matcher.ref_id
            if rule.from_matcher.kind is not None:
                from_dict["kind"] = rule.from_matcher.kind
            if rule.to_matcher.ref_id is not None:
                to_dict["ref_id"] = rule.to_matcher.ref_id
            if rule.to_matcher.kind is not None:
                to_dict["kind"] = rule.to_matcher.kind
            if rule.unless_edge:
                rule_def["unless_edge"] = list(rule.unless_edge)
        elif isinstance(rule, RequireRule):
            rule_type = "require"
            rule_def = {
                "for": {},
                "has_edge_to": {},
            }
            for_dict = rule_def["for"]
            assert isinstance(for_dict, dict)
            has_edge_dict = rule_def["has_edge_to"]
            assert isinstance(has_edge_dict, dict)
            if rule.for_matcher.ref_id is not None:
                for_dict["ref_id"] = rule.for_matcher.ref_id
            if rule.for_matcher.kind is not None:
                for_dict["kind"] = rule.for_matcher.kind
            if rule.has_edge_to.ref_id is not None:
                has_edge_dict["ref_id"] = rule.has_edge_to.ref_id
            if rule.has_edge_to.kind is not None:
                has_edge_dict["kind"] = rule.has_edge_to.kind
            if rule.edge_kind is not None:
                rule_def["edge_kind"] = rule.edge_kind
        else:
            continue  # pragma: no cover

        conn.execute(
            "INSERT INTO rules (name, description, rule_type, rule_json, enabled) "
            "VALUES (?, ?, ?, ?, 1)",
            (rule.name, rule.description, rule_type, json.dumps(rule_def)),
        )
        result.rules_loaded += 1

    conn.commit()


def _resolve_docs_dir(project_root: Path) -> Path:
    """Resolve docs directory from config.yml or use default ``docs``.

    Checks ``.beadloom/config.yml`` for a ``docs_dir`` key.  If present,
    returns ``project_root / <value>``.  Otherwise falls back to
    ``project_root / "docs"``.
    """
    config_path = project_root / ".beadloom" / "config.yml"
    if config_path.exists():
        import yaml

        config = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
        docs_path = config.get("docs_dir")
        if isinstance(docs_path, str) and docs_path:
            return project_root / docs_path
    return project_root / "docs"


def resolve_scan_paths(project_root: Path) -> list[str]:
    """Resolve source scan directories from config.yml.

    Reads ``scan_paths`` from ``.beadloom/config.yml``.  Falls back to
    ``["src", "lib", "app"]`` when config is absent or has no scan_paths.
    """
    config_path = project_root / ".beadloom" / "config.yml"
    if config_path.exists():
        import yaml

        config = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
        paths = config.get("scan_paths")
        if isinstance(paths, list) and paths:
            return [str(p) for p in paths]
    return list(_DEFAULT_SCAN_DIRS)


def reindex(project_root: Path, *, docs_dir: Path | None = None) -> ReindexResult:
    """Full reindex: drop all tables, re-create schema, reload everything.

    Parameters
    ----------
    project_root:
        Root of the project (where ``.beadloom/`` lives).
    docs_dir:
        Optional explicit documentation directory.  When *None* the
        directory is resolved from ``.beadloom/config.yml`` (key
        ``docs_dir``) with a fallback to ``<project_root>/docs``.

    Returns
    -------
    ReindexResult
        Summary with counts and diagnostics.
    """
    result = ReindexResult()

    db_path = project_root / ".beadloom" / "beadloom.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = open_db(db_path)

    # Drop + re-create.
    _drop_all_tables(conn)
    create_schema(conn)

    # 1. Load YAML graph.
    graph_dir = project_root / ".beadloom" / "_graph"
    if graph_dir.is_dir():
        graph_result = load_graph(graph_dir, conn)
        result.nodes_loaded = graph_result.nodes_loaded
        result.edges_loaded = graph_result.edges_loaded
        result.errors.extend(graph_result.errors)
        result.warnings.extend(graph_result.warnings)

    # Collect known ref_ids for edge creation.
    seen_ref_ids = {row[0] for row in conn.execute("SELECT ref_id FROM nodes").fetchall()}

    # 2. Index documents.
    if docs_dir is None:
        docs_dir = _resolve_docs_dir(project_root)
    if docs_dir.is_dir():
        if graph_dir.is_dir():
            ref_map, doc_ref_warnings = _build_doc_ref_map(
                graph_dir,
                project_root,
                docs_dir,
            )
            result.warnings.extend(doc_ref_warnings)
        else:
            ref_map = {}
        doc_result = index_docs(docs_dir, conn, ref_id_map=ref_map)
        result.docs_indexed = doc_result.docs_indexed
        result.chunks_indexed = doc_result.chunks_indexed

    # 3. Index code symbols.
    symbols_count, sym_warnings = _index_code_files(project_root, conn, seen_ref_ids)
    result.symbols_indexed = symbols_count
    result.warnings.extend(sym_warnings)

    # 3b. Extract and index code imports.
    from beadloom.graph.import_resolver import index_imports

    result.imports_indexed = index_imports(project_root, conn)

    # 3c. Load architecture rules from rules.yml.
    rules_path = project_root / ".beadloom" / "_graph" / "rules.yml"
    if rules_path.is_file():
        _load_rules_into_db(rules_path, conn, result)

    # 4. Build initial sync state.
    _build_initial_sync_state(conn)

    # 5. Populate FTS5 search index.
    from beadloom.context_oracle.search import populate_search_index

    populate_search_index(conn)

    # 5b. Clear persistent bundle cache (invalidated by full reindex).
    conn.execute("DELETE FROM bundle_cache")
    conn.commit()

    # 6. Set meta.
    now = datetime.now(tz=timezone.utc).isoformat()
    set_meta(conn, "last_reindex_at", now)
    set_meta(conn, "beadloom_version", __version__)
    set_meta(conn, "schema_version", SCHEMA_VERSION)

    # 7. Take health snapshot for trend tracking.
    take_snapshot(conn)

    # 8. Populate file_index for subsequent incremental runs.
    current_files = _scan_project_files(project_root, docs_dir)
    _populate_file_index(conn, current_files)

    # 9. Store parser fingerprint for incremental reindex to detect new parsers.
    _store_parser_fingerprint(conn, _compute_parser_fingerprint())

    conn.close()
    return result


# ---------------------------------------------------------------------------
# Incremental reindex helpers
# ---------------------------------------------------------------------------


def _compute_parser_fingerprint() -> str:
    """Compute a fingerprint of currently available tree-sitter parsers.

    Returns a sorted, comma-separated string of supported extensions.
    When new parser packages are installed, this string changes, signalling
    that a full code reindex is needed.
    """
    exts = supported_extensions()
    return ",".join(sorted(exts))


def _get_stored_parser_fingerprint(conn: sqlite3.Connection) -> str | None:
    """Read the stored parser fingerprint from file_index.

    Uses a sentinel row with ``path='__parser_fingerprint__'``.
    Returns ``None`` if not stored.
    """
    try:
        row = conn.execute(
            "SELECT hash FROM file_index WHERE path = '__parser_fingerprint__'"
        ).fetchone()
    except Exception:
        return None
    return row["hash"] if row else None


def _store_parser_fingerprint(conn: sqlite3.Connection, fingerprint: str) -> None:
    """Store the parser fingerprint in file_index as a sentinel row."""
    now = datetime.now(tz=timezone.utc).isoformat()
    conn.execute(
        "INSERT INTO file_index (path, hash, kind, indexed_at) "
        "VALUES ('__parser_fingerprint__', ?, 'code', ?) "
        "ON CONFLICT(path) DO UPDATE SET hash=excluded.hash, "
        "indexed_at=excluded.indexed_at",
        (fingerprint, now),
    )
    conn.commit()


def _compute_file_hash(path: Path) -> str:
    """Compute SHA-256 hash of a file."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _scan_project_files(
    project_root: Path,
    docs_dir: Path,
) -> dict[str, tuple[str, str]]:
    """Scan project files and return ``{relative_path: (sha256, kind)}``."""
    files: dict[str, tuple[str, str]] = {}

    # Graph YAML files
    graph_dir = project_root / ".beadloom" / "_graph"
    if graph_dir.is_dir():
        for f in sorted(graph_dir.glob("*.yml")):
            rel = str(f.relative_to(project_root))
            files[rel] = (_compute_file_hash(f), "graph")

    # Doc files
    if docs_dir.is_dir():
        for f in sorted(docs_dir.rglob("*.md")):
            rel = str(f.relative_to(project_root))
            files[rel] = (_compute_file_hash(f), "doc")

    # Code files
    for dirname in resolve_scan_paths(project_root):
        scan_dir = project_root / dirname
        if not scan_dir.is_dir():
            continue
        for f in sorted(scan_dir.rglob("*")):
            if f.suffix not in _CODE_EXTENSIONS or not f.is_file():
                continue
            rel = str(f.relative_to(project_root))
            files[rel] = (_compute_file_hash(f), "code")

    return files


def _get_stored_file_index(
    conn: sqlite3.Connection,
) -> dict[str, tuple[str, str]]:
    """Read file_index from DB. Returns ``{path: (hash, kind)}``."""
    try:
        rows = conn.execute("SELECT path, hash, kind FROM file_index").fetchall()
    except Exception:  # table may not exist on first run
        return {}
    return {
        row["path"]: (row["hash"], row["kind"]) for row in rows if not row["path"].startswith("__")
    }


def _diff_files(
    current: dict[str, tuple[str, str]],
    stored: dict[str, tuple[str, str]],
) -> tuple[set[str], set[str], set[str]]:
    """Compare current vs stored files. Returns ``(changed, added, deleted)``."""
    changed: set[str] = set()
    added: set[str] = set()

    for path, (hash_, _kind) in current.items():
        if path not in stored:
            added.add(path)
        elif stored[path][0] != hash_:
            changed.add(path)

    deleted = stored.keys() - current.keys()
    return changed, added, deleted


def _graph_yaml_changed(
    current_files: dict[str, tuple[str, str]],
    stored_files: dict[str, tuple[str, str]],
) -> bool:
    """Check whether any graph YAML file was added, removed, or modified.

    This is a direct comparison of hashes for files with ``kind == "graph"``
    in *current_files* vs *stored_files*.  Unlike :func:`_diff_files` (which
    relies on ``file_index`` being perfectly in sync), this function
    explicitly filters by kind so that graph changes are never missed — even
    when ``file_index`` is stale or partially populated.
    """
    current_graph = {p: h for p, (h, k) in current_files.items() if k == "graph"}
    stored_graph = {p: h for p, (h, k) in stored_files.items() if k == "graph"}

    # Different set of graph files → change.
    if current_graph.keys() != stored_graph.keys():
        return True

    # Same set — compare hashes.
    return any(current_graph[p] != stored_graph[p] for p in current_graph)


def _populate_file_index(
    conn: sqlite3.Connection,
    current_files: dict[str, tuple[str, str]],
) -> None:
    """Replace the entire file_index with *current_files*."""
    conn.execute("DELETE FROM file_index")
    now = datetime.now(tz=timezone.utc).isoformat()
    for path, (hash_, kind) in current_files.items():
        conn.execute(
            "INSERT INTO file_index (path, hash, kind, indexed_at) VALUES (?, ?, ?, ?)",
            (path, hash_, kind, now),
        )
    conn.commit()


def _update_file_index(
    conn: sqlite3.Connection,
    current_files: dict[str, tuple[str, str]],
    changed: set[str],
    added: set[str],
    deleted: set[str],
) -> None:
    """Incrementally update file_index for affected paths."""
    now = datetime.now(tz=timezone.utc).isoformat()
    for path in deleted:
        conn.execute("DELETE FROM file_index WHERE path = ?", (path,))
    for path in changed | added:
        hash_, kind = current_files[path]
        conn.execute(
            "INSERT INTO file_index (path, hash, kind, indexed_at) "
            "VALUES (?, ?, ?, ?) "
            "ON CONFLICT(path) DO UPDATE SET hash=excluded.hash, "
            "indexed_at=excluded.indexed_at",
            (path, hash_, kind, now),
        )
    conn.commit()


def _index_single_doc(
    conn: sqlite3.Connection,
    md_path: Path,
    docs_dir: Path,
    ref_map: dict[str, str],
) -> tuple[int, int]:
    """Index one doc file. Returns ``(docs_count, chunks_count)``."""
    content = md_path.read_text(encoding="utf-8")
    rel_path = str(md_path.relative_to(docs_dir))
    file_hash = hashlib.sha256(content.encode()).hexdigest()
    ref_id = ref_map.get(rel_path)

    conn.execute(
        "INSERT INTO docs (path, kind, ref_id, hash) VALUES (?, ?, ?, ?)",
        (rel_path, "other", ref_id, file_hash),
    )
    doc_id = conn.execute("SELECT id FROM docs WHERE path = ?", (rel_path,)).fetchone()[0]

    chunks = chunk_markdown(content)
    for chunk in chunks:
        conn.execute(
            "INSERT INTO chunks (doc_id, chunk_index, heading, section, "
            "content, node_ref_id) VALUES (?, ?, ?, ?, ?, ?)",
            (
                doc_id,
                chunk["chunk_index"],
                chunk["heading"],
                chunk["section"],
                chunk["content"],
                ref_id,
            ),
        )
    conn.commit()
    return 1, len(chunks)


def _index_single_code_file(
    conn: sqlite3.Connection,
    file_path: Path,
    project_root: Path,
    seen_ref_ids: set[str],
) -> int:
    """Index one code file. Returns symbol count."""
    symbols = extract_symbols(file_path)
    rel_path = str(file_path.relative_to(project_root))
    count = 0

    for sym in symbols:
        conn.execute(
            "INSERT INTO code_symbols (file_path, symbol_name, kind, "
            "line_start, line_end, annotations, file_hash) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                rel_path,
                sym["symbol_name"],
                sym["kind"],
                sym["line_start"],
                sym["line_end"],
                json.dumps(sym["annotations"], ensure_ascii=False),
                sym["file_hash"],
            ),
        )
        count += 1

        annotations: dict[str, Any] = sym["annotations"]
        for _key, ref_id in annotations.items():
            if ref_id in seen_ref_ids:
                conn.execute(
                    "INSERT OR IGNORE INTO edges (src_ref_id, dst_ref_id, kind) VALUES (?, ?, ?)",
                    (ref_id, ref_id, "touches_code"),
                )

    conn.commit()
    return count


def incremental_reindex(
    project_root: Path,
    *,
    docs_dir: Path | None = None,
) -> ReindexResult:
    """Incremental reindex: only process changed files.

    Falls back to full reindex when:
    - ``file_index`` is empty (first run after upgrade)
    - Any graph YAML file changed (safest: full reload)

    Parameters
    ----------
    project_root:
        Root of the project.
    docs_dir:
        Optional explicit docs directory.

    Returns
    -------
    ReindexResult
        Summary with counts for re-indexed items.
    """
    result = ReindexResult()

    db_path = project_root / ".beadloom" / "beadloom.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = open_db(db_path)
    create_schema(conn)

    if docs_dir is None:
        docs_dir = _resolve_docs_dir(project_root)

    # Scan current files on disk.
    current_files = _scan_project_files(project_root, docs_dir)

    # Read stored hashes from previous run.
    stored_files = _get_stored_file_index(conn)

    if not stored_files:
        # First run — fall back to full reindex.
        conn.close()
        return reindex(project_root, docs_dir=docs_dir)

    # Check if parser availability changed (e.g. new tree-sitter grammar installed).
    current_fingerprint = _compute_parser_fingerprint()
    stored_fingerprint = _get_stored_parser_fingerprint(conn)
    if stored_fingerprint is not None and current_fingerprint != stored_fingerprint:
        conn.close()
        return reindex(project_root, docs_dir=docs_dir)

    # Belt-and-suspenders: always check graph YAML files directly.
    # This catches changes even if file_index got out of sync with the DB
    # (e.g. interrupted reindex, partial writes, or upgrade edge cases).
    graph_affected = _graph_yaml_changed(current_files, stored_files)
    if graph_affected:
        conn.close()
        return reindex(project_root, docs_dir=docs_dir)

    changed, added, deleted = _diff_files(current_files, stored_files)

    if not changed and not added and not deleted:
        # Nothing changed — just update timestamp.
        now = datetime.now(tz=timezone.utc).isoformat()
        set_meta(conn, "last_reindex_at", now)
        take_snapshot(conn)
        conn.close()
        result.nothing_changed = True
        return result

    # --- Only docs / code changed — true incremental path ---

    docs_dir_rel = docs_dir.relative_to(project_root)

    # Known ref_ids for edge creation.
    seen_ref_ids: set[str] = {
        row[0] for row in conn.execute("SELECT ref_id FROM nodes").fetchall()
    }

    # Doc → ref_id mapping (from graph YAML).
    graph_dir = project_root / ".beadloom" / "_graph"
    if graph_dir.is_dir():
        ref_map, doc_ref_warns = _build_doc_ref_map(
            graph_dir,
            project_root,
            docs_dir,
        )
        result.warnings.extend(doc_ref_warns)
    else:
        ref_map = {}

    # Process deleted files.
    for path in deleted:
        kind = stored_files[path][1]
        if kind == "doc":
            doc_rel = str(type(docs_dir_rel)(path).relative_to(docs_dir_rel))
            conn.execute(
                "DELETE FROM sync_state WHERE doc_path = ?",
                (doc_rel,),
            )
            conn.execute("DELETE FROM docs WHERE path = ?", (doc_rel,))
        elif kind == "code":
            conn.execute(
                "DELETE FROM code_symbols WHERE file_path = ?",
                (path,),
            )
            conn.execute(
                "DELETE FROM sync_state WHERE code_path = ?",
                (path,),
            )

    # Process changed files (delete old data, re-index).
    for path in changed:
        kind = current_files[path][1]
        if kind == "doc":
            doc_rel = str(type(docs_dir_rel)(path).relative_to(docs_dir_rel))
            conn.execute("DELETE FROM docs WHERE path = ?", (doc_rel,))
            conn.execute(
                "DELETE FROM sync_state WHERE doc_path = ?",
                (doc_rel,),
            )
            abs_path = project_root / path
            d, c = _index_single_doc(conn, abs_path, docs_dir, ref_map)
            result.docs_indexed += d
            result.chunks_indexed += c
        elif kind == "code":
            conn.execute(
                "DELETE FROM code_symbols WHERE file_path = ?",
                (path,),
            )
            conn.execute(
                "DELETE FROM sync_state WHERE code_path = ?",
                (path,),
            )
            abs_path = project_root / path
            result.symbols_indexed += _index_single_code_file(
                conn,
                abs_path,
                project_root,
                seen_ref_ids,
            )

    # Process added files.
    for path in added:
        kind = current_files[path][1]
        if kind == "doc":
            abs_path = project_root / path
            d, c = _index_single_doc(conn, abs_path, docs_dir, ref_map)
            result.docs_indexed += d
            result.chunks_indexed += c
        elif kind == "code":
            abs_path = project_root / path
            result.symbols_indexed += _index_single_code_file(
                conn,
                abs_path,
                project_root,
                seen_ref_ids,
            )

    # Rebuild sync_state (cheap full rebuild).
    conn.execute("DELETE FROM sync_state")
    _build_initial_sync_state(conn)

    # Rebuild FTS5 search index.
    from beadloom.context_oracle.search import populate_search_index

    populate_search_index(conn)

    # Clear persistent bundle cache (conservative invalidation).
    conn.execute("DELETE FROM bundle_cache")
    conn.commit()

    # Update file_index.
    _update_file_index(conn, current_files, changed, added, deleted)

    # Update meta.
    now = datetime.now(tz=timezone.utc).isoformat()
    set_meta(conn, "last_reindex_at", now)
    set_meta(conn, "beadloom_version", __version__)

    # Health snapshot.
    take_snapshot(conn)

    conn.close()
    return result
