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
    build_reference_state,
    build_sync_state,
    check_reference_drift,
    check_sync,
    mark_reference_synced,
    mark_synced,
    mark_synced_by_ref,
)
from beadloom.doc_sync.scanner import (
    DocScanner,
    Mention,
)
from beadloom.doc_sync.surface import (
    VALID_SURFACES,
    aggregate_hash,
    parse_watches,
)

__all__ = [
    "VALID_SURFACES",
    "AuditFinding",
    "AuditResult",
    "DocIndexResult",
    "DocScanner",
    "Fact",
    "FactRegistry",
    "Mention",
    "SyncPair",
    "aggregate_hash",
    "build_reference_state",
    "build_sync_state",
    "check_reference_drift",
    "check_sync",
    "chunk_markdown",
    "classify_section",
    "compare_facts",
    "index_docs",
    "mark_reference_synced",
    "mark_synced",
    "mark_synced_by_ref",
    "parse_watches",
    "run_audit",
]
