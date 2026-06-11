# Graph Loader (component)

Internal building block of the graph domain.

**Source:** `src/beadloom/graph/loader.py`

---

## Overview

Parses the `.beadloom/_graph/*.yml` files (nodes + edges) and populates the
`nodes` / `edges` SQLite tables. Validates `ref_id` uniqueness and edge
integrity (every edge endpoint must resolve to a declared node). This is the
ingestion seam every other graph capability (lint, diff, ctx, snapshot) reads
from after reindex.

> Component doc skeleton (BDL-051 S3b / BEAD-14). Tech-writer (BEAD-13) fills prose.
