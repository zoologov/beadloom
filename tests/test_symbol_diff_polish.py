"""Tests for BEAD-10: symbol diff in generate_polish_data / format_polish_text."""

from __future__ import annotations

import hashlib
import sqlite3
from typing import TYPE_CHECKING, Any

import yaml

from beadloom.onboarding.doc_generator import (
    _detect_symbol_changes,
    format_polish_text,
    generate_polish_data,
)

if TYPE_CHECKING:
    from pathlib import Path


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _root_node() -> dict[str, Any]:
    return {"ref_id": "myproject", "kind": "service", "source": "", "summary": "Root"}


def _domain_node(name: str = "auth") -> dict[str, Any]:
    return {
        "ref_id": name,
        "kind": "domain",
        "summary": f"{name} domain",
        "source": f"src/{name}/",
    }


def _write_graph_yaml(tmp_path: Path, data: dict[str, Any]) -> None:
    """Write a graph YAML file so ``generate_polish_data`` can load it."""
    graph_dir = tmp_path / ".beadloom" / "_graph"
    graph_dir.mkdir(parents=True, exist_ok=True)
    (graph_dir / "services.yml").write_text(
        yaml.dump(data, default_flow_style=False), encoding="utf-8"
    )


def _default_graph_data() -> dict[str, Any]:
    return {
        "nodes": [
            _root_node(),
            _domain_node("auth"),
        ],
        "edges": [
            {"src": "auth", "dst": "myproject", "kind": "part_of"},
        ],
    }


def _create_full_db(tmp_path: Path) -> Path:
    """Create a beadloom.db with all required tables for symbol diff tests."""
    db_dir = tmp_path / ".beadloom"
    db_dir.mkdir(parents=True, exist_ok=True)
    db_path = db_dir / "beadloom.db"

    conn = sqlite3.connect(str(db_path))
    conn.execute(
        "CREATE TABLE IF NOT EXISTS nodes ("
        "  ref_id TEXT PRIMARY KEY,"
        "  kind TEXT NOT NULL,"
        "  summary TEXT NOT NULL DEFAULT '',"
        "  source TEXT,"
        "  extra TEXT DEFAULT '{}'"
        ")"
    )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS edges ("
        "  src_ref_id TEXT NOT NULL,"
        "  dst_ref_id TEXT NOT NULL,"
        "  kind TEXT NOT NULL,"
        "  extra TEXT DEFAULT '{}',"
        "  PRIMARY KEY (src_ref_id, dst_ref_id, kind)"
        ")"
    )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS code_symbols ("
        "  id INTEGER PRIMARY KEY AUTOINCREMENT,"
        "  file_path TEXT NOT NULL,"
        "  symbol_name TEXT NOT NULL,"
        "  kind TEXT NOT NULL,"
        "  line_start INTEGER NOT NULL,"
        "  line_end INTEGER NOT NULL,"
        "  annotations TEXT DEFAULT '{}',"
        "  file_hash TEXT NOT NULL"
        ")"
    )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS sync_state ("
        "  id INTEGER PRIMARY KEY AUTOINCREMENT,"
        "  doc_path TEXT NOT NULL,"
        "  code_path TEXT NOT NULL,"
        "  ref_id TEXT NOT NULL,"
        "  code_hash_at_sync TEXT NOT NULL,"
        "  doc_hash_at_sync TEXT NOT NULL,"
        "  synced_at TEXT NOT NULL,"
        "  status TEXT NOT NULL DEFAULT 'ok',"
        "  symbols_hash TEXT DEFAULT '',"
        "  UNIQUE(doc_path, code_path)"
        ")"
    )
    conn.commit()
    conn.close()
    return db_path


def _compute_symbols_hash_from_list(symbols: list[tuple[str, str]]) -> str:
    """Compute SHA-256 matching _compute_symbols_hash algorithm."""
    data = "|".join(f"{name}:{kind}" for name, kind in symbols)
    return hashlib.sha256(data.encode()).hexdigest()


def _insert_symbols(
    db_path: Path,
    ref_id: str,
    symbols: list[tuple[str, str]],
    file_path: str = "src/auth/core.py",
    file_hash: str = "abc123",
) -> None:
    """Insert code_symbols rows annotated with the given ref_id."""
    import json

    conn = sqlite3.connect(str(db_path))
    for name, kind in symbols:
        annotations = json.dumps({"domain": ref_id})
        conn.execute(
            "INSERT INTO code_symbols (file_path, symbol_name, kind, "
            "line_start, line_end, annotations, file_hash) "
            "VALUES (?, ?, ?, 1, 10, ?, ?)",
            (file_path, name, kind, annotations, file_hash),
        )
    conn.commit()
    conn.close()


def _insert_sync_state(
    db_path: Path,
    ref_id: str,
    symbols_hash: str,
    doc_path: str = "domains/auth/README.md",
    code_path: str = "src/auth/core.py",
) -> None:
    """Insert a sync_state row with a stored symbols_hash."""
    conn = sqlite3.connect(str(db_path))
    conn.execute(
        "INSERT INTO sync_state (doc_path, code_path, ref_id, "
        "code_hash_at_sync, doc_hash_at_sync, synced_at, status, symbols_hash) "
        "VALUES (?, ?, ?, 'hash1', 'hash2', '2025-01-01T00:00:00Z', 'ok', ?)",
        (doc_path, code_path, ref_id, symbols_hash),
    )
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# TestDetectSymbolChanges — no DB
# ---------------------------------------------------------------------------


class TestDetectSymbolChangesNoDb:
    """_detect_symbol_changes returns None when no DB exists."""

    def test_returns_none_without_db(self, tmp_path: Path) -> None:
        result = _detect_symbol_changes(tmp_path, "auth")
        assert result is None


# ---------------------------------------------------------------------------
# TestDetectSymbolChanges — no sync_state entries
# ---------------------------------------------------------------------------


class TestDetectSymbolChangesNoSyncState:
    """_detect_symbol_changes returns None when no sync_state entries exist."""

    def test_returns_none_when_no_sync_entries(self, tmp_path: Path) -> None:
        _create_full_db(tmp_path)
        result = _detect_symbol_changes(tmp_path, "auth")
        assert result is None

    def test_returns_none_when_empty_symbols_hash(self, tmp_path: Path) -> None:
        """sync_state row exists but symbols_hash is empty string."""
        db_path = _create_full_db(tmp_path)
        _insert_sync_state(db_path, "auth", symbols_hash="")
        result = _detect_symbol_changes(tmp_path, "auth")
        assert result is None


# ---------------------------------------------------------------------------
# TestDetectSymbolChanges — drift detected
# ---------------------------------------------------------------------------


class TestDetectSymbolChangesDrift:
    """_detect_symbol_changes detects drift when symbols changed."""

    def test_detects_drift_when_symbol_added(self, tmp_path: Path) -> None:
        """New symbol added since last sync triggers drift."""
        db_path = _create_full_db(tmp_path)

        # Original state: one symbol.
        original_symbols = [("login", "function")]
        original_hash = _compute_symbols_hash_from_list(original_symbols)
        _insert_sync_state(db_path, "auth", symbols_hash=original_hash)

        # Current state: two symbols (one added).
        current_symbols = [("login", "function"), ("logout", "function")]
        _insert_symbols(db_path, "auth", current_symbols)

        result = _detect_symbol_changes(tmp_path, "auth")

        assert result is not None
        assert result["has_drift"] is True
        assert len(result["current_symbols"]) == 2
        assert "symbols changed" in result["message"]
        assert "2 current symbols" in result["message"]

    def test_detects_drift_when_symbol_removed(self, tmp_path: Path) -> None:
        """Symbol removed since last sync triggers drift."""
        db_path = _create_full_db(tmp_path)

        # Original: two symbols.
        original_symbols = [("login", "function"), ("logout", "function")]
        original_hash = _compute_symbols_hash_from_list(original_symbols)
        _insert_sync_state(db_path, "auth", symbols_hash=original_hash)

        # Current: one symbol (one removed).
        current_symbols = [("login", "function")]
        _insert_symbols(db_path, "auth", current_symbols)

        result = _detect_symbol_changes(tmp_path, "auth")

        assert result is not None
        assert result["has_drift"] is True
        assert len(result["current_symbols"]) == 1

    def test_detects_drift_when_kind_changed(self, tmp_path: Path) -> None:
        """Symbol kind change triggers drift (e.g. function -> class)."""
        db_path = _create_full_db(tmp_path)

        original_symbols = [("Auth", "function")]
        original_hash = _compute_symbols_hash_from_list(original_symbols)
        _insert_sync_state(db_path, "auth", symbols_hash=original_hash)

        # Same name, different kind.
        current_symbols = [("Auth", "class")]
        _insert_symbols(db_path, "auth", current_symbols)

        result = _detect_symbol_changes(tmp_path, "auth")

        assert result is not None
        assert result["has_drift"] is True

    def test_detects_drift_when_all_symbols_removed(self, tmp_path: Path) -> None:
        """All symbols removed since last sync triggers drift."""
        db_path = _create_full_db(tmp_path)

        original_symbols = [("login", "function")]
        original_hash = _compute_symbols_hash_from_list(original_symbols)
        _insert_sync_state(db_path, "auth", symbols_hash=original_hash)

        # No current symbols inserted — all removed.

        result = _detect_symbol_changes(tmp_path, "auth")

        assert result is not None
        assert result["has_drift"] is True
        assert result["current_symbols"] == []


# ---------------------------------------------------------------------------
# TestDetectSymbolChanges — no drift
# ---------------------------------------------------------------------------


class TestDetectSymbolChangesNoDrift:
    """_detect_symbol_changes returns None when symbols are unchanged."""

    def test_no_drift_when_symbols_unchanged(self, tmp_path: Path) -> None:
        db_path = _create_full_db(tmp_path)

        symbols = [("login", "function"), ("logout", "function")]
        stored_hash = _compute_symbols_hash_from_list(symbols)
        _insert_sync_state(db_path, "auth", symbols_hash=stored_hash)

        # Insert the SAME symbols as current.
        _insert_symbols(db_path, "auth", symbols)

        result = _detect_symbol_changes(tmp_path, "auth")
        assert result is None


# ---------------------------------------------------------------------------
# TestGeneratePolishDataSymbolChanges
# ---------------------------------------------------------------------------


class TestGeneratePolishDataSymbolChanges:
    """generate_polish_data includes symbol_changes when drift exists."""

    def test_includes_symbol_changes_on_drift(self, tmp_path: Path) -> None:
        _write_graph_yaml(tmp_path, _default_graph_data())
        db_path = _create_full_db(tmp_path)

        # Set up stored hash for one symbol.
        original_symbols = [("login", "function")]
        original_hash = _compute_symbols_hash_from_list(original_symbols)
        _insert_sync_state(db_path, "auth", symbols_hash=original_hash)

        # Current state has a different symbol set.
        current_symbols = [("login", "function"), ("logout", "function")]
        _insert_symbols(db_path, "auth", current_symbols)

        result = generate_polish_data(tmp_path, ref_id="auth")
        auth_node = result["nodes"][0]

        assert "symbol_changes" in auth_node
        assert auth_node["symbol_changes"]["has_drift"] is True
        assert len(auth_node["symbol_changes"]["current_symbols"]) == 2

    def test_no_symbol_changes_when_no_drift(self, tmp_path: Path) -> None:
        _write_graph_yaml(tmp_path, _default_graph_data())
        db_path = _create_full_db(tmp_path)

        symbols = [("login", "function")]
        stored_hash = _compute_symbols_hash_from_list(symbols)
        _insert_sync_state(db_path, "auth", symbols_hash=stored_hash)
        _insert_symbols(db_path, "auth", symbols)

        result = generate_polish_data(tmp_path, ref_id="auth")
        auth_node = result["nodes"][0]

        assert "symbol_changes" not in auth_node

    def test_no_symbol_changes_without_db(self, tmp_path: Path) -> None:
        _write_graph_yaml(tmp_path, _default_graph_data())

        result = generate_polish_data(tmp_path, ref_id="auth")
        auth_node = result["nodes"][0]

        assert "symbol_changes" not in auth_node

    def test_instructions_mention_symbol_drift(self, tmp_path: Path) -> None:
        _write_graph_yaml(tmp_path, _default_graph_data())

        result = generate_polish_data(tmp_path)
        assert "symbol drift" in result["instructions"]


# ---------------------------------------------------------------------------
# TestFormatPolishTextSymbolDrift
# ---------------------------------------------------------------------------


class TestFormatPolishTextSymbolDrift:
    """format_polish_text shows drift warning when symbol_changes present."""

    def test_shows_drift_warning(self) -> None:
        data: dict[str, Any] = {
            "nodes": [
                {
                    "ref_id": "auth",
                    "kind": "domain",
                    "summary": "Auth domain",
                    "source": "src/auth/",
                    "symbols": [],
                    "depends_on": [],
                    "used_by": [],
                    "doc_path": "docs/domains/auth/README.md",
                    "doc_status": "exists",
                    "symbol_changes": {
                        "has_drift": True,
                        "current_symbols": [
                            {"name": "login", "kind": "function"},
                            {"name": "logout", "kind": "function"},
                        ],
                        "message": "symbols changed since last doc sync (2 current symbols)",
                    },
                },
            ],
            "architecture": {"project_name": "testproject"},
            "instructions": "Enrich the docs.",
        }
        text = format_polish_text(data)

        assert "\u26a0 Symbol drift:" in text
        assert "symbols changed since last doc sync" in text

    def test_no_drift_warning_without_changes(self) -> None:
        data: dict[str, Any] = {
            "nodes": [
                {
                    "ref_id": "auth",
                    "kind": "domain",
                    "summary": "Auth domain",
                    "source": "src/auth/",
                    "symbols": [],
                    "depends_on": [],
                    "used_by": [],
                    "doc_path": "docs/domains/auth/README.md",
                    "doc_status": "exists",
                },
            ],
            "architecture": {"project_name": "testproject"},
            "instructions": "Enrich the docs.",
        }
        text = format_polish_text(data)

        assert "Symbol drift" not in text

    def test_drift_warning_with_full_pipeline(self, tmp_path: Path) -> None:
        """End-to-end: generate_polish_data -> format_polish_text shows drift."""
        _write_graph_yaml(tmp_path, _default_graph_data())
        db_path = _create_full_db(tmp_path)

        original_symbols = [("login", "function")]
        original_hash = _compute_symbols_hash_from_list(original_symbols)
        _insert_sync_state(db_path, "auth", symbols_hash=original_hash)

        current_symbols = [("login", "function"), ("logout", "function")]
        _insert_symbols(db_path, "auth", current_symbols)

        data = generate_polish_data(tmp_path, ref_id="auth")
        text = format_polish_text(data)

        assert "\u26a0 Symbol drift:" in text
        assert "symbols changed since last doc sync" in text
