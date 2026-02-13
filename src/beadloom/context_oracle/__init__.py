"""Context Oracle domain — BFS traversal, context bundle assembly, cache, search."""

from beadloom.context_oracle.builder import (
    bfs_subgraph,
    build_context,
    collect_chunks,
    suggest_ref_id,
)
from beadloom.context_oracle.cache import CacheEntry, ContextCache, SqliteCache, compute_etag
from beadloom.context_oracle.code_indexer import (
    LangConfig,
    clear_cache,
    extract_symbols,
    get_lang_config,
    parse_annotations,
    supported_extensions,
)
from beadloom.context_oracle.search import has_fts5, populate_search_index, search_fts5

__all__ = [
    "CacheEntry",
    "ContextCache",
    "LangConfig",
    "SqliteCache",
    "bfs_subgraph",
    "build_context",
    "clear_cache",
    "collect_chunks",
    "compute_etag",
    "extract_symbols",
    "get_lang_config",
    "has_fts5",
    "parse_annotations",
    "populate_search_index",
    "search_fts5",
    "suggest_ref_id",
    "supported_extensions",
]
