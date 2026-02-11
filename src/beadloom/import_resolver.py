"""Import resolver: extract imports via tree-sitter and resolve to graph nodes."""

# beadloom:domain=context-oracle

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import TYPE_CHECKING

from tree_sitter import Parser

from beadloom.code_indexer import get_lang_config

if TYPE_CHECKING:
    import sqlite3
    from pathlib import Path

    from tree_sitter import Node as TSNode


# Rust built-in crates to skip.
_RUST_BUILTIN_CRATES: frozenset[str] = frozenset({"std", "core", "alloc"})

# Go standard library packages have no '/' in their path (heuristic).
# We skip those.


@dataclass(frozen=True)
class ImportInfo:
    """A single import extracted from source code."""

    file_path: str  # path to source file
    line_number: int  # 1-based line number
    import_path: str  # raw import path (e.g. "beadloom.auth.tokens")
    resolved_ref_id: str | None  # mapped graph node ref_id (nullable)


# ---------------------------------------------------------------------------
# Language-specific import extractors
# ---------------------------------------------------------------------------


def _extract_python_imports(root: TSNode, file_path: str) -> list[ImportInfo]:
    """Extract imports from a Python AST root node."""
    results: list[ImportInfo] = []

    for child in root.children:
        if child.type == "import_statement":
            # `import X` or `import X.Y.Z`
            for sub in child.children:
                if sub.type == "dotted_name":
                    path = sub.text.decode("utf-8") if sub.text else ""
                    if path:
                        results.append(
                            ImportInfo(
                                file_path=file_path,
                                line_number=child.start_point.row + 1,
                                import_path=path,
                                resolved_ref_id=None,
                            )
                        )

        elif child.type == "import_from_statement":
            # `from X import Y` or `from . import Y` (relative)
            # Check for relative import: look for relative_import child
            is_relative = False
            module_path: str | None = None

            for sub in child.children:
                if sub.type == "relative_import":
                    is_relative = True
                    break
                if sub.type == "dotted_name" and module_path is None:
                    # The first dotted_name after 'from' is the module path
                    module_path = sub.text.decode("utf-8") if sub.text else ""

            if is_relative:
                continue

            if module_path:
                results.append(
                    ImportInfo(
                        file_path=file_path,
                        line_number=child.start_point.row + 1,
                        import_path=module_path,
                        resolved_ref_id=None,
                    )
                )

    return results


def _get_ts_import_source(node: TSNode) -> str | None:
    """Extract the string value from a TypeScript/JS import statement's source."""
    for child in node.children:
        if child.type == "string":
            # The string node contains quote chars and a string_fragment
            for sub in child.children:
                if sub.type == "string_fragment":
                    return sub.text.decode("utf-8") if sub.text else None
    return None


def _extract_ts_imports(root: TSNode, file_path: str) -> list[ImportInfo]:
    """Extract imports from a TypeScript/JavaScript AST root node."""
    results: list[ImportInfo] = []

    for child in root.children:
        if child.type != "import_statement":
            continue

        source = _get_ts_import_source(child)
        if source is None:
            continue

        # Skip relative imports
        if source.startswith(".") or source.startswith(".."):
            continue

        results.append(
            ImportInfo(
                file_path=file_path,
                line_number=child.start_point.row + 1,
                import_path=source,
                resolved_ref_id=None,
            )
        )

    return results


def _extract_go_import_spec(spec: TSNode, file_path: str) -> ImportInfo | None:
    """Extract a single Go import spec, returning None for stdlib imports."""
    # Find the interpreted_string_literal
    for child in spec.children:
        if child.type == "interpreted_string_literal":
            # Get the content (without quotes)
            for sub in child.children:
                if sub.type == "interpreted_string_literal_content":
                    path = sub.text.decode("utf-8") if sub.text else ""
                    if not path:
                        return None
                    # Skip stdlib: no '/' in path
                    if "/" not in path:
                        return None
                    return ImportInfo(
                        file_path=file_path,
                        line_number=spec.start_point.row + 1,
                        import_path=path,
                        resolved_ref_id=None,
                    )
    return None


def _extract_go_imports(root: TSNode, file_path: str) -> list[ImportInfo]:
    """Extract imports from a Go AST root node."""
    results: list[ImportInfo] = []

    for child in root.children:
        if child.type != "import_declaration":
            continue

        for sub in child.children:
            if sub.type == "import_spec":
                info = _extract_go_import_spec(sub, file_path)
                if info is not None:
                    results.append(info)
            elif sub.type == "import_spec_list":
                for spec in sub.children:
                    if spec.type == "import_spec":
                        info = _extract_go_import_spec(spec, file_path)
                        if info is not None:
                            results.append(info)

    return results


def _get_rust_use_path(node: TSNode) -> str | None:
    """Recursively extract the full path from a Rust use_declaration argument node."""
    if node.type == "scoped_identifier":
        return node.text.decode("utf-8") if node.text else None
    if node.type == "identifier":
        return node.text.decode("utf-8") if node.text else None
    if node.type == "scoped_use_list":
        # e.g. `std::{io, fs}` — extract the root prefix
        return node.text.decode("utf-8") if node.text else None
    if node.type == "use_wildcard":
        return node.text.decode("utf-8") if node.text else None
    return None


def _extract_rust_imports(root: TSNode, file_path: str) -> list[ImportInfo]:
    """Extract imports from a Rust AST root node."""
    results: list[ImportInfo] = []

    for child in root.children:
        if child.type != "use_declaration":
            continue

        # Find the argument of `use` (scoped_identifier, scoped_use_list, etc.)
        for sub in child.children:
            path = _get_rust_use_path(sub)
            if path is None:
                continue

            # Determine the root crate name
            root_ident = path.split("::")[0] if "::" in path else path

            # Skip built-in crates
            if root_ident in _RUST_BUILTIN_CRATES:
                break

            # Skip relative imports (super, self)
            if root_ident in ("super", "self"):
                break

            results.append(
                ImportInfo(
                    file_path=file_path,
                    line_number=child.start_point.row + 1,
                    import_path=path,
                    resolved_ref_id=None,
                )
            )
            break  # Only one path per use_declaration

    return results


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def extract_imports(file_path: Path) -> list[ImportInfo]:
    """Extract import statements from a source file using tree-sitter.

    Detects language by file extension.  Returns empty list if the language
    is not supported or the grammar package is not installed.
    """
    config = get_lang_config(file_path.suffix)
    if config is None:
        return []

    try:
        content = file_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []

    if not content.strip():
        return []

    content_bytes = content.encode("utf-8")
    parser = Parser(config.language)
    tree = parser.parse(content_bytes)
    root = tree.root_node

    file_str = str(file_path)
    ext = file_path.suffix

    if ext == ".py":
        return _extract_python_imports(root, file_str)
    if ext in (".ts", ".tsx", ".js", ".jsx"):
        return _extract_ts_imports(root, file_str)
    if ext == ".go":
        return _extract_go_imports(root, file_str)
    if ext == ".rs":
        return _extract_rust_imports(root, file_str)

    return []


def _import_path_to_file_paths(import_path: str) -> list[str]:
    """Convert a Python dotted import path to possible file paths.

    E.g. ``beadloom.auth.tokens`` -> [
        ``src/beadloom/auth/tokens.py``,
        ``src/beadloom/auth/tokens/__init__.py``,
        ``beadloom/auth/tokens.py``,
        ``beadloom/auth/tokens/__init__.py``,
    ]
    """
    parts = import_path.replace(".", "/")
    candidates: list[str] = []
    for prefix in ("src/", "lib/", "app/", ""):
        candidates.append(f"{prefix}{parts}.py")
        candidates.append(f"{prefix}{parts}/__init__.py")
    return candidates


def resolve_import_to_node(
    import_path: str,
    file_path: Path,  # kept for future use (relative resolution)
    conn: sqlite3.Connection,
) -> str | None:
    """Map an import path to a graph node ref_id.

    Strategy:
    1. Convert import path to possible file paths
    2. Look up file_path in code_symbols -> get annotations -> find matching node
    3. Fallback: match file path against nodes.source column

    Returns ``None`` if no mapping found.
    """
    # Strategy 1: check code_symbols for files matching the import path
    possible_files = _import_path_to_file_paths(import_path)

    for candidate in possible_files:
        rows = conn.execute(
            "SELECT annotations FROM code_symbols WHERE file_path = ? LIMIT 1",
            (candidate,),
        ).fetchall()

        for row in rows:
            annotations_str: str = row[0] if row[0] else "{}"
            try:
                annotations: dict[str, str] = json.loads(annotations_str)
            except (json.JSONDecodeError, TypeError):
                continue

            # Look for domain/service/feature annotation and match to node ref_id
            for kind in ("domain", "service", "feature"):
                value = annotations.get(kind)
                if value is not None:
                    ref_id = f"{kind}:{value}"
                    node_row = conn.execute(
                        "SELECT ref_id FROM nodes WHERE ref_id = ?",
                        (ref_id,),
                    ).fetchone()
                    if node_row is not None:
                        return str(node_row[0])

    # Strategy 2: match against nodes.source column
    # Convert dotted path to directory-like path for matching
    dir_path = import_path.replace(".", "/")
    for prefix in ("src/", "lib/", "app/", ""):
        candidate_source = f"{prefix}{dir_path}"
        node_row = conn.execute(
            "SELECT ref_id FROM nodes WHERE source = ?",
            (candidate_source,),
        ).fetchone()
        if node_row is not None:
            return str(node_row[0])

    return None


def _collect_source_files(project_root: Path) -> list[Path]:
    """Collect all supported source files from src/, lib/, app/ directories."""
    from beadloom.code_indexer import supported_extensions

    exts = supported_extensions()
    files: list[Path] = []

    for dir_name in ("src", "lib", "app"):
        base = project_root / dir_name
        if not base.is_dir():
            continue
        for ext in exts:
            files.extend(base.rglob(f"*{ext}"))

    return sorted(files)


def index_imports(project_root: Path, conn: sqlite3.Connection) -> int:
    """Scan all source files and index their imports into the code_imports table.

    Scans ``src/``, ``lib/``, and ``app/`` directories.
    Returns the count of imports indexed.
    """
    source_files = _collect_source_files(project_root)
    total = 0

    for file_path in source_files:
        imports = extract_imports(file_path)
        if not imports:
            continue

        # Compute file hash for the import records
        try:
            content = file_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue

        file_hash = hashlib.sha256(content.encode()).hexdigest()

        for imp in imports:
            resolved = resolve_import_to_node(imp.import_path, file_path, conn)
            conn.execute(
                "INSERT INTO code_imports"
                " (file_path, line_number, import_path, resolved_ref_id, file_hash)"
                " VALUES (?, ?, ?, ?, ?)"
                " ON CONFLICT(file_path, line_number, import_path)"
                " DO UPDATE SET resolved_ref_id = excluded.resolved_ref_id,"
                " file_hash = excluded.file_hash",
                (str(file_path), imp.line_number, imp.import_path, resolved, file_hash),
            )
            total += 1

    conn.commit()
    return total
