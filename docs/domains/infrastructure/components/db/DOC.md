# DB (component)

Internal building block of the infrastructure domain.

**Source:** `src/beadloom/infrastructure/db.py`

---

## Overview

The domain-agnostic SQLite layer: connection management, schema creation, and
the `meta` key/value helpers. Every other domain reads and writes through this
single, lowest-layer module — it owns the database file lifecycle and the table
definitions the rest of Beadloom depends on.

> Component doc skeleton (BDL-051 S3b / BEAD-14). Tech-writer (BEAD-13) fills prose.
