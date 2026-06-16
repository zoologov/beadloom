# beadloom:domain=application
# beadloom:feature=reindex
"""Full reindex orchestration: drop, re-create, and reload the whole index.

This module owns the top-level :func:`reindex` use case — the ordered pipeline
that snapshots sync baselines, drops and re-creates the schema, then reloads
the YAML graph, docs, code symbols, imports, rules, node-extra enrichments,
sync state, search index, and health snapshot from scratch. It composes the
cohesive helpers in this package; it holds the sequence, not the mechanics.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from beadloom.application.reindex.change_detection import (
    _compute_parser_fingerprint,
    _populate_file_index,
    _scan_project_files,
    _store_parser_fingerprint,
)
from beadloom.application.reindex.enrichment import (
    _extract_and_store_routes,
    _store_git_activity,
    _store_test_mappings,
)
from beadloom.application.reindex.indexing import (
    _build_doc_ref_map,
    _index_code_files,
    _resolve_docs_dir,
)
from beadloom.application.reindex.models import _TABLES_TO_DROP, ReindexResult
from beadloom.application.reindex.rules_loader import _load_rules_into_db
from beadloom.application.reindex.sync_state import (
    _build_initial_sync_state,
    _snapshot_sync_baselines,
)
from beadloom.infrastructure.db import SCHEMA_VERSION, create_schema, open_db, set_meta
from beadloom.infrastructure.health import take_snapshot

if TYPE_CHECKING:
    import sqlite3
    from pathlib import Path


def _beadloom_version() -> str:
    """Return the in-tree package version.

    Imported lazily (function-local) so this application-layer module does not
    take a module-level dependency on the root ``beadloom`` package namespace,
    which would create a spurious ``application -> beadloom`` graph edge.  The
    version is only a string constant, not an architectural dependency.
    """
    from beadloom import __version__

    return __version__


def _drop_all_tables(conn: sqlite3.Connection) -> None:
    """Drop all application tables to allow a clean re-create."""
    for table in _TABLES_TO_DROP:
        conn.execute(f"DROP TABLE IF EXISTS {table}")
    conn.commit()


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

    # Snapshot sync baselines before drop.
    preserved_symbols, preserved_pairs = _snapshot_sync_baselines(conn)

    # Drop + re-create.
    _drop_all_tables(conn)
    create_schema(conn)

    # 1. Load YAML graph.
    from beadloom.graph.loader import load_graph

    graph_dir = project_root / ".beadloom" / "_graph"
    if graph_dir.is_dir():
        graph_result = load_graph(graph_dir, conn)
        result.nodes_loaded = graph_result.nodes_loaded
        result.edges_loaded = graph_result.edges_loaded
        result.errors.extend(graph_result.errors)
        result.warnings.extend(graph_result.warnings)

    # Collect known ref_ids for edge creation.
    seen_ref_ids = {row[0] for row in conn.execute("SELECT ref_id FROM nodes").fetchall()}

    # 1b. Store deep config in root node's extra.
    from beadloom.onboarding.config_reader import read_deep_config

    deep_config = read_deep_config(project_root)
    root_row = conn.execute(
        "SELECT ref_id, extra FROM nodes WHERE source = '' OR source IS NULL"
    ).fetchone()
    if root_row is not None:
        existing_extra: dict[str, Any] = json.loads(root_row["extra"] or "{}")
        existing_extra["config"] = deep_config
        conn.execute(
            "UPDATE nodes SET extra = ? WHERE ref_id = ?",
            (json.dumps(existing_extra, ensure_ascii=False), root_row["ref_id"]),
        )
        conn.commit()

    # 2. Index documents.
    if docs_dir is None:
        docs_dir = _resolve_docs_dir(project_root)
    if docs_dir.is_dir():
        from beadloom.doc_sync.doc_indexer import index_docs

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

    # 3d. Map test files to source nodes and store in nodes.extra.
    _store_test_mappings(project_root, conn)

    # 3e. Analyze git activity and store in nodes.extra.
    _store_git_activity(conn, project_root)

    # 3f. Extract API routes and store in nodes.extra.
    _extract_and_store_routes(project_root, conn)

    # 4. Build initial sync state.
    _build_initial_sync_state(
        conn,
        preserved_symbols=preserved_symbols,
        preserved_pairs=preserved_pairs,
    )

    # 4b. Baseline reference-doc surface hashes (BDL-057 Layer 2; advisory).
    from beadloom.doc_sync.engine import build_reference_state

    build_reference_state(conn, project_root)

    # 5. Populate FTS5 search index.
    from beadloom.context_oracle.search import populate_search_index

    populate_search_index(conn)

    # 5b. Clear persistent bundle cache (invalidated by full reindex).
    conn.execute("DELETE FROM bundle_cache")
    conn.commit()

    # 6. Set meta.
    now = datetime.now(tz=timezone.utc).isoformat()
    set_meta(conn, "last_reindex_at", now)
    set_meta(conn, "beadloom_version", _beadloom_version())
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
