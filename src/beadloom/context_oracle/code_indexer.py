"""Code symbol indexer: tree-sitter parsing and beadloom annotation extraction."""

# beadloom:domain=context-oracle
# beadloom:feature=code-indexer

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from tree_sitter import Language, Parser

# Re-exported on purpose: the import resolver reads a component's imports from the
# same blocks this indexer reads its symbols from, and reaches the tree-sitter
# facilities through this module only (the one declared `import-resolver ->
# code-indexer` crossing in rules.yml), rather than adding a second one.
from beadloom.context_oracle.vue_sfc import script_blocks as script_blocks

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable
    from pathlib import Path

    from tree_sitter import Node as TSNode

# Regex for beadloom annotations in comments.
_ANNOTATION_RE = re.compile(r"beadloom:(.+)")
_KV_RE = re.compile(r"(\w+)=(\S+)")

#: A module-level annotation written INSIDE a module docstring.
#:
#: tree-sitter reads a docstring as a string node, not a comment, so until
#: BDL-061.50 every ``# beadloom:`` line placed there was invisible to the
#: extractor — and therefore to every annotation-keyed reader (sync pairs, deny
#: rules, symbol counts). Five modules in Beadloom's own ``src/`` are written
#: that way, and the residue it produced was reported as "no indexed code" for
#: a fully indexed file (review .7 MAJOR 3).
#:
#: The line must carry the language's comment marker at **column 0**, which is
#: what separates a declaration from a documented EXAMPLE: prose shows the
#: syntax in an indented code sample (``    # beadloom:domain=...``) or in the
#: in-doc HTML form (``<!-- beadloom:watches=... -->``), and a module that
#: documents the convention must not thereby claim a node. Measured on this
#: repo: ``doc_sync/surface.py`` does exactly that in its own docstring.
_DOCSTRING_ANNOTATION_RE = re.compile(r"^#[ \t]*beadloom:(.+)$")


@dataclass(frozen=True)
class LangConfig:
    """Tree-sitter configuration for a programming language."""

    language: Language
    comment_types: frozenset[str]
    symbol_types: dict[str, str]  # node_type -> kind
    wrapper_types: frozenset[str]  # types that wrap definitions (e.g. decorated_definition)
    #: Node types that may hold a module docstring, scanned for annotations the
    #: way comments are.  Empty for every language whose module-level
    #: documentation IS a comment; only Python has a docstring statement.
    docstring_types: frozenset[str] = frozenset()
    #: Declarations whose names an ``export`` wrapper binds (``export const``,
    #: ``export let``, ``export var``), read together with ``export default``.
    #: Empty for every language without JS/TS export statements.
    exported_binding_types: frozenset[str] = frozenset()


#: The JS/TS declarations an ``export`` statement binds names with.
_JS_BINDING_TYPES = frozenset({"lexical_declaration", "variable_declaration"})

#: The kind of symbol a JS/TS value is, for the value types that are not data.
#: An exported binding holding any other value is a ``variable``.
_JS_VALUE_KINDS: dict[str, str] = {
    "arrow_function": "function",
    "function_expression": "function",
    "function": "function",
    "generator_function": "function",
    "class": "class",
}
_VARIABLE_KIND = "variable"

#: The name a module's default export is imported by, and so the name of an
#: ``export default`` whose value declares none.
_DEFAULT_EXPORT = "default"

#: Single-file-component extensions, each mapped to the script extension whose
#: grammar must be installed for the component's script blocks to be read.
_SFC_SCRIPT_EXTENSIONS: dict[str, str] = {".vue": ".js"}
_COMPONENT_KIND = "component"


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
        docstring_types=frozenset({"expression_statement"}),
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
        exported_binding_types=_JS_BINDING_TYPES,
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
        exported_binding_types=_JS_BINDING_TYPES,
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


def _load_java() -> LangConfig:
    """Java language configuration (tree-sitter-java)."""
    import tree_sitter_java as ts_java

    return LangConfig(
        language=Language(ts_java.language()),
        comment_types=frozenset({"line_comment", "block_comment"}),
        symbol_types={
            "class_declaration": "class",
            "enum_declaration": "class",
            "record_declaration": "class",
            "interface_declaration": "type",
            "annotation_type_declaration": "type",
            "method_declaration": "function",
        },
        wrapper_types=frozenset(),
    )


def _load_swift() -> LangConfig:
    """Swift language configuration (tree-sitter-swift)."""
    import tree_sitter_swift as ts_swift

    return LangConfig(
        language=Language(ts_swift.language()),
        comment_types=frozenset({"comment", "multiline_comment"}),
        symbol_types={
            "class_declaration": "class",
            "protocol_declaration": "type",
            "function_declaration": "function",
        },
        wrapper_types=frozenset(),
    )


def _load_objc() -> LangConfig:
    """Objective-C language configuration (tree-sitter-objc)."""
    import tree_sitter_objc as ts_objc

    return LangConfig(
        language=Language(ts_objc.language()),
        comment_types=frozenset({"comment"}),
        symbol_types={
            "class_interface": "class",
            "class_implementation": "class",
            "protocol_declaration": "type",
            "function_definition": "function",
        },
        wrapper_types=frozenset(),
    )


def _load_c() -> LangConfig:
    """C language configuration (tree-sitter-c)."""
    import tree_sitter_c as ts_c

    return LangConfig(
        language=Language(ts_c.language()),
        comment_types=frozenset({"comment"}),
        symbol_types={
            "function_definition": "function",
            "struct_specifier": "class",
            "enum_specifier": "class",
            "type_definition": "type",
        },
        wrapper_types=frozenset(),
    )


def _load_cpp() -> LangConfig:
    """C++ language configuration (tree-sitter-cpp)."""
    import tree_sitter_cpp as ts_cpp

    return LangConfig(
        language=Language(ts_cpp.language()),
        comment_types=frozenset({"comment"}),
        symbol_types={
            "function_definition": "function",
            "class_specifier": "class",
            "struct_specifier": "class",
            "enum_specifier": "class",
            "namespace_definition": "class",
            "type_definition": "type",
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
    ".java": _load_java,
    ".swift": _load_swift,
    ".m": _load_objc,
    ".mm": _load_objc,
    ".c": _load_c,
    ".h": _load_c,
    ".cpp": _load_cpp,
    ".hpp": _load_cpp,
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


def _can_parse(extension: str) -> bool:
    """True when a file with *extension* can be read for symbols here.

    A single-file component has no grammar of its own: it is readable when the
    grammar of its script blocks is installed.
    """
    return get_lang_config(_SFC_SCRIPT_EXTENSIONS.get(extension, extension)) is not None


def supported_extensions() -> frozenset[str]:
    """Return the set of file extensions with available grammars."""
    candidates = (*_EXTENSION_LOADERS, *_SFC_SCRIPT_EXTENSIONS)
    return frozenset(ext for ext in candidates if _can_parse(ext))


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
    return {ext: _can_parse(ext) for ext in extensions}


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


def parse_docstring_annotations(text: str) -> dict[str, str]:
    """Parse the beadloom annotations declared inside a module docstring.

    Every line of the docstring is considered, not only the first: a docstring
    is prose, and the annotation lines are routinely separated by it.  A line
    counts only in the strict declaration form — the comment marker at column 0,
    then ``beadloom:<key>=<value>`` — so that a documented EXAMPLE (indented, or
    written in the in-doc ``<!-- ... -->`` form) is never mistaken for a claim of
    ownership.  See :data:`_DOCSTRING_ANNOTATION_RE`.

    Returns a dict of key->value pairs, empty when the docstring declares none.
    """
    found: dict[str, str] = {}
    for line in text.splitlines():
        match = _DOCSTRING_ANNOTATION_RE.match(line)
        if match:
            found.update(_KV_RE.findall(match.group(1)))
    return found


def _docstring_node_text(node: TSNode, config: LangConfig) -> str | None:
    """The raw text of *node* when it is a docstring statement, else ``None``.

    A docstring is an expression statement whose whole content is a string
    literal; anything else in that node type (an assignment, a call) is code and
    must not be scanned for annotations.
    """
    if node.type not in config.docstring_types:
        return None
    children = [child for child in node.children if child.is_named]
    if len(children) != 1 or "string" not in children[0].type:
        return None
    return node.text.decode("utf-8") if node.text else None


def _get_symbol_name(node: TSNode) -> str | None:
    """Extract symbol name from a definition node.

    Handles standard ``name`` field, Go ``type_declaration``
    where the name lives inside a ``type_spec`` child, and
    C/C++ declarator chains (``function_definition``,
    ``type_definition``) where the name is nested inside
    ``declarator`` fields.
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

    # C/C++ declarator chain: function_definition -> declarator (function_declarator)
    # -> declarator (identifier); type_definition -> declarator (type_identifier).
    declarator = node.child_by_field_name("declarator")
    if declarator is not None:
        # For type_definition the declarator IS the type_identifier leaf.
        if declarator.type == "type_identifier":
            return declarator.text.decode("utf-8") if declarator.text else None
        # For function_definition, drill into the inner declarator.
        inner = declarator.child_by_field_name("declarator")
        if inner is not None:
            return inner.text.decode("utf-8") if inner.text else None

    # Objective-C: class_interface, class_implementation, protocol_declaration
    # have no ``name`` field.  The first ``identifier`` child is the name.
    for child in node.children:
        if child.type == "identifier":
            return child.text.decode("utf-8") if child.text else None

    return None


def _unwrap_node(node: TSNode, config: LangConfig) -> TSNode | None:
    """Unwrap wrapper types (decorators, export statements) to find the actual definition."""
    if node.type not in config.wrapper_types:
        return node

    for child in node.children:
        if child.type in config.symbol_types:
            return child
    return None


def _value_kind(value: TSNode) -> str:
    """The symbol kind of a JS/TS value: a function, a class, or a variable."""
    return _JS_VALUE_KINDS.get(value.type, _VARIABLE_KIND)


def _declarator_symbol(declarator: TSNode) -> tuple[str, str, TSNode] | None:
    """The ``(name, kind, span)`` a ``variable_declarator`` binds, if it names one."""
    if declarator.type != "variable_declarator":
        return None
    name = declarator.child_by_field_name("name")
    if name is None or name.type != "identifier" or not name.text:
        return None
    value = declarator.child_by_field_name("value")
    kind = _value_kind(value) if value is not None else _VARIABLE_KIND
    return name.text.decode("utf-8"), kind, declarator


def _exported_bindings(export: TSNode, config: LangConfig) -> list[tuple[str, str, TSNode]]:
    """The ``(name, kind, span)`` of each name an ``export`` statement binds.

    Covers what is not a declaration of a symbol type: ``export const/let/var``,
    one symbol per declarator whose target is a plain identifier (a destructuring
    pattern names no single symbol), and ``export default <value>``, named
    ``default`` because that is the name it is imported by.
    """
    if not config.exported_binding_types:
        return []
    for child in export.children:
        if child.type in config.exported_binding_types:
            declared = (_declarator_symbol(d) for d in child.children)
            return [symbol for symbol in declared if symbol is not None]
    value = export.child_by_field_name("value")
    if value is not None and any(child.type == _DEFAULT_EXPORT for child in export.children):
        return [(_DEFAULT_EXPORT, _value_kind(value), export)]
    return []


def _statement_symbols(child: TSNode, config: LangConfig) -> list[tuple[str, str, TSNode]]:
    """The ``(name, kind, span)`` of each symbol one top-level statement declares."""
    actual = child
    if child.type in config.wrapper_types:
        unwrapped = _unwrap_node(child, config)
        if unwrapped is None:
            return _exported_bindings(child, config)
        actual = unwrapped
    kind = config.symbol_types.get(actual.type)
    if kind is None:
        return []
    name = _get_symbol_name(actual)
    if name is None:
        return []
    # A wrapper's span is the symbol's span: decorators and ``export`` included.
    return [(name, kind, child)]


@dataclass
class _SymbolWalk:
    """One file's symbols, and what its walk carries from statement to statement.

    A file is walked as one module even when it is several parse trees, as a
    Vue component with two script blocks is: an annotation written before the
    first symbol of the file applies to every symbol in it.
    """

    file_hash: str
    module_annotation: dict[str, str] = field(default_factory=dict)
    found_first_symbol: bool = False
    symbols: list[dict[str, Any]] = field(default_factory=list)

    def scan(self, root: TSNode, config: LangConfig, *, first_line: int = 1) -> None:
        """Read the top-level statements of *root*, whose row 0 is *first_line*."""
        pending_annotation: dict[str, str] = {}
        for child in root.children:
            # Check for comment with beadloom annotation.
            if child.type in config.comment_types:
                text = child.text.decode("utf-8") if child.text else ""
                ann = parse_annotations(text)
                if ann:
                    pending_annotation = ann
                    if not self.found_first_symbol:
                        self.module_annotation.update(ann)
                continue

            # A module docstring may carry the module-level annotation. It is not
            # a comment node, so it needs its own strict reader (BDL-061.50).
            docstring = _docstring_node_text(child, config)
            if docstring is not None:
                ann = parse_docstring_annotations(docstring)
                if ann and not self.found_first_symbol:
                    self.module_annotation.update(ann)
                continue

            declared = _statement_symbols(child, config)
            if declared:
                self.found_first_symbol = True
                # Module-level annotations apply to all symbols; symbol-specific
                # annotations (pending) take precedence via dict merge order.
                merged = {**self.module_annotation, **pending_annotation}
                for name, kind, span in declared:
                    self._add(name, kind, span, merged, first_line)
            # Any non-comment statement ends what a pending annotation applies to.
            pending_annotation = {}

    def _add(
        self, name: str, kind: str, span: TSNode, annotations: dict[str, str], first_line: int
    ) -> None:
        # tree-sitter rows are 0-based within the parsed text.
        self.symbols.append(
            {
                "symbol_name": name,
                "kind": kind,
                "line_start": first_line + span.start_point.row,
                "line_end": first_line + span.end_point.row,
                "annotations": dict(annotations),
                "file_hash": self.file_hash,
            }
        )


def _component_symbols(file_path: Path, content: str, walk: _SymbolWalk) -> list[dict[str, Any]]:
    """The symbols of a single-file component: the component, then its scripts'.

    Each script block is parsed by the grammar its ``lang`` names, and each symbol
    is placed on its line in the component file. The template and the style are
    not code and are not read. The component is itself a symbol, named after its
    file as Vue names it, and it stands for the component's default export, so
    the ``export default`` of a ``<script>`` block is not a second symbol.
    """
    for block in script_blocks(content):
        config = get_lang_config(block.extension)
        if config is None:
            continue
        tree = Parser(config.language).parse(block.text.encode("utf-8"))
        walk.scan(tree.root_node, config, first_line=block.file_line(0))
    component = {
        "symbol_name": file_path.stem,
        "kind": _COMPONENT_KIND,
        "line_start": 1,
        "line_end": len(content.splitlines()),
        "annotations": dict(walk.module_annotation),
        "file_hash": walk.file_hash,
    }
    body = [s for s in walk.symbols if s["symbol_name"] != _DEFAULT_EXPORT]
    return [component, *body]


def extract_symbols(file_path: Path) -> list[dict[str, Any]]:
    """Extract top-level symbols from a source file using tree-sitter.

    Detects language by file extension.  Returns empty list if the language
    is not supported or the grammar package is not installed.  A Vue
    single-file component is read through its script blocks.

    Returns a list of symbol dicts with: ``symbol_name``, ``kind``,
    ``line_start``, ``line_end``, ``annotations``, ``file_hash``.
    """
    suffix = file_path.suffix
    if not _can_parse(suffix):
        return []

    content = file_path.read_text(encoding="utf-8")
    if not content.strip():
        return []

    walk = _SymbolWalk(file_hash=hashlib.sha256(content.encode()).hexdigest())
    if suffix in _SFC_SCRIPT_EXTENSIONS:
        return _component_symbols(file_path, content, walk)

    config = get_lang_config(suffix)
    if config is None:  # pragma: no cover - _can_parse said the grammar is there
        return []
    tree = Parser(config.language).parse(content.encode("utf-8"))
    walk.scan(tree.root_node, config)
    return walk.symbols
