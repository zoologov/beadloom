# Infrastructure

Domain-agnostic SQLite database layer, health metrics, and git activity analysis.

> Note: the cross-domain orchestrators (`reindex`, `doctor`, `debt_report`, `watcher`)
> live in the [application](../application/README.md) layer, not here, so that
> `infrastructure` never imports a domain (the DDD Dependency Rule).

## Components

Internal building blocks, each with a `DOC.md`:

- **[DB](components/db/DOC.md)** — the domain-agnostic SQLite layer (connection, schema, migrations, `meta`).
- **[Health](components/health/DOC.md)** — health snapshots + trend computation.
- **[Git Activity](components/git-activity/DOC.md)** — per-node `git log` activity metrics.
- **[MCP Tools](components/mcp-tools/DOC.md)** — the canonical MCP tool-name catalog.
- **[Scan Paths](components/scan-paths/DOC.md)** — resolves source scan directories from `config.yml` so domains do not import `application`.
- **[Doc Roots](components/doc-roots/DOC.md)** — the three documentation spaces (TO-BE / AS-IS / WORKING), their configurable roots and kinds, and which space a document belongs to. Beside `scan-paths` for the same reason: `doc-sync` resolves the WORKING freshness exemption without reaching up into `application`.
- **[Atomic IO](components/atomic-io/DOC.md)** — atomic YAML writes (temp-file + `os.replace`) so a crash mid-write never corrupts the source-of-truth graph YAML.
- **[Console Streams](components/console-streams/DOC.md)** — the CLI's own `stdout`/`stderr` keep the operator's codec but degrade an unencodable glyph to its escape instead of dying on it.
- **[Surface Registry](components/surface-registry/DOC.md)** — the port through which the services layer hands its live CLI/MCP surface to the checks below it, so `doctor` / `docs audit` / `sync-check` can compare a documented claim against runtime truth without importing upward.

## Specification

### Modules

- **surface_registry.py** — the CLI surface port. `register_cli_group(provider)` is called by `services/cli.py` on import; `get_cli_group()` is read by `application/doctor.py`, `doc_sync/audit.py` and `doc_sync/surface.py`, so those checks can compare a documented claim against runtime truth without importing upward into `services` (BDL-UX #159). The provider is stored as a callable and invoked per read, and one that raises degrades to `None`. **Unknown is not zero:** the getter returns `None` when nothing is registered — distinct from a real but empty surface — so a caller reports "not verified" rather than announcing a count it never looked at. Only the CLI needs a port: the MCP tool list already has a canonical lower-layer source in `mcp_tools.MCP_TOOL_CATALOG` (pinned equal to the server's registry by a test, and present in every process), so its consumers read that directly.
- **console_streams.py** — `tolerate_unencodable_output()` relaxes `strict` to `backslashreplace` on this process's `sys.stdout`/`sys.stderr`, and never touches their **codec**: a terminal is the one stream whose encoding genuinely belongs to the operator's locale, so writing UTF-8 into a latin-1 terminal would only move the damage. MEASURED under `LC_ALL=en_US.ISO-8859-1` before it existed (BDL-061.42): `python -m beadloom.ai_agents.ai_techwriter --help` exited 1 on a `→` in its own help text, and a passing `beadloom guard` wrote nothing at all, because the verdict line carries an em dash. Applied at each Click entry object (`_root.TolerantOutputGroup`, the harness's `_TolerantOutputCommand`) rather than in a callback, because Click answers `--help` while parsing. An explicit `PYTHONIOENCODING=...:replace` and any stream without `reconfigure` are left alone.
- **db.py** — `open_db()` opens a SQLite connection with WAL mode and foreign keys enabled, returning a connection with `sqlite3.Row` row factory. `create_schema()` creates all tables and applies incremental migrations via `ensure_schema_migrations()`. `get_meta()`/`set_meta()` for key-value metadata. Exports `SCHEMA_VERSION` constant (currently `"4"` — BDL-038 G7 added `external` to the `nodes`/`edges`/`foreign_edges` `lifecycle` CHECK). The `rules` table's `rule_type` is **free-form `TEXT` (no CHECK)** since BDL-061 S4: the CHECK enumerated the rule vocabulary a second time next to the loader that already validates it, so every new rule type broke every EXISTING database — the loader accepted `scenario_coverage` and the insert raised `IntegrityError` on any `beadloom.db` created before the release, on the adopter's machine rather than on ours. `_migrate_drop_rule_type_check()` rebuilds a table that still carries the old CHECK (rename-create-copy-drop, idempotent, no `SCHEMA_VERSION` gate — the same mechanism as the `kind` and `lifecycle` CHECK migrations).
- **health.py** — `take_snapshot()` captures current index statistics (node/edge/doc counts, coverage percentage, stale docs, isolated nodes) and persists them to the `health_snapshots` table. `get_latest_snapshots()` retrieves history for trend comparison. `compute_trend()` computes trend indicators (arrows and deltas) between two snapshots.
- **git_activity.py** — `GitActivity` frozen dataclass holds per-node metrics: `commits_30d`, `commits_90d`, `last_commit_date`, `top_contributors`, `activity_level`. `analyze_git_activity()` runs `git log --since=90 days ago`, parses output, maps changed files to nodes via longest source-prefix match, and classifies activity (hot: >20 commits/30d, warm: 5-20, cold: 1-4, dormant: 0 commits/90d).
- **mcp_tools.py** — single-source catalog of MCP tool metadata used by AGENTS.md generation. `McpToolDoc` describes one tool; `mcp_tool_names()` returns the canonical tool-name list (pinned to the live MCP `_TOOLS` registry by a drift-guard test) so the documented tool count cannot drift.
- **scan_paths.py** — `resolve_scan_paths()` reads `scan_paths` from `.beadloom/config.yml`, falling back to `("src", "lib", "app")`. A domain-agnostic config reader at the lowest layer so `graph` (import resolution) and `application` (reindex) resolve scan directories without a domain importing `application` (closes the BDL-059 S3 layering inversion).
- **repository.py** — the centralized, typed reads over the index, and the single answer to **which node owns a file**: the most specific node whose `source` covers it. `covering_prefix()` / `source_covers()` are public because the rule engine's file attribution applies the same rule and the two must not each keep a copy (BDL-061.50). `get_owned_code_files()` reads `file_index`, not `code_symbols`, so a module with no top-level symbol still belongs to its node. See the [repository component doc](components/repository/DOC.md).
- **doc_roots.py** — `resolve_doc_spaces(project_root)` reads the `doc_roots` block from `.beadloom/config.yml` into the three documentation spaces — TO-BE (intent), AS-IS (reality, held against the code by `sync-check`) and WORKING (ephemeral, exempt from freshness by declaration) — each with its own roots and document kinds, and `DocSpaces.space_of(rel_path)` answers which space a document belongs to. Kind wins over root, because `ACTIVE.md` lives INSIDE the TO-BE tree and a root-first answer would classify every WORKING document as intent and exempt nothing. Root globs are matched with the same reach `Path.glob` gives them rather than with `fnmatch`, which lets `*` cross a separator: a file a root FINDS and the classifier puts in no space is the check disagreeing with itself. A domain-agnostic config reader at the lowest layer, beside `scan_paths.py`, so `doc_sync` resolves the WORKING exemption without importing `application`. Configuration errors are carried, never raised, so one malformed line cannot become a crashing gate that names the wrong file (BDL-061 S5). Among roots the WORKING space is consulted FIRST, because its shipped root list is empty and the AS-IS default is the catch-all `docs/**/*.md`: if the catch-all won, a root a project declared WORKING would be silently inert. `DocSpaces.project_path(doc_path)` translates the docs-dir-relative path a `sync_state` row carries into the one project-relative spelling every root glob is written in, so freshness and the spaces report classify one file alike, and `resolve_docs_dir(project_root)` is the single reader of the `docs_dir` key three readers held before (`beadloom-mr2l.75`).
- **atomic_io.py** — `write_yaml_atomic(path, data, **dump_kwargs)` serializes with `yaml.dump(**dump_kwargs)`, writes to a temp file in the same directory, `fsync`s it, then commits with `Path.replace` (atomic on POSIX). Every graph-YAML writer (`graph` loader/patcher, `services` link patcher, `onboarding` scaffolders) routes through it so a crash mid-write cannot corrupt the source-of-truth graph YAML; dump options pass through verbatim so output bytes are unchanged (BDL-060 S1 / G6).

### Database Schema

Stored in `.beadloom/beadloom.db` (WAL mode):
- `nodes`, `edges` — architecture graph. Their `kind` columns are **free-form `TEXT` (no CHECK)** so any paradigm's vocabulary (DDD `domain`/`service`, FSD `page`/`widget`/`repository`, …) is stored and federated faithfully — Beadloom is paradigm-agnostic, not DDD-only (BDL-038 / U1). Both carry a `lifecycle` column (`active`/`planned`/`deprecated`/`dead`/`external`, default `active`; BDL-037 + BDL-038 G7 `external`). `edges` also carries a `contract_key` column (default `''`) that is part of its primary key, so multiple AMQP contracts (`produces`/`consumes`) on the same `(src,dst,kind)` pair do not collapse (BDL-037 #102)
- `foreign_edges` — cross-repo edges whose at least one endpoint is a `@repo:ref_id` reference to a node in another repo; kept separate because a foreign endpoint cannot satisfy the `edges` FK to local nodes (BDL-037 #100). Carries the same `lifecycle` CHECK (incl. `external`)
- `docs`, `chunks` — document index
- `code_symbols` — code symbol index (includes `annotations` JSON and `file_hash`)
- `code_imports` — resolved import relationships
- `sync_state` — doc-code synchronization (includes `symbols_hash` for drift detection, `doc_hash_at_last_edit` for two-phase sync that survives reindex, and `baseline_source` recording where the baseline CAME FROM — `index_build` / `carried` / `attested`). Its `status` CHECK carries four verdicts, `ok`/`stale`/`missing`/`unverified`: the last two are states in which the checker could not know, and writing them as `ok` is what let a deleted doc and a rebuilt index both read fresh (BDL-UX #174/#175)
- `declared_docs` — the DECLARED documentation surface: every doc a node names in its `docs:` list, whether or not the file exists. `docs` indexes files found on disk, so without this table deleting a declared doc simply removed it from the index and no check could miss it. A cache of the committed graph YAML, rebuilt on reindex
- `file_index` — file hash tracking for incremental reindex (includes `__parser_fingerprint__` sentinel row)
- `health_snapshots` — trend tracking (persists across reindexes)
- `graph_snapshots` — point-in-time architecture graph captures (nodes_json, edges_json, symbols_count, label)
- `bundle_cache` — L2 persistent bundle cache
- `search_index` — FTS5 full-text search index
- `rules` — architecture rules from `rules.yml`
- `meta` — index metadata

### Parser Fingerprint

`incremental_reindex()` tracks available tree-sitter parsers via a fingerprint (sorted comma-separated `supported_extensions()`). Stored as a sentinel row in `file_index` with `path='__parser_fingerprint__'`. When the fingerprint changes (e.g. after `uv tool install "beadloom[languages]"`), a full code reindex is triggered automatically, ensuring new language parsers are used without requiring `--full`.

## API

Module `src/beadloom/infrastructure/surface_registry.py`:
- `register_cli_group(provider: Callable[[], Any])` — services register the root Click group
- `get_cli_group()` -> `Any | None` — the group, or `None` when the surface is unknown
- `reset_surface_providers()` — clears the provider (tests only)

Module `src/beadloom/infrastructure/db.py`:
- `SCHEMA_VERSION` — schema version constant (currently `"4"`; v3 → v4 rebuilt the `lifecycle` CHECK to admit `external`)
- `open_db(db_path: Path)` -> `sqlite3.Connection` — opens DB with WAL mode, foreign keys, and `Row` factory
- `ensure_schema_migrations(conn)` — applies incremental schema migrations (e.g. `symbols_hash` column, `doc_hash_at_last_edit` column for two-phase sync, the `lifecycle` column on `nodes`/`edges`, the `edges.contract_key` rebuild, the `foreign_edges` table for BDL-037 federation, the BDL-038 / U1 rebuild that drops the legacy DDD-only `kind` CHECK on `nodes`/`edges` so `kind` is free-form, and the BDL-038 / G7 rebuild (`_migrate_lifecycle_external`, v3 → v4) that adds `external` to the `nodes`/`edges`/`foreign_edges` `lifecycle` CHECK — all additive + idempotent, guarded on the stored DDL/columns; the rebuild uses `PRAGMA legacy_alter_table=ON` so renaming a rebuilt table does not dangle dependent FK references)
- `create_schema(conn)` — creates all tables and indexes, calls `ensure_schema_migrations()`
- `get_meta(conn, key, default=None)` -> `str | None`
- `set_meta(conn, key, value)` — upserts a key in the `meta` table

Module `src/beadloom/infrastructure/health.py`:
- `HealthSnapshot` — frozen dataclass with `taken_at`, `nodes_count`, `edges_count`, `docs_count`, `coverage_pct`, `stale_count`, `isolated_count`
- `take_snapshot(conn)` -> `HealthSnapshot` — computes and persists health metrics
- `get_latest_snapshots(conn, n=2)` -> `list[HealthSnapshot]`
- `compute_trend(current, previous)` -> `dict[str, str]` — computes trend indicators between two snapshots

Module `src/beadloom/infrastructure/git_activity.py`:
- `GitActivity` — frozen dataclass: `commits_30d`, `commits_90d`, `last_commit_date`, `top_contributors`, `activity_level`
- `analyze_git_activity(project_root, source_dirs)` -> `dict[str, GitActivity]` — parses `git log` for 90 days, maps files to nodes, classifies activity level (hot/warm/cold/dormant)

> The orchestrator modules `reindex`, `doctor`, `debt_report`, and `watcher` were
> relocated to the [application](../application/README.md) layer. Their API and
> tests are documented there.

## Testing

Tests: `tests/test_db.py`, `tests/test_health.py`, `tests/test_reindex_activity.py`
