# Doc Indexer (component)

Internal building block of the doc-sync domain.

**Source:** `src/beadloom/doc_sync/doc_indexer.py`

---

## Overview

Scans the project's Markdown documentation, chunks it, and populates the SQLite
`docs` / chunk tables (with content hashes). This index backs FTS5 search and is
the doc half of every sync-check pair — the source-of-record for what
documentation exists and whether it has changed.

> Component doc skeleton (BDL-051 S3b / BEAD-14). Tech-writer (BEAD-13) fills prose.
