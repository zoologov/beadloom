"""Document indexer: Markdown scanning, chunking, and SQLite population."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import sqlite3
    from pathlib import Path

# Maximum chunk size in characters.
MAX_CHUNK_SIZE = 2000

# Section classification rules: (pattern, section_type).
_SECTION_RULES: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"spec|specification|requirements|business.?rules", re.I), "spec"),
    (re.compile(r"invariant|constraint", re.IGNORECASE), "invariants"),
    (re.compile(r"\bapi\b|endpoint|route", re.IGNORECASE), "api"),
    (re.compile(r"test|testing", re.IGNORECASE), "tests"),
    (re.compile(r"limit", re.IGNORECASE), "constraints"),
]

# Regex for H2 headings.
_H2_RE = re.compile(r"^## (.+)$", re.MULTILINE)


@dataclass
class DocIndexResult:
    """Summary of document indexing."""

    docs_indexed: int = 0
    chunks_indexed: int = 0


def classify_section(heading: str) -> str:
    """Classify a section heading into a known type.

    Returns one of: ``spec``, ``invariants``, ``api``, ``tests``,
    ``constraints``, ``other``.
    """
    for pattern, section_type in _SECTION_RULES:
        if pattern.search(heading):
            return section_type
    return "other"


def chunk_markdown(text: str) -> list[dict[str, Any]]:
    """Split Markdown text into chunks by H2 headings.

    Each chunk contains: ``heading``, ``section``, ``content``,
    ``chunk_index``.  Chunks exceeding :data:`MAX_CHUNK_SIZE` are
    further split by paragraphs.
    """
    if not text.strip():
        return []

    # Split by H2 markers.
    parts: list[tuple[str, str]] = []  # (heading, body)
    splits = _H2_RE.split(text)

    # splits[0] is text before the first H2 (intro).
    intro = splits[0].strip()
    if intro:
        # Remove H1 if present.
        intro_lines = intro.split("\n")
        body_lines = [
            line for line in intro_lines if not line.startswith("# ") and line != "#"
        ]
        body = "\n".join(body_lines).strip()
        if body:
            parts.append(("", body))

    # Remaining pairs: heading, body.
    for i in range(1, len(splits), 2):
        heading = splits[i].strip()
        body = splits[i + 1].strip() if i + 1 < len(splits) else ""
        if heading or body:
            parts.append((heading, body))

    # Build chunks, splitting large sections by paragraphs.
    chunks: list[dict[str, Any]] = []
    idx = 0
    for heading, body in parts:
        section = classify_section(heading)
        if len(body) <= MAX_CHUNK_SIZE:
            chunks.append({
                "heading": heading,
                "section": section,
                "content": body,
                "chunk_index": idx,
            })
            idx += 1
        else:
            # Split by paragraphs (double newline).
            paragraphs = re.split(r"\n\n+", body)
            current = ""
            for para in paragraphs:
                if current and len(current) + len(para) + 2 > MAX_CHUNK_SIZE:
                    chunks.append({
                        "heading": heading,
                        "section": section,
                        "content": current.strip(),
                        "chunk_index": idx,
                    })
                    idx += 1
                    current = para
                else:
                    current = f"{current}\n\n{para}" if current else para
            if current.strip():
                chunks.append({
                    "heading": heading,
                    "section": section,
                    "content": current.strip(),
                    "chunk_index": idx,
                })
                idx += 1

    return chunks


def index_docs(
    docs_dir: Path,
    conn: sqlite3.Connection,
    *,
    ref_id_map: dict[str, str] | None = None,
) -> DocIndexResult:
    """Scan *docs_dir* for ``.md`` files, chunk them, and insert into SQLite.

    Parameters
    ----------
    docs_dir:
        Root directory to scan for Markdown files.
    conn:
        Open SQLite connection with schema created.
    ref_id_map:
        Optional mapping of relative doc path → node ref_id.
        Used to link docs and chunks to graph nodes.

    Returns
    -------
    DocIndexResult
        Counts of indexed docs and chunks.
    """
    result = DocIndexResult()
    if ref_id_map is None:
        ref_id_map = {}

    for md_path in sorted(docs_dir.rglob("*.md")):
        content = md_path.read_text(encoding="utf-8")
        rel_path = str(md_path.relative_to(docs_dir))
        file_hash = hashlib.sha256(content.encode()).hexdigest()
        ref_id = ref_id_map.get(rel_path)

        conn.execute(
            "INSERT INTO docs (path, kind, ref_id, hash) VALUES (?, ?, ?, ?)",
            (rel_path, "other", ref_id, file_hash),
        )
        doc_id = conn.execute(
            "SELECT id FROM docs WHERE path = ?", (rel_path,)
        ).fetchone()[0]
        result.docs_indexed += 1

        chunks = chunk_markdown(content)
        for chunk in chunks:
            conn.execute(
                "INSERT INTO chunks (doc_id, chunk_index, heading, section, content, "
                "node_ref_id) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    doc_id,
                    chunk["chunk_index"],
                    chunk["heading"],
                    chunk["section"],
                    chunk["content"],
                    ref_id,
                ),
            )
            result.chunks_indexed += 1

    conn.commit()
    return result
