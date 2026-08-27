"""Doc Sync domain — documentation sync engine and doc indexer."""

from beadloom.doc_sync.audit import (
    AuditFinding,
    AuditResult,
    Fact,
    FactRegistry,
    FactSet,
    compare_facts,
    run_audit,
)
from beadloom.doc_sync.audit_coverage import (
    FactCoverage,
    assess_coverage,
)
from beadloom.doc_sync.audit_self_surface import (
    declared_project_name,
    foreign_project_reason,
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
    ExcludedDoc,
    Mention,
    ScanSurface,
    unreadable_reason,
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
    "ExcludedDoc",
    "Fact",
    "FactCoverage",
    "FactRegistry",
    "FactSet",
    "Mention",
    "ScanSurface",
    "SyncPair",
    "aggregate_hash",
    "assess_coverage",
    "build_reference_state",
    "build_sync_state",
    "check_reference_drift",
    "check_sync",
    "chunk_markdown",
    "classify_section",
    "compare_facts",
    "declared_project_name",
    "foreign_project_reason",
    "index_docs",
    "mark_reference_synced",
    "mark_synced",
    "mark_synced_by_ref",
    "parse_watches",
    "run_audit",
    "unreadable_reason",
]
