"""Doc Sync domain — documentation sync engine and doc indexer."""

from beadloom.doc_sync.audit import (
    AuditFinding,
    AuditResult,
    Fact,
    FactRegistry,
    compare_facts,
    run_audit,
)
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
from beadloom.doc_sync.scanner import (
    DocScanner,
    Mention,
)

__all__ = [
    "AuditFinding",
    "AuditResult",
    "DocIndexResult",
    "DocScanner",
    "Fact",
    "FactRegistry",
    "Mention",
    "SyncPair",
    "build_sync_state",
    "check_sync",
    "chunk_markdown",
    "classify_section",
    "compare_facts",
    "index_docs",
    "mark_synced",
    "mark_synced_by_ref",
    "run_audit",
]
