# Scan Paths (component)

Internal building block of the infrastructure domain.

**Source:** `src/beadloom/infrastructure/scan_paths.py`, `src/beadloom/infrastructure/python_projects.py`

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
- `find_python_projects(project_root)` (BDL-083 S2a, BDL-UX #332) — every Python project the
  project holds: a `pyproject.toml` at the root, between the root and a scan path, or under a
  scan path, with `node_modules`, `site-packages`, `venv`, `__pycache__` and hidden directories
  not entered and a scan path outside the root not followed. The root's project comes first.
- `census_packaging(project_root)` — the packaging the room census reads: the root's when the
  root holds a `pyproject.toml`, else the first project found, with the others named in a note.

## Collaborators

- `application/reindex/` uses it for the full/incremental scan and re-exports
  it for backward-compatible import paths.
- `graph/import_resolver.py` uses it to enumerate source files for import
  indexing.
- `application/rooms.py` reads the packaging `census_packaging` chooses, so a monorepo whose
  Python project is `backend/pyproject.toml` declares its interpreters and distribution.

> Component doc (BDL-059 S3). Public surface verified against `scan_paths.py`.
