"""Tests for beadloom.import_resolver — import extraction and resolution."""

from __future__ import annotations

import hashlib
import json
from typing import TYPE_CHECKING

import pytest

from beadloom.context_oracle.code_indexer import clear_cache
from beadloom.infrastructure.db import create_schema, open_db

if TYPE_CHECKING:
    import sqlite3
    from pathlib import Path


@pytest.fixture(autouse=True)
def _clear_lang_cache() -> None:
    """Clear language cache before each test to avoid cross-test pollution."""
    clear_cache()


@pytest.fixture()
def conn(tmp_path: Path) -> sqlite3.Connection:
    """Create a fresh in-memory-like SQLite database with schema."""
    db_path = tmp_path / "test.db"
    c = open_db(db_path)
    create_schema(c)
    return c


# ---------------------------------------------------------------------------
# Helpers for grammar availability
# ---------------------------------------------------------------------------


def _ts_available() -> bool:
    try:
        import tree_sitter_typescript  # noqa: F401

        return True
    except ImportError:
        return False


def _go_available() -> bool:
    try:
        import tree_sitter_go  # noqa: F401

        return True
    except ImportError:
        return False


def _rust_available() -> bool:
    try:
        import tree_sitter_rust  # noqa: F401

        return True
    except ImportError:
        return False


# ===================================================================
# extract_imports — Python
# ===================================================================


class TestExtractImportsPython:
    """Python import extraction via tree-sitter."""

    def test_import_os(self, tmp_path: Path) -> None:
        """Plain `import os` produces import_path='os'."""
        from beadloom.graph.import_resolver import extract_imports

        py = tmp_path / "module.py"
        py.write_text("import os\n")
        results = extract_imports(py)
        assert len(results) == 1
        assert results[0].import_path == "os"
        assert results[0].line_number == 1
        assert results[0].resolved_ref_id is None

    def test_import_dotted(self, tmp_path: Path) -> None:
        """`import beadloom.core` -> import_path='beadloom.core'."""
        from beadloom.graph.import_resolver import extract_imports

        py = tmp_path / "module.py"
        py.write_text("import beadloom.core\n")
        results = extract_imports(py)
        assert len(results) == 1
        assert results[0].import_path == "beadloom.core"

    def test_from_import(self, tmp_path: Path) -> None:
        """`from beadloom.auth import tokens` -> import_path='beadloom.auth'."""
        from beadloom.graph.import_resolver import extract_imports

        py = tmp_path / "module.py"
        py.write_text("from beadloom.auth import tokens\n")
        results = extract_imports(py)
        assert len(results) == 1
        assert results[0].import_path == "beadloom.auth"

    def test_from_deep_import(self, tmp_path: Path) -> None:
        """`from beadloom.auth.models import User` -> import_path='beadloom.auth.models'."""
        from beadloom.graph.import_resolver import extract_imports

        py = tmp_path / "module.py"
        py.write_text("from beadloom.auth.models import User\n")
        results = extract_imports(py)
        assert len(results) == 1
        assert results[0].import_path == "beadloom.auth.models"

    def test_relative_import_dot_skipped(self, tmp_path: Path) -> None:
        """`from . import sibling` is skipped (relative import)."""
        from beadloom.graph.import_resolver import extract_imports

        py = tmp_path / "module.py"
        py.write_text("from . import sibling\n")
        results = extract_imports(py)
        assert len(results) == 0

    def test_relative_import_dotdot_skipped(self, tmp_path: Path) -> None:
        """`from ..parent import thing` is skipped (relative import)."""
        from beadloom.graph.import_resolver import extract_imports

        py = tmp_path / "module.py"
        py.write_text("from ..parent import thing\n")
        results = extract_imports(py)
        assert len(results) == 0

    def test_relative_import_dot_module_skipped(self, tmp_path: Path) -> None:
        """`from .local import helper` is skipped (relative import)."""
        from beadloom.graph.import_resolver import extract_imports

        py = tmp_path / "module.py"
        py.write_text("from .local import helper\n")
        results = extract_imports(py)
        assert len(results) == 0

    def test_multiple_imports_in_file(self, tmp_path: Path) -> None:
        """Multiple import statements yield multiple ImportInfo entries."""
        from beadloom.graph.import_resolver import extract_imports

        py = tmp_path / "multi.py"
        py.write_text("import os\nimport json\nfrom pathlib import Path\n")
        results = extract_imports(py)
        assert len(results) == 3
        paths = {r.import_path for r in results}
        assert paths == {"os", "json", "pathlib"}

    def test_file_path_recorded(self, tmp_path: Path) -> None:
        """ImportInfo records the file path."""
        from beadloom.graph.import_resolver import extract_imports

        py = tmp_path / "check_path.py"
        py.write_text("import os\n")
        results = extract_imports(py)
        assert results[0].file_path == str(py)

    def test_empty_file(self, tmp_path: Path) -> None:
        """Empty Python file yields no imports."""
        from beadloom.graph.import_resolver import extract_imports

        py = tmp_path / "empty.py"
        py.write_text("")
        results = extract_imports(py)
        assert results == []

    def test_unsupported_extension(self, tmp_path: Path) -> None:
        """Unsupported file extension returns empty list."""
        from beadloom.graph.import_resolver import extract_imports

        txt = tmp_path / "data.txt"
        txt.write_text("import os\n")
        results = extract_imports(txt)
        assert results == []


# ===================================================================
# extract_imports — TypeScript / JavaScript
# ===================================================================


class TestExtractImportsTypeScript:
    """TypeScript / JavaScript import extraction."""

    @pytest.mark.skipif(not _ts_available(), reason="tree-sitter-typescript not installed")
    def test_named_import(self, tmp_path: Path) -> None:
        """`import { X } from 'some-module'` -> import_path='some-module'."""
        from beadloom.graph.import_resolver import extract_imports

        ts = tmp_path / "app.ts"
        ts.write_text("import { X } from 'some-module';\n")
        results = extract_imports(ts)
        assert len(results) == 1
        assert results[0].import_path == "some-module"

    @pytest.mark.skipif(not _ts_available(), reason="tree-sitter-typescript not installed")
    def test_default_import(self, tmp_path: Path) -> None:
        """`import X from 'path'` -> import_path='path'."""
        from beadloom.graph.import_resolver import extract_imports

        ts = tmp_path / "app.ts"
        ts.write_text("import Y from 'path';\n")
        results = extract_imports(ts)
        assert len(results) == 1
        assert results[0].import_path == "path"

    @pytest.mark.skipif(not _ts_available(), reason="tree-sitter-typescript not installed")
    def test_relative_import_skipped(self, tmp_path: Path) -> None:
        """`import './relative'` is skipped."""
        from beadloom.graph.import_resolver import extract_imports

        ts = tmp_path / "app.ts"
        ts.write_text("import './relative';\n")
        results = extract_imports(ts)
        assert len(results) == 0

    @pytest.mark.skipif(not _ts_available(), reason="tree-sitter-typescript not installed")
    def test_relative_parent_import_skipped(self, tmp_path: Path) -> None:
        """`import { A } from '../parent'` is skipped (relative)."""
        from beadloom.graph.import_resolver import extract_imports

        ts = tmp_path / "app.ts"
        ts.write_text("import { A } from '../parent';\n")
        results = extract_imports(ts)
        assert len(results) == 0

    @pytest.mark.skipif(not _ts_available(), reason="tree-sitter-typescript not installed")
    def test_js_file_uses_ts_parser(self, tmp_path: Path) -> None:
        """JavaScript file is parsed the same way as TypeScript."""
        from beadloom.graph.import_resolver import extract_imports

        js = tmp_path / "app.js"
        js.write_text("import { handler } from 'express';\n")
        results = extract_imports(js)
        assert len(results) == 1
        assert results[0].import_path == "express"

    @pytest.mark.skipif(not _ts_available(), reason="tree-sitter-typescript not installed")
    def test_namespace_import(self, tmp_path: Path) -> None:
        """`import * as pkg from 'external-pkg'` -> import_path='external-pkg'."""
        from beadloom.graph.import_resolver import extract_imports

        ts = tmp_path / "app.ts"
        ts.write_text("import * as pkg from 'external-pkg';\n")
        results = extract_imports(ts)
        assert len(results) == 1
        assert results[0].import_path == "external-pkg"


# ===================================================================
# extract_imports — Go
# ===================================================================


class TestExtractImportsGo:
    """Go import extraction."""

    @pytest.mark.skipif(not _go_available(), reason="tree-sitter-go not installed")
    def test_stdlib_import_skipped(self, tmp_path: Path) -> None:
        """`import "fmt"` is skipped (stdlib, no slash)."""
        from beadloom.graph.import_resolver import extract_imports

        go = tmp_path / "main.go"
        go.write_text('package main\n\nimport "fmt"\n')
        results = extract_imports(go)
        assert len(results) == 0

    @pytest.mark.skipif(not _go_available(), reason="tree-sitter-go not installed")
    def test_third_party_import(self, tmp_path: Path) -> None:
        """`import "github.com/org/repo/pkg"` -> import_path with slash."""
        from beadloom.graph.import_resolver import extract_imports

        go = tmp_path / "main.go"
        go.write_text('package main\n\nimport "github.com/org/repo/pkg"\n')
        results = extract_imports(go)
        assert len(results) == 1
        assert results[0].import_path == "github.com/org/repo/pkg"

    @pytest.mark.skipif(not _go_available(), reason="tree-sitter-go not installed")
    def test_grouped_imports(self, tmp_path: Path) -> None:
        """Grouped import block extracts multiple entries, skipping stdlib."""
        from beadloom.graph.import_resolver import extract_imports

        go = tmp_path / "main.go"
        go.write_text('package main\n\nimport (\n    "os"\n    "github.com/other/lib"\n)\n')
        results = extract_imports(go)
        # "os" is skipped (stdlib), only "github.com/other/lib" remains
        assert len(results) == 1
        assert results[0].import_path == "github.com/other/lib"

    @pytest.mark.skipif(not _go_available(), reason="tree-sitter-go not installed")
    def test_aliased_import(self, tmp_path: Path) -> None:
        """Aliased import `alias "github.com/x/y"` still extracts the path."""
        from beadloom.graph.import_resolver import extract_imports

        go = tmp_path / "main.go"
        go.write_text('package main\n\nimport (\n    myalias "github.com/aliased/pkg"\n)\n')
        results = extract_imports(go)
        assert len(results) == 1
        assert results[0].import_path == "github.com/aliased/pkg"


# ===================================================================
# extract_imports — Rust
# ===================================================================


class TestExtractImportsRust:
    """Rust import extraction."""

    @pytest.mark.skipif(not _rust_available(), reason="tree-sitter-rust not installed")
    def test_std_skipped(self, tmp_path: Path) -> None:
        """`use std::collections::HashMap` is skipped (std crate)."""
        from beadloom.graph.import_resolver import extract_imports

        rs = tmp_path / "lib.rs"
        rs.write_text("use std::collections::HashMap;\n")
        results = extract_imports(rs)
        assert len(results) == 0

    @pytest.mark.skipif(not _rust_available(), reason="tree-sitter-rust not installed")
    def test_crate_import(self, tmp_path: Path) -> None:
        """`use crate::auth::tokens` -> import_path='crate::auth::tokens'."""
        from beadloom.graph.import_resolver import extract_imports

        rs = tmp_path / "lib.rs"
        rs.write_text("use crate::auth::tokens;\n")
        results = extract_imports(rs)
        assert len(results) == 1
        assert results[0].import_path == "crate::auth::tokens"

    @pytest.mark.skipif(not _rust_available(), reason="tree-sitter-rust not installed")
    def test_external_crate_import(self, tmp_path: Path) -> None:
        """`use mylib::core` -> import_path='mylib::core'."""
        from beadloom.graph.import_resolver import extract_imports

        rs = tmp_path / "lib.rs"
        rs.write_text("use mylib::core;\n")
        results = extract_imports(rs)
        assert len(results) == 1
        assert results[0].import_path == "mylib::core"

    @pytest.mark.skipif(not _rust_available(), reason="tree-sitter-rust not installed")
    def test_core_and_alloc_skipped(self, tmp_path: Path) -> None:
        """`use core::...` and `use alloc::...` are skipped (builtin crates)."""
        from beadloom.graph.import_resolver import extract_imports

        rs = tmp_path / "lib.rs"
        rs.write_text("use core::fmt::Display;\nuse alloc::vec::Vec;\n")
        results = extract_imports(rs)
        assert len(results) == 0

    @pytest.mark.skipif(not _rust_available(), reason="tree-sitter-rust not installed")
    def test_super_skipped(self, tmp_path: Path) -> None:
        """`use super::parent` is skipped (relative)."""
        from beadloom.graph.import_resolver import extract_imports

        rs = tmp_path / "lib.rs"
        rs.write_text("use super::parent;\n")
        results = extract_imports(rs)
        assert len(results) == 0

    @pytest.mark.skipif(not _rust_available(), reason="tree-sitter-rust not installed")
    def test_self_skipped(self, tmp_path: Path) -> None:
        """`use self::internal::helper` is skipped (relative)."""
        from beadloom.graph.import_resolver import extract_imports

        rs = tmp_path / "lib.rs"
        rs.write_text("use self::internal::helper;\n")
        results = extract_imports(rs)
        assert len(results) == 0

    @pytest.mark.skipif(not _rust_available(), reason="tree-sitter-rust not installed")
    def test_mod_declaration_skipped(self, tmp_path: Path) -> None:
        """`mod internal;` is not an import — must be skipped."""
        from beadloom.graph.import_resolver import extract_imports

        rs = tmp_path / "lib.rs"
        rs.write_text("mod internal;\n")
        results = extract_imports(rs)
        assert len(results) == 0


# ===================================================================
# resolve_import_to_node
# ===================================================================


class TestResolveImportToNode:
    """Tests for import path -> graph node resolution."""

    def test_resolves_via_annotation_domain(
        self,
        tmp_path: Path,
        conn: sqlite3.Connection,
    ) -> None:
        """Import resolves to a node via code_symbols annotation match."""
        from beadloom.graph.import_resolver import resolve_import_to_node

        # Insert a node
        conn.execute(
            "INSERT INTO nodes (ref_id, kind, summary) VALUES (?, ?, ?)",
            ("domain:auth", "domain", "Auth domain"),
        )
        # Insert a code symbol with annotation referencing that node
        conn.execute(
            "INSERT INTO code_symbols"
            " (file_path, symbol_name, kind, line_start, line_end, annotations, file_hash)"
            " VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                "src/beadloom/auth/tokens.py",
                "verify_token",
                "function",
                10,
                20,
                json.dumps({"domain": "auth"}),
                "abc123",
            ),
        )
        conn.commit()

        result = resolve_import_to_node("beadloom.auth.tokens", tmp_path, conn)
        assert result == "domain:auth"

    def test_resolves_via_node_source(
        self,
        tmp_path: Path,
        conn: sqlite3.Connection,
    ) -> None:
        """Fallback: import resolves via nodes.source column match."""
        from beadloom.graph.import_resolver import resolve_import_to_node

        conn.execute(
            "INSERT INTO nodes (ref_id, kind, summary, source) VALUES (?, ?, ?, ?)",
            ("service:api", "service", "API service", "src/beadloom/api"),
        )
        conn.commit()

        result = resolve_import_to_node("beadloom.api", tmp_path, conn)
        assert result == "service:api"

    def test_returns_none_when_no_match(
        self,
        tmp_path: Path,
        conn: sqlite3.Connection,
    ) -> None:
        """Returns None if no node matches the import path."""
        from beadloom.graph.import_resolver import resolve_import_to_node

        result = resolve_import_to_node("unknown.module", tmp_path, conn)
        assert result is None


# ===================================================================
# index_imports
# ===================================================================


class TestIndexImports:
    """Tests for full-project import indexing."""

    def test_indexes_python_imports(
        self,
        tmp_path: Path,
        conn: sqlite3.Connection,
    ) -> None:
        """Indexes imports from Python source files in src/ directory."""
        from beadloom.graph.import_resolver import index_imports

        src = tmp_path / "src" / "myapp"
        src.mkdir(parents=True)
        py = src / "main.py"
        py.write_text("import os\nimport json\n")

        count = index_imports(tmp_path, conn)
        assert count == 2

        rows = conn.execute("SELECT * FROM code_imports").fetchall()
        assert len(rows) == 2

    def test_correct_data_in_table(
        self,
        tmp_path: Path,
        conn: sqlite3.Connection,
    ) -> None:
        """Verify the data inserted into code_imports is correct."""
        from beadloom.graph.import_resolver import index_imports

        src = tmp_path / "src" / "myapp"
        src.mkdir(parents=True)
        py = src / "main.py"
        content = "import os\n"
        py.write_text(content)

        index_imports(tmp_path, conn)

        rows = conn.execute("SELECT * FROM code_imports").fetchall()
        assert len(rows) == 1
        row = rows[0]
        assert row["import_path"] == "os"
        assert row["line_number"] == 1
        expected_hash = hashlib.sha256(content.encode()).hexdigest()
        assert row["file_hash"] == expected_hash

    def test_returns_count(
        self,
        tmp_path: Path,
        conn: sqlite3.Connection,
    ) -> None:
        """Returns the number of imports indexed."""
        from beadloom.graph.import_resolver import index_imports

        src = tmp_path / "src" / "pkg"
        src.mkdir(parents=True)
        (src / "a.py").write_text("import os\nimport sys\n")
        (src / "b.py").write_text("import json\n")

        count = index_imports(tmp_path, conn)
        assert count == 3

    def test_empty_project(
        self,
        tmp_path: Path,
        conn: sqlite3.Connection,
    ) -> None:
        """No source directories -> 0 imports."""
        from beadloom.graph.import_resolver import index_imports

        count = index_imports(tmp_path, conn)
        assert count == 0

    def test_scans_lib_and_app_dirs(
        self,
        tmp_path: Path,
        conn: sqlite3.Connection,
    ) -> None:
        """Also scans lib/ and app/ directories."""
        from beadloom.graph.import_resolver import index_imports

        lib = tmp_path / "lib"
        lib.mkdir()
        (lib / "util.py").write_text("import os\n")

        app = tmp_path / "app"
        app.mkdir()
        (app / "main.py").write_text("import sys\n")

        count = index_imports(tmp_path, conn)
        assert count == 2

    def test_stores_relative_paths(
        self,
        tmp_path: Path,
        conn: sqlite3.Connection,
    ) -> None:
        """file_path in code_imports is stored as relative, not absolute."""
        from beadloom.graph.import_resolver import index_imports

        src = tmp_path / "src" / "myapp"
        src.mkdir(parents=True)
        (src / "main.py").write_text("import os\n")

        index_imports(tmp_path, conn)

        row = conn.execute("SELECT file_path FROM code_imports").fetchone()
        assert row is not None
        path = row["file_path"]
        assert not path.startswith("/"), f"Expected relative path, got: {path}"
        assert path == "src/myapp/main.py"

    def test_idempotent_reindex(
        self,
        tmp_path: Path,
        conn: sqlite3.Connection,
    ) -> None:
        """Re-indexing the same files replaces old records (upsert)."""
        from beadloom.graph.import_resolver import index_imports

        src = tmp_path / "src" / "pkg"
        src.mkdir(parents=True)
        (src / "a.py").write_text("import os\n")

        index_imports(tmp_path, conn)
        count = index_imports(tmp_path, conn)
        assert count == 1

        rows = conn.execute("SELECT * FROM code_imports").fetchall()
        assert len(rows) == 1


# ===================================================================
# Hierarchical source-prefix resolution
# ===================================================================


class TestHierarchicalResolution:
    """Tests for the new path-prefix matching resolver."""

    def test_resolves_django_import_via_source(
        self,
        tmp_path: Path,
        conn: sqlite3.Connection,
    ) -> None:
        """Django-style import resolves via node source prefix."""
        from beadloom.graph.import_resolver import resolve_import_to_node

        conn.execute(
            "INSERT INTO nodes (ref_id, kind, summary, source) VALUES (?, ?, ?, ?)",
            ("apps-accounts", "domain", "Accounts", "backend/apps/accounts/"),
        )
        conn.commit()

        result = resolve_import_to_node(
            "apps.accounts.models",
            tmp_path,
            conn,
            scan_paths=["backend"],
        )
        assert result == "apps-accounts"

    def test_resolves_deepest_node(
        self,
        tmp_path: Path,
        conn: sqlite3.Connection,
    ) -> None:
        """When multiple nodes match, returns the deepest (most specific)."""
        from beadloom.graph.import_resolver import resolve_import_to_node

        conn.execute(
            "INSERT INTO nodes (ref_id, kind, summary, source) VALUES (?, ?, ?, ?)",
            ("apps", "domain", "Apps", "backend/apps/"),
        )
        conn.execute(
            "INSERT INTO nodes (ref_id, kind, summary, source) VALUES (?, ?, ?, ?)",
            ("apps-core", "service", "Core", "backend/apps/core/"),
        )
        conn.commit()

        result = resolve_import_to_node(
            "apps.core.models",
            tmp_path,
            conn,
            scan_paths=["backend"],
        )
        assert result == "apps-core"

    def test_ts_alias_resolves(
        self,
        tmp_path: Path,
        conn: sqlite3.Connection,
    ) -> None:
        """TS @/ alias resolves to node under src/."""
        from beadloom.graph.import_resolver import resolve_import_to_node

        conn.execute(
            "INSERT INTO nodes (ref_id, kind, summary, source) VALUES (?, ?, ?, ?)",
            ("src-shared", "service", "Shared", "frontend/src/shared/"),
        )
        conn.commit()

        result = resolve_import_to_node(
            "@/shared/utils",
            tmp_path,
            conn,
            scan_paths=["frontend"],
            is_ts=True,
        )
        assert result == "src-shared"

    def test_npm_package_returns_none(
        self,
        tmp_path: Path,
        conn: sqlite3.Connection,
    ) -> None:
        """npm package imports return None (not local code)."""
        from beadloom.graph.import_resolver import resolve_import_to_node

        result = resolve_import_to_node(
            "vue",
            tmp_path,
            conn,
            is_ts=True,
        )
        assert result is None

    def test_ts_tilde_alias_resolves(
        self,
        tmp_path: Path,
        conn: sqlite3.Connection,
    ) -> None:
        """TS ~/ alias also resolves to src/."""
        from beadloom.graph.import_resolver import resolve_import_to_node

        conn.execute(
            "INSERT INTO nodes (ref_id, kind, summary, source) VALUES (?, ?, ?, ?)",
            ("src-hooks", "domain", "Hooks", "frontend/src/hooks/"),
        )
        conn.commit()

        result = resolve_import_to_node(
            "~/hooks/useSomething",
            tmp_path,
            conn,
            scan_paths=["frontend"],
            is_ts=True,
        )
        assert result == "src-hooks"


# ===================================================================
# create_import_edges
# ===================================================================


class TestCreateImportEdges:
    """Tests for depends_on edge creation from resolved imports."""

    def test_creates_depends_on_edge(
        self,
        conn: sqlite3.Connection,
    ) -> None:
        """Resolved import creates a depends_on edge between nodes."""
        from beadloom.graph.import_resolver import create_import_edges

        # Setup: two nodes.
        conn.execute(
            "INSERT INTO nodes (ref_id, kind, summary, source) VALUES (?, ?, ?, ?)",
            ("apps-tasks", "domain", "Tasks", "backend/apps/tasks/"),
        )
        conn.execute(
            "INSERT INTO nodes (ref_id, kind, summary, source) VALUES (?, ?, ?, ?)",
            ("apps-core", "service", "Core", "backend/apps/core/"),
        )
        # A resolved import from tasks → core.
        conn.execute(
            "INSERT INTO code_imports "
            "(file_path, line_number, import_path, resolved_ref_id, file_hash) "
            "VALUES (?, ?, ?, ?, ?)",
            ("backend/apps/tasks/views.py", 1, "apps.core.models", "apps-core", "abc"),
        )
        conn.commit()

        edges = create_import_edges(conn)
        assert edges == 1

        row = conn.execute("SELECT * FROM edges WHERE kind = 'depends_on'").fetchone()
        assert row is not None
        assert row["src_ref_id"] == "apps-tasks"
        assert row["dst_ref_id"] == "apps-core"

    def test_no_self_edges(
        self,
        conn: sqlite3.Connection,
    ) -> None:
        """Import within the same node does not create an edge."""
        from beadloom.graph.import_resolver import create_import_edges

        conn.execute(
            "INSERT INTO nodes (ref_id, kind, summary, source) VALUES (?, ?, ?, ?)",
            ("apps-core", "service", "Core", "backend/apps/core/"),
        )
        conn.execute(
            "INSERT INTO code_imports "
            "(file_path, line_number, import_path, resolved_ref_id, file_hash) "
            "VALUES (?, ?, ?, ?, ?)",
            ("backend/apps/core/views.py", 1, "apps.core.models", "apps-core", "abc"),
        )
        conn.commit()

        edges = create_import_edges(conn)
        assert edges == 0

    def test_deduplicates_edges(
        self,
        conn: sqlite3.Connection,
    ) -> None:
        """Multiple imports between same nodes create only one edge."""
        from beadloom.graph.import_resolver import create_import_edges

        conn.execute(
            "INSERT INTO nodes (ref_id, kind, summary, source) VALUES (?, ?, ?, ?)",
            ("apps-tasks", "domain", "Tasks", "backend/apps/tasks/"),
        )
        conn.execute(
            "INSERT INTO nodes (ref_id, kind, summary, source) VALUES (?, ?, ?, ?)",
            ("apps-core", "service", "Core", "backend/apps/core/"),
        )
        # Two different imports from same source to same target.
        conn.execute(
            "INSERT INTO code_imports "
            "(file_path, line_number, import_path, resolved_ref_id, file_hash) "
            "VALUES (?, ?, ?, ?, ?)",
            ("backend/apps/tasks/views.py", 1, "apps.core.models", "apps-core", "abc"),
        )
        conn.execute(
            "INSERT INTO code_imports "
            "(file_path, line_number, import_path, resolved_ref_id, file_hash) "
            "VALUES (?, ?, ?, ?, ?)",
            ("backend/apps/tasks/views.py", 2, "apps.core.choices", "apps-core", "abc"),
        )
        conn.commit()

        edges = create_import_edges(conn)
        assert edges == 1

    def test_index_imports_creates_edges(
        self,
        tmp_path: Path,
        conn: sqlite3.Connection,
    ) -> None:
        """Full index_imports pipeline creates depends_on edges."""
        from beadloom.graph.import_resolver import index_imports

        # Setup: nodes with source directories.
        conn.execute(
            "INSERT INTO nodes (ref_id, kind, summary, source) VALUES (?, ?, ?, ?)",
            ("api", "feature", "API", "src/api/"),
        )
        conn.execute(
            "INSERT INTO nodes (ref_id, kind, summary, source) VALUES (?, ?, ?, ?)",
            ("auth", "domain", "Auth", "src/auth/"),
        )
        conn.commit()

        # File in api/ imports from auth.
        api_dir = tmp_path / "src" / "api"
        api_dir.mkdir(parents=True)
        (api_dir / "views.py").write_text("from auth import tokens\n")

        auth_dir = tmp_path / "src" / "auth"
        auth_dir.mkdir(parents=True)
        (auth_dir / "tokens.py").write_text("TOKEN = 'abc'\n")

        index_imports(tmp_path, conn)

        edges = conn.execute("SELECT * FROM edges WHERE kind = 'depends_on'").fetchall()
        assert len(edges) == 1
        assert edges[0]["src_ref_id"] == "api"
        assert edges[0]["dst_ref_id"] == "auth"
