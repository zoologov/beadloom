"""Code symbol indexer: tree-sitter parsing and beadloom annotation extraction."""

# beadloom:domain=context-oracle

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from tree_sitter import Language, Parser

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable
    from pathlib import Path

    from tree_sitter import Node as TSNode

# Regex for beadloom annotations in comments.
_ANNOTATION_RE = re.compile(r"beadloom:(.+)")
_KV_RE = re.compile(r"(\w+)=(\S+)")


@dataclass(frozen=True)
class LangConfig:
    """Tree-sitter configuration for a programming language."""

    language: Language
    comment_types: frozenset[str]
    symbol_types: dict[str, str]  # node_type -> kind
    wrapper_types: frozenset[str]  # types that wrap definitions (e.g. decorated_definition)


# ---- Language loaders (lazy, handle ImportError) ----


def _load_python() -> LangConfig:
    import tree_sitter_python as tspython

    return LangConfig(
        language=Language(tspython.language()),
        comment_types=frozenset({"comment"}),
        symbol_types={
            "function_definition": "function",
            "class_definition": "class",
        },
        wrapper_types=frozenset({"decorated_definition"}),
    )


def _load_typescript() -> LangConfig:
    import tree_sitter_typescript as tstypescript

    return LangConfig(
        language=Language(tstypescript.language_typescript()),
        comment_types=frozenset({"comment"}),
        symbol_types={
            "function_declaration": "function",
            "class_declaration": "class",
            "interface_declaration": "type",
            "type_alias_declaration": "type",
        },
        wrapper_types=frozenset({"export_statement"}),
    )


def _load_tsx() -> LangConfig:
    import tree_sitter_typescript as tstypescript

    return LangConfig(
        language=Language(tstypescript.language_tsx()),
        comment_types=frozenset({"comment"}),
        symbol_types={
            "function_declaration": "function",
            "class_declaration": "class",
            "interface_declaration": "type",
            "type_alias_declaration": "type",
        },
        wrapper_types=frozenset({"export_statement"}),
    )


def _load_go() -> LangConfig:
    import tree_sitter_go as tsgo

    return LangConfig(
        language=Language(tsgo.language()),
        comment_types=frozenset({"comment"}),
        symbol_types={
            "function_declaration": "function",
            "method_declaration": "function",
            "type_declaration": "type",
        },
        wrapper_types=frozenset(),
    )


def _load_rust() -> LangConfig:
    import tree_sitter_rust as tsrust

    return LangConfig(
        language=Language(tsrust.language()),
        comment_types=frozenset({"line_comment"}),
        symbol_types={
            "function_item": "function",
            "struct_item": "class",
            "enum_item": "type",
            "trait_item": "type",
        },
        wrapper_types=frozenset(),
    )


def _load_kotlin() -> LangConfig:
    import tree_sitter_kotlin as tskotlin

    return LangConfig(
        language=Language(tskotlin.language()),
        comment_types=frozenset({"line_comment", "block_comment"}),
        symbol_types={
            "class_declaration": "class",
            "object_declaration": "class",
            "function_declaration": "function",
        },
        wrapper_types=frozenset(),
    )


# Extension -> loader function mapping.
_EXTENSION_LOADERS: dict[str, Callable[[], LangConfig]] = {
    ".py": _load_python,
    ".ts": _load_typescript,
    ".tsx": _load_tsx,
    ".js": _load_typescript,
    ".jsx": _load_tsx,
    ".go": _load_go,
    ".rs": _load_rust,
    ".kt": _load_kotlin,
    ".kts": _load_kotlin,
}

# Cache for loaded languages (None means "tried and failed / unsupported").
_LANG_CACHE: dict[str, LangConfig | None] = {}


def get_lang_config(extension: str) -> LangConfig | None:
    """Get language config for a file extension, or ``None`` if unsupported/unavailable."""
    if extension in _LANG_CACHE:
        return _LANG_CACHE[extension]

    loader = _EXTENSION_LOADERS.get(extension)
    if loader is None:
        _LANG_CACHE[extension] = None
        return None

    try:
        config = loader()
    except ImportError:
        _LANG_CACHE[extension] = None
        return None

    _LANG_CACHE[extension] = config
    return config


def supported_extensions() -> frozenset[str]:
    """Return the set of file extensions with available grammars."""
    available: set[str] = set()
    for ext in _EXTENSION_LOADERS:
        if get_lang_config(ext) is not None:
            available.add(ext)
    return frozenset(available)


def clear_cache() -> None:
    """Clear the language config cache (useful for testing)."""
    _LANG_CACHE.clear()


def check_parser_availability(extensions: Iterable[str]) -> dict[str, bool]:
    """Check whether a tree-sitter parser is available for each extension.

    Parameters
    ----------
    extensions:
        An iterable of file extensions (e.g. ``[".ts", ".tsx", ".py"]``).

    Returns
    -------
    dict[str, bool]
        Mapping of extension to ``True`` if a parser is installed, ``False`` otherwise.
    """
    return {ext: get_lang_config(ext) is not None for ext in extensions}


def parse_annotations(line: str) -> dict[str, str]:
    """Parse a beadloom annotation from a comment line.

    Format: ``# beadloom:<key>=<value>[ <key>=<value>]*``

    Returns a dict of key->value pairs, or empty dict if no annotation.
    """
    match = _ANNOTATION_RE.search(line)
    if not match:
        return {}
    payload = match.group(1)
    return dict(_KV_RE.findall(payload))


def _get_symbol_name(node: TSNode) -> str | None:
    """Extract symbol name from a definition node.

    Handles standard ``name`` field, plus Go ``type_declaration``
    where the name lives inside a ``type_spec`` child.
    """
    name_node = node.child_by_field_name("name")
    if name_node is not None:
        return name_node.text.decode("utf-8") if name_node.text else None

    # Go type_declaration: name is in type_spec child.
    for child in node.children:
        if child.type == "type_spec":
            spec_name = child.child_by_field_name("name")
            if spec_name is not None:
                return spec_name.text.decode("utf-8") if spec_name.text else None

    return None


def _unwrap_node(node: TSNode, config: LangConfig) -> TSNode | None:
    """Unwrap wrapper types (decorators, export statements) to find the actual definition."""
    if node.type not in config.wrapper_types:
        return node

    for child in node.children:
        if child.type in config.symbol_types:
            return child
    return None


def extract_symbols(file_path: Path) -> list[dict[str, Any]]:
    """Extract top-level symbols from a source file using tree-sitter.

    Detects language by file extension.  Returns empty list if the language
    is not supported or the grammar package is not installed.

    Returns a list of symbol dicts with: ``symbol_name``, ``kind``,
    ``line_start``, ``line_end``, ``annotations``, ``file_hash``.
    """
    config = get_lang_config(file_path.suffix)
    if config is None:
        return []

    content = file_path.read_text(encoding="utf-8")
    if not content.strip():
        return []

    file_hash = hashlib.sha256(content.encode()).hexdigest()
    content_bytes = content.encode("utf-8")

    parser = Parser(config.language)
    tree = parser.parse(content_bytes)

    symbols: list[dict[str, Any]] = []
    pending_annotation: dict[str, str] = {}
    module_annotation: dict[str, str] = {}
    found_first_symbol = False

    for child in tree.root_node.children:
        # Check for comment with beadloom annotation.
        if child.type in config.comment_types:
            text = child.text.decode("utf-8") if child.text else ""
            ann = parse_annotations(text)
            if ann:
                pending_annotation = ann
                if not found_first_symbol:
                    module_annotation.update(ann)
            continue

        # Check if this is a wrapper type that needs unwrapping.
        actual = child
        if child.type in config.wrapper_types:
            unwrapped = _unwrap_node(child, config)
            if unwrapped is None:
                pending_annotation = {}
                continue
            actual = unwrapped
        elif child.type not in config.symbol_types:
            # Non-symbol, non-comment -- reset pending annotation.
            pending_annotation = {}
            continue

        kind = config.symbol_types.get(actual.type)
        if kind is None:
            pending_annotation = {}
            continue

        name = _get_symbol_name(actual)
        if name is None:
            pending_annotation = {}
            continue

        found_first_symbol = True
        # tree-sitter uses 0-based rows; we want 1-based lines.
        line_start = child.start_point.row + 1
        line_end = child.end_point.row + 1

        # Module-level annotations apply to all symbols; symbol-specific
        # annotations (pending) take precedence via dict merge order.
        merged = {**module_annotation, **pending_annotation}

        symbols.append(
            {
                "symbol_name": name,
                "kind": kind,
                "line_start": line_start,
                "line_end": line_end,
                "annotations": merged,
                "file_hash": file_hash,
            }
        )
        pending_annotation = {}

    return symbols
