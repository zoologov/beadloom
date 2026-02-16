# RFC: BDL-015 — Beadloom v1.5 Technical Specification

**Status:** Implemented (v1.5.0)
**Created:** 2026-02-15
**Reference:** STRATEGY-2.md §4-5

---

## 1. Overview

Three parallel phases delivering v1.5:
- **Phase 8** — Smart Bootstrap: rich graph from first `init`
- **Phase 8.5** — Doc Sync v2: honest drift detection (fix UX #15, #18, #21)
- **Phase 9** — Mobile Languages: +5 languages (Kotlin, Java, Swift, C/C++, Obj-C)

No cross-phase dependencies. All three can be developed and tested independently.

---

## 2. Phase 8: Smart Bootstrap

### 2.1 Current state
- `bootstrap_project()` in `scanner.py` (line 988) creates 2-level nodes + `part_of` edges
- `_detect_framework_summary()` detects only 4 patterns (Django, React, Python package, Dockerfile)
- No import analysis at bootstrap time — `depends_on` edges only after `reindex`
- No README parsing, no entry point discovery

### 2.2 Implementation

#### README ingestion (8.1)
```python
# scanner.py — new function
def _ingest_readme(project_root: Path) -> dict[str, str]:
    """Extract project description and tech stack from README/docs."""
    # Parse: README.md, CONTRIBUTING.md, ARCHITECTURE.md, docs/README.md
    # Extract: first paragraph as description, tech mentions, architecture notes
    # Store in root node extra: {"readme_description": "...", "tech_stack": [...]}
```

#### Extended framework detection (8.2)
```python
# scanner.py — extend _detect_framework_summary()
# Add detection for: FastAPI, Flask, Express, NestJS, Next.js, Vue,
# Spring Boot, Gin, Actix, SwiftUI, Jetpack Compose, UIKit
# Two mechanisms: file markers + import content analysis
_FRAMEWORK_PATTERNS: list[tuple[str, str, Callable]] = [
    ("fastapi", "FastAPI service", _check_fastapi),
    ("flask", "Flask app", _check_flask),
    # ...
]
```

#### Entry point discovery (8.3)
```python
# scanner.py — new function
def _discover_entry_points(
    source_path: Path, extensions: set[str]
) -> list[dict[str, str]]:
    """Find entry points: __main__.py, main(), CLI frameworks, etc."""
    # Checks: __main__.py, if __name__, Click/Typer groups,
    # Go/Rust/Java/Kotlin main(), Swift @main, AppDelegate
```

#### Import analysis at bootstrap (8.4)
```python
# scanner.py — new function in bootstrap_project()
def _quick_import_scan(
    project_root: Path,
    clusters: dict[str, dict],
    source_dirs: list[str],
) -> list[dict[str, str]]:
    """Lightweight import scan during bootstrap.
    Reuses extract_imports() from import_resolver.py.
    Maps imports to cluster names, creates depends_on edges.
    """
```

---

## 3. Phase 8.5: Doc Sync v2

### 3.1 Current state
- `check_sync()` in `doc_sync/engine.py` compares `doc_hash` and `code_hash` from `sync_state` table
- Hash tracks file-level changes between reindexes
- Cannot detect: code symbols changed but doc file untouched (semantic drift)
- `incremental_reindex()` doesn't properly reload graph YAML changes (UX #21)

### 3.2 Implementation

#### Symbol-level drift (8.5.1)
```sql
-- New column in sync_state table
ALTER TABLE sync_state ADD COLUMN symbols_hash TEXT DEFAULT '';
```

```python
# doc_sync/engine.py — new logic
def _compute_symbols_hash(conn: Connection, ref_id: str) -> str:
    """SHA256 of sorted code_symbols for a node."""
    rows = conn.execute(
        "SELECT symbol_name, kind FROM code_symbols "
        "WHERE annotations LIKE ? ORDER BY file_path, symbol_name",
        (f'%"{ref_id}"%',),
    ).fetchall()
    return hashlib.sha256(str(rows).encode()).hexdigest()

# In check_sync(): compare symbols_hash vs symbols_hash_at_sync
# If symbols changed but doc unchanged → status = "stale"
```

#### Incremental reindex fix (8.5.4)
```python
# reindex.py — fix graph YAML detection
# Current: graph YAML check exists (line 703-709) but relies on file_index
# Bug: graph YAML files may not be in file_index if they weren't changed
#       since last index, causing the check to fail
# Fix: always check graph YAML file hashes against stored state
```

---

## 4. Phase 9: Mobile Languages

### 4.1 Pattern for adding a language

Each language requires changes in 4 files:

1. **code_indexer.py**: `_load_<lang>()` → `LangConfig` + register in `_EXTENSION_LOADERS`
2. **import_resolver.py**: `_extract_<lang>_imports()` + dispatch in `extract_imports()`
3. **reindex.py**: add extensions to `_CODE_EXTENSIONS`
4. **pyproject.toml**: add `tree-sitter-<lang>` to `[languages]` optional deps

### 4.2 Language configs

| Language | Package | Extensions | Symbol types | Comment types |
|----------|---------|------------|-------------|---------------|
| Kotlin | tree-sitter-kotlin | .kt, .kts | class, data_class, interface, enum_class, function | line_comment |
| Java | tree-sitter-java | .java | class, record, interface, enum | line_comment, block_comment |
| Swift | tree-sitter-swift | .swift | class, struct, protocol, enum, function | comment |
| C | tree-sitter-c | .c, .h | function_definition, struct, enum | comment |
| C++ | tree-sitter-cpp | .cpp, .hpp | function_definition, class, struct, enum | comment |
| Obj-C | tree-sitter-objc | .m, .mm | interface, protocol, function | comment |

### 4.3 Test pattern
- Conditional skip: `@pytest.mark.skipif(not _<lang>_available(), ...)`
- Use `tmp_path` with real code content
- Test symbol extraction + import extraction separately

---

## 5. Database changes

| Change | Table | Type |
|--------|-------|------|
| Add `symbols_hash` | sync_state | ALTER TABLE ADD COLUMN |

No new tables needed. Entry points and framework info stored in `nodes.extra` (JSON).

---

## 6. Risk mitigation

| Risk | Mitigation |
|------|------------|
| tree-sitter grammar API differences | Each language tested independently; graceful fallback |
| scanner.py too large after Phase 8 | Consider extracting _detect_framework_summary to own module |
| Incremental reindex regression | Full test coverage for both incremental and full paths |
