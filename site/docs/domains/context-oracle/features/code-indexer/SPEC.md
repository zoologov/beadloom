<!-- beadloom:badge-start -->
> ✅ **fresh**
> 
> last synced 2026-06-14T18:52:29.106245+00:00 · coverage 100% (`code-indexer`)
> 
> _Validation by Beadloom `doc_sync` — same source as `sync-check`._
<!-- beadloom:badge-end -->

# Code Indexer

Tree-sitter code symbol indexer for the context-oracle domain.

**Source:** `src/beadloom/context_oracle/code_indexer.py`

---

## Specification

### Purpose

Parse source files with tree-sitter to extract code **symbols** (functions,
classes, methods, …) and the inline `# beadloom:<key>=<value>` **annotations**
attached to them. The resulting `code_symbols` rows (with `file_hash` /
`symbols_hash`) are the substrate for sync-check freshness, the rule engine
(including the `module-coverage` lint), and the `ctx` / `why` context bundles.

### Contract

- **Input:** source files under the configured `scan_paths` (default `src/`).
- **Output:** one `code_symbols` row per indexed symbol — `file_path`,
  `symbol_name`, `kind`, `line_start`, `line_end`, `annotations` (JSON of the
  parsed beadloom keys), `file_hash`.
- **Invariants:** module-level annotation comments (appearing before the first
  symbol) apply to every symbol in the file; symbol-specific annotations take
  precedence on merge.

> Skeleton (BDL-051 S3b / BEAD-14). The tech-writer pass (BEAD-13) fills prose.
