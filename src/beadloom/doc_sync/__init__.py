"""Doc Sync domain — documentation sync engine and doc indexer."""

from beadloom.doc_sync.doc_indexer import (
    DocIndexResult,
    chunk_markdown,
    classify_section,
    index_docs,
)
from beadloom.doc_sync.engine import (
    SyncPair,
    build_sync_state,
    check_sync,
    mark_synced,
    mark_synced_by_ref,
)

__all__ = [
    "DocIndexResult",
    "SyncPair",
    "build_sync_state",
    "check_sync",
    "chunk_markdown",
    "classify_section",
    "index_docs",
    "mark_synced",
    "mark_synced_by_ref",
]
