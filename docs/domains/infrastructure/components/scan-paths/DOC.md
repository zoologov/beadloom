# Scan Paths (component)

Internal building block of the infrastructure domain.

**Source:** `src/beadloom/infrastructure/scan_paths.py`

---

## Overview

A small, domain-agnostic config reader that resolves the source scan
directories for a project. It reads `scan_paths` from `.beadloom/config.yml`
and falls back to `["src", "lib", "app"]` when the config is absent or has no
`scan_paths`.

It lives in `infrastructure` (the lowest layer) so that domains — notably
`graph` (the import resolver) — and the `application` reindex orchestrator can
both resolve scan directories without a domain reaching UP into `application`.
This closes the historic `graph -> application.reindex` layering inversion
(BDL-059 S3): the dependency now points DOWN into infrastructure, satisfying the
`architecture-layers` rule without any lazy-import workaround.

## Public surface

- `resolve_scan_paths(project_root)` — return the list of scan directory names
  for the project, read from `config.yml` (or the default fallback).

## Collaborators

- `application/reindex/` uses it for the full/incremental scan and re-exports
  it for backward-compatible import paths.
- `graph/import_resolver.py` uses it to enumerate source files for import
  indexing.

> Component doc (BDL-059 S3). Public surface verified against `scan_paths.py`.
