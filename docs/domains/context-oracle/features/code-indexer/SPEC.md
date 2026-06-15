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

## Invariants

- Module-level annotations apply to every symbol in the file; symbol-specific
  annotations override them on merge.
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
- `get_lang_config(extension: str) -> LangConfig | None` — resolve the
  tree-sitter configuration for a file extension.
- `supported_extensions() -> frozenset[str]` — the registered extensions.
- `check_parser_availability(extensions) -> dict[str, bool]` — report which
  grammar packages are installed.
- `clear_cache() -> None` — drop the cached `LangConfig` objects.

## Testing

Tests: `tests/test_code_indexer.py`
