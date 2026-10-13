# beadloom:domain=application
# beadloom:feature=reindex
"""The code files the reindex saw and read no symbol from: no parser for their language.

BDL-082 S2a. The reindex records every code file under the scan paths in ``file_index``,
read or not, and ``extract_symbols`` returns nothing for a file whose grammar is not
installed. Measured on a project of TypeScript and Vue files without the ``languages``
extra, ``init`` printed "Index: 0 symbols, 0 imports" and nothing else, so a graph with no
import in it read as a graph of code that imports nothing. This module counts those files
by language; the commands that re-index say so.
"""

from __future__ import annotations

import sqlite3
from collections import Counter
from dataclasses import dataclass
from typing import TYPE_CHECKING

from beadloom.application.reindex.change_detection import is_sentinel_path
from beadloom.application.reindex.models import _is_missing_table_error
from beadloom.context_oracle.code_indexer import check_parser_availability

if TYPE_CHECKING:
    from pathlib import Path

#: The language each code extension the reindex reads is written in, by its own name.
LANGUAGE_OF: dict[str, str] = {
    ".py": "Python",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".js": "JavaScript",
    ".jsx": "JavaScript",
    ".mjs": "JavaScript",
    ".cjs": "JavaScript",
    ".vue": "Vue",
    ".go": "Go",
    ".rs": "Rust",
    ".kt": "Kotlin",
    ".kts": "Kotlin",
    ".java": "Java",
    ".swift": "Swift",
    ".m": "Objective-C",
    ".mm": "Objective-C",
    ".c": "C",
    ".h": "C",
    ".cpp": "C++",
    ".hpp": "C++",
}


@dataclass(frozen=True)
class UnreadCode:
    """*files* code files in *language* that the reindex read no symbol from."""

    language: str
    files: int


def _suffix(path: str) -> str:
    name = path.rsplit("/", 1)[-1]
    return f".{name.rsplit('.', 1)[-1]}" if "." in name else ""


def unread_code(conn: sqlite3.Connection) -> tuple[UnreadCode, ...]:
    """The indexed code files whose language has no parser installed, most first."""
    rows = conn.execute("SELECT path FROM file_index WHERE kind = 'code'").fetchall()
    suffixes = Counter(_suffix(str(row[0])) for row in rows if not is_sentinel_path(str(row[0])))
    readable = check_parser_availability(suffixes)
    by_language: Counter[str] = Counter()
    for suffix, count in suffixes.items():
        if not readable[suffix]:
            by_language[LANGUAGE_OF.get(suffix, suffix)] += count
    return tuple(
        UnreadCode(language, files)
        for language, files in sorted(by_language.items(), key=lambda item: (-item[1], item[0]))
    )


def read_unread_code(project_root: Path) -> tuple[UnreadCode, ...]:
    """:func:`unread_code` over the index of *project_root*; nothing when it has none."""
    db_path = project_root / ".beadloom" / "beadloom.db"
    if not db_path.is_file():
        return ()
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        return unread_code(conn)
    except sqlite3.OperationalError as exc:  # an index written before file_index existed
        if _is_missing_table_error(exc):
            return ()
        raise
    finally:
        conn.close()
