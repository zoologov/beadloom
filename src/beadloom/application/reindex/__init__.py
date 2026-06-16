# beadloom:domain=application
# beadloom:feature=reindex
"""Reindex orchestrator: full rebuild and incremental reindex.

This package decomposes the former ``application/reindex.py`` monolith by
responsibility (BDL-059 S4, cohesion-driven):

- :mod:`.models` — :class:`ReindexResult`, :class:`_SyncPairSnapshot`, and the
  pipeline constants (table-drop order, code extensions, ext->lang map).
- :mod:`.rules_loader` — serialize parsed architecture rules into the ``rules``
  table (``_serialize_rule`` / ``_load_rules_into_db``).
- :mod:`.indexing` — scan docs and source files into ``docs``/``chunks`` and
  ``code_symbols`` rows; docs-dir + doc-ref-map resolution.
- :mod:`.enrichment` — augment ``nodes.extra`` with test mappings, routes, and
  git activity.
- :mod:`.sync_state` — snapshot and rebuild the ``sync_state`` baselines.
- :mod:`.change_detection` — file-index hashing/diffing + parser fingerprint
  (the incremental change-detection layer).
- :mod:`.full` — the :func:`reindex` (full rebuild) orchestration.
- :mod:`.incremental` — the :func:`incremental_reindex` orchestration.

This ``__init__`` re-exports the public surface so
``from beadloom.application.reindex import X`` stays stable, and binds
``analyze_git_activity`` / ``supported_extensions`` at the package level so the
enrichment / change-detection helpers (and tests) can patch them here.
"""

from __future__ import annotations

from beadloom.application.reindex.change_detection import (
    _compute_file_hash,
    _compute_parser_fingerprint,
    _diff_files,
    _get_stored_file_index,
    _get_stored_parser_fingerprint,
    _graph_yaml_changed,
    _populate_file_index,
    _scan_project_files,
    _store_parser_fingerprint,
    _update_file_index,
)
from beadloom.application.reindex.enrichment import (
    _extract_and_store_routes,
    _store_git_activity,
    _store_test_mappings,
    _update_node_extra,
)
from beadloom.application.reindex.full import _beadloom_version, _drop_all_tables, reindex
from beadloom.application.reindex.incremental import incremental_reindex
from beadloom.application.reindex.indexing import (
    _build_doc_ref_map,
    _index_code_files,
    _index_single_code_file,
    _index_single_doc,
    _resolve_docs_dir,
)
from beadloom.application.reindex.models import (
    _CODE_EXTENSIONS,
    _EXT_TO_LANG,
    _TABLES_TO_DROP,
    ReindexResult,
    _is_missing_table_error,
    _SyncPairSnapshot,
)
from beadloom.application.reindex.rules_loader import (
    _load_rules_into_db,
    _serialize_node_matcher,
    _serialize_rule,
)
from beadloom.application.reindex.sync_state import (
    _build_initial_sync_state,
    _snapshot_sync_baselines,
)

# Re-exported at the package level so ``_store_git_activity`` and
# ``_compute_parser_fingerprint`` resolve them via this namespace (honouring
# ``patch("beadloom.application.reindex.<name>")``), and for back-compat with
# callers/tests that import them from here.
from beadloom.context_oracle.code_indexer import supported_extensions
from beadloom.infrastructure.git_activity import analyze_git_activity
from beadloom.infrastructure.scan_paths import resolve_scan_paths

# The public surface is the four orchestration/result names plus the three
# infrastructure re-exports. The private (``_``-prefixed) helpers are also
# re-exported here for back-compat with existing callers/tests that import them
# from ``beadloom.application.reindex`` directly; they are listed so the
# re-exports are explicit (and not flagged as unused).
__all__ = [
    "_CODE_EXTENSIONS",
    "_EXT_TO_LANG",
    "_TABLES_TO_DROP",
    "ReindexResult",
    "_SyncPairSnapshot",
    "_beadloom_version",
    "_build_doc_ref_map",
    "_build_initial_sync_state",
    "_compute_file_hash",
    "_compute_parser_fingerprint",
    "_diff_files",
    "_drop_all_tables",
    "_extract_and_store_routes",
    "_get_stored_file_index",
    "_get_stored_parser_fingerprint",
    "_graph_yaml_changed",
    "_index_code_files",
    "_index_single_code_file",
    "_index_single_doc",
    "_is_missing_table_error",
    "_load_rules_into_db",
    "_populate_file_index",
    "_resolve_docs_dir",
    "_scan_project_files",
    "_serialize_node_matcher",
    "_serialize_rule",
    "_snapshot_sync_baselines",
    "_store_git_activity",
    "_store_parser_fingerprint",
    "_store_test_mappings",
    "_update_file_index",
    "_update_node_extra",
    "analyze_git_activity",
    "incremental_reindex",
    "reindex",
    "resolve_scan_paths",
    "supported_extensions",
]
