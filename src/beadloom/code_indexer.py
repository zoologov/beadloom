"""Code symbol indexer: tree-sitter parsing and beadloom annotation extraction."""

from __future__ import annotations

import hashlib
import re
from typing import TYPE_CHECKING, Any

import tree_sitter_python as tspython
from tree_sitter import Language, Parser

if TYPE_CHECKING:
    from pathlib import Path

    from tree_sitter import Node as TSNode

# Compile the Python grammar once at module level.
_PY_LANGUAGE = Language(tspython.language())

# Regex for beadloom annotations in comments.
_ANNOTATION_RE = re.compile(r"beadloom:(.+)")
_KV_RE = re.compile(r"(\w+)=(\S+)")

# Top-level node types that produce symbols.
_SYMBOL_TYPES = frozenset({
    "function_definition",
    "class_definition",
    "decorated_definition",
})


def parse_annotations(line: str) -> dict[str, str]:
    """Parse a beadloom annotation from a comment line.

    Format: ``# beadloom:<key>=<value>[ <key>=<value>]*``

    Returns a dict of key→value pairs, or empty dict if no annotation.
    """
    match = _ANNOTATION_RE.search(line)
    if not match:
        return {}
    payload = match.group(1)
    return dict(_KV_RE.findall(payload))


def _get_symbol_info(node: TSNode) -> tuple[str, str] | None:
    """Extract (name, kind) from a definition node.

    Handles plain and decorated definitions.
    """
    actual = node
    if node.type == "decorated_definition":
        # The actual definition is the last child.
        for child in node.children:
            if child.type in ("function_definition", "class_definition"):
                actual = child
                break
        else:
            return None

    name_node = actual.child_by_field_name("name")
    if name_node is None:
        return None

    name = name_node.text.decode("utf-8") if name_node.text else ""
    if actual.type == "class_definition":
        return (name, "class")
    return (name, "function")


def extract_symbols(file_path: Path) -> list[dict[str, Any]]:
    """Extract top-level Python symbols from a file using tree-sitter.

    Returns a list of symbol dicts with: ``symbol_name``, ``kind``,
    ``line_start``, ``line_end``, ``annotations``, ``file_hash``.
    """
    content = file_path.read_text(encoding="utf-8")
    if not content.strip():
        return []

    file_hash = hashlib.sha256(content.encode()).hexdigest()
    content_bytes = content.encode("utf-8")

    parser = Parser(_PY_LANGUAGE)
    tree = parser.parse(content_bytes)

    symbols: list[dict[str, Any]] = []
    pending_annotation: dict[str, str] = {}
    module_annotation: dict[str, str] = {}
    found_first_symbol = False

    for child in tree.root_node.children:
        # Check for comment with beadloom annotation.
        if child.type == "comment":
            text = child.text.decode("utf-8") if child.text else ""
            ann = parse_annotations(text)
            if ann:
                pending_annotation = ann
                if not found_first_symbol:
                    module_annotation.update(ann)
            continue

        if child.type not in _SYMBOL_TYPES:
            # Non-symbol, non-comment — reset pending annotation.
            pending_annotation = {}
            continue

        info = _get_symbol_info(child)
        if info is None:
            pending_annotation = {}
            continue

        found_first_symbol = True
        name, kind = info
        # tree-sitter uses 0-based rows; we want 1-based lines.
        line_start = child.start_point.row + 1
        line_end = child.end_point.row + 1

        # Module-level annotations apply to all symbols; symbol-specific
        # annotations (pending) take precedence via dict merge order.
        merged = {**module_annotation, **pending_annotation}

        symbols.append({
            "symbol_name": name,
            "kind": kind,
            "line_start": line_start,
            "line_end": line_end,
            "annotations": merged,
            "file_hash": file_hash,
        })
        pending_annotation = {}

    return symbols
