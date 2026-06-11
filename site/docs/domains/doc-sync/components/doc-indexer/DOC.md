<!-- beadloom:badge-start -->
> ✅ **fresh**
> 
> last synced 2026-06-11T14:19:08.709748+00:00 · coverage 100% (`doc-indexer`)
> 
> _Validation by Beadloom `doc_sync` — same source as `sync-check`._
<!-- beadloom:badge-end -->

# Doc Indexer (component)

Internal building block of the doc-sync domain.

**Source:** `src/beadloom/doc_sync/doc_indexer.py`

---

## Overview

Scans the project's Markdown documentation, chunks it, and populates the SQLite
`docs` / chunk tables (with content hashes). This index backs FTS5 search and is
the doc half of every sync-check pair — the source-of-record for what
documentation exists and whether it has changed.

## Public surface

- `index_docs(...)` — scan the docs tree, chunk each file, and populate the
  `docs` / `chunks` tables; returns a `DocIndexResult`.
- `chunk_markdown(text)` — split Markdown into section chunks by H2 heading
  (capped at `MAX_CHUNK_SIZE` = 2000 chars per chunk).
- `classify_section(heading)` — map a heading to a section label
  (`spec` / `invariants` / `constraints` / `api` / `tests` / `other`) via
  `_SECTION_RULES`.
- `DocIndexResult` — the dataclass summarizing an index run.

## Collaborators

Writes the `docs` / `chunks` tables consumed by the `search` (FTS5) feature and
the `context-builder` (chunk collection). It is the doc half of every
`sync-check` pair — the section labels it assigns drive chunk-priority ordering
in the context bundle.

> Component doc (BDL-051). Public surface verified against `doc_indexer.py`.
