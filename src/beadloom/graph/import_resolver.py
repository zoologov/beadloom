"""Import resolver: extract imports via tree-sitter and resolve to graph nodes."""

# beadloom:domain=graph
# beadloom:feature=import-resolver

from __future__ import annotations

import hashlib
import json
import posixpath
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING

from tree_sitter import Parser

from beadloom.context_oracle.code_indexer import get_lang_config, script_blocks
from beadloom.graph.go_modules import GoModules
from beadloom.graph.import_manifests import record_manifests
from beadloom.graph.js_specifiers import (
    aliased_targets,
    is_relative_specifier,
    module_file_candidates,
    relative_import_candidates,
)
from beadloom.graph.jvm_packages import JVM_EXTENSIONS, JvmPackages, read_jvm_packages
from beadloom.graph.rules.layers import part_of_ancestors
from beadloom.graph.swift_packages import SwiftPackages
from beadloom.graph.tsconfig_paths import TsConfigs
from beadloom.infrastructure.repository import get_owning_ref_id
from beadloom.infrastructure.scan_paths import resolve_scan_paths

if TYPE_CHECKING:
    import sqlite3
    from collections.abc import Collection, Iterator, Sequence
    from pathlib import Path

    from tree_sitter import Node as TSNode


# Rust built-in crates to skip.
_RUST_BUILTIN_CRATES: frozenset[str] = frozenset({"std", "core", "alloc"})

# Well-known TS/JS path aliases mapped to directory names. The LAST reading of a
# non-relative specifier: what a project's tsconfig `paths`/`baseUrl` and its
# `imports.aliases:` map it to is tried first, and only a specifier none of them
# names an existing file for is read through this table (BDL-080 `beadloom-cwzc`).
_TS_ALIAS_MAP: dict[str, str] = {
    "@/": "src/",
    "~/": "src/",
}

# Every Go import is recorded, the standard library's too: which path names the
# standard library is the resolver's answer, because ``resolve_go_import`` maps
# only the modules the project holds. A path with no '/' is not always the
# standard library — ``module tidewater`` is imported as ``"tidewater"`` — and
# the extractor, which reads no ``go.mod``, cannot tell (``beadloom-jcng``).


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


def _walk(root: TSNode) -> Iterator[TSNode]:
    """Yield every node in the tree, pre-order (the root's descendants).

    Extraction used to consider only ``root.children`` — the file's TOP-LEVEL
    statements — so an import inside a function, a class body, an
    ``if TYPE_CHECKING:`` guard or a ``try:`` block was invisible to the
    dependency graph. Those are precisely the places an import is put to defer
    cost or to break a cycle, so the graph was blind to the very edges the
    cycle and boundary rules exist to judge (BDL-UX #159). Measured on this
    repo when the walk was introduced: 460 nested imports, 231 of them
    first-party — about a third of all imports.

    Statement types the extractors match do not nest inside themselves, so a
    full walk cannot double-count a single statement.
    """
    # Document order (pre-order): imports must be reported in the order they
    # appear, so line numbers read naturally and extraction is deterministic.
    stack = list(reversed(root.children))
    while stack:
        node = stack.pop()
        yield node
        stack.extend(reversed(node.children))


def _extract_python_imports(root: TSNode, file_path: str) -> list[ImportInfo]:
    """Extract imports from a Python AST root node."""
    results: list[ImportInfo] = []

    for child in _walk(root):
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


#: The delimiter tokens of a JS string or template string, which carry no text.
_QUOTE_TOKENS = frozenset({"'", '"', "`"})


def _dynamic_import_source(node: TSNode) -> str | None:
    """The specifier of ``import('...')`` when it is a literal, else ``None``.

    A dynamic import is a ``call_expression`` whose callee is the ``import``
    keyword, not an ``import_statement``, so the statement match never saw it
    and a lazily loaded module was invisible to the graph (BDL-076 J2). Only a
    literal names a module: a string, or a template string with no ``${...}``.
    A computed specifier (``import(name)``, ``import('./' + a)``) names nothing
    this reader can know, and yields ``None``.
    """
    if node.type != "call_expression" or not node.children:
        return None
    if node.children[0].type != "import":
        return None
    arguments = node.child_by_field_name("arguments")
    specifier = arguments.named_children[0] if arguments and arguments.named_children else None
    if specifier is None or specifier.type not in ("string", "template_string"):
        return None
    parts = [sub for sub in specifier.children if sub.type not in _QUOTE_TOKENS]
    if not parts or any(sub.type != "string_fragment" for sub in parts):
        return None
    return "".join(sub.text.decode("utf-8") for sub in parts if sub.text)


def _extract_ts_imports(root: TSNode, file_path: str) -> list[ImportInfo]:
    """Extract imports from a TypeScript/JavaScript AST root node.

    A re-export (``export { X } from './x'``, ``export * from '../y'``) names a
    module the same way an import does, and it is how an ``index.js`` facade
    exposes its folder, so it is read too. An ``export`` without a ``from`` has
    no source string among its direct children and yields nothing. A dynamic
    ``import('...')`` with a literal specifier is read as well
    (:func:`_dynamic_import_source`).

    Relative specifiers are kept as written. They used to be skipped here, so a
    JS/TS project got no ``depends_on`` edge between its own modules (BDL-076
    J1, measured by A0); :func:`resolve_relative_import` now maps them to files.
    """
    results: list[ImportInfo] = []

    for child in _walk(root):
        if child.type in ("import_statement", "export_statement"):
            source = _get_ts_import_source(child)
        elif child.type == "call_expression":
            source = _dynamic_import_source(child)
        else:
            continue
        if source is None:
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
    """Extract a single Go import spec, returning None for an empty path."""
    # Find the interpreted_string_literal
    for child in spec.children:
        if child.type == "interpreted_string_literal":
            # Get the content (without quotes)
            for sub in child.children:
                if sub.type == "interpreted_string_literal_content":
                    path = sub.text.decode("utf-8") if sub.text else ""
                    if not path:
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

    for child in _walk(root):
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

    for child in _walk(root):
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
    for child in _walk(root):
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
    for child in _walk(root):
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
    for child in _walk(root):
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


# C/C++ standard and system headers to skip.
_C_SYSTEM_HEADERS: frozenset[str] = frozenset(
    {
        # C standard headers
        "stdio.h",
        "stdlib.h",
        "string.h",
        "math.h",
        "assert.h",
        "ctype.h",
        "errno.h",
        "float.h",
        "limits.h",
        "locale.h",
        "setjmp.h",
        "signal.h",
        "stdarg.h",
        "stddef.h",
        "time.h",
        "stdint.h",
        "stdbool.h",
        "inttypes.h",
        "complex.h",
        "fenv.h",
        "iso646.h",
        "tgmath.h",
        "wchar.h",
        "wctype.h",
        # C++ standard headers
        "iostream",
        "string",
        "vector",
        "map",
        "set",
        "algorithm",
        "memory",
        "functional",
        "utility",
        "numeric",
        "iterator",
        "fstream",
        "sstream",
        "iomanip",
        "cstdlib",
        "cstdio",
        "cstring",
        "cmath",
        "cassert",
        "climits",
        "cstdint",
        "array",
        "deque",
        "list",
        "queue",
        "stack",
        "unordered_map",
        "unordered_set",
        "tuple",
        "bitset",
        "chrono",
        "thread",
        "mutex",
        "condition_variable",
        "atomic",
        "future",
        "type_traits",
        "stdexcept",
        "exception",
        "new",
        "typeinfo",
        "initializer_list",
        "optional",
        "variant",
        "any",
        "filesystem",
        "regex",
        "random",
        "ratio",
        "complex",
    }
)


def _extract_c_cpp_imports(root: TSNode, file_path: str) -> list[ImportInfo]:
    """Extract ``#include`` directives from C/C++ files.

    Skips well-known C/C++ standard library headers.
    """
    results: list[ImportInfo] = []
    for node in _walk(root):
        if node.type != "preproc_include":
            continue
        path_node = node.child_by_field_name("path")
        if path_node is None:
            continue
        raw = path_node.text.decode("utf-8") if path_node.text else ""
        # Strip surrounding quotes or angle brackets.
        raw = raw.strip('"<>')
        if not raw:
            continue
        if raw in _C_SYSTEM_HEADERS:
            continue
        results.append(
            ImportInfo(
                file_path=file_path,
                line_number=node.start_point.row + 1,
                import_path=raw,
                resolved_ref_id=None,
            )
        )
    return results


# Apple/system frameworks to skip for Objective-C imports.
_OBJC_SYSTEM_FRAMEWORKS: frozenset[str] = frozenset(
    {
        "Foundation",
        "UIKit",
        "AppKit",
        "CoreData",
        "CoreGraphics",
        "CoreFoundation",
        "CoreLocation",
        "CoreBluetooth",
        "CoreMedia",
        "CoreText",
        "CoreImage",
        "CoreAnimation",
        "CoreML",
        "CoreMotion",
        "CoreTelephony",
        "CoreServices",
        "MapKit",
        "MessageUI",
        "Photos",
        "QuartzCore",
        "Security",
        "StoreKit",
        "SystemConfiguration",
        "WebKit",
        "AVFoundation",
        "GameKit",
        "HealthKit",
        "HomeKit",
        "MediaPlayer",
        "Metal",
        "MetalKit",
        "MultipeerConnectivity",
        "ARKit",
        "RealityKit",
        "SceneKit",
        "SpriteKit",
        "Vision",
        "NaturalLanguage",
        "CloudKit",
        "WidgetKit",
        "WatchKit",
        "Accessibility",
        "Combine",
        "SwiftUI",
        "ObjectiveC",
        "XCTest",
    }
)


def _extract_objc_imports(root: TSNode, file_path: str) -> list[ImportInfo]:
    """Extract ``#import`` and ``@import`` directives from Objective-C files.

    Skips well-known Apple/system frameworks.
    """
    results: list[ImportInfo] = []
    for node in _walk(root):
        if node.type == "preproc_include":
            # #import <Framework/Header.h> or #import "Header.h"
            # In tree-sitter-objc, #import uses preproc_include with:
            #   - system_lib_string for angle-bracket imports
            #   - string_literal for quoted imports
            for child in node.children:
                if child.type == "system_lib_string":
                    raw = child.text.decode("utf-8") if child.text else ""
                    raw = raw.strip("<>")
                    if not raw:
                        continue
                    # Check if it's a system framework (e.g. Foundation/Foundation.h)
                    base = raw.split("/")[0] if "/" in raw else raw
                    if base in _OBJC_SYSTEM_FRAMEWORKS:
                        continue
                    results.append(
                        ImportInfo(
                            file_path=file_path,
                            line_number=node.start_point.row + 1,
                            import_path=raw,
                            resolved_ref_id=None,
                        )
                    )
                elif child.type == "string_literal":
                    # Quoted import: #import "MyHeader.h"
                    # Extract text from string_content child
                    for sub in child.children:
                        if sub.type == "string_content":
                            raw = sub.text.decode("utf-8") if sub.text else ""
                            if raw:
                                results.append(
                                    ImportInfo(
                                        file_path=file_path,
                                        line_number=node.start_point.row + 1,
                                        import_path=raw,
                                        resolved_ref_id=None,
                                    )
                                )
                            break

        elif node.type == "module_import":
            # @import Module; or @import Module.SubModule;
            # Identifiers are direct children separated by dots
            parts: list[str] = []
            for child in node.children:
                if child.type == "identifier":
                    parts.append(child.text.decode("utf-8") if child.text else "")
            if parts:
                module_name = ".".join(parts)
                root_module = parts[0]
                if root_module not in _OBJC_SYSTEM_FRAMEWORKS:
                    results.append(
                        ImportInfo(
                            file_path=file_path,
                            line_number=node.start_point.row + 1,
                            import_path=module_name,
                            resolved_ref_id=None,
                        )
                    )

    return results


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def extract_imports(file_path: Path) -> list[ImportInfo]:
    """Extract import statements from a source file using tree-sitter.

    Detects language by file extension.  Returns empty list if the language
    is not supported or the grammar package is not installed.
    """
    if file_path.suffix == _VUE_EXTENSION:
        return _extract_component_imports(file_path)

    config = get_lang_config(file_path.suffix)
    if config is None:
        return []

    content = _read_source(file_path)
    if content is None:
        return []

    root = Parser(config.language).parse(content.encode("utf-8")).root_node

    file_str = str(file_path)
    ext = file_path.suffix

    if ext == ".py":
        return _extract_python_imports(root, file_str)
    if ext in _SCRIPT_EXTENSIONS:
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
    if ext in (".m", ".mm"):
        return _extract_objc_imports(root, file_str)
    if ext in (".c", ".h", ".cpp", ".hpp"):
        return _extract_c_cpp_imports(root, file_str)

    return []


_VUE_EXTENSION = ".vue"

#: The extensions whose files are JS/TS modules read by one extractor; ``.mjs`` and
#: ``.cjs`` since BDL-080 (``beadloom-zd4m``), which the code indexer parses as JavaScript.
_SCRIPT_EXTENSIONS = frozenset({".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs"})


def _read_source(file_path: Path) -> str | None:
    """A source file's text, or ``None`` when it is unreadable or blank."""
    try:
        content = file_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None
    return content if content.strip() else None


def _extract_component_imports(file_path: Path) -> list[ImportInfo]:
    """The imports of a Vue single-file component, at their lines in the ``.vue`` file.

    Each ``<script>``/``<script setup>`` block is parsed by the JS/TS grammar its
    ``lang`` names and read by the JS/TS extractor; the template and the style
    are not code and are not read. The blocks come from the same finder the
    symbol indexer uses (``script_blocks``, BDL-076 J3), so the two readers
    cannot disagree on where a component's code is. Until BDL-076 J2 a
    component yielded no import at all, and ``why`` on a composable a component
    imported reported no dependents.
    """
    content = _read_source(file_path)
    if content is None:
        return []
    results: list[ImportInfo] = []
    for block in script_blocks(content):
        config = get_lang_config(block.extension)
        if config is None:
            continue
        root = Parser(config.language).parse(block.text.encode("utf-8")).root_node
        results.extend(
            replace(imp, line_number=block.file_line(imp.line_number - 1))
            for imp in _extract_ts_imports(root, str(file_path))
        )
    return results


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


def _first_existing(candidates: Sequence[str], project_root: Path) -> str | None:
    """The first of *candidates* that is a file under *project_root*, or ``None``."""
    for candidate in candidates:
        if (project_root / candidate).is_file():
            return candidate
    return None


def _mapped_file(tree: _ImportTree, importer: str, specifier: str) -> str | None:
    """The file a non-relative JS/TS *specifier* names through what the project declares.

    Read in the order a project's own tooling reads it (BDL-080 ``beadloom-cwzc``): the
    ``paths`` of the tsconfig governing *importer*, then the aliases declared under
    ``imports.aliases:`` (the ones Babel ``module-resolver`` or Vite ``resolve.alias``
    apply and no tsconfig carries), then ``baseUrl``. ``None`` when no declaration maps
    the specifier to an existing file; the caller then reads it as it did before any
    declaration was read.
    """
    for targets in (
        tree.ts_configs.mapped(specifier, importer),
        aliased_targets(specifier, tree.aliases),
        tree.ts_configs.under_base_url(specifier, importer),
    ):
        for target in targets:
            found = _first_existing(module_file_candidates(target), tree.project_root)
            if found is not None:
                return found
    return None


def resolve_relative_import(
    specifier: str,
    importer: str,
    project_root: Path,
    conn: sqlite3.Connection,
) -> str | None:
    """Map a relative JS/TS *specifier* to the node that owns the file it names.

    The first candidate of :func:`relative_import_candidates` that exists on
    disk is the file; its owner is decided by the one ownership rule
    (``get_owning_ref_id``, most specific source wins) — the rule the importing
    side of an edge is attributed by. Returns ``None`` when the specifier names
    no file, or names a file no node owns; the caller records either as an
    unresolved import rather than dropping it.
    """
    found = _first_existing(relative_import_candidates(specifier, importer), project_root)
    return get_owning_ref_id(conn, found) if found is not None else None


def _find_node_by_source_prefix(
    dir_path: str,
    scan_paths: list[str],
    conn: sqlite3.Connection,
) -> str | None:
    """Find the graph node whose ``source`` directory contains *dir_path*.

    Walks up the path hierarchy to find the deepest (most specific) node.
    Handles both ``source`` values with and without trailing slashes.

    The walk under a scan path stops BELOW that scan path's root: neither the
    root nor anything above it is tried. A0 (BDL-076) measured what happened
    otherwise: with ``site/.vitepress/theme`` as a scan path, every Python
    import no file answered (``typing``, ``pathlib`` …, 1,318 of them) walked
    up to ``site/`` and became one of 103 false edges into the node owning it.
    A node whose source IS a scan root would catch every such import the same
    way. The bare (no-prefix) reading keeps its walk to the first segment.
    """
    roots = [p.strip("/") for p in scan_paths]
    roots.append("")  # bare path

    for root in roots:
        candidate = f"{root}/{dir_path}" if root else dir_path
        parts = candidate.split("/")
        floor = len(root.split("/")) if root else 0
        # Walk from deepest to shallowest, never reaching the scan root.
        for i in range(len(parts), floor, -1):
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

    Delegates to the single ownership rule in ``infrastructure/repository``
    (most specific source wins). This previously walked up from the file's
    PARENT directory, so a node whose source IS a file never owned that file —
    its imports were attributed to the enclosing directory's node instead.
    """
    return get_owning_ref_id(conn, rel_path)


def resolve_import_to_node(
    import_path: str,
    file_path: Path,
    conn: sqlite3.Connection,
    scan_paths: list[str] | None = None,
    *,
    source_files: Collection[str],
    is_ts: bool = False,
) -> str | None:
    """Map an import path to a graph node ref_id.

    Strategy (in order):
    1. Ownership of the imported FILE — the most specific node whose source
       covers it. This is the same rule the importing side uses, so an edge
       always connects the two nodes that actually own the two files. A
       candidate is the imported file only when it is one of *source_files*,
       the project-relative POSIX paths of the source files in the tree.
    2. Code-symbols annotation lookup (``# beadloom:domain=X``).
    3. Hierarchical source-prefix matching against ``nodes.source``.

    Strategy 1 exists because 3 resolves a dotted path to an EXTENSION-LESS
    directory path, which can never match a node whose source is a file — so
    every import used to land on the nearest enclosing directory node, silently
    collapsing feature/component dependencies into their domain (BDL-UX #144).

    Whether a candidate exists is read from *source_files* and from no table of
    the index (``beadloom-nh7h``). It used to be read from ``code_symbols`` or
    ``file_index``: a module of re-exports holds no symbol, and a full reindex
    fills ``file_index`` only after it resolves the imports, so a fresh index
    resolved ``tui``'s import of ``graph_reads`` to ``application`` and a second
    reindex of the same tree to ``graph-reads``.

    Returns ``None`` if no mapping found.
    """
    effective_scan = scan_paths or ["src", "lib", "app"]

    possible_files = _import_path_to_file_paths(import_path, scan_paths)

    # Strategy 1: the node that owns the imported file.
    for candidate in possible_files:
        if candidate not in source_files:
            continue
        owner = get_owning_ref_id(conn, candidate)
        if owner is not None:
            return owner

    # Strategy 2: code_symbols annotation match.
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

    # Strategy 3: hierarchical source-prefix matching.
    if is_ts:
        normalized = _normalize_ts_import(import_path)
        if normalized is None:
            return None  # npm package — not resolvable
        dir_path = normalized
    else:
        dir_path = import_path.replace(".", "/")

    return _find_node_by_source_prefix(dir_path, effective_scan, conn)


#: The extension of a Go source file, and the suffix of a Go test file.
_GO_EXTENSION = ".go"
_GO_TEST_SUFFIX = "_test.go"


def resolve_go_import(
    import_path: str,
    importer: str,
    project_root: Path,
    conn: sqlite3.Connection,
    modules: GoModules,
) -> str | None:
    """Map a Go *import_path* to the node that owns the package it names (BDL-076 B5).

    *importer* is the importing file's project-relative POSIX path. The package's
    directory comes from the project's Go modules (:mod:`.go_modules`: the module
    path stripped, the rest read under that module's ``go.mod``); its owner is
    decided by the one ownership rule, applied to the package's first non-test
    ``.go`` file in name order, so a node sourced at a directory or at a file of
    the package are both found. ``None`` for the standard library, a module the
    project does not hold, and a package directory that holds no Go file.

    Go imports never go through :func:`resolve_import_to_node`: its dotted-path
    reading turned ``net/http`` into a node whose source is ``net/``.
    """
    directory = modules.package_directory(import_path, importer)
    if directory is None:
        return None
    package = project_root / directory
    if not package.is_dir():
        return None
    files = sorted(p.name for p in package.glob(f"*{_GO_EXTENSION}") if p.is_file())
    if not files:
        return None
    primary = next((name for name in files if not name.endswith(_GO_TEST_SUFFIX)), files[0])
    return get_owning_ref_id(conn, posixpath.join(directory, primary))


#: The extension of a Swift source file.
_SWIFT_EXTENSION = ".swift"


def _swift_module(import_path: str) -> str:
    """The module a Swift import names: ``import Core.Route`` names ``Core``."""
    return import_path.split(".", 1)[0]


def resolve_swift_import(
    import_path: str,
    importer: str,
    project_root: Path,
    conn: sqlite3.Connection,
    packages: SwiftPackages,
) -> str | None:
    """Map a Swift *import_path* to the node that owns the target it names (BDL-076 B7).

    *importer* is the importing file's project-relative POSIX path. The target's
    folder comes from the project's manifests (:mod:`.swift_packages`: the target
    of that name in the importer's own package, else the one other package that
    declares it); its owner is decided by the one ownership rule, applied to the
    folder itself, so a node sourced at the target folder or above it is found.
    ``None`` for an Apple framework, a product of a package the project does not
    hold, a target with no Swift source and a folder that does not exist.

    The caller reads an import here only when some manifest declares its module;
    a project with no ``Package.swift`` keeps the dotted-path reading of
    :func:`resolve_import_to_node`, which finds a module folder under a scan path.
    """
    directory = packages.module_directory(import_path, importer)
    if directory is None or not (project_root / directory).is_dir():
        return None
    return get_owning_ref_id(conn, f"{directory}/")


def resolve_jvm_import(
    import_path: str,
    file_path: Path,
    conn: sqlite3.Connection,
    scan_paths: list[str],
    packages: JvmPackages,
    *,
    source_files: Collection[str],
) -> str | None:
    """Map a Java or Kotlin *import_path* to the node that owns the package it names.

    The package is the one the project's files DECLARE (:mod:`.jvm_packages`, R2
    finding 6), and its owner is decided by the one ownership rule, applied to
    the package's folder. Kotlin's recommended layout omits the common root
    package from the folders, so the dotted path names no folder there; it is
    still the reading for an import whose package no file declares, which keeps
    every import that resolved before resolving the same way.

    Where several folders declare the package, the import reaches those holding
    the class it names, else all of them, and it resolves only when one node owns
    every folder it reaches: never to a folder picked by the order it was read in
    (the re-review's finding m5).
    """
    if packages.package(import_path) is None:
        return resolve_import_to_node(
            import_path, file_path, conn, scan_paths=scan_paths, source_files=source_files
        )
    owners = {get_owning_ref_id(conn, f"{folder}/") for folder in packages.folders(import_path)}
    return owners.pop() if len(owners) == 1 else None


#: Extensions whose files write their imports in one language, mapped to one
#: representative extension of it. An extension not listed is its own language.
_IMPORT_LANGUAGE: dict[str, str] = {
    ".tsx": ".ts",
    ".js": ".ts",
    ".jsx": ".ts",
    ".mjs": ".ts",
    ".cjs": ".ts",
    ".vue": ".ts",
    ".kts": ".kt",
    # Java and Kotlin share the JVM's one package namespace: a Kotlin file imports
    # a Java class by its package and the other way round, and Gradle keeps the
    # two in separate roots (`src/main/java`, `src/main/kotlin`) of one module
    # (BDL-076 B6).
    ".java": ".kt",
    ".mm": ".m",
    ".h": ".c",
    ".cpp": ".c",
    ".hpp": ".c",
}


def _import_language(extension: str) -> str:
    """The language an *extension*'s files write their imports in."""
    return _IMPORT_LANGUAGE.get(extension, extension)


def scan_path_languages(
    project_root: Path, scan_paths: Sequence[str], files: Sequence[Path]
) -> dict[str, frozenset[str]]:
    """The import languages each scan path holds files of, keyed by the scan path as given."""
    return {
        scan_path: frozenset(
            _import_language(path.suffix)
            for path in files
            if path.is_relative_to(project_root / scan_path)
        )
        for scan_path in scan_paths
    }


def _scan_paths_for(
    extension: str, scan_paths: list[str], languages: dict[str, frozenset[str]]
) -> list[str]:
    """The scan paths an import written in *extension*'s language is read through.

    A Python import is never prefixed with a scan path that holds no Python, nor
    a JS/TS one with a Python-only path: a module of one language cannot live
    under a folder that holds none of that language (BDL-076 J2). An importer
    whose language no scan path holds — a file outside every scan path — keeps
    the full list, which is how it was read before.
    """
    language = _import_language(extension)
    own = [path for path in scan_paths if language in languages.get(path, frozenset())]
    return own or scan_paths


def _collect_source_files(project_root: Path) -> list[Path]:
    """Collect all supported source files from configured scan directories."""
    from beadloom.context_oracle.code_indexer import supported_extensions

    exts = supported_extensions()
    files: list[Path] = []

    for dir_name in resolve_scan_paths(project_root):
        base = project_root / dir_name
        if not base.is_dir():
            continue
        for ext in exts:
            files.extend(base.rglob(f"*{ext}"))

    return sorted(files)


def _part_of_ancestors(conn: sqlite3.Connection) -> dict[str, set[str]]:
    """Map each node to the set of nodes it is (transitively) ``part_of``.

    This body reads the direct ``part_of`` edges; the climb is
    :func:`beadloom.graph.rules.layers.part_of_ancestors`, which is the ONE
    ancestry walk in the codebase (BDL-070 A1). It used to be two — this one and
    the rule engine's — and the epic that unified them exists because three
    bodies answering "what layer is this node in" gave three answers.
    """
    parents: dict[str, set[str]] = {}
    for row in conn.execute(
        "SELECT src_ref_id, dst_ref_id FROM edges WHERE kind = 'part_of'"
    ).fetchall():
        child, parent = str(row[0]), str(row[1])
        if child != parent:  # the root service is part_of itself by convention
            parents.setdefault(child, set()).add(parent)

    return {child: set(part_of_ancestors(child, parents)) for child in parents}


# Provenance marker written into the ``extra`` column of every ``depends_on``
# edge DERIVED from a code import. Edges declared in the graph YAML carry their
# own extra and are never marked, which is what lets an incremental refresh
# delete the derived set without touching a declared edge. ``INSERT OR IGNORE``
# means a pair declared in YAML keeps the YAML row (and stays unmarked).
_DERIVED_BY_IMPORTS = "imports"
_DERIVED_EDGE_EXTRA = json.dumps({"derived": _DERIVED_BY_IMPORTS}, ensure_ascii=False)


def delete_derived_import_edges(conn: sqlite3.Connection) -> int:
    """Delete the ``depends_on`` edges derived from code imports.

    Returns the number of rows deleted. Edges without the provenance marker —
    i.e. declared in the graph YAML — are left alone.
    """
    cursor = conn.execute(
        "DELETE FROM edges WHERE kind = 'depends_on' "
        "AND json_extract(extra, '$.derived') = ?",
        (_DERIVED_BY_IMPORTS,),
    )
    return int(cursor.rowcount or 0)


def refresh_import_edges(conn: sqlite3.Connection) -> int:
    """Rebuild the derived ``depends_on`` edge set from ``code_imports``.

    The derived edges are a pure function of the ``code_imports`` table, so a
    refresh is delete-then-recreate. Doing only the recreate half is how a
    removed import kept a dependency edge alive for the cycle and layer rules
    to trip over (the mirror image of BDL-UX #142).
    """
    delete_derived_import_edges(conn)
    return create_import_edges(conn)


def create_import_edges(conn: sqlite3.Connection) -> int:
    """Create ``depends_on`` edges from resolved code imports.

    For each resolved import, finds the importing file's owning node
    and creates a ``depends_on`` edge to the target node (if different).

    Containment is skipped in ONE direction only. A node does not "depend on"
    its own parts: a package facade re-exporting its children says nothing the
    ``part_of`` edge did not, and paired with a child's ordinary upward import
    it manufactures a node-level cycle with no module-level counterpart
    (BDL-UX #144).

    The reverse is kept. A child reaching into shared code that lives in its
    container but belongs to no other node is a REAL dependency; dropping it
    made such a node report "depends on nothing", which is false — and a
    confidently wrong answer is worse than a coarse one.

    Returns the number of edges created.
    """
    rows = conn.execute(
        "SELECT DISTINCT file_path, resolved_ref_id "
        "FROM code_imports WHERE resolved_ref_id IS NOT NULL"
    ).fetchall()

    ancestors = _part_of_ancestors(conn)
    edges_created = 0
    seen: set[tuple[str, str]] = set()

    for row in rows:
        rel_path: str = row[0]
        target_ref_id: str = row[1]

        source_ref_id = _find_node_for_file(rel_path, conn)
        if not source_ref_id or source_ref_id == target_ref_id:
            continue
        # Drop only parent -> child (the container depending on its own part).
        if source_ref_id in ancestors.get(target_ref_id, ()):
            continue

        edge_key = (source_ref_id, target_ref_id)
        if edge_key in seen:
            continue
        seen.add(edge_key)

        conn.execute(
            "INSERT OR IGNORE INTO edges (src_ref_id, dst_ref_id, kind, extra) "
            "VALUES (?, ?, 'depends_on', ?)",
            (source_ref_id, target_ref_id, _DERIVED_EDGE_EXTRA),
        )
        edges_created += 1

    conn.commit()
    return edges_created


_TS_EXTENSIONS = frozenset({*_SCRIPT_EXTENSIONS, _VUE_EXTENSION})


@dataclass(frozen=True)
class _ImportTree:
    """What every import of one indexing run is resolved against: the tree as it is now.

    An answer is a function of this and of the graph's nodes, and of nothing an
    earlier run left in the index (``beadloom-nh7h``). *source_files* are the
    project-relative POSIX paths of the source files under the scan paths; the
    manifest readers each read their files once, on first use. *aliases* are the
    ``(alias, folder)`` pairs the project declares under ``imports.aliases:``, read
    by the caller, because the graph domain does not read that block itself.
    """

    project_root: Path
    scan_paths: list[str]
    languages: dict[str, frozenset[str]]
    source_files: frozenset[str]
    go_modules: GoModules
    swift_packages: SwiftPackages
    jvm_packages: JvmPackages
    ts_configs: TsConfigs
    aliases: tuple[tuple[str, str], ...]


def _read_import_tree(
    project_root: Path, files: Sequence[Path], aliases: Sequence[tuple[str, str]]
) -> _ImportTree:
    """Read the tree one run resolves its imports against; *files* are its source files."""
    scan_paths = resolve_scan_paths(project_root)
    return _ImportTree(
        project_root=project_root,
        scan_paths=scan_paths,
        languages=scan_path_languages(project_root, scan_paths, files),
        source_files=frozenset(path.relative_to(project_root).as_posix() for path in files),
        go_modules=GoModules(project_root),
        swift_packages=SwiftPackages(project_root),
        jvm_packages=read_jvm_packages(project_root, files),
        ts_configs=TsConfigs(project_root),
        aliases=tuple(aliases),
    )


def _record_manifests(conn: sqlite3.Connection, tree: _ImportTree) -> None:
    """Record the fingerprint of every declaration *tree*'s answers were read through."""
    record_manifests(
        conn, tree.go_modules, tree.swift_packages, tree.ts_configs, tree.aliases
    )


def _resolve_import(
    tree: _ImportTree, conn: sqlite3.Connection, importer: str, import_path: str
) -> str | None:
    """Resolve one import of the file at *importer*, a project-relative path.

    The one dispatch both the extraction of a file and the re-resolution of a
    stored row go through, so the two cannot answer differently.
    """
    importer_posix = importer.replace("\\", "/")
    suffix = posixpath.splitext(importer_posix)[1]
    file_path = tree.project_root / importer_posix
    scan_paths = _scan_paths_for(suffix, tree.scan_paths, tree.languages)
    is_ts = suffix in _TS_EXTENSIONS
    if suffix == _GO_EXTENSION:
        return resolve_go_import(
            import_path, importer_posix, tree.project_root, conn, tree.go_modules
        )
    if suffix == _SWIFT_EXTENSION and tree.swift_packages.declares(_swift_module(import_path)):
        return resolve_swift_import(
            import_path, importer_posix, tree.project_root, conn, tree.swift_packages
        )
    if suffix in JVM_EXTENSIONS and tree.jvm_packages:
        return resolve_jvm_import(
            import_path,
            file_path,
            conn,
            scan_paths,
            tree.jvm_packages,
            source_files=tree.source_files,
        )
    if is_ts and is_relative_specifier(import_path):
        return resolve_relative_import(import_path, importer_posix, tree.project_root, conn)
    if is_ts:
        mapped = _mapped_file(tree, importer_posix, import_path)
        if mapped is not None:
            return get_owning_ref_id(conn, mapped)
    return resolve_import_to_node(
        import_path,
        file_path,
        conn,
        scan_paths=scan_paths,
        source_files=tree.source_files,
        is_ts=is_ts,
    )


def _index_one_file(file_path: Path, tree: _ImportTree, conn: sqlite3.Connection) -> int:
    """Index one source file's imports into ``code_imports``; return the count."""
    imports = extract_imports(file_path)
    if not imports:
        return 0

    try:
        content = file_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return 0

    file_hash = hashlib.sha256(content.encode()).hexdigest()
    rel_path = str(file_path.relative_to(tree.project_root))

    for imp in imports:
        resolved = _resolve_import(tree, conn, rel_path, imp.import_path)
        conn.execute(
            "INSERT INTO code_imports"
            " (file_path, line_number, import_path, resolved_ref_id, file_hash)"
            " VALUES (?, ?, ?, ?, ?)"
            " ON CONFLICT(file_path, line_number, import_path)"
            " DO UPDATE SET resolved_ref_id = excluded.resolved_ref_id,"
            " file_hash = excluded.file_hash",
            (rel_path, imp.line_number, imp.import_path, resolved, file_hash),
        )
    return len(imports)


def _reresolve_stored_imports(
    tree: _ImportTree, conn: sqlite3.Connection, *, skip: Collection[str]
) -> int:
    """Resolve every stored import again, except those of the files in *skip*.

    An import's answer depends on files other than its own: on whether the file
    it names exists, and on that file's annotations. An incremental run that
    re-read only the files it touched kept the answer an import got when its
    target was absent, or still present, so it disagreed with a fresh index of
    the same tree (``beadloom-nh7h``). The rows are not parsed again; each
    answer is cached per importer folder and import path, which is everything a
    dispatch reads of the importer. Returns the number of rows whose answer
    changed.
    """
    rows = conn.execute(
        "SELECT id, file_path, import_path, resolved_ref_id FROM code_imports"
    ).fetchall()
    cache: dict[tuple[str, str, str], str | None] = {}
    changed = 0
    for row_id, importer, import_path, stored in rows:
        if importer in skip:
            continue
        folder, name = posixpath.split(str(importer).replace("\\", "/"))
        key = (folder, posixpath.splitext(name)[1], str(import_path))
        if key not in cache:
            cache[key] = _resolve_import(tree, conn, str(importer), str(import_path))
        if cache[key] != stored:
            conn.execute(
                "UPDATE code_imports SET resolved_ref_id = ? WHERE id = ?", (cache[key], row_id)
            )
            changed += 1
    return changed


def index_imports(
    project_root: Path,
    conn: sqlite3.Connection,
    *,
    aliases: Sequence[tuple[str, str]] = (),
) -> int:
    """Scan all source files and index their imports into the code_imports table.

    Scans directories listed in ``scan_paths`` from config.yml.
    After indexing, creates ``depends_on`` edges from resolved imports.
    *aliases* are the ``(alias, folder)`` pairs of ``imports.aliases:``; the
    application layer reads them, with the refusals of that block.
    Returns the count of imports indexed.
    """
    files = _collect_source_files(project_root)
    tree = _read_import_tree(project_root, files, aliases)
    total = sum(_index_one_file(file_path, tree, conn) for file_path in files)
    conn.commit()
    _record_manifests(conn, tree)

    # Create depends_on edges from resolved imports.
    refresh_import_edges(conn)

    return total


def reindex_file_imports(
    project_root: Path,
    conn: sqlite3.Connection,
    *,
    touched: Sequence[str],
    removed: Sequence[str],
    aliases: Sequence[tuple[str, str]] = (),
) -> int:
    """Re-extract imports for *touched* files and forget those *removed*.

    This is the incremental counterpart of :func:`index_imports`. Without it an
    incremental reindex left ``code_imports`` — and therefore every
    ``forbid_import`` / cycle / layer rule — describing the working tree as it
    was at the last FULL rebuild, so the documented ``reindex && lint`` loop
    reported a clean boundary over a real violation (BDL-UX #142). Both lists
    are project-relative paths.

    Every other file's imports are then resolved again against the same tree,
    without parsing them, because a touched or removed file can change what an
    untouched one's import names (``beadloom-nh7h``), and so can a manifest: a
    caller that saw only a manifest change passes both lists empty
    (``beadloom-jcng``), and so can a tsconfig or a declared alias (``beadloom-cwzc``).
    The result equals a fresh index of the tree, and the fingerprint of the
    manifests it was read through is recorded. The derived
    ``depends_on`` edge set is rebuilt afterwards, so an import that disappeared
    stops being a dependency instead of lingering.

    Returns the number of imports indexed for the touched files.
    """
    for rel_path in (*touched, *removed):
        conn.execute("DELETE FROM code_imports WHERE file_path = ?", (rel_path,))

    tree = _read_import_tree(project_root, _collect_source_files(project_root), aliases)
    extensions = _supported_extensions()
    total = 0
    for rel_path in touched:
        file_path = project_root / rel_path
        if file_path.suffix not in extensions or not file_path.is_file():
            continue
        total += _index_one_file(file_path, tree, conn)
    _reresolve_stored_imports(tree, conn, skip=frozenset(touched))

    conn.commit()
    _record_manifests(conn, tree)
    refresh_import_edges(conn)
    return total


def _supported_extensions() -> frozenset[str]:
    """The source extensions the indexer can parse (lazy import, cached upstream)."""
    from beadloom.context_oracle.code_indexer import supported_extensions

    return frozenset(supported_extensions())
