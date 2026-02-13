"""Tests for beadloom.doc_indexer — Markdown chunking and doc indexing."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from beadloom.doc_sync.doc_indexer import chunk_markdown, classify_section, index_docs
from beadloom.infrastructure.db import create_schema, open_db

if TYPE_CHECKING:
    import sqlite3
    from pathlib import Path


# --- classify_section ---


class TestClassifySection:
    @pytest.mark.parametrize(
        ("heading", "expected"),
        [
            ("Business rules", "spec"),
            ("Specification", "spec"),
            ("Requirements", "spec"),
            ("Invariants", "invariants"),
            ("Constraints", "invariants"),
            ("API endpoints", "api"),
            ("REST API", "api"),
            ("Routes", "api"),
            ("Testing", "tests"),
            ("Test plan", "tests"),
            ("Limits", "constraints"),
            ("Random heading", "other"),
            ("", "other"),
        ],
    )
    def test_classification(self, heading: str, expected: str) -> None:
        assert classify_section(heading) == expected


# --- chunk_markdown ---


class TestChunkMarkdown:
    def test_splits_by_h2(self) -> None:
        md = (
            "# Title\n\nIntro paragraph.\n\n"
            "## Section One\n\nContent one.\n\n"
            "## Section Two\n\nContent two.\n"
        )
        chunks = chunk_markdown(md)
        assert len(chunks) == 3  # intro + 2 sections
        assert chunks[1]["heading"] == "Section One"
        assert "Content one." in chunks[1]["content"]
        assert chunks[2]["heading"] == "Section Two"

    def test_intro_before_first_h2(self) -> None:
        md = "# Doc Title\n\nSome intro text.\n\n## First\n\nBody.\n"
        chunks = chunk_markdown(md)
        assert chunks[0]["heading"] == ""
        assert "Some intro text." in chunks[0]["content"]

    def test_large_section_splits_by_paragraph(self) -> None:
        # Each paragraph is ~600 chars, 4 paragraphs = ~2400 > 2000 limit
        para = "A" * 600
        md = f"## Big Section\n\n{para}\n\n{para}\n\n{para}\n\n{para}\n"
        chunks = chunk_markdown(md)
        assert len(chunks) >= 2  # must be split
        for c in chunks:
            assert len(c["content"]) <= 2000

    def test_section_classification(self) -> None:
        md = "## Business rules\n\nRule 1.\n\n## API endpoints\n\nGET /foo\n"
        chunks = chunk_markdown(md)
        assert chunks[0]["section"] == "spec"
        assert chunks[1]["section"] == "api"

    def test_chunk_index_sequential(self) -> None:
        md = "## A\n\nText A.\n\n## B\n\nText B.\n\n## C\n\nText C.\n"
        chunks = chunk_markdown(md)
        indices = [c["chunk_index"] for c in chunks]
        assert indices == list(range(len(chunks)))

    def test_empty_document(self) -> None:
        chunks = chunk_markdown("")
        assert chunks == []

    def test_no_headings(self) -> None:
        md = "Just a paragraph.\n\nAnother paragraph.\n"
        chunks = chunk_markdown(md)
        assert len(chunks) == 1
        assert chunks[0]["heading"] == ""
        assert "Just a paragraph." in chunks[0]["content"]

    def test_h3_not_split(self) -> None:
        """Only H2 causes splits, not H3."""
        md = "## Main\n\nText.\n\n### Sub\n\nMore text.\n"
        chunks = chunk_markdown(md)
        assert len(chunks) == 1
        assert "### Sub" in chunks[0]["content"]


# --- index_docs ---


@pytest.fixture()
def db(tmp_path: Path) -> sqlite3.Connection:
    conn = open_db(tmp_path / "test.db")
    create_schema(conn)
    return conn


@pytest.fixture()
def docs_dir(tmp_path: Path) -> Path:
    d = tmp_path / "docs"
    d.mkdir()
    return d


class TestIndexDocs:
    def test_indexes_single_doc(self, db: sqlite3.Connection, docs_dir: Path) -> None:
        (docs_dir / "readme.md").write_text("## Overview\n\nHello world.\n")
        result = index_docs(docs_dir, db)
        assert result.docs_indexed == 1
        row = db.execute("SELECT * FROM docs").fetchone()
        assert row["path"] == "readme.md"
        assert row["kind"] == "other"
        assert len(row["hash"]) == 64  # SHA256 hex

    def test_indexes_chunks(self, db: sqlite3.Connection, docs_dir: Path) -> None:
        (docs_dir / "spec.md").write_text(
            "## Business rules\n\nRule 1.\n\n## API\n\nGET /endpoint\n"
        )
        index_docs(docs_dir, db)
        chunks = db.execute("SELECT heading, section FROM chunks ORDER BY chunk_index").fetchall()
        assert len(chunks) == 2
        assert chunks[0]["section"] == "spec"
        assert chunks[1]["section"] == "api"

    def test_nested_docs(self, db: sqlite3.Connection, docs_dir: Path) -> None:
        sub = docs_dir / "domains" / "routing"
        sub.mkdir(parents=True)
        (sub / "README.md").write_text("## Routing\n\nRouting domain.\n")
        result = index_docs(docs_dir, db)
        assert result.docs_indexed == 1
        row = db.execute("SELECT path FROM docs").fetchone()
        assert row["path"] == "domains/routing/README.md"

    def test_sha256_hash(self, db: sqlite3.Connection, docs_dir: Path) -> None:
        import hashlib

        content = "## Test\n\nContent.\n"
        (docs_dir / "test.md").write_text(content)
        index_docs(docs_dir, db)
        row = db.execute("SELECT hash FROM docs").fetchone()
        expected = hashlib.sha256(content.encode()).hexdigest()
        assert row["hash"] == expected

    def test_empty_docs_dir(self, db: sqlite3.Connection, docs_dir: Path) -> None:
        result = index_docs(docs_dir, db)
        assert result.docs_indexed == 0
        assert result.chunks_indexed == 0

    def test_skips_non_md_files(self, db: sqlite3.Connection, docs_dir: Path) -> None:
        (docs_dir / "image.png").write_bytes(b"\x89PNG")
        (docs_dir / "notes.txt").write_text("not markdown")
        (docs_dir / "actual.md").write_text("## Real doc\n\nContent.\n")
        result = index_docs(docs_dir, db)
        assert result.docs_indexed == 1

    def test_ref_id_mapping(self, db: sqlite3.Connection, docs_dir: Path) -> None:
        """When ref_id_map is provided, docs get linked to nodes."""
        db.execute(
            "INSERT INTO nodes (ref_id, kind, summary) VALUES (?, ?, ?)",
            ("feat1", "feature", "Feature 1"),
        )
        db.commit()
        (docs_dir / "spec.md").write_text("## Spec\n\nContent.\n")
        ref_map = {"spec.md": "feat1"}
        result = index_docs(docs_dir, db, ref_id_map=ref_map)
        assert result.docs_indexed == 1
        row = db.execute("SELECT ref_id FROM docs WHERE path = ?", ("spec.md",)).fetchone()
        assert row["ref_id"] == "feat1"

    def test_chunks_get_node_ref_id(self, db: sqlite3.Connection, docs_dir: Path) -> None:
        """Chunks inherit node_ref_id from their parent doc."""
        db.execute(
            "INSERT INTO nodes (ref_id, kind, summary) VALUES (?, ?, ?)",
            ("n1", "domain", "D"),
        )
        db.commit()
        (docs_dir / "domain.md").write_text("## Overview\n\nDomain info.\n")
        index_docs(docs_dir, db, ref_id_map={"domain.md": "n1"})
        row = db.execute("SELECT node_ref_id FROM chunks").fetchone()
        assert row["node_ref_id"] == "n1"

    def test_doc_kind_classification(self, db: sqlite3.Connection, docs_dir: Path) -> None:
        """Docs kind defaults to 'other' (proper classification is in BEAD-20)."""
        (docs_dir / "test.md").write_text("## Test\n\nBody.\n")
        index_docs(docs_dir, db)
        row = db.execute("SELECT kind FROM docs").fetchone()
        assert row["kind"] == "other"
