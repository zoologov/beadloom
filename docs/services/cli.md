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

**`--bootstrap` also appends an ignore block to the project's `.gitignore`, once** (BDL-061.35). Before it, Beadloom wrote an ignore entry nowhere, so an adopter collected untracked churn from the very first `reindex`. The block names the derived state only — `.beadloom/**/*.db{,-wal,-shm}` and `.beadloom/guard-firings.jsonl` — and each pattern carries its reason in the file; the graph under `.beadloom/_graph/` and `flow.yml` are source and stay committable. It is **written once and never rewritten**: a run that finds the marker does nothing, so deleting a line is a real override rather than an edit the next run undoes (a team that wants the guard firing record committed removes that line, once). Nothing is written outside a git working tree, a pattern the project already declares is not duplicated, and the project's own lines are untouched. The write is reported (`✓ Ignored: N generated path(s) …`), because silently editing someone's `.gitignore` is its own surprise.

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

The incremental path re-extracts imports for the code files it touched, deletes the imports of files that disappeared, and rebuilds the derived `depends_on` edge set (marked `extra.derived='imports'`, so a graph-declared edge is never collateral damage). A boundary violation introduced between two incremental runs is therefore caught by `lint` without a full rebuild. Two counters in the summary do not describe that work: `Imports:` and `Rules:` are only populated on the `--full` path and print `0` on an incremental run that did refresh them.

**Reindex sets the freshness baseline.** `sync_state` is (re-)established from the tree being indexed, so a reindex into a fresh or deleted database makes every declared pair fresh by construction. That is why doc freshness must be checked after an *incremental* reindex on an existing index — see `beadloom sync-check`.

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
beadloom sync-check [--porcelain] [--json] [--report] [--ref REF_ID] [--since GIT_REF]
                    [--record-surface] [--project DIR]
```

Exit codes: 0 = all OK, 1 = error, 2 = a pair is stale **or missing**.

- `--porcelain` -- TAB-separated output for scripts. Format: `status\tref_id\tdoc_path\tcode_path\treason`.
- `--json` -- structured JSON output with summary and pair details. Each pair includes `status`, `ref_id`, `doc_path`, `code_path`, `reason`, `baseline`, and optional `details`.
- `--report` -- ready-to-post Markdown report for CI (GitHub/GitLab).
- `--ref` -- filter results by ref_id.
- `--record-surface` -- record the declared documentation surface (pair + declared-doc counts) to the committed `.beadloom/sync-surface.json`. A later run compares against it and says so when the surface SHRANK; no ordinary run rewrites it, because a check that silently re-records the number it checks against re-attests without evidence.
- `--since GIT_REF` -- compute drift against the code state at a **git ref** (e.g. the push's parent commit) instead of the stored `sync_state` baseline. Reports pairs whose code drifted since the ref while the doc was not correspondingly updated. This makes drift detection work on a **fresh CI checkout**: a clean clone reindexes from scratch and re-baselines `sync_state` to the just-pushed code, so without a ref baseline `sync-check` sees 0 stale even when the push left a doc behind. Mirrors `beadloom diff --since`. Used by the AI tech-writer harness (it passes the push parent — `github.event.before` / `$CI_COMMIT_BEFORE_SHA`, falling back to `HEAD~1`).

**What a green count covers.** A node that declares `docs:` contributes pairs from its `# beadloom:` annotations or, when those yield none, from the files its `source:` owns — the pairing is independent of node kind. Whatever is still uncovered is listed BY NAME with a reason, as an advisory line that never changes the exit code: `no_indexed_code` (no indexed code under the node's source), `files_owned_by_nested_nodes` (every file under it belongs to a more specific node) and `no_source` (the node declares no source path). `--json` carries the same list in `data.unchecked` with `summary.unchecked`; `--porcelain` prints one `unchecked` line per unchecked doc.

Measured on this repository: of 279 declared pairs, 275 are checked and the other 4 are listed with their reason.

**Four verdicts, because unverifiable is not clean.** `ok` and `stale` are outcomes of a comparison that happened. `missing` (the doc file, the code file, or a doc the graph DECLARES is not on disk) fails the check at exit 2 — the gate is not satisfied by having less to check. `unverified` (`reason=no_baseline`) means nothing could be compared; it is printed as `[not verified]`, counted separately, and never counted as fresh. Every pair also reports `baseline` — `index`, `git:HEAD` or `none` — so a green result says what it was green against.

**Where the baseline lives, and why a rebuild no longer blinds it.** `.beadloom/beadloom.db` is a cache, not the record: a database built from scratch used to store the current tree AS the baseline, so `sync-check` reported every pair fresh, including pairs whose doc was never updated (measured before the fix: incremental reindex → exit 2 with 6 stale; `rm .beadloom/beadloom.db*` + reindex → exit 0 with 0 stale, same tree). Each pair now records where its baseline came from, and a pair whose baseline was fabricated at index-build time is corroborated against **git `HEAD`** — the baseline a rebuild cannot destroy, because it is committed. Where git cannot answer (not a repository, no commit, no git binary), the pair reads `unverified` rather than fresh. `--since <ref>` remains the strongest form and is what the CI harness passes on a fresh checkout. A clean database is still the right instrument for `lint`, and it is no longer a way to get a green `sync-check` for free.

**The count is part of the contract.** `--record-surface` writes `.beadloom/sync-surface.json` (committed, so a rebuild cannot lose it). A later run whose declared surface FELL says so by name — `declared surface SHRANK since it was recorded: 275 → 269 pair(s)` — instead of quietly printing the smaller number. It is a warning, not a verdict: the cause that matters (a declared doc that is gone) fails on its own.

Human-readable output includes reason-aware formatting:
- `missing` status: `[missing]` with which side is gone (`the linked doc file is gone`, `the paired code file is gone`, `declared in the graph, not on disk`).
- `unverified` status: `[not verified]` with the reason there was no baseline.
- `untracked_files` reason: displays list of untracked files in `details`.
- `missing_modules` reason: displays list of missing modules in `details`.
- Other stale reasons (e.g. `symbols_changed`, `content_changed`): displays `reason` next to the code path.

**Reference surface drift (advisory).** A high-traffic overview doc can opt in to
freshness against a coarse interface surface with an in-doc annotation near its
top:

```markdown
<!-- beadloom:watches=cli,graph,flow.yml -->
```

The watched surfaces are `cli` (the Click command + flag tree), `graph` (the
node + edge identity set), and `flow.yml` (the normalized `.beadloom/flow.yml`).
`reindex` baselines the aggregate hash of the declared surfaces; `sync-check`
recomputes it and, when the surface changed, emits a pair with `reason =
surface_drift` and **severity warning**. In `--json`, `summary.surface_drift`
and a `references[]` array carry these pairs (stored-baseline mode only; the
`--since` shape is unchanged). Surface drift is advisory — it never changes the
exit code or fails `beadloom ci`; it asks a human to re-read the overview and
clear it with `sync-update`.

### beadloom sync-update

Review and update stale documentation.

```bash
# Show sync status for a ref_id
beadloom sync-update REF_ID --check [--project DIR]

# Interactive: open stale docs in $EDITOR, mark synced after editing
beadloom sync-update REF_ID [--project DIR]

# Non-interactive: re-baseline freshness without an editor or prompt
beadloom sync-update REF_ID --yes [--project DIR]

# Non-interactive, fixpoint loop: re-baseline every currently-stale ref
beadloom sync-update --all --yes [--project DIR]
```

`--yes` (`-y`) records that the doc(s) for the ref match the code now (recomputes
file hashes + symbols hash, sets `status='ok'`), prints a concise summary, and
exits 0 — no editor, no prompt. This is the primitive a CI/script fixpoint loop
uses to re-baseline freshness after a doc is rewritten; it is the same operation
the interactive path performs after an edit. `--all` re-baselines every ref
`sync-check` currently flags stale (deterministic; requires `--yes`).

`REF_ID` also accepts the **path of a reference doc** (one carrying a
`watches:` annotation). In that case `sync-update` recomputes and stores the
doc's aggregate surface hash, clearing a `surface_drift` warning — the same
re-attestation as a symbol pair.

**`--check` never writes**, on either kind of argument:

```bash
$ beadloom sync-update docs/architecture.md --check
  [surface drift] docs/architecture.md watches cli, graph
```

It did until BDL-061 S3b. The reference-doc branch was reached *before* the
`--check` guard, so the flag whose whole contract is "tell me, do not change
anything" re-baselined the doc and printed `Re-baselined reference doc <path>`;
measured on this repository, the drift count fell from 7 to 6 on a run that asked
for a report, and the next `sync-check` read clean for a reason nobody recorded.
That is BDL-UX #147 (`lint` mutating its index) in another command, and #163
(re-attesting without evidence) reached by accident rather than by choice
(BDL-UX #189).

For automated doc updates, use your AI agent (Claude Code, Cursor, etc.) with Beadloom's MCP tools. See `.beadloom/AGENTS.md` for agent instructions.

### beadloom install-hooks

Install (or remove) Beadloom's git hooks: a **pre-commit** hook (the lighter
synchronization check) and a **pre-push** hook (the authoritative blocking
**Beadloom Gate**). By default both are installed.

```bash
# Install BOTH hooks (pre-commit warn mode + pre-push Gate)
beadloom install-hooks [--mode warn|block] [--project DIR]

# Install only one
beadloom install-hooks --pre-commit [--mode warn|block] [--project DIR]
beadloom install-hooks --pre-push [--project DIR]

# Remove (both, or the selected one)
beadloom install-hooks --remove [--pre-commit|--pre-push] [--project DIR]
```

**Pre-commit hook** runs, in order: ruff lint, mypy, `beadloom sync-check`
(`--mode warn` reports stale docs; `--mode block` fails the commit on stale docs),
and finally the **ACTIVE / tracker coherence** step. That last step is a guarded
auto-fix: it runs only when BOTH `bd` and `beadloom` are on `PATH`, calls
`beadloom active-sync` to reconcile each epic's ACTIVE.md bead-status table from
`bd` and re-export `.beads/issues.jsonl`, then restages the touched
`.claude/development/docs/features/**` files and `.beads/issues.jsonl` so the
commit is coherent **by construction**. It never blocks the commit (it runs even
in `block` mode without affecting the exit code), and in any repo without `bd` —
or without ACTIVE tables — the block is a complete no-op (see
[`active-sync`](#beadloom-active-sync)).

**Pre-push hook (Beadloom Gate)** is the authoritative blocking enforcement of
the hard invariant *"no code in `main` without current docs."* On every push it
runs the full Gate (`beadloom ci` — incremental reindex → `lint --strict`
(module-coverage included) → sync-check → docs-audit → config-check → doctor) and **exits
non-zero to block the push** on red, printing an
actionable message ("Beadloom Gate failed … run the tech-writer (or
`/coordinator`) then re-push; `git push --no-verify` to override"). It is
**fail-safe**: in any repo without `beadloom` on `PATH` the hook is a safe no-op
and never blocks. The full Gate lives in pre-push (not duplicated on every commit)
because pushes are less frequent than commits; the pre-commit hook stays the
lighter warn/block check. `--no-verify` is the documented (discouraged) escape
hatch.

Both hooks are idempotent — re-running `install-hooks` overwrites cleanly.

### beadloom active-sync

Reconcile each epic's `ACTIVE.md` bead-status table from `bd` — the source of
truth — and re-export the tracked `.beads/issues.jsonl`.

```bash
# Fix mode (default): rewrite drifted Status cells + bd export the jsonl
beadloom active-sync [--epic KEY] [--no-export] [--project DIR]

# Check mode: report drift without writing; exit 1 if any drift, 0 if clean
beadloom active-sync --check [--epic KEY] [--project DIR]

# Machine-readable JSON (works with --check or fix mode)
beadloom active-sync --json [--check] [--epic KEY] [--project DIR]
```

For every epic's `ACTIVE.md`, it finds the bead-status table and rewrites each
Status cell to match the bead's current `bd` status (`closed → ✓ done`,
`in_progress → in progress`, `open`/`ready → ready`, and `blocked` for an `open`
bead with an open blocker). A richer coordinator note is preserved when its state
already agrees (e.g. `✓ done (PASS-WITH-FIXES)` is left intact for a `closed`
bead). Only Status cells change — prose, the Progress Log, and other columns are
byte-preserved. The reconcile core (`application/active_table.py`,
`reconcile_active_tables` / `bd_status_to_cell`) is the same one the MCP S4
process-tools (`checkpoint` / `complete_bead`) use.

This is the mechanism that keeps `ACTIVE.md` honest **by construction** — wired
into the pre-commit hook (above), the coordinator no longer hand-edits
bead-status rows; the table is reconciled from `bd` on every commit.

- `--epic KEY` — reconcile only `features/<KEY>/ACTIVE.md` (default: every
  `features/*/ACTIVE.md`).
- `--check` — report drift on a throwaway copy without writing; **exit 1** if any
  row would change, **exit 0** when clean. Never writes and never exports.
- `--json` — machine-readable output: `{ "changed_files": [...], "drifted_rows":
  [ { "path", "bead_id", "old", "new" }, ... ] }`.
- `--no-export` — skip the `bd export` jsonl sync (fix mode only).
- `--project DIR` — project root (default: current directory).

In fix mode (no `--check`), after rewriting it best-effort runs
`bd export -o .beads/issues.jsonl` — but only when that file is already
git-tracked — so the tracked tracker artifact stays honest across
branch/squash-merge. `--no-export` skips that step.

**No-op contract.** `active-sync` exits **0 and writes nothing** when there is no
`ACTIVE.md` with a bead-status table, OR when `bd` is unavailable, OR when
`.beads/issues.jsonl` is not tracked (the export is skipped). So a non-flow repo —
or any adopter without the agentic flow — is never affected; the command (and the
hook step that calls it) is a safe out-of-the-box no-op.

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

- `--label` -- optional label for the snapshot (e.g. `pre-refactor`).

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
- `json` -- structured output: a backward-compatible `violations` array (now with an additive `remediation` key), a stable agent-actionable `findings` array (`{kind, rule, severity, locations, why, remediation}`), a `suppressed` array naming every crossing a `forbid_import` exemption excused, and a `summary` object (whose `violations_suppressed` is that array's length). Deterministic (violations are pre-sorted).
- `porcelain` -- one colon-separated line per violation (default when piped).
- `github` -- GitHub Actions workflow commands (`::error file=…,line=…::<rule>: <message> — <remediation>`) so violations surface as inline PR annotations; warnings use `::warning`.

Each violation carries an agent-actionable `remediation` hint derived per rule kind (deny/forbid → remove/reroute the import or edge; cycle → break the cycle at a named edge; layer → invert the dependency or extract a shared abstraction; cardinality → split the node; require → add the required edge).

Exit codes: 0 = clean (or violations without `--strict`/`--fail-on-warn`), 1 = violations with `--strict` (errors only) or `--fail-on-warn` (any violation), 2 = configuration error or missing index.

**A deny rule can only check a file it can place.** An import's source end is attributed to a node by annotation OR by ownership — the same most-specific-`source` rule that derives the `depends_on` edges — so a file with no annotation, or one written where the extractor could not read it, is no longer invisible to every deny rule (measured before the fix on this repository: 22 of 128 import-source files, BDL-061.50). What still belongs to no node is counted rather than skipped: `Files: N scanned, M imports resolved, K attributable to no node` on the rich header, `summary.files_unattributed` in `--format json`, and the same clause on the no-violations summary line. The clause is absent when K is zero. A deny rule that never saw a file did not clear it.

**A rule that cannot check anything reports itself.** All nine rule types the loader dispatches are covered: a matcher that selects no node, a `has_edge_to` naming a node the graph does not contain, an edge kind that never runs between two layered nodes, a `check` with no threshold set, a `from:`/`to:` glob matching zero candidates anywhere in the index, a `source_root` with no module under it. Each is a `rule_liveness` finding, always `warn` — it describes the configuration rather than the code, so one mistyped glob cannot turn an adopter's green project red — and it is printed by default, typed in `--format json` as `kind: rule_liveness`, and counted in `summary.rules_inert`. The rich summary line carries the count only when it is non-zero (`N rules evaluated, M of them unable to check anything`), so the advertised rule count cannot over-claim while the everyday line keeps its shape (BDL-061.48). Two silences are deliberate and are properties of the INDEX rather than of any rule: an index with zero resolved imports makes every `deny` rule inert, which the header's `0 imports resolved` already says, and an empty graph silences the pass entirely so a fresh clone does not light up nine warnings.

**What an exemption excused is part of the answer.** A `forbid_import` rule may carry `exempt:` entries that baseline a pre-existing crossing (see the [rule-engine SPEC](../domains/graph/features/rule-engine/SPEC.md)). Every run says how many crossings they suppressed — `", N crossings suppressed by an exemption"` on the summary line, `violations_suppressed` plus the `suppressed` array under `--format json`, and the same clause on the `0 violations, N rules evaluated` line printed when a piped run has nothing to report. Without it, `0 violations` reads as "nothing crossed" when it means "what crossed was excused" (BDL-061.49). An entry whose `until:` leads with an ISO date that has passed, and which is still suppressing something, is reported as a `rule_liveness` finding (`warn`); it keeps suppressing, so no build reddens because a day passed. `--fail-on-warn` is the lever for a project that wants that deadline enforced.

Without `--strict` the exit code stays 0 even when error-severity violations were printed. That is deliberate — changing it would turn an adopter's green pipeline red on upgrade — so `lint` names the omission on stderr instead (`warning: N error-severity violation(s) found, but the exit code stays 0 without --strict`).

**Which form writes the index.** Plain `beadloom lint` reindexes first and therefore WRITES `.beadloom/beadloom.db` (measured: its sha256 changes). This is by design: the default must never lint a stale graph. `--no-reindex` is the read-only form — it leaves `beadloom.db` byte-identical (measured under both `journal_mode=wal` and `journal_mode=delete`) and refuses a missing index at exit 2 with `index not found … Run 'beadloom reindex' first` rather than creating one and reporting `0 violations` against it. Two qualifications, both measured: on a WAL index the read-only form still creates and leaves the `beadloom.db-wal` / `beadloom.db-shm` sidecars, so byte-identity is a property of the FILE and not of `.beadloom/`; and `--no-reindex` answers about the INDEX rather than about the working tree, so with a stale index it reports `0 violations` over a boundary violation that plain `lint --strict` catches on the same tree (BDL-UX, `beadloom-mr2l`). Use it when you have just reindexed, or when the read-only property is what you need.

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

Scans markdown documentation for numeric mentions (version strings, counts) and compares them against ground-truth facts collected from the project infrastructure (manifest files, graph DB, MCP tools, CLI commands). The audit is stable and runs as the **docs-audit step inside `beadloom ci`**, where it blocks the gate on `stale>0`.

- `--json` -- structured JSON output with facts, findings, unmatched mentions, per-fact `coverage`, `unverified_facts` and the `scan_surface`.
- `--fail-if` -- CI gate expression. Supported formats: `stale>N` / `stale>=N` (mentions that disagree with ground truth) and `unverified>N` / `unverified>=N` (declared facts the run checked nothing for). Exits with code 1 when the condition is met.
- `--stale-only` -- show only stale findings (omit fresh matches).
- `--verbose` -- include extra detail: unmatched mentions, the documents that were not read (with the reason each was skipped), and the ones scanned for versions only.
- `--path` -- override default scan paths with custom glob patterns (can be specified multiple times).

Exit codes: 0 = no issues (or below threshold), 1 = `--fail-if` condition met.

**What a green audit covers.** `N mention(s) fresh` counts what the audit FOUND, not what it
CHECKED, and the two were measured nine-fold apart on this repo: nine declared facts, thirteen
verifications, all thirteen of the same fact (BDL-UX #173). Every declared fact therefore
carries its own coverage — `verified` (something was compared), `not_covered` (no document
states it) or `unreadable` (the extractor cannot read a claim of that value at all, with the
reason) — printed against the fact in the `Ground Truth` block and summarised on one line:

```
2 of 9 declared fact(s) verified; NOT VERIFIED: cli_command_count, edge_count, ...
46 document(s) scanned, 33 not read, 1 scanned for versions only (file-type heuristic)
```

A fact nothing was found for is never counted as passing. Coverage does not fail the gate —
documentation is not required to state every fact — but `--fail-if unverified>N` makes it
enforceable for a project that wants it.

**What counts as a claim.** A line is split on whitespace and only a token whose whole core is a number is a candidate — all digits, or digits in thousands groups (`6,390`, read whole as `6390`). A number inside a larger token is an identifier rather than a claim (`BDL-061.33`, `v2.2.0`, `utf-8`) and is never extracted; markdown emphasis, brackets and trailing punctuation around the token are stripped first. A claim also reaches only to the end of its own clause: a modifier or a noun on the far side of `,` `;` `:` or a dash belongs to the rest of the sentence, so `The graph holds 316 edges, one per import.` is read (the `per` is not modifying the count) while the `14` in `exposes 18 tools: 14 over the graph` is not (it is a breakdown, not the total). See `docs/domains/doc-sync/features/docs-audit/SPEC.md` for the layer model and the declared blind spots.

**Tuning false positives.** The audit masks dates, hex, issue IDs, line refs, and version pins, and applies per-fact tolerances. Two `.beadloom/config.yml` keys handle the rest:

```yaml
docs_audit:
  tolerances:
    node_count: 0.1          # accept counts within 10% of ground truth
  ignore:                    # suppress one {path, fact, value} false match each
    - path: docs/guides/vitepress-site.md
      fact: cli_command_count
      value: 404
```

`docs_audit.ignore` is a list of `{path, fact, value}` triples. Each suppresses exactly one keyword-proximity false positive — for example a subset count stated next to the correct total, or an HTTP status code matched as a command count — **without** rewording correct prose and **without** masking a genuine stale fact of the same type elsewhere. Use it only for confirmed false positives; genuine stale facts must be corrected in the doc.

Examples:

```bash
# Human-readable Rich output
beadloom docs audit

# CI gate: fail if any stale docs
beadloom docs audit --fail-if=stale>0

# Stricter: also fail when a declared fact is stated by no document at all
beadloom docs audit --fail-if=unverified>0

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
beadloom config-check [--project DIR]   # exit 1 on BLOCKING drift, 0 otherwise
beadloom config-check --fix [--project DIR]  # regenerate drifted artifacts, then re-check
```

Since **BDL-061 S3** a drift carries a severity. `error` exits 1; `warn` is
printed (`! <file>: <reason>` plus a `-> <remediation>` line) and exits 0, so an
adopter upgrading into this release does not go red for a file scaffolded before
the flow manifest existed. The clean line says which case it is —
`Agent-config in sync — no blocking drift (N warning(s) — see above).`

Re-runs the same `setup-rules --refresh` generator in memory and diffs its output against on-disk content for `.beadloom/AGENTS.md`, the auto-managed sections of `.claude/CLAUDE.md`, and present IDE adapter files. For those three, only the auto-managed regions are compared — editing user-authored prose (the AGENTS.md `custom` block, CLAUDE.md content outside the `auto-start`/`auto-end` markers) never trips them. The composed artifacts are a separate check with its own rules, described below. Prints which file drifted, why, and the remediation; an absent target file is skipped unless the project adopted the flow, in which case it is `missing`. `--fix` regenerates via the refresh path (`config_sync.apply_config_fixes`), names every file it changed, declines any body Beadloom cannot prove it wrote, and re-checks. Delegates to `onboarding/config_sync.py:check_config_drift()`.

As of BDL-048, when a repo has the agentic flow scaffolded (`beadloom setup-agentic-flow`), `config-check` also drift-checks the **scaffolded flow files**. As of **BDL-061 S3** it checks them against their **composition result** rather than against fixed bytes: `.claude/CLAUDE.md`, each `.claude/commands/*` and each `.claude/agents/*` must equal `CORE + the flow.yml overlays + the project layer in .beadloom/flow/`. That is what makes a project extension legal — it is part of the expected output — while a change to a shipped fragment still differs from it and is reported.

Two things this closed, both measured:

- **The `CLAUDE.md` body was checked by nothing.** `config-check` diffed only the marker-bounded auto-regions, so on a freshly scaffolded project, appending a project-local paragraph, deleting the whole of section 7, and replacing the entire file with the single line `# gone` all returned zero drifts — and `beadloom ci` printed `config-check PASS: agent-config in sync` over it (BDL-UX #177).
- **`--fix` used to delete hand edits.** It restored every divergent file byte-identical, with no diff and no confirmation, which is why a team's standing engineering practice could not live in a role adapter at all (BDL-UX #139, #152). For the slash commands and `CLAUDE.md` it no longer does: it runs the scaffold's non-forcing path, names `.beadloom/flow/<kind>/<name>.md` and leaves the edit where it is.

**`--fix` may only rewrite what Beadloom wrote (BDL-UX #186, closed in BDL-061 `.59`).** The role adapters were the one kind left out: `refresh_composed_adapters` rewrote `.claude/agents/<role>.md` unconditionally, so doing what the closing line said (*Run `beadloom setup-rules --refresh` (or `config-check --fix`) to fix.*) undid what the line above it promised — and the re-check then printed `Agent-config in sync — no blocking drift` at exit 0 over the deletion. Verified by sha256 on a clean repository. Now:

- an adapter classified `hand_edited` or `unverified` is **declined**: left byte-identical, named in the output, and its finding keeps the exit code honest;
- everything else is recomposed as before, and the run **names every file it created or rewrote**, measured by digesting the artifact surface before and after rather than by trusting each writer's self-report;
- the closing advice stops offering `config-check --fix` for a finding `--fix` will decline (`ConfigDrift.fixable`).

The remedy is unchanged and now actually terminates: move the additions into `.beadloom/flow/roles/<role>.md`, then re-run `beadloom setup-agentic-flow`.

Which of the two a divergence *is*, is decided by the flow manifest (`.beadloom/flow-manifest.json`): every write records the body's sha256, so `stale` (Beadloom wrote it, the composition moved — `error`, recompose), `hand_edited` (`error`, never rewritten) `missing` (we wrote it and it is gone — `error`) and `unverified` (nothing accounts for it, so the two cannot be told apart — `warn`) are separate findings and not one word. The `CLAUDE.md` body is JUDGED only when the file is Beadloom's: a manifest entry, or the `<!-- beadloom:composed` stamp the shipped core begins with — a project's own hand-written `CLAUDE.md` is never policed. Not judged is not the same as not mentioned: in a project that adopted the flow, a `CLAUDE.md` with neither signal is named at `unverified`/`warn` rather than passed over. Those two signals are independent on purpose: deleting the generated manifest used to downgrade a hand edit to `warn` and the command to exit 0, and deleting one scaffolded file used to switch the checks off for every other one. Neither does now — the deletions are themselves reported (BDL-061 `.57`). `config-check` also names, at `warn`, a project layer in effect (its prose is composed but not judged) and an `overlays.suppress` entry that has expired or that names no rule in the composed flow.

**A downgrade across an upgrade is itself a finding (BDL-061 S3b).** The
constraint this project has always stated runs one way — *no adopter's green
project turns red on upgrade* — and review `.11` measured the other direction: a
repo that hand-edited a role file before the flow manifest existed used to block
at `error` and, after the manifest shipped, has no entry for that file, reads
`unverified`, and warns at exit 0. A downgrade is the worse of the two, because a
red is loud and correlates with the release while a downgrade is silent: the
project was correctly failing, now passes, and the evidence it ever failed is
gone. So every severity Beadloom reduced *for want of evidence* carries
`ConfigDrift.weakened_from`, and the command says so — on the passing path as
well as the blocking one:

```
Agent-config in sync — no blocking drift (5 warning(s) — see above).
  This pass is WEAKER than it would be: 5 finding(s) are `warn` only because
  Beadloom cannot prove what it wrote — each would be an `error` with the
  evidence. A verdict that got quieter across an upgrade is a finding, not a pass.
    -> restore `.beadloom/flow-manifest.json` (re-run `beadloom setup-agentic-flow`)
       to get the blocking verdict back.
```

The exit code deliberately does **not** change: a `warn` must not block, or
fixing the silence would itself be the red-on-upgrade the rule exists to prevent.
And nothing is recorded to compute it — the downgrade follows from the finding's
own state, because `config-check` writing on every run to keep a verdict history
would be BDL-UX #147/#189 in the one command whose job is to look without
touching.

As of **BDL-052 S3**, when a valid `.beadloom/flow.yml` is present `config-check` also: (a) validates `flow.yml` itself (an invalid config is reported as drift; an absent one is not); and (b) byte-compares each **composed role adapter** (`<tool>/agents/<role>.md` for every tool the config names) against the freshly recomposed body (`compose_role(...)` for the configured architecture + stack overlays) — `config_sync._composed_adapter_drifts`. When a `flow.yml` is present the role agents are composer-owned, so the byte-vendor compare is skipped for `agents` (it would false-positive on a non-Python stack). `--fix` recomposes the per-tool adapter sets except the ones it declines (`config_sync.refresh_composed_adapters`, which returns an `AdapterRefresh` of `rewritten` + `declined`). **Known limitation:** the composed-adapter check iterates only the tools named in `flow.yml`, so adapters left behind by a tool dropped from a narrowed `flow.yml` (e.g. orphaned `.cursor/agents/*`) are neither flagged nor recomposed; a follow-up bead tracks an orphaned-adapter lint.

### beadloom guard

Evaluate one flow guard — the enforcement primitive the agentic flow binds to (BDL-061 S1).

```bash
beadloom guard NAME [--context KEY=VALUE ...] [--json] [--project DIR]
beadloom guard NAME --hook claude-code            # harness event as JSON on stdin
beadloom guard --liveness [--json] [--project DIR]
```

Returns a verdict `{guard, outcome, why, not_covered[], remediation, context}` — plus `recorded` and `not_recorded_because` under `--json` — where `outcome` is `pass` / `warn` / `block` / `skip` / `error`. **Exit codes carry the outcome** so a shell adapter needs no parsing: `0` for `pass`/`skip`, `1` for `warn` (shown, never blocking), `2` for `block`, and `3` for a usage or configuration error reported to a **shell** caller — deliberately not `2`, which is Click's own usage code and would otherwise be indistinguishable from a genuine block. That distinction is answered only to the caller it means something to: reached through `--hook`, the same class exits `2` (BDL-061.33). It exited `3` there until S2, and `3` stops no tool call — so a `.beadloom/flow.yml` that would not parse left every bound guard announcing that it could not answer while every edit went through. The mapping lives in the CLI, keyed on the harness the adapter already declares, rather than in the generated script: a script that maps codes carries logic, and the next harness would have to re-implement it. `warn`, `block` and `error` are written to **stderr** (the stream a hook harness shows the agent); `pass` and `skip` go to stdout, as does `--json` in every case.

`3` is for a defect in the project's *declared configuration* (an unparseable `guards:` block, an exclusion with no reason, a guard name nobody registered) and for a command line that could not be used at all (no guard named, `--liveness` with a name, a malformed `--context` pair, an unsupported `--hook` harness) — stable defects that fail the same way on every invocation. Anything that goes wrong while answering about *this* edit — a hook payload that cannot be decoded or parsed, a project that cannot be located, an exception anywhere — is an `error` verdict at `2`, the one code the shipped adapter blocks on.

**`3` is not what a hook sees, and that is the point (BDL-061.33).** The harness stops the tool call on `2` and on nothing else, so while the class exited `3` unconditionally, all five cases above were an `error` verdict — loud on stderr, and letting the edit through. The reachable one is a `.beadloom/flow.yml` that will not parse, the one file of this feature an adopter edits by hand: while it will not parse, every bound guard answered "could not tell" and nothing was enforced. The distinction `3` draws is worth keeping, so it is kept for the caller that can act on it and dropped for the one that cannot: `beadloom guard` run by a person or by CI still exits `3`, and the same defect reached through `--hook` exits `2` and stops the edit. Mapping the whole class to `2` would have spent the distinction on a caller with no use for it; mapping it in the emitted script would have put logic in an adapter and left the next harness to re-derive it. An unsupported `--hook` harness blocks for the same reason, since Beadloom cannot know the exit vocabulary of a tool it does not support.

`error` means **the guard could not answer** — a refused path (see below), a `guards:` block that will not parse, a project that cannot be located, or any failure inside the evaluation. It exits `2`, because the adapter's harness blocks on 2 and on nothing else, and because `1` is the `warn` code a harness reads as "carry on". Every invocation runs inside one boundary: argument parsing, the stdin read and the evaluation all come back through it, so a failure anywhere is a recorded verdict rather than a traceback — including a **`KeyboardInterrupt`**, which since BDL-061.31 is a recorded `error` at exit 2 rather than an escape to Click's exit 1. That means Ctrl-C during a guarded edit *blocks* that edit: an interrupted guard checked nothing, and "could not answer" must never read as "passed". Rendering the verdict happens after the boundary and is wrapped, so a failure while printing is reported on stderr and the exit code stays the verdict's. Every invocation that names a registered guard in a located project is recorded, `error` included — an evaluation missing from `guard-firings.jsonl` is invisible to `--liveness`. The four invocations that leave no record say so (`not recorded: <reason>` on stderr): a successful `--liveness` report evaluated nothing, an unlocatable project has nowhere to write, an invocation that named no guard asked about nothing, and an unregistered name has nothing to attribute the row to. The last two were one reason until BDL-061.34, which is why `beadloom guard` with no name used to report `'(no guard named)' is not a registered guard` — a placeholder quoted as though it had been typed, and identical to what a caller who really typed it got.

Shipped guards: `bead-claimed` (an edit happens under a claimed work item) and `working-branch` (work happens off the protected trunk; `options.trunk`, default `main`). Both skip — with a stated reason — when their evidence is unavailable (`bd` not present, no branch checked out), because a guard that silently does not apply is indistinguishable from one that passed.

Guards are declared in `.beadloom/flow.yml`; an absent `guards:` block means every guard runs at the shipped default (`warn`), so an upgrade never turns a green project red:

```yaml
guards:
  bead-claimed:
    strictness: { default: warn, epic: block, chore: off }
    exclusions:
      - path: "scripts/**"
        reason: "operational scripts are not bead-scoped"
        until: "BDL-0xx introduces a scripts node"
```

Strictness resolves per work kind (`--context work_kind=epic`) with a `default` fallback. **An exclusion must carry both `reason` and `until`** — one without either is a configuration error (exit 3 from a shell, exit 2 through a hook), because an unnamed, undated exclusion disables a gate permanently by accident. `until` may name a **deadline** (it LEADS with an ISO `YYYY-MM-DD`, optionally followed by the prose that explains it) or an **event** (anything else, as above — what retires a real exclusion is usually a landed change, not a day). A deadline is parsed by the same function the `forbid_import` exemptions of `rules.yml` use, so the two surfaces cannot promise different things; once it passes, the exclusion says so in its own skip reason (`… (until 2024-01-01 — EXPIRED)`) and `--liveness` flags it as `exit condition has passed: '<pattern>'`. It is never enforced — the exclusion keeps applying, because a guard that starts blocking with no commit behind it is worse than the silence being reported (BDL-061.49). A `guards:` key naming an unregistered guard is likewise an error, not a no-op, and so is **a key the loader does not read** — a guard body carries `strictness` / `exclusions` / `options`, an exclusion carries `path` / `reason` / `until` (BDL-061.34): `option:` for `options:` used to drop the declared `trunk` and leave `working-branch` comparing against `main`, which passes an edit made on the project's real trunk at exit 0. There is **no `on:` key**: which tool invocations count as an edit, and which guards run on them, is decided by the harness adapter (in Claude Code, the matcher and the per-guard entries in `.claude/settings.json`), not by Beadloom. An `on:` key shipped in the S1 schema with no consumer and was deleted rather than quoted; it returns wired in S3.

**That matcher is the enforcement surface, and it is narrower than "every edit".** The emitted adapter is registered on `PreToolUse` for `Edit|Write|MultiEdit|NotebookEdit`, so a file written through `Bash` — `sed -i`, a heredoc, `python3 - <<EOF` — invokes no guard, produces no verdict and writes no firing. `--liveness` therefore cannot distinguish a session that edited entirely outside the matcher from one that complied: both leave the same record. This is a property of the binding rather than of a verdict, so no `not_covered` note can carry it (there is no evaluation to attach one to) — see BDL-UX #170 and the [flow-guards SPEC](../domains/application/features/flow-guards/SPEC.md#the-enforcement-surface).

With no `--project`, the **project root is discovered** by walking up from the working directory to the nearest ancestor containing `.beadloom/`; with `--project`, that directory is used verbatim and **must carry `.beadloom/` itself** — the flag names a project, not a directory. A missing path, a file, and an ordinary directory with no marker are one refusal: a guard that cannot locate a project answers `error` (exit 2) and creates nothing, by any route. Until BDL-061.31 any existing directory was honoured, so `--project <an ordinary directory>` found no `flow.yml`, silently traded the project's declared `block` for the shipped default `warn` (a non-blocking exit 1), and manufactured `.beadloom/` there when the firing was written — the record belongs to the project, not to wherever the process was pointed, and a firing written where `--liveness` does not read it is indistinguishable from no firing. A directory this process **may not read** is the same refusal since BDL-061.32: `click.Path` defaults `readable=True`, and that check runs in Click, so `--project <an unreadable directory>` used to be a usage error at exit 2 with no verdict, no record and nothing on stdout for `--json` to parse. No parameter of `beadloom guard` declares a conversion Click can refuse — every reason an argument cannot be used is answered by the guard, not by the argument parser.

`--context KEY=VALUE` is repeatable, and where a key is given twice **the last occurrence wins**. `--context path=...` is resolved against the project root before any exclusion is matched — `..` collapsed, symlinks followed — so a declared exclusion cannot be turned into an opt-out by respelling the path (`scripts/../src/app.py` is guarded, not skipped). A path resolving outside the project root is matched against no exclusion at all, and the verdict names it in `not_covered`.

The path is model-supplied, so its **shape is narrowed rather than repaired**: a well-formed target carries no C0 control character or `DEL`, no backslash, no leading `~`, and is encodable for the filesystem, and it is judged exactly as supplied — nothing is stripped first, because `str.strip()` also removes nine C0 characters the same rule refuses, which turned a `block` into a `skip` quoting a pattern that does not cover the file. Anything else is refused with an `error` verdict naming the offending rule — never normalised into a guess, and never a traceback. Each rule removes a spelling that means one file to the guard and another to the writer (`src\app.py` skipped a `*.py` exclusion while the write landed on `src/app.py`; a NUL crashed the process out on exit 1, the non-blocking code, leaving no record at all).

`--hook HARNESS` reads the harness's own hook event as JSON on stdin and derives the context from it (`claude-code`: `tool_input.file_path`, `tool_name`, `hook_event_name`). The event is read as **bytes** and decoded as UTF-8 strictly, so a payload the harness could not encode is refused (`error`, exit 2) identically under every locale — reading it as text left the decode to `sys.stdin`, whose error handler is `surrogateescape` under `LC_ALL=C`/`PYTHONUTF8=1` (the default in most containers), and there the undecodable bytes silently became a file name the guard then evaluated (BDL-061.36). The emitted adapter (`.claude/hooks/beadloom-guard.sh`, written by `beadloom setup-agentic-flow`) contains no logic — it is one `exec beadloom guard "$1" --hook claude-code` — so a hook and a shell cannot produce different verdicts.

`--liveness` reports, per guard, its effective strictness, how many times it fired, its last outcome, and four ways a gate stops protecting anything: `never-fired` (no firing that reached a verdict — an `error` is counted and shown, but does not clear the flag, because a guard that ran three times and answered none of them is not a live gate), `excluded-everywhere` (every strictness `off`, or nothing escapes the exclusion **list** — decided by matching the patterns against representative paths, not by comparing spellings, and asked of the list because `*` and `*/**` are each narrow and together exempt everything), `matches no file in the project: '<pattern>'` (a declared exclusion that exempts nothing that currently exists — a typo'd `scrpits/**` is safe but was silent), and `exit condition has passed: '<pattern>'` (its `until:` names a date that is behind us). A gate that cannot demonstrate it ran is treated as not having run. Every CLI evaluation appends one line to `.beadloom/guard-firings.jsonl`, which is the only file guards write — never the index they inspect. Decision logic lives in `application/guards/evaluation.py`; the CLI only renders it.

### beadloom ci

The unified enforcement gate — the single CI convergence point (principle 7: identical for Cursor / Claude Code / human authors).

```bash
beadloom ci [--hub EXPORT.json ...] [--fail-on CSV] [--format {rich,json,github}] [--no-reindex] [--project DIR]
```

Composes the existing checkers, in order, into ONE verdict with a single exit code (0 = all steps passed, 1 = any step failed):

1. `reindex` (incremental) — unless `--no-reindex`.
2. `lint --strict` — architecture boundary rules at error severity.
3. `sync-check` — doc↔code freshness (stale pairs fail).
4. `docs audit` — stale numeric facts in documentation (`stale>0` fails). The step line also states its coverage — `M/N declared fact(s) verified` plus the names of the facts it checked nothing for — because a count of findings says nothing about the facts nobody stated.
5. `config-check` — AgentConfigAsCode drift.
6. `doctor` — graph/data integrity; ONLY `ERROR`-severity checks fail the gate (WARNING/INFO advisories never block — no false gate).
7. `federate --fail-on` — the cross-service landscape gate, only when `--hub` export(s) are given (safe-default fail-set `breaking,drift,orphaned_consumer,undeclared_producer`; no-false-gate verdicts rejected).

**What `--no-reindex` changes about the verdict.** It skips step 1, so every later step describes the INDEX rather than the working tree. With an index older than the tree, the `lint` step reports `PASS` over a live error-severity violation that the same gate catches after a reindex (measured), and the `sync-check` step compares against whatever baseline the index holds. Use it only where something else has just reindexed.

**Honest gate (the Phase-0 lesson):** the report names every step that ran and its outcome — `PASS` / `WARN` / `FAIL` / `SKIP` — never a green that silently skipped a step, and never a `PASS` over something the step could not check (`WARN`: it ran, found nothing wrong, and part of what it reports on was not verifiable — see `sync-check` above). **No short-circuit:** all steps run and ALL findings are collected even after an earlier failure, so one run surfaces every problem. `--format` applies uniformly across every step; findings share the agent-actionable `{kind, rule, severity, locations, why, remediation}` shape (`github` emits valid `::error file=<path>,line=<n>::<msg>` workflow-command annotations, matching `lint --format github`; `json` emits `{ok, steps[]}`). The per-repo `beadloom-aac-lint.yml` reindex+lint+sync steps collapse into one `beadloom ci` call. Orchestration lives in `application/gate.py:run_ci_gate()`; the CLI only parses options and renders.

### beadloom setup-mcp

Configure MCP server for your editor.

```bash
beadloom setup-mcp [--tool {claude-code,cursor,windsurf}] [--project DIR]
beadloom setup-mcp --remove [--tool {claude-code,cursor,windsurf}] [--project DIR]
```

- `claude-code` (default) -- `.mcp.json` in project root
- `cursor` -- `.cursor/mcp.json` in project root
- `windsurf` -- `~/.codeium/windsurf/mcp_config.json` (global)

### beadloom setup-ai-techwriter

Scaffold the AI tech-writer (BDL-047 / F4.1; harness packaged in BDL-051 / S2)
into this repo for one-command, 3-step opt-in. In the `setup-*` family alongside
`setup-mcp` / `setup-rules`.

```bash
beadloom setup-ai-techwriter --platform {github,gitlab} [--project DIR]
```

Idempotently scaffolds (clean overwrite on re-run):

- **No Python vendoring.** As of BDL-051 / S2 the harness ships **inside** the
  installed `beadloom` package as the `beadloom.ai_agents.ai_techwriter` domain,
  so adopters depend on `beadloom` and invoke it directly via
  `python -m beadloom.ai_agents.ai_techwriter` (the BDL-047/048 `tools/` Python
  vendoring + drift-guard machinery is retired). Only the operator artifacts —
  the Goose `recipe.yaml` (a readable reference of the agent's blast radius) and
  `provision-runner.sh` — are copied (from package data via
  `importlib.resources`) into `tools/ai_techwriter/` for operator convenience.
- The chosen platform's CI wrapper: `.github/workflows/ai-techwriter.yml`
  (GitHub) **or** an `ai-techwriter` job in `.gitlab-ci.yml` (GitLab). As of
  BDL-049 both trigger on a **PR to main/master** — GitHub `on: pull_request`
  (`opened`/`synchronize`/`reopened`), GitLab `merge_request_event` — plus a
  manual fallback (`workflow_dispatch`). They call the same
  `python -m beadloom.ai_agents.ai_techwriter` entrypoint; the PR path passes
  `--target pr-branch` and `--since $(git merge-base origin/<base> HEAD)` so the
  agent commits its refresh into the PR branch; the manual path uses
  `--target branch-pr`. A loop-guard skips the agent's own
  `[skip ai-techwriter]` commit, and `cancel-in-progress: true` supersedes older
  runs. Only the trigger, the secret naming (`QWEN_API_KEY` repo secret vs CI/CD
  variable), and `--platform` differ. An existing `.gitlab-ci.yml` is appended to
  (job-only, stripping the standalone `stages:` header) — never blindly
  clobbered; an already-wired file is left as-is.
- `tools/ai_techwriter/provision-runner.sh` — a hardened, idempotent,
  executable (`0o755`) self-hosted-runner provisioner (`--platform/--repo/--token`):
  guarantees swap **before** any apt/build (the OOM lesson), RAM (~2 GB min,
  ~4 GB recommended) + disk (~5 GB) prechecks, fail-hard on the critical
  steps (toolchain + runner register/start), and best-effort + verified
  Goose/beadloom/bd installs reported at the end.
- `docs/guides/ai-techwriter.md` — the 3-step getting-started guide.

Delegates to `onboarding/ai_techwriter_setup.py:scaffold()`.

### beadloom setup-agentic-flow

Scaffold Beadloom's proven multi-agent dev flow into this repo (BDL-048 / 052).
In the `setup-*` family alongside `setup-rules` / `setup-mcp` /
`setup-ai-techwriter`.

```bash
beadloom setup-agentic-flow [--project DIR] [--force] \
    [--tool claude|cursor]...        # repeatable; default: flow.yml or claude
    [--architecture ddd|fsd]         # default: flow.yml or ddd
    [--stack python,fastapi,javascript,typescript,vuejs]  # CSV; default: flow.yml or auto-detected
```

Since **BDL-061 S3** every flow artifact is **composed** from four layers in a
fixed order — the shipped stack-neutral CORE, one architecture overlay
(`ddd`/`fsd`), each selected stack overlay **sorted**, and the project fragment
under `.beadloom/flow/` — for all three kinds:

| kind | written to | project fragment |
|------|-----------|------------------|
| `roles` | `.claude/agents/<role>.md`, `.cursor/agents/<role>.md` | `.beadloom/flow/roles/<role>.md` |
| `commands` | `.claude/commands/<cmd>.md` | `.beadloom/flow/commands/<cmd>.md` |
| `claude` | `.claude/CLAUDE.md` | `.beadloom/flow/claude/CLAUDE.md` |

`cursor` additionally gets a `.cursor/rules/beadloom-flow.md` orchestrator
pointer. Selection comes from `.beadloom/flow.yml`, overridden by the
`--tool`/`--architecture`/`--stack` flags (defaults `claude` / `ddd` /
auto-detected stack — **flag → flow.yml → default** precedence). An invalid
selection raises a `FlowConfigError` naming the bad value + the allowed set.
`config-check` compares each artifact against its composition, so a project
fragment is part of the expected output while a change to a shipped fragment is
not. See the [Project Overlays guide](../guides/project-overlays.md).

`.claude/CLAUDE.md` keeps two auto-regions generated for THIS project via the
same `refresh_claude_md` machinery `setup-rules --refresh` uses: `project-info`
and `doc-language` (rendered from `language:` in `flow.yml`). Every bullet in
`project-info` is read from **the target project** — its declared version
(`pyproject.toml` including a `dynamic` one, `package.json`, `Cargo.toml`), its
`requires-python` verbatim, its declared dependencies, its own `src/` packages
and the architecture its `flow.yml` names. A fact that cannot be read is
**omitted, never substituted**.

> Until **BDL-061 S3b** it was not. The version bullet rendered Beadloom's own
> `__version__` (a JavaScript project a major version behind was told ours), the
> architecture line said `DDD packages` whatever the project declared, the stack
> line matched the project's manifest against *Beadloom's* dependency names and
> printed our Python floor as theirs, and the package scan fell back to looking
> for `src/beadloom/` inside the adopter's tree. Each read correct on this one
> repository by coincidence, which is why four slices of scrutiny passed over it
> (BDL-UX #183). The same coincidence covered `beadloom doctor`, which audited
> those four claims in an adopter's file against *our* state; it now reads
> theirs, and reports `not verified` for a fact the project does not declare.

**The command records the selection it composed from.** A first run writes
`.beadloom/flow.yml` — and never writes over an existing one, since that file is
the adopter's policy (`language` and `overlays.suppress` have no flag and live
only there). Before BDL-061 S3b it resolved the selection in memory and never
wrote it down, so a virgin scaffold on a fresh TypeScript project left
`beadloom config-check` — the command this one's own closing advice recommends —
at **exit 1 with four errors**, remediated by advice to add a `flow.yml` by
running the command just run (BDL-UX #187). The same fix closed a divergence
found alongside it: `scaffold()` re-resolved from disk *without* the flags, so
`--architecture fsd` composed the role adapters as `fsd` and the commands and
`CLAUDE.md` as `ddd`.

It also writes the **flow-guard binding** (BDL-061 S1): `.claude/hooks/beadloom-guard.sh`
— one `exec beadloom guard "$1" --hook claude-code` — and one `PreToolUse` entry per
registered guard in `.claude/settings.json`, matched on `Edit|Write|MultiEdit|NotebookEdit`.
The guard names come from the registry, so a guard added in a later release is wired by
re-running this command. Registration is a **merge**: existing hooks survive, re-running adds
only the missing entries, and a `settings.json` that cannot be parsed is reported and left
untouched. Those four tool calls are the whole enforcement surface — a file written through
`Bash` fires no guard (see [`beadloom guard`](#beadloom-guard)).

The command makes the same whole-working-set `.gitignore` call `init` makes (see
[`beadloom init`](#beadloom-init)), for a project initialised by a Beadloom older than
the block: the guards' firing record is one entry in that set, not a special case owned
by the guard scaffolder.

A composed command or `CLAUDE.md` that already matches is left alone; a
hand-edited one is **skipped** (reported as such) so user edits are not silently
clobbered; `--force` overwrites it. Composed role adapters are owned by the
configurator (re-running recomposes them). Delegates to
`onboarding/role_adapters.py:generate_adapters()` (the adapters) +
`onboarding/agentic_flow_setup.py:scaffold()` (the commands + CLAUDE.md).

The command **prints what it found**, not only what it wrote: the files an older
layout left behind, each with the exact `rm -f` command (BDL-UX #137), and a
migration note naming the project-layer path a hand edit belongs in.

```
Left alone (1) — your edits are the only copy of an intent, so Beadloom did not
recompose over them:
  = .claude/commands/coordinator.md: hand-edited … move the additions to
    .beadloom/flow/commands/coordinator.md

Left by an older flow layout (5) — reported, never deleted:
  ? .claude/commands/dev.md: left by an older flow layout (the role moved to
    .claude/agents/dev.md) — remove with `rm -f .claude/commands/dev.md`
```

Until BDL-061 S3b both lists were computed on every run and read by **nothing**
outside the library, so BDL-UX #137's closure and S3's migration-guidance
criterion were true of `scaffold()` and false of the command anybody runs. What
the user saw instead was `Skipped .claude/commands/coordinator.md (hand-edited;
use --force)` — advice to run the destructive flag, naming nowhere the edit could
safely go (BDL-UX #188). NO CALLER, NO CAPABILITY.

The command prints the **honest boundary**: the coordinator + `Agent`-spawn are
Claude-Code-native (orchestration stays in the harness); the Beadloom MCP
process-tools are the deterministic, tool-agnostic substrate the flow calls; and
the single source of TRUE enforcement remains `beadloom ci` in CI (the in-flow
gates are advisory-strong, not a substitute for CI). See the
[Agentic Dev Flow guide](../guides/agentic-flow.md).

### beadloom setup-branch-protection

Configure trunk-based branch protection on `main` via `gh api` (BDL-049), so the
CI gate becomes **true enforcement** rather than advisory. GitHub only.

```bash
beadloom setup-branch-protection --repo OWNER/NAME [--branch main] [--check CONTEXT]... [--dry-run]
```

Idempotently sets `main` (or `--branch`) protection with a declarative
`PUT repos/{owner}/{repo}/branches/{branch}/protection`: a **PR is required** (no
direct push), the scaffolded default set of `ci.yml` checks — `gate`, `tests (3.10)`,
`tests (3.11)`, `tests (3.12)`, `tests (3.13)`, `tests-locale (C)`,
`tests-locale (en_US.ISO-8859-1)`, `tests-windows`, `site-build`, `ai-techwriter`
(ci.yml's job names + matrix legs) — are **required status checks**
(`strict: true`), and `enforce_admins: true` + 0 required reviews so the
**solo owner is never locked out** (can self-merge). `PUT .../protection` is
declarative, so re-running re-settles the same state.

- `--repo OWNER/NAME` (required) — the GitHub repository (e.g. `acme/widget`).
- `--branch` (default `main`) — the trunk to protect.
- `--check CONTEXT` (repeatable) — overrides the default required-check contexts
  (the consolidated `ci.yml` job check-runs listed above) **entirely**. A context
  MUST match a real GitHub check-run name EXACTLY and must NOT be a
  **path-filtered** workflow's check: such a check does not run on PRs that miss
  the filter, so under `strict: true` the PR — and therefore `main` — would never
  become mergeable. BDL-050 dropped the `tests` `paths:` filter precisely so each
  matrix leg runs on every PR and is a reliable required check.
- `--dry-run` — print the exact `gh api` call + JSON payload without touching
  GitHub.

**A required context must be a check that can go green.** `PUT .../protection` is
declarative and re-running it is harmless in itself, but the payload is the
DEFAULT set above, and `strict: true` means every context in it must pass before
a pull request can merge. Requiring a check-run that is red — or that does not
exist in your pipeline at all — makes the branch permanently unmergeable until it
is green or the context is removed. **On this repository today that is a live
constraint, and the reason has moved:** the two `tests-locale` legs added in
BDL-061.38 were knowingly red (108 ASCII / 83 8-bit locale-attributable failures,
measured) and BDL-061.42 turned both **green**; the `tests-windows` leg added in
BDL-061.39 is now the red one, and deliberately so — nothing in this project had
ever executed on Windows when it landed, so its first runs are the measurement
rather than a regression. `main` therefore still carries the seven
pre-BDL-061.38 contexts while `DEFAULT_STATUS_CHECK_CONTEXTS` names ten.
**Sequencing:** running `beadloom setup-branch-protection` here today would apply
all ten and block every merge until the Windows leg is green. Re-run it once the
locale rows and `tests-windows` have all been observed green on a real PR, or
pass `--check` explicitly for the set your pipeline can actually satisfy.

Delegates to `onboarding/branch_protection.py:apply_branch_protection()` (the
`gh` invocation is injected via a `GhRunner` seam for mockable tests).

### beadloom mcp-serve

Launch MCP stdio server.

```bash
beadloom mcp-serve [--project DIR]
```

## API

As of BDL-059 S4, `src/beadloom/services/cli.py` is a thin registration shell:
it imports each command module for its registration side effects and
re-exports `main` (plus the private helpers tests import) so
`beadloom.services.cli.main` stays the stable entry point. The command
implementations live in the `src/beadloom/services/commands/` package — one
cohesive module per command group: `_root` (the `main` group + global options),
`query` (`ctx`/`search`/`why`/`graph`/`diff`), `index_ops` (`reindex`/`link`),
`status` (`status` + `--debt-report` rendering), `docsync`
(`sync-check`/`sync-update`/`install-hooks`/`active-sync`/`ci`), `federation`
(`export`/`federate`), `docs` (the `docs` group: `generate`/`site`/`audit`/`polish`),
`setup` (the `init`/`setup-*`/`mcp` commands), `dashboard` (`tui`/`ui`/`watch`),
and `snapshot` (the `snapshot` group). The `status` command's data-gathering was
moved DOWN to the application layer (`application/status.py`:
`gather_status`/`compute_context_metrics`/`StatusData`); the command keeps only
the Rich/JSON presentation. The CLI surface (every command, option, help text,
output, and exit code) is unchanged by the split.

Commands (re-exported from the package via the registration shell):

- `main` -- Click group: `beadloom [--verbose|-v] [--quiet|-q] [--version] COMMAND`
- `reindex` -- rebuild SQLite index (incremental by default, `--full` for complete rebuild)
- `ctx` -- get context bundle for ref_id(s)
- `graph` -- show architecture graph (Mermaid, C4-Mermaid, C4-PlantUML, or JSON) with `--format`, `--level`, `--scope` options
- `export` -- export the indexed graph as a deterministic federation artifact (JSON, schema v1) with `--out`
- `federate` -- aggregate >=2 satellite export artifacts into one federated graph (drift verdicts + staleness)
- `doctor` -- run validation checks
- `status` -- show index statistics with health trends and context metrics (data gathered by `application/status.py:gather_status`); `--debt-report` mode with `--fail-if`, `--category` flags
- `sync_check` -- check doc-code sync with reason/details (reason-aware output for `untracked_files`, `missing_modules`, `symbols_changed`); `--since GIT_REF` measures drift against a git ref instead of the stored baseline (fresh-checkout / per-push drift detection)
- `sync_update` -- review and update stale docs interactively; `--check` for status-only; `--yes`/`-y` for a non-interactive re-baseline; `--all` (with `--yes`) re-baselines every stale ref
- `install_hooks` -- install/remove the pre-commit hook (lint -> mypy -> sync-check -> guarded ACTIVE/tracker-coherence auto-fix step) AND/OR the pre-push Beadloom Gate hook (`beadloom ci`, blocks the push on red; `command -v beadloom` guard -> safe no-op outside a flow repo); `--pre-commit`/`--pre-push` selectors (default both), `--remove`, idempotent
- `active_sync` -- reconcile each epic's ACTIVE.md bead-status table from `bd` (`--epic`/`--check`/`--json`/`--no-export`); fix mode also `bd export`s the tracked `.beads/issues.jsonl`; safe no-op when no ACTIVE table or no `bd`; delegates to `application/active_table.py:reconcile_active_tables()`
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
- `setup_ai_techwriter` -- scaffold the AI tech-writer (vendored harness + recipe + chosen platform CI wrapper + getting-started guide) for one-command opt-in; delegates to `onboarding/ai_techwriter_setup.py:scaffold()`
- `setup_agentic_flow` -- scaffold the packaged multi-agent dev flow (`.claude/agents/*` + `commands/*` vendored byte-identical + CLAUDE.md auto-regions per-project); idempotent, `--force` overwrites hand-edited flow files; delegates to `onboarding/agentic_flow_setup.py:scaffold()`
- `config_check` -- AgentConfigAsCode drift gate (`--fix` regenerates); reuses the `setup-rules --refresh` generator; also drift-checks/restores the scaffolded agentic-flow files when the flow is present
- `ci` -- unified enforcement gate composing reindex -> lint -> sync-check -> docs-audit -> config-check -> doctor -> (optional `--hub`) federate into one exit code; the docs-audit step blocks on stale facts (`stale>0`); honest per-step PASS/WARN/FAIL/SKIP; uniform `--format {rich,json,github}` (github = valid `::error file=,line=` annotations); delegates to `application/gate.py:run_ci_gate()`
- `mcp_serve` -- run MCP stdio server
- `docs` -- Click group for doc commands (`generate`, `polish`, `audit`)
- `tui` -- launch TUI dashboard (primary command, multi-screen with `--no-watch`)
- `ui` -- launch TUI dashboard (alias for `tui`)
- `watch_cmd` -- watch files and auto-reindex
- `init` -- project initialization (bootstrap, import, interactive, non-interactive with `--yes`/`--mode`/`--force`)

All commands accept `--project DIR` to specify the project root. The current directory is used by default.

## Testing

CLI is tested via `click.testing.CliRunner`. Each command has a corresponding test file in `tests/test_cli_*.py`: `test_cli_reindex.py`, `test_cli_ctx.py`, `test_cli_graph.py`, `test_cli_status.py`, `test_cli_sync_check.py`, `test_cli_sync_update.py`, `test_cli_hooks.py`, `test_cli_link.py`, `test_cli_docs.py`, `test_cli_mcp.py`, `test_cli_watch.py`, `test_cli_diff.py`, `test_cli_why.py`, `test_cli_lint.py`, `test_cli_init.py`, `test_cli_snapshot.py`, `test_cli_config_check.py`, `test_cli_setup_agentic_flow.py`, `test_cli_active_sync.py` (+ `test_cli_active_sync_hardening.py`).
