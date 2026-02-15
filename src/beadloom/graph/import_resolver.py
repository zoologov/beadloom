"""Import resolver: extract imports via tree-sitter and resolve to graph nodes."""

# beadloom:domain=graph

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import TYPE_CHECKING

from tree_sitter import Parser

from beadloom.context_oracle.code_indexer import get_lang_config

if TYPE_CHECKING:
    import sqlite3
    from pathlib import Path

    from tree_sitter import Node as TSNode


# Rust built-in crates to skip.
_RUST_BUILTIN_CRATES: frozenset[str] = frozenset({"std", "core", "alloc"})

# Well-known TS/JS path aliases mapped to directory names.
_TS_ALIAS_MAP: dict[str, str] = {
    "@/": "src/",
    "~/": "src/",
}

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


# Kotlin standard-library package prefixes to skip.
_KOTLIN_STDLIB_PREFIXES: tuple[str, ...] = ("kotlin.", "kotlinx.", "java.", "javax.", "android.")


def _extract_kotlin_imports(root: TSNode, file_path: str) -> list[ImportInfo]:
    """Extract imports from a Kotlin AST root node."""
    results: list[ImportInfo] = []
    for child in root.children:
        if child.type == "import":
            # Find the qualified_identifier (dotted path)
            for sub in child.children:
                if sub.type == "qualified_identifier":
                    path = sub.text.decode("utf-8") if sub.text else ""
                    if path and not any(path.startswith(p) for p in _KOTLIN_STDLIB_PREFIXES):
                        results.append(
                            ImportInfo(
                                file_path=file_path,
                                line_number=child.start_point.row + 1,
                                import_path=path,
                                resolved_ref_id=None,
                            )
                        )
                    break
    return results


# Java standard-library package prefixes to skip.
_JAVA_STDLIB_PREFIXES: tuple[str, ...] = ("java.", "javax.", "android.", "sun.", "com.sun.")


def _extract_java_imports(root: TSNode, file_path: str) -> list[ImportInfo]:
    """Extract imports from Java files."""
    results: list[ImportInfo] = []
    for child in root.children:
        if child.type != "import_declaration":
            continue

        # Find the scoped_identifier or identifier child for the import path.
        path: str | None = None
        is_wildcard = False
        for sub in child.children:
            if sub.type in ("scoped_identifier", "identifier"):
                path = sub.text.decode("utf-8") if sub.text else ""
            elif sub.type == "asterisk":
                is_wildcard = True

        if not path:
            continue

        # For wildcard imports, append .* to the path.
        if is_wildcard:
            path = f"{path}.*"

        # Skip standard library imports.
        if any(path.startswith(p) for p in _JAVA_STDLIB_PREFIXES):
            continue

        results.append(
            ImportInfo(
                file_path=file_path,
                line_number=child.start_point.row + 1,
                import_path=path,
                resolved_ref_id=None,
            )
        )
    return results


# Apple/system frameworks to skip for Swift imports.
_SWIFT_STDLIB_MODULES: frozenset[str] = frozenset(
    {
        "Foundation",
        "UIKit",
        "SwiftUI",
        "Combine",
        "CoreData",
        "CoreGraphics",
        "MapKit",
        "AVFoundation",
        "CoreLocation",
        "CoreImage",
        "CoreText",
        "CoreAnimation",
        "CoreML",
        "ARKit",
        "RealityKit",
        "SceneKit",
        "SpriteKit",
        "GameplayKit",
        "Metal",
        "MetalKit",
        "Vision",
        "NaturalLanguage",
        "CloudKit",
        "StoreKit",
        "WidgetKit",
        "AppKit",
        "WatchKit",
        "Accessibility",
        "Swift",
        "os",
        "Darwin",
        "Dispatch",
        "ObjectiveC",
        "XCTest",
    }
)


def _extract_swift_imports(root: TSNode, file_path: str) -> list[ImportInfo]:
    """Extract imports from a Swift AST root node."""
    results: list[ImportInfo] = []
    for child in root.children:
        if child.type != "import_declaration":
            continue

        # Find the identifier child (contains the module path).
        for sub in child.children:
            if sub.type == "identifier":
                path = sub.text.decode("utf-8") if sub.text else ""
                if not path:
                    break

                # Determine root module name (before first dot).
                root_module = path.split(".")[0] if "." in path else path

                # Skip Apple/system frameworks.
                if root_module in _SWIFT_STDLIB_MODULES:
                    break

                results.append(
                    ImportInfo(
                        file_path=file_path,
                        line_number=child.start_point.row + 1,
                        import_path=path,
                        resolved_ref_id=None,
                    )
                )
                break
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
    if ext in (".kt", ".kts"):
        return _extract_kotlin_imports(root, file_str)
    if ext == ".java":
        return _extract_java_imports(root, file_str)
    if ext == ".swift":
        return _extract_swift_imports(root, file_str)

    return []


def _import_path_to_file_paths(
    import_path: str,
    scan_paths: list[str] | None = None,
) -> list[str]:
    """Convert a Python dotted import path to possible file paths.

    Uses *scan_paths* as directory prefixes.  Always includes the bare
    (no-prefix) variant for packages installed at root level.

    E.g. with ``scan_paths=["src"]`` and ``beadloom.auth.tokens``::

        src/beadloom/auth/tokens.py
        src/beadloom/auth/tokens/__init__.py
        beadloom/auth/tokens.py
        beadloom/auth/tokens/__init__.py
    """
    parts = import_path.replace(".", "/")
    prefixes = [f"{p}/" for p in (scan_paths or ["src", "lib", "app"])]
    prefixes.append("")  # bare path (no prefix)
    candidates: list[str] = []
    for prefix in prefixes:
        candidates.append(f"{prefix}{parts}.py")
        candidates.append(f"{prefix}{parts}/__init__.py")
    return candidates


def _normalize_ts_import(import_path: str) -> str | None:
    """Normalize a TS/JS import path, resolving known aliases.

    Returns the normalized path (e.g. ``src/shared/utils``) or *None*
    if the import is an npm package (not resolvable to a local node).
    """
    for alias, replacement in _TS_ALIAS_MAP.items():
        if import_path.startswith(alias):
            return replacement + import_path[len(alias) :]
    # Non-aliased, non-relative imports are npm packages — skip.
    return None


def _find_node_by_source_prefix(
    dir_path: str,
    scan_paths: list[str],
    conn: sqlite3.Connection,
) -> str | None:
    """Find the graph node whose ``source`` directory contains *dir_path*.

    Walks up the path hierarchy to find the deepest (most specific) node.
    Handles both ``source`` values with and without trailing slashes.
    """
    prefixes = [f"{p}/" for p in scan_paths]
    prefixes.append("")  # bare path

    for prefix in prefixes:
        candidate = f"{prefix}{dir_path}"
        parts = candidate.split("/")
        # Walk from deepest to shallowest.
        for i in range(len(parts), 0, -1):
            segment = "/".join(parts[:i])
            # Try with and without trailing slash.
            for source in (f"{segment}/", segment):
                row = conn.execute(
                    "SELECT ref_id FROM nodes WHERE source = ?",
                    (source,),
                ).fetchone()
                if row is not None:
                    return str(row[0])
    return None


def _find_node_for_file(
    rel_path: str,
    conn: sqlite3.Connection,
) -> str | None:
    """Find the graph node that *owns* a file by its relative path.

    Walks up the directory hierarchy, matching against ``nodes.source``.
    """
    parts = rel_path.split("/")
    # Skip the filename itself — start from its parent directory.
    for i in range(len(parts) - 1, 0, -1):
        segment = "/".join(parts[:i])
        for source in (f"{segment}/", segment):
            row = conn.execute(
                "SELECT ref_id FROM nodes WHERE source = ?",
                (source,),
            ).fetchone()
            if row is not None:
                return str(row[0])
    return None


def resolve_import_to_node(
    import_path: str,
    file_path: Path,
    conn: sqlite3.Connection,
    scan_paths: list[str] | None = None,
    *,
    is_ts: bool = False,
) -> str | None:
    """Map an import path to a graph node ref_id.

    Strategy (in order):
    1. Code-symbols annotation lookup (``# beadloom:domain=X``).
    2. Hierarchical source-prefix matching against ``nodes.source``.

    Returns ``None`` if no mapping found.
    """
    effective_scan = scan_paths or ["src", "lib", "app"]

    # Strategy 1: code_symbols annotation match.
    possible_files = _import_path_to_file_paths(import_path, scan_paths)

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

    # Strategy 2: hierarchical source-prefix matching.
    if is_ts:
        normalized = _normalize_ts_import(import_path)
        if normalized is None:
            return None  # npm package — not resolvable
        dir_path = normalized
    else:
        dir_path = import_path.replace(".", "/")

    return _find_node_by_source_prefix(dir_path, effective_scan, conn)


def _collect_source_files(project_root: Path) -> list[Path]:
    """Collect all supported source files from configured scan directories."""
    from beadloom.context_oracle.code_indexer import supported_extensions
    from beadloom.infrastructure.reindex import resolve_scan_paths

    exts = supported_extensions()
    files: list[Path] = []

    for dir_name in resolve_scan_paths(project_root):
        base = project_root / dir_name
        if not base.is_dir():
            continue
        for ext in exts:
            files.extend(base.rglob(f"*{ext}"))

    return sorted(files)


def create_import_edges(conn: sqlite3.Connection) -> int:
    """Create ``depends_on`` edges from resolved code imports.

    For each resolved import, finds the importing file's owning node
    and creates a ``depends_on`` edge to the target node (if different).

    Returns the number of edges created.
    """
    rows = conn.execute(
        "SELECT DISTINCT file_path, resolved_ref_id "
        "FROM code_imports WHERE resolved_ref_id IS NOT NULL"
    ).fetchall()

    edges_created = 0
    seen: set[tuple[str, str]] = set()

    for row in rows:
        rel_path: str = row[0]
        target_ref_id: str = row[1]

        source_ref_id = _find_node_for_file(rel_path, conn)
        if not source_ref_id or source_ref_id == target_ref_id:
            continue

        edge_key = (source_ref_id, target_ref_id)
        if edge_key in seen:
            continue
        seen.add(edge_key)

        conn.execute(
            "INSERT OR IGNORE INTO edges (src_ref_id, dst_ref_id, kind) "
            "VALUES (?, ?, 'depends_on')",
            (source_ref_id, target_ref_id),
        )
        edges_created += 1

    conn.commit()
    return edges_created


def index_imports(project_root: Path, conn: sqlite3.Connection) -> int:
    """Scan all source files and index their imports into the code_imports table.

    Scans directories listed in ``scan_paths`` from config.yml.
    After indexing, creates ``depends_on`` edges from resolved imports.
    Returns the count of imports indexed.
    """
    from beadloom.infrastructure.reindex import resolve_scan_paths

    scan_paths = resolve_scan_paths(project_root)
    source_files = _collect_source_files(project_root)
    total = 0

    ts_extensions = frozenset({".ts", ".tsx", ".js", ".jsx", ".vue"})

    for file_path in source_files:
        imports = extract_imports(file_path)
        if not imports:
            continue

        try:
            content = file_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue

        file_hash = hashlib.sha256(content.encode()).hexdigest()
        rel_path = str(file_path.relative_to(project_root))
        is_ts = file_path.suffix in ts_extensions

        for imp in imports:
            resolved = resolve_import_to_node(
                imp.import_path,
                file_path,
                conn,
                scan_paths=scan_paths,
                is_ts=is_ts,
            )
            conn.execute(
                "INSERT INTO code_imports"
                " (file_path, line_number, import_path, resolved_ref_id, file_hash)"
                " VALUES (?, ?, ?, ?, ?)"
                " ON CONFLICT(file_path, line_number, import_path)"
                " DO UPDATE SET resolved_ref_id = excluded.resolved_ref_id,"
                " file_hash = excluded.file_hash",
                (rel_path, imp.line_number, imp.import_path, resolved, file_hash),
            )
            total += 1

    conn.commit()

    # Create depends_on edges from resolved imports.
    create_import_edges(conn)

    return total
