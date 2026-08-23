# Code Indexer

Tree-sitter code symbol indexer for the context-oracle domain.

**Source:** `src/beadloom/context_oracle/code_indexer.py`

---

## Specification

### Purpose

Parse source files with tree-sitter to extract code **symbols** (functions,
classes, methods) and the inline `# beadloom:<key>=<value>` **annotations**
attached to them. The resulting `code_symbols` rows — each carrying a
`file_hash` — are the substrate for sync-check freshness, the rule engine
(including the `module-coverage` lint), and the `ctx` / `why` context bundles.

### Language support

A per-language `LangConfig` (loaded lazily and cached) names the tree-sitter
grammar, the comment node types, and the symbol-node types for each language.
The indexer ships configurations for Python, TypeScript, TSX, Go, Rust, Kotlin,
Java, Swift, Objective-C, C, and C++. `get_lang_config` resolves a config by
file extension; `supported_extensions` lists the registered extensions; and
`check_parser_availability` reports which grammar packages are actually
installed, so a missing optional grammar degrades gracefully rather than
failing the index.

### Annotation extraction

`parse_annotations` reads a single comment line into a dict of beadloom keys.
During parsing, a comment that appears **before the first symbol** is treated as
a module-level annotation applied to every symbol in the file; a comment
immediately preceding a symbol is symbol-specific and takes precedence on merge.

**A module docstring is read too** (BDL-061.50). tree-sitter sees a docstring as
a string node, not a comment, so a `# beadloom:` line written inside one was
invisible to the extractor — and therefore to every annotation-keyed reader:
sync pairs, deny rules, symbol counts. Five modules in Beadloom's own `src/` are
written that way, and the residue it produced was a `sync-check` reason that
claimed *no indexed code* for a fully indexed file.

The docstring form is **strict**, and the strictness is the point: the line must
carry the language's comment marker at **column 0**.

```python
"""Application read facade.

# beadloom:domain=application          <- a declaration: read
# beadloom:feature=graph-reads         <- every line is read, not just the first
"""
```

```python
"""How to annotate.

Write it at the top of the module::

    # beadloom:domain=example          <- an EXAMPLE: not read
    <!-- beadloom:watches=cli,graph -->  <- also an example: not read
"""
```

Documenting the convention must not silently claim a node: this repository's own
`doc_sync/surface.py` shows the in-doc `<!-- beadloom:watches=... -->` form
inside its docstring, and an indented `# beadloom:` sample is the ordinary way
prose shows the syntax. Only Python declares a docstring node type
(`LangConfig.docstring_types`); every other language's module-level
documentation IS a comment and is already read.

## Invariants

- Module-level annotations apply to every symbol in the file; symbol-specific
  annotations override them on merge.
- A module docstring annotation is module-level: it never overrides a comment
  written against a symbol.
- Only the strict form counts inside a docstring — comment marker at column 0,
  one declaration per line, every line considered.
- A module with **no top-level symbol** produces no symbol row and therefore
  carries no annotation into the index, whatever its docstring says. Such a
  module is still paired with its doc through the node that OWNS it (see
  `doc-sync/sync-check`); this is a limit of the symbol table, not of the
  extractor.
- An unsupported extension, a missing grammar, or an empty file yields an empty
  symbol list rather than an error.
- Each symbol carries the SHA-256 `file_hash` of its source file, which is what
  sync-check baselines against.

## API

Module `src/beadloom/context_oracle/code_indexer.py`:

- `extract_symbols(file_path: Path) -> list[dict[str, Any]]` — extract
  top-level symbols; each dict has `symbol_name`, `kind`, `line_start`,
  `line_end`, `annotations`, `file_hash`.
- `parse_annotations(line: str) -> dict[str, str]` — parse beadloom keys from a
  comment line.
- `parse_docstring_annotations(text: str) -> dict[str, str]` — parse the strict
  declaration lines out of a module docstring (BDL-061.50).
- `get_lang_config(extension: str) -> LangConfig | None` — resolve the
  tree-sitter configuration for a file extension.
- `supported_extensions() -> frozenset[str]` — the registered extensions.
- `check_parser_availability(extensions) -> dict[str, bool]` — report which
  grammar packages are installed.
- `clear_cache() -> None` — drop the cached `LangConfig` objects.

## Testing

Tests: `tests/test_code_indexer.py`,
`tests/test_s3_owns_nothing.py::TestDocstringAnnotationsAreRead` — the docstring
form, including the two non-vacuity guards that keep a documented EXAMPLE from
being read as a declaration.
