# BDL-009: Import Analysis Improvements (v1.1.0)

> **Status:** COMPLETE
> **Version:** 1.1.0
> **Date:** 2026-02-12
> **Epic:** none (minor release, no dedicated epic)

---

## What was done

Small v1.1.0 release between BDL-007 (v1.0) and BDL-008 (v1.2 DDD restructuring).
No formal epic was created — the work was done as incremental improvements.

### Added
- **Deep import analysis** — `depends_on` edges generated from resolved imports between graph nodes
- **Hierarchical source-prefix resolver** — handles Django-style imports (`apps.core.models`), TypeScript `@/` aliases
- **Auto-reindex after init** — no more manual `beadloom reindex` needed after `--bootstrap`
- **Noise directory filtering** — `static`, `templates`, `migrations`, `fixtures`, `locale`, `media`, `assets` excluded

### Fixed
- Source dir discovery expanded (`backend`, `frontend`, `server`, `client`)
- `reindex` and `import_resolver` read `scan_paths` from `config.yml`
- `node_modules` filtered from recursive scans
- `.vue` files recognized as code extensions

## Commits

```
dcb3ac7 chore: bump version to 1.1.0
3b0f2ff docs: add v1.1.0 changelog entry
```

## Why no BDL- prefix in commits

This release predated the formalization of BDL-* epic prefixes for all work.
Starting from BDL-008, all significant work gets a dedicated epic.
