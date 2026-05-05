<!-- beadloom:badge-start -->
> ✅ **fresh**
> 
> last synced 2026-06-02T05:39:03.489493+00:00 · coverage 100% (`cli`)
> 
> _Validation by Beadloom `doc_sync` — same source as `sync-check`._
<!-- beadloom:badge-end -->

# CLI Reference

Beadloom CLI is built on Click and provides a set of commands for managing the knowledge index.

## Specification

### Global Options

```
beadloom [--verbose|-v] [--quiet|-q] [--version] COMMAND
```

- `--verbose` / `-v` -- verbose output
- `--quiet` / `-q` -- errors only
- `--version` -- show version

### beadloom init

Project initialization. Three modes:

```bash
# Generate graph from code structure (auto-detects architecture)
beadloom init --bootstrap [--preset {monolith,microservices,monorepo}] [--project DIR]

# Import existing documentation
beadloom init --import DOCS_DIR [--project DIR]

# Non-interactive mode (for CI/scripting)
beadloom init --yes [--mode {bootstrap,import,both}] [--force] [--project DIR]

# Interactive mode (default when no flags given)
beadloom init [--project DIR]
```

`--bootstrap` scans source directories (src, lib, app, services, packages), classifies subdirectories using architecture-aware preset rules, infers edges from directory nesting, and generates `.beadloom/_graph/services.yml` + `.beadloom/config.yml`.

`--preset` selects an architecture preset:
- `monolith` -- top dirs are domains; subdirs map to features, entities, services
- `microservices` -- top dirs are services; shared code becomes domains
- `monorepo` -- packages/apps are services; manifest deps become edges

When `--preset` is omitted, Beadloom auto-detects: `services/` or `cmd/` -> microservices, `packages/` or `apps/` -> monorepo, otherwise -> monolith.

`--import` classifies .md files (ADR, feature, architecture, other) and generates `.beadloom/_graph/imported.yml`.

`--yes` / `-y` enables non-interactive mode: no prompts, uses defaults. Combined with `--mode` to select the initialization strategy:
- `bootstrap` (default) -- generate graph from code
- `import` -- classify existing docs
- `both` -- bootstrap graph and import docs

`--force` overwrites an existing `.beadloom/` directory. Without it, non-interactive init skips if `.beadloom/` already exists.

Projects without a `docs/` directory work fine -- Beadloom operates in zero-doc mode with code-only context (graph nodes, annotations, context oracle).

### beadloom reindex

Full reindex: drops all tables and reloads from scratch.

```bash
beadloom reindex [--full] [--docs-dir DIR] [--project DIR]
```

- `--full` -- force full rebuild (drop all tables and re-create)
- `--docs-dir` -- documentation directory (default: from config.yml or `docs/`)

Default mode is incremental (only changed files). Use `--full` to force complete rebuild.

Order: drop tables -> create schema -> load graph YAML -> index docs -> index code -> resolve imports -> load rules -> build sync state -> populate FTS5 -> take health snapshot.

When no changes are detected, displays current DB totals (nodes, edges, docs, symbols) instead of reindex counts. Warns about missing tree-sitter parsers when symbols == 0.

### beadloom ctx

Get a context bundle for the specified ref_id(s).

```bash
beadloom ctx REF_ID [REF_ID...] [--json|--markdown] [--depth N] [--max-nodes N] [--max-chunks N] [--project DIR]
```

Outputs Markdown by default. `--json` for machine-readable format.

### beadloom graph

Architecture graph visualization. Supports Mermaid, C4-Mermaid, and C4-PlantUML output formats.

```bash
# Full graph in Mermaid format (default)
beadloom graph [--project DIR]

# Subgraph from specified nodes
beadloom graph REF_ID [REF_ID...] [--depth N] [--json]

# C4 architecture diagram (Mermaid C4 syntax)
beadloom graph --format c4 [--level {context,container,component}] [--project DIR]

# C4 architecture diagram (PlantUML C4 syntax)
beadloom graph --format c4-plantuml [--level container] [--project DIR]

# C4 component diagram scoped to a specific container
beadloom graph --format c4 --level component --scope graph [--project DIR]
```

- `--format` -- output format: `mermaid` (default), `c4` (Mermaid C4 syntax), or `c4-plantuml` (C4-PlantUML syntax).
- `--level` -- C4 diagram level (only used with `--format=c4` or `--format=c4-plantuml`):
  - `context` -- System-level nodes only (highest abstraction)
  - `container` (default) -- System and Container nodes
  - `component` -- Children of a specific container (requires `--scope`)
- `--scope` -- ref_id of the container to zoom into when `--level=component`. Required for component-level diagrams.

C4 level assignment uses `part_of` depth: root nodes become Systems, depth 1 becomes Containers, depth 2+ becomes Components. Nodes can override this by setting `c4_level` in their YAML `extra` field. Nodes tagged `external` render as `_Ext` variants; nodes tagged `database` or `storage` render as `Db` variants.

### beadloom status

Index statistics with health trends.

```bash
beadloom status [--json] [--project DIR]
```

Shows Rich-formatted dashboard with: node count (broken down by kind), edges, documents, symbols, per-kind documentation coverage, stale docs, isolated nodes, empty summaries. Includes trend indicators comparing current reindex with previous snapshot. Also displays context metrics: average bundle token size, largest bundle (ref_id + tokens), total indexed symbols.

`--json` -- structured JSON output.

#### status --debt-report

Architecture debt report mode. Aggregates health signals from lint, sync-check, doctor, git activity, and test mapper into a single 0-100 debt score with category breakdown and top offending nodes.

```bash
beadloom status --debt-report [--json] [--fail-if=EXPR] [--category=NAME] [--project DIR]
```

- `--debt-report` -- show architecture debt report instead of the standard status dashboard.
- `--json` -- output the debt report as structured JSON (with `--debt-report`).
- `--fail-if=EXPR` -- CI gate: exit 1 if condition is met. Requires `--debt-report`. Supported expressions:
  - `score>N` -- fail if overall debt score exceeds N.
  - `errors>N` -- fail if rule violation error count exceeds N.
- `--category=NAME` -- filter the debt report to a single category. Accepted names: `rules`, `docs`, `complexity`, `tests` (short names) or `rule_violations`, `doc_gaps`, `test_gaps` (internal names).

The debt score formula combines four categories:
- **Rule Violations** -- weighted count of lint rule errors and warnings.
- **Documentation Gaps** -- undocumented nodes, stale docs, untracked files.
- **Complexity** -- oversized domains (by symbol count), high fan-out nodes, dormant domains.
- **Test Gaps** -- untested domains/features.

Severity classification: `clean` (0), `low` (1-10), `medium` (11-25), `high` (26-50), `critical` (51-100).

Examples:

```bash
# Human-readable Rich output
beadloom status --debt-report

# Machine-readable JSON
beadloom status --debt-report --json

# CI gate: fail if score exceeds 30
beadloom status --debt-report --fail-if=score>30

# CI gate: fail if any lint errors
beadloom status --debt-report --fail-if=errors>0

# Filter to documentation gaps only
beadloom status --debt-report --category=docs
```

### beadloom doctor

Architecture graph validation.

```bash
beadloom doctor [--project DIR]
```

Checks:
- Nodes with empty summary
- Documents not linked to nodes
- Nodes without documentation
- Isolated nodes (no edges)

### beadloom sync-check

Check doc-code synchronization.

```bash
beadloom sync-check [--porcelain] [--json] [--report] [--ref REF_ID] [--project DIR]
```

Exit codes: 0 = all OK, 1 = error, 2 = stale pairs found.

- `--porcelain` -- TAB-separated output for scripts. Format: `status\tref_id\tdoc_path\tcode_path\treason`.
- `--json` -- structured JSON output with summary and pair details. Each pair includes `status`, `ref_id`, `doc_path`, `code_path`, `reason`, and optional `details`.
- `--report` -- ready-to-post Markdown report for CI (GitHub/GitLab).
- `--ref` -- filter results by ref_id.

Human-readable output includes reason-aware formatting:
- `untracked_files` reason: displays list of untracked files in `details`.
- `missing_modules` reason: displays list of missing modules in `details`.
- Other stale reasons (e.g. `symbols_changed`, `content_changed`): displays `reason` next to the code path.

### beadloom sync-update

Review and update stale documentation.

```bash
# Show sync status for a ref_id
beadloom sync-update REF_ID --check [--project DIR]

# Interactive: open stale docs in $EDITOR, mark synced after editing
beadloom sync-update REF_ID [--project DIR]
```

For automated doc updates, use your AI agent (Claude Code, Cursor, etc.) with Beadloom's MCP tools. See `.beadloom/AGENTS.md` for agent instructions.

### beadloom install-hooks

Install git pre-commit hook for synchronization checking.

```bash
# Install (warning mode)
beadloom install-hooks [--mode warn|block] [--project DIR]

# Remove
beadloom install-hooks --remove [--project DIR]
```

### beadloom link

Manage external tracker links on graph nodes.

```bash
# Add a link (label auto-detected from URL)
beadloom link REF_ID URL [--label LABEL] [--project DIR]

# List links for a node
beadloom link REF_ID [--project DIR]

# Remove a link
beadloom link REF_ID --remove URL [--project DIR]
```

Auto-detected labels: `github`, `github-pr`, `jira`, `linear`, `link` (fallback).

### beadloom diff

Show graph changes since a git ref.

```bash
beadloom diff [--since REF] [--json] [--project DIR]
```

Compares current graph YAML with state at the given ref (default: HEAD). Exit code 0 = no changes, 1 = changes detected.

### beadloom export

Export the indexed graph as a deterministic cross-repo federation artifact (JSON).

```bash
beadloom export [--out FILE] [--project DIR]
```

Reads the indexed graph from SQLite (read-only) and emits a self-describing JSON artifact (schema v1): `repo`, `commit_sha`, `exported_at`, `generator`, and the `nodes` / `edges` arrays (each carrying `lifecycle`; edges may carry AMQP `contract` meta). The `edges` array unions the local `edges` table and the cross-repo `foreign_edges` table so declared `@repo:` links survive. Output is byte-deterministic (sorted nodes/edges + sorted keys). `--out` writes to a file; otherwise prints to stdout. Exits 1 if the database is missing (run `beadloom reindex` first). See the [federation SPEC](../domains/graph/features/federation/SPEC.md).

### beadloom federate

Aggregate ≥2 satellite export artifacts into one federated graph (hub).

```bash
beadloom federate EXPORT1.json EXPORT2.json [...] [--project DIR]
```

Composes the namespaced node/edge union (`@repo:ref_id` identity), resolves `@repo:` foreign refs, assigns a three-valued intent-vs-reality verdict per edge (`OK` / `DRIFT` / `EXPECTED` / `CLEANUP_CANDIDATE` / `UNDECLARED` / `DEAD`), reconciles AMQP contracts (confirmed both-sides vs one-sided), and reports per-satellite staleness (commit_sha + age). Writes `.beadloom/federated.json` + `.beadloom/federated.txt` in the hub project root and echoes the report (with any DRIFT) to stdout. Requires at least two artifacts; exits 1 otherwise or if a file is not a JSON object. The `--fail-on <csv>` landscape gate (writes artifacts first, then exits 1 on matching verdicts) prints an agent-actionable `fix:` hint per failing verdict (BREAKING / ORPHANED_CONSUMER / UNDECLARED_PRODUCER / DRIFT). See the [federation SPEC](../domains/graph/features/federation/SPEC.md).

### beadloom snapshot

Architecture snapshot management. Snapshots capture the current graph state (nodes, edges, symbols) for later comparison.

#### beadloom snapshot save

Save the current graph state as a snapshot.

```bash
beadloom snapshot save [--label LABEL] [--project DIR]
```

- `--label` -- optional label for the snapshot (e.g. `v1.6.0`).

#### beadloom snapshot list

List all saved architecture snapshots.

```bash
beadloom snapshot list [--json] [--project DIR]
```

Shows snapshot ID, label, creation time, and counts (nodes, edges, symbols). `--json` for structured output.

#### beadloom snapshot compare

Compare two architecture snapshots to see what changed.

```bash
beadloom snapshot compare OLD_ID NEW_ID [--json] [--project DIR]
```

Displays added/removed/changed nodes and added/removed edges between the two snapshots. Both `OLD_ID` and `NEW_ID` are required integer snapshot IDs.

### beadloom search

Search nodes and documentation by keyword.

```bash
beadloom search QUERY [--kind {domain,feature,service,entity,adr}] [--limit N] [--json] [--project DIR]
```

Uses FTS5 full-text search when available, falls back to SQL LIKE. Run `beadloom reindex` first to populate the search index.

### beadloom why

Show impact analysis for a node -- upstream dependencies and downstream dependents.

```bash
beadloom why REF_ID [--depth N] [--json] [--reverse] [--format {panel,tree}] [--project DIR]
```

- `--reverse` -- focus on what this node depends on (upstream only) instead of the default full analysis.
- `--format` -- output format: `panel` (Rich panels, default) or `tree` (plain text for CI/scripting).

### beadloom lint

Run architecture lint rules against the project.

```bash
beadloom lint [--format {rich,json,porcelain,github}] [--strict] [--fail-on-warn] [--no-reindex] [--project DIR]
```

Checks cross-boundary imports against rules defined in `rules.yml`. Format auto-detects: `rich` if TTY, `porcelain` if piped.

`--format` options:
- `rich` -- human-readable text (default on a TTY).
- `json` -- structured output: a backward-compatible `violations` array (now with an additive `remediation` key), a stable agent-actionable `findings` array (`{kind, rule, severity, locations, why, remediation}`), and a `summary` object. Deterministic (violations are pre-sorted).
- `porcelain` -- one colon-separated line per violation (default when piped).
- `github` -- GitHub Actions workflow commands (`::error file=…,line=…::<rule>: <message> — <remediation>`) so violations surface as inline PR annotations; warnings use `::warning`.

Each violation carries an agent-actionable `remediation` hint derived per rule kind (deny/forbid → remove/reroute the import or edge; cycle → break the cycle at a named edge; layer → invert the dependency or extract a shared abstraction; cardinality → split the node; require → add the required edge).

Exit codes: 0 = clean (or violations without `--strict`/`--fail-on-warn`), 1 = violations with `--strict` (errors only) or `--fail-on-warn` (any violation), 2 = configuration error.

### beadloom tui

Launch interactive terminal dashboard (primary command).

```bash
beadloom tui [--project DIR] [--no-watch]
```

Multi-screen architecture workstation with graph explorer, debt gauge, lint panel, doc status, and keyboard actions. Requires: `pip install beadloom[tui]`.

- `--no-watch` -- disable file watcher (for CI/testing)

### beadloom ui

Launch interactive terminal dashboard (alias for `tui`).

```bash
beadloom ui [--project DIR] [--no-watch]
```

Backward-compatible alias for `beadloom tui`. Requires: `pip install beadloom[tui]`.

### beadloom watch

Watch files and auto-reindex on changes.

```bash
beadloom watch [--debounce MS] [--project DIR]
```

Monitors graph YAML, documentation, and source files. Graph changes trigger full reindex; other changes trigger incremental. Requires: `pip install beadloom[watch]`.

### beadloom docs generate

Generate documentation skeletons from the architecture graph.

```bash
beadloom docs generate [--project DIR]
```

Creates `docs/` tree: `architecture.md`, domain READMEs, service pages, feature SPECs. Never overwrites existing files. All generated files include `<!-- enrich with: beadloom docs polish -->` markers.

### beadloom docs site

Generate a VitePress content tree from the architecture graph.

```bash
beadloom docs site [--out DIR] [--federated FILE] [--project DIR]
```

Reads the indexed graph read-only and emits, under `--out` (default `site/`):

- `index.md` -- architecture overview: domain/service/feature counts, the top-level C4/Mermaid diagram, and a health summary line (nodes/edges/docs/coverage/stale).
- per-node pages (`domains/<ref>.md`, `services/<ref>.md`, `features/<ref>.md`) -- each with summary, source, public symbols, `part_of`/`depends_on`/`uses` edges rendered as Markdown links to the other node pages, linked hand-written docs, and an embedded scoped C4/Mermaid diagram.
- `dashboard.md` + `dashboard.data.json` -- **Showcase A**, the AaC/DocAsCode metrics dashboard (lint count + severity, debt score + trend, doc coverage / sync-check freshness / stale count, doctor pass-fail, and an optional federated rollup). Every number comes from the SAME code path as its gate (`lint` / `debt-report` / `sync-check` / `doctor` / `federate`) -- honest by construction.
- `landscape.md` -- **Showcase B**, the 🌟 cross-repo landscape map: a Mermaid diagram of the federated contract graph (with `--federated`) or the local graph (without), edges labelled by their verdict, a `classDef` health overlay, and clickable nodes linking to their intra-repo page.
- `docs/**` + `docs/index.md` -- **Showcase C**, the published validated documentation: the REAL `docs/**` tree copied verbatim (the source of truth, rendered as-is) with a per-doc `doc_sync` freshness badge injected into the COPY only. The source `docs/` is NEVER mutated.
- `.vitepress/config.generated.mjs` -- the nav/sidebar config imported by the committed VitePress scaffold (`site/.vitepress/config.mjs`); sections: Dashboard / Architecture / Landscape / Documentation.

Beadloom produces, VitePress renders. Output is deterministic (sorted, stable frontmatter, no wall-clock in the diffed output) and is NEVER written into the source `docs/` tree -- only under `--out`. `--federated` takes a `federate` hub artifact (`federated.json`) and drives the Showcase B landscape map. To render: `cd site && npm install && npm run docs:build` (preview with `npm run docs:preview`). See the [VitePress Site guide](../guides/vitepress-site.md).

### beadloom docs audit

Detect stale numeric facts in project documentation.

```bash
beadloom docs audit [--json] [--fail-if EXPR] [--stale-only] [--verbose] [--path GLOB]... [--project DIR]
```

Scans markdown documentation for numeric mentions (version strings, counts) and compares them against ground-truth facts collected from the project infrastructure (manifest files, graph DB, MCP tools, CLI commands).

- `--json` -- structured JSON output with facts, findings, and unmatched mentions.
- `--fail-if` -- CI gate expression. Supported format: `stale>N` or `stale>=N`. Exits with code 1 when condition is met.
- `--stale-only` -- show only stale findings (omit fresh matches).
- `--verbose` -- include extra detail (unmatched mentions, fact sources).
- `--path` -- override default scan paths with custom glob patterns (can be specified multiple times).

Exit codes: 0 = no issues (or below threshold), 1 = `--fail-if` condition met.

Examples:

```bash
# Human-readable Rich output
beadloom docs audit

# CI gate: fail if any stale docs
beadloom docs audit --fail-if=stale>0

# JSON output for scripting
beadloom docs audit --json --stale-only

# Scan only specific paths
beadloom docs audit --path "docs/**/*.md" --path "README.md"
```

### beadloom docs polish

Generate structured data for AI-driven documentation enrichment.

```bash
beadloom docs polish [--format {text,json}] [--ref-id REF_ID] [--project DIR]
```

- `text` (default) -- human-readable summary with enrichment instructions
- `json` -- structured JSON with nodes (symbols, dependencies, existing docs), Mermaid diagram, and AI prompt
- `--ref-id` -- filter to a single node

### beadloom prime

Output compact project context for AI agent injection.

```bash
beadloom prime [--json] [--update] [--project DIR]
```

- `--json` -- structured JSON output
- `--update` -- regenerate `.beadloom/AGENTS.md` before outputting context

Returns architecture summary, health status (stale docs, lint violations), architecture rules, domain list, and agent instructions.

### beadloom setup-rules

Create IDE rules files that reference `.beadloom/AGENTS.md`.

```bash
# Auto-detect installed IDEs
beadloom setup-rules [--project DIR]

# Target a specific IDE
beadloom setup-rules --tool {cursor,windsurf,cline} [--project DIR]
```

Creates thin adapter files (`.cursorrules`, `.windsurfrules`, `.clinerules`) that instruct agents to read AGENTS.md.

### beadloom config-check

AgentConfigAsCode freshness gate: verify that generated agent-config is in sync with the graph.

```bash
beadloom config-check [--project DIR]   # exit 1 on drift, 0 when clean
beadloom config-check --fix [--project DIR]  # regenerate drifted artifacts, then re-check
```

Re-runs the same `setup-rules --refresh` generator in memory and diffs its output against on-disk content for `.beadloom/AGENTS.md`, the auto-managed sections of `.claude/CLAUDE.md`, and present IDE adapter files. Checks ONLY auto-managed regions — editing user-authored prose (the AGENTS.md `custom` block, CLAUDE.md content outside the `auto-start`/`auto-end` markers) never trips it. Prints which file drifted, why, and the remediation (`beadloom setup-rules --refresh`); absent target files are skipped. `--fix` regenerates via the refresh path and re-checks. Delegates to `onboarding/config_sync.py:check_config_drift()`.

### beadloom ci

The unified enforcement gate — the single CI convergence point (principle 7: identical for Cursor / Claude Code / human authors).

```bash
beadloom ci [--hub EXPORT.json ...] [--fail-on CSV] [--format {rich,json,github}] [--no-reindex] [--project DIR]
```

Composes the existing checkers, in order, into ONE verdict with a single exit code (0 = all steps passed, 1 = any step failed):

1. `reindex` (incremental) — unless `--no-reindex`.
2. `lint --strict` — architecture boundary rules at error severity.
3. `sync-check` — doc↔code freshness (stale pairs fail).
4. `config-check` — AgentConfigAsCode drift.
5. `doctor` — graph/data integrity; ONLY `ERROR`-severity checks fail the gate (WARNING/INFO advisories never block — no false gate).
6. `federate --fail-on` — the cross-service landscape gate, only when `--hub` export(s) are given (safe-default fail-set `breaking,drift,orphaned_consumer,undeclared_producer`; no-false-gate verdicts rejected).

**Honest gate (the Phase-0 lesson):** the report names every step that ran and its outcome — `PASS` / `FAIL` / `SKIP` — never a green that silently skipped a step. **No short-circuit:** all steps run and ALL findings are collected even after an earlier failure, so one run surfaces every problem. `--format` applies uniformly across every step; findings share the agent-actionable `{kind, rule, severity, locations, why, remediation}` shape (`github` emits valid `::error file=<path>,line=<n>::<msg>` workflow-command annotations, matching `lint --format github`; `json` emits `{ok, steps[]}`). The per-repo `beadloom-aac-lint.yml` reindex+lint+sync steps collapse into one `beadloom ci` call. Orchestration lives in `application/gate.py:run_ci_gate()`; the CLI only parses options and renders.

### beadloom setup-mcp

Configure MCP server for your editor.

```bash
beadloom setup-mcp [--tool {claude-code,cursor,windsurf}] [--project DIR]
beadloom setup-mcp --remove [--tool {claude-code,cursor,windsurf}] [--project DIR]
```

- `claude-code` (default) -- `.mcp.json` in project root
- `cursor` -- `.cursor/mcp.json` in project root
- `windsurf` -- `~/.codeium/windsurf/mcp_config.json` (global)

### beadloom mcp-serve

Launch MCP stdio server.

```bash
beadloom mcp-serve [--project DIR]
```

## API

Module `src/beadloom/services/cli.py`:

- `main` -- Click group: `beadloom [--verbose|-v] [--quiet|-q] [--version] COMMAND`
- `reindex` -- rebuild SQLite index (incremental by default, `--full` for complete rebuild)
- `ctx` -- get context bundle for ref_id(s)
- `graph` -- show architecture graph (Mermaid, C4-Mermaid, C4-PlantUML, or JSON) with `--format`, `--level`, `--scope` options
- `export` -- export the indexed graph as a deterministic federation artifact (JSON, schema v1) with `--out`
- `federate` -- aggregate >=2 satellite export artifacts into one federated graph (drift verdicts + staleness)
- `doctor` -- run validation checks
- `status` -- show index statistics with health trends and context metrics; `--debt-report` mode with `--fail-if`, `--category` flags
- `sync_check` -- check doc-code sync with reason/details (reason-aware output for `untracked_files`, `missing_modules`, `symbols_changed`)
- `sync_update` -- review and update stale docs interactively
- `install_hooks` -- install/remove pre-commit hook
- `link` -- manage external tracker links
- `search` -- FTS5 search with LIKE fallback
- `why` -- impact analysis (upstream + downstream) with `--reverse` and `--format {panel,tree}`
- `diff_cmd` -- graph changes since a git ref
- `snapshot` -- Click group for snapshot commands (`save`, `list`, `compare`)
- `snapshot_save` -- save current graph state as a snapshot
- `snapshot_list` -- list all saved snapshots
- `snapshot_compare` -- compare two snapshots (added/removed/changed nodes and edges)
- `lint` -- architecture lint with `--strict`, `--fail-on-warn`, auto-format detection, agent-actionable `remediation`, and `--format {rich,json,porcelain,github}` (GitHub annotations)
- `prime` -- compact project context for AI agents
- `setup_mcp` -- configure MCP server for editor
- `setup_rules` -- create IDE rules files
- `config_check` -- AgentConfigAsCode drift gate (`--fix` regenerates); reuses the `setup-rules --refresh` generator
- `ci` -- unified enforcement gate composing reindex -> lint -> sync-check -> config-check -> doctor -> (optional `--hub`) federate into one exit code; honest per-step PASS/FAIL/SKIP; uniform `--format {rich,json,github}` (github = valid `::error file=,line=` annotations); delegates to `application/gate.py:run_ci_gate()`
- `mcp_serve` -- run MCP stdio server
- `docs` -- Click group for doc commands (`generate`, `polish`, `audit`)
- `tui` -- launch TUI dashboard (primary command, multi-screen with `--no-watch`)
- `ui` -- launch TUI dashboard (alias for `tui`)
- `watch_cmd` -- watch files and auto-reindex
- `init` -- project initialization (bootstrap, import, interactive, non-interactive with `--yes`/`--mode`/`--force`)

All commands accept `--project DIR` to specify the project root. The current directory is used by default.

## Testing

CLI is tested via `click.testing.CliRunner`. Each command has a corresponding test file in `tests/test_cli_*.py`: `test_cli_reindex.py`, `test_cli_ctx.py`, `test_cli_graph.py`, `test_cli_status.py`, `test_cli_sync_check.py`, `test_cli_sync_update.py`, `test_cli_hooks.py`, `test_cli_link.py`, `test_cli_docs.py`, `test_cli_mcp.py`, `test_cli_watch.py`, `test_cli_diff.py`, `test_cli_why.py`, `test_cli_lint.py`, `test_cli_init.py`, `test_cli_snapshot.py`, `test_cli_config_check.py`.
