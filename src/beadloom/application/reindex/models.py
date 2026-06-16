# beadloom:domain=application
# beadloom:feature=reindex
"""Reindex model: result dataclass, sync snapshot, and pipeline constants.

This module owns the *data* of the reindex pipeline — the immutable shapes and
constants that the orchestrators and helpers share. It holds no I/O and no
orchestration, only the model: the :class:`ReindexResult` summary, the
:class:`_SyncPairSnapshot` two-phase sync record, the table-drop order, and the
file-extension/language tables that bound code scanning and route extraction.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import sqlite3

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

# File extension -> language label for route extraction.
_EXT_TO_LANG: dict[str, str] = {
    ".py": "python",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".js": "javascript",
    ".jsx": "javascript",
    ".go": "go",
    ".java": "java",
    ".kt": "kotlin",
    ".kts": "kotlin",
    ".graphql": "graphql",
    ".gql": "graphql",
    ".proto": "protobuf",
}

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
        ".m",
        ".mm",
        ".c",
        ".h",
        ".cpp",
        ".hpp",
    }
)


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


@dataclass
class _SyncPairSnapshot:
    """Preserved per-pair sync data across reindex for two-phase detection."""

    doc_hash_at_last_edit: str
    code_hash_at_sync: str


def _is_missing_table_error(exc: sqlite3.OperationalError) -> bool:
    """Return True only when *exc* is SQLite's "no such table" error.

    Used to handle the first-run case (a table not yet created) without
    swallowing other operational errors (corruption, locking, etc.).
    """
    return "no such table" in str(exc).lower()
