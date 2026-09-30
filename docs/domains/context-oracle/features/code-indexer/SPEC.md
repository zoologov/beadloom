# Code Indexer

Tree-sitter code symbol indexer for the context-oracle domain.

**Source:** `src/beadloom/context_oracle/code_indexer.py`, which reads Vue components through
`src/beadloom/context_oracle/vue_sfc.py` (owned by the context-oracle domain)

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

Vue single-file components (BDL-076 J3) have no loader of their own:
`get_lang_config(".vue")` is `None`. `.vue` is in `supported_extensions()`, and
`check_parser_availability` reports it available, whenever the grammar of the
`.js` loader (`tree_sitter_typescript`) is installed. That changes the parser
fingerprint, so the first reindex after upgrade is a full code reindex.

### Symbol kinds

The indexer owns the symbol vocabulary: `function`, `class`, `type`,
`component` and, since BDL-076 J3, `variable`. `code_symbols.kind` carries no
CHECK constraint, so a new kind needs no schema change (see the
[db component](../../../infrastructure/components/db/DOC.md)).

### JS/TS export forms

An `export` statement names symbols that are not declarations of a symbol type:

- `export const`, `export let`, `export var`: one symbol per declarator whose
  target is a plain identifier. The kind follows the value: `function` for an
  arrow function, function expression or generator, `class` for a class
  expression, `variable` for anything else or no value.
- A destructuring declarator (`export const { a, b } = obj`) names no symbol.
- An anonymous `export default <value>` is a symbol named `default`, the name
  it is imported by. A named `export default function f` or `class F` is the
  symbol `f` or `F`, as before.
- A top-level `const`/`let`/`var` without `export` is not a symbol.

### Vue single-file components

`vue_sfc.script_blocks(source)` finds every `<script>` and `<script setup>`
block, its 0-based `line_offset` in the file and its grammar by `lang`: `ts` →
`.ts`, `tsx` → `.tsx`, `jsx` → `.jsx`, any other value or none → `.js`. A tag
that only begins with `script` (`<script-docs>`) is not a script block.

`extract_symbols` on a `.vue` file returns:

1. a `component` symbol named after the file stem, spanning line 1 to the last
   line, carrying the module annotations;
2. the symbols of each block, parsed by the loader the block's extension names,
   at their lines in the `.vue` file.

The component symbol stands for the default export, so a block's
`export default` is dropped rather than recorded as a second symbol. Inside
`<script setup>` a top-level `function` declaration is a symbol, as in any JS
module. The `<template>` and `<style>` are not read: a style-only edit changes
the file hash but no symbol, and an annotation in a template-only component
has no place to live, because HTML comments are not read.

The blocks of one component are walked as one module (`_SymbolWalk`): an
annotation written before the first symbol of the file applies to every symbol
in both blocks.

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
- A `.vue` symbol's lines are lines of the `.vue` file, never of the script
  block it was parsed from.
- `.vue` is supported exactly when the `.js` loader's grammar is installed; the
  whole component is never parsed as TypeScript.

## API

Module `src/beadloom/context_oracle/code_indexer.py`:

- `extract_symbols(file_path: Path) -> list[dict[str, Any]]` — extract
  top-level symbols; each dict has `symbol_name`, `kind`, `line_start`,
  `line_end`, `annotations`, `file_hash`. A `.vue` file yields its `component`
  symbol first, then its script blocks' symbols.
- `parse_annotations(line: str) -> dict[str, str]` — parse beadloom keys from a
  comment line.
- `parse_docstring_annotations(text: str) -> dict[str, str]` — parse the strict
  declaration lines out of a module docstring (BDL-061.50).
- `get_lang_config(extension: str) -> LangConfig | None` — resolve the
  tree-sitter configuration for a file extension.
- `supported_extensions() -> frozenset[str]` — the registered extensions whose
  grammar is installed, plus `.vue` when the `.js` grammar is.
- `script_blocks` — re-exported from `vue_sfc`, so the import resolver reads a
  component's imports from the same blocks through its one declared crossing
  into `code_indexer`.
- `check_parser_availability(extensions) -> dict[str, bool]` — report which
  grammar packages are installed.
- `clear_cache() -> None` — drop the cached `LangConfig` objects.
- `LangConfig.exported_binding_types` — the declarations an `export` wrapper
  binds names with; set for the TypeScript and TSX loaders only.

Module `src/beadloom/context_oracle/vue_sfc.py`:

- `script_blocks(source: str) -> tuple[ScriptBlock, ...]` — the script blocks
  of a component, in file order. Parses nothing.
- `ScriptBlock(text, line_offset, extension)` — frozen; `file_line(row)` maps a
  0-based row of the block to the 1-based line of the file.

## Testing

Tests: `tests/integration/context_oracle/code_indexer/test_code_indexer.py`,
`tests/integration/context_oracle/code_indexer/test_javascript_exports.py` (the export forms),
`tests/integration/context_oracle/code_indexer/test_vue_support.py` (script blocks, lines, `lang`,
annotations across blocks, a missing grammar),
`tests/acceptance/context-oracle/code-indexer/vue_single_file_components.feature` (4 scenarios),
`tests/test_a_declaration_that_owns_nothing_is_reported.py::TestDocstringAnnotationsAreRead` — the
docstring form, including the two non-vacuity guards that keep a documented EXAMPLE from being read
as a declaration.
