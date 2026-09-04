# Beadloom Architecture

<!-- beadloom:watches=graph,cli -->

> 📘 **reference** — overview/deep-dive, not tied to a single code symbol. It aligns with (does not replace) the generated [`/architecture` C4 overview](services/cli.md#beadloom-docs-site) on the published portal.

Beadloom turns Architecture as Code into Architectural Intelligence — structured, queryable knowledge about your system that humans and AI agents consume in <20ms.

## System Design

The system is organized into six DDD domain packages, an application (use-case orchestration) layer, and two interface layers:

**Domains:**
1. **Context Oracle** (`context_oracle/`) — BFS graph traversal, context bundle assembly, code indexing, two-tier caching, FTS5 search, `why` impact analysis
2. **Doc Sync** (`doc_sync/`) — doc↔code synchronization tracking, stale detection, symbol-level hashing, docs audit, document shape and writing-standard quality checks
3. **Graph** (`graph/`) — YAML graph loader, diff engine, rule engine, import resolver (eleven languages, `_EXTENSION_LOADERS`), architecture linter, C4 diagram emitter, federation
4. **Onboarding** (`onboarding/`) — project bootstrap, doc generation/polishing, architecture-aware presets, AGENTS.md / IDE-rules generation, config sync, one skip policy every reader of `.beadloom/_graph/` applies before it looks at a graph file (`graph_files.py`), and the **agentic-flow composer** (`flow_config.py`, `composer.py`, `role_composer.py`, `role_adapters.py`, `flow_manifest.py`, `flow_suppression.py`), which assembles every flow artifact from CORE + architecture + stack + the project layer in `.beadloom/flow/`
5. **Infrastructure** (`infrastructure/`) — domain-agnostic SQLite database layer, health metrics, git-activity tracking, and the configuration readers for where source (`scan_paths`) and documentation (`docs_dir`, `doc_roots`) live
6. **AI Agents** (`ai_agents/`) — governed AI-agent harnesses that ship inside the wheel; hosts the deterministic, seam-isolated **AI tech-writer** (`ai_agents/ai_techwriter/`, run via `python -m beadloom.ai_agents.ai_techwriter`). A **leaf consumer**: it may read `application`/`context_oracle`/`graph`/`doc_sync` APIs but must never be imported by the core domains or services (enforced by the `core-no-import-ai-agents` / `application-no-import-ai-agents` `forbid_import` rules).

**Application (use-case orchestration)** (`application/`) — composes the domains into end-to-end use cases. It owns:
- `reindex/` — the full + incremental reindex pipeline (drop → recreate → reload graph/docs/code/sync; SHA-256 `file_index` for incremental runs), a cohesion-split package
- `doctor.py` — graph + data integrity checks
- `status.py` — the read-side of `beadloom status` (index/coverage/health/trend counts + context-bundle metrics)
- `debt_report/` — architecture-debt aggregation, scoring, trend tracking, CI gating, a cohesion-split package
- `watcher.py` — file watcher for auto-reindex on change
- `gate.py` — the unified `beadloom ci` gate (reindex → lint → sync-check → docs audit → docs-quality → doc-spaces → config-check → doctor → optional federate)
- `guards/` — the flow-guard primitive behind `beadloom guard` (BDL-061 S1): a verdict per named guard, the `guards:` block of `.beadloom/flow.yml`, one invocation boundary, and the firing record `--liveness` reads
- `waves/` — the wave decision behind `beadloom waves` (BDL-061 S6): resolve each bead's declared node scope, decide from the graph which beads may run at once with one named reason per serialised pair, and check the plan-time precondition of each of the four media every wave shares whatever its width, and hold each bead's declaration against the `## Axes` section its work item recorded, a cohesion-split package
- `review_brief/` — the reviewer's input behind `beadloom review-brief` (BDL-061 S6): assemble the assignment, the declared scope, the specification documents, the bound scenarios and the changed files, and withhold the bead's own comments until a verdict is recorded
- the VitePress site generators — `site.py` (orchestrator), `site_pages.py`, `site_nav.py`, `site_about.py`, `site_dashboard/` (a cohesion-split package), `site_landscape.py`, `site_published.py`, `site_mermaid_guard.py`, `site_metrics_history.py`

**Interface layers:**
- **Services** (`services/`) — **CLI** (`services/cli.py` is a thin Click registration shell; the command implementations live in the `services/commands/` package, one cohesive module per command group) and **MCP Server** (`services/mcp_server.py`, stdio server with 18 tools for AI agents — 14 graph read/write tools + four BDL-048 process-tools). Both call into the application layer and Context Oracle; the CLI never reaches past those layers.
- **TUI** (`tui/`) — interactive terminal architecture workstation (Textual): dashboard, explorer, doc-status screens.

A `layers` rule in `.beadloom/_graph/rules.yml` enforces the direction `services / tui → application → domains` (the interface layers depend inward; domains never depend on the application or service layers).

### Node Kinds

The graph distinguishes the kinds of node it tracks:

| Kind | Doc | Annotation | Description |
|------|-----|------------|-------------|
| `service` | `services/<name>.md` | `# beadloom:service=<id>` | An interface/process boundary (CLI, MCP server, TUI) |
| `domain` | `domains/<name>/README.md` | `# beadloom:domain=<id>` | A DDD domain package |
| `feature` | `features/<name>/SPEC.md` | `# beadloom:feature=<id>` | A user-facing capability inside a domain |
| `component` | `<name>/DOC.md` | `# beadloom:component=<id>` | An internal/infra building block — the mirror of a `feature` for code that is not user-facing |
| `entity` / `adr` | — | — | Domain entities and architecture decisions |

The **`component` kind** (BDL-051) and the **`module-coverage` lint** (promoted to `severity: error`) together close the no-shadow-code gap: every `src` module with at least one symbol must be a tracked node (`feature` or `component`, or covered by a node's `source` — including a **directory** source like `tui/`) or named on a small, visible `exempt:` list in `rules.yml`. A new untracked module therefore fails `beadloom lint --strict` / `beadloom ci`.

---

## Specification

### Data Flow

The `application/reindex/` orchestrator drives the indexing pipeline, calling
each domain in order; the resulting SQLite index is then read back by Context
Oracle for sub-20ms context bundles.

```
YAML Graph Files (.beadloom/_graph/*.yml)
       ↓
   application/reindex/  (orchestrates the pipeline below)
       │
       ├─ graph/loader.py            → SQLite (nodes, edges, rules)
       ├─ graph/import_resolver.py   → SQLite (code_imports)
       ├─ doc_sync/doc_indexer.py    → SQLite (docs, chunks, search_index)
       ├─ context_oracle/code_indexer.py → SQLite (code_symbols)
       └─ (writes file_index, health_snapshots)
       ↓
   context_oracle/builder.py ← BFS traversal → context bundle (JSON)
       ↓                                       ↕ L1 memory / L2 SQLite cache
   services/cli.py / services/mcp_server.py / tui/ → user / AI agent
```

### SQLite Schema

The database is stored in `.beadloom/beadloom.db` and uses WAL mode for concurrent access.

**Core tables (9):**

| Table | Key columns | Description |
|-------|-------------|-------------|
| `nodes` | ref_id (PK), kind, summary, source, extra | Graph nodes (domain, feature, service, entity, adr) |
| `edges` | src_ref_id, dst_ref_id, kind (composite PK), extra | Graph edges (part_of, depends_on, uses, implements, touches_entity, touches_code) |
| `docs` | id (PK), path (UNIQUE), kind, ref_id (FK→nodes), hash, metadata | Document index |
| `chunks` | id (PK), doc_id (FK→docs), chunk_index, heading, section, content, node_ref_id | Document chunks (max 2000 chars) |
| `code_symbols` | id (PK), file_path, symbol_name, kind, line_start, line_end, annotations, file_hash | Code symbols (function, class, type, route, component) |
| `sync_state` | id (PK), doc_path, code_path, ref_id (FK→nodes), code_hash_at_sync, doc_hash_at_sync, doc_hash_at_last_edit, synced_at, status, symbols_hash, file_symbols_hash, baseline_source | Doc↔code sync state. Four verdicts (`ok`, `stale`, `missing`, `unverified`); `baseline_source` records where the row's baseline came from — `index_build`, `carried` or `attested` — and is carried verbatim across a reindex, never promoted. `symbols_hash` is the whole NODE's symbol surface, `file_symbols_hash` this pair's OWN code file: only the second makes a pair stale, and a pair whose sibling moved is `unverified/sibling_symbols_changed` rather than a `stale` verdict nobody can discharge (BDL-UX #182) |
| `declared_docs` | declared_path (PK), doc_path, ref_id (FK→nodes) | Every doc path a node DECLARES in its `docs:` list, whether or not the file is on disk. A cache of the committed graph YAML, refreshed on reindex, so a declaration outlives the file it names |
| `reference_state` | doc_path (PK), watches, aggregate_hash, status | Surface-drift baseline for reference docs that opt in with `<!-- beadloom:watches=... -->`. Kept apart from `sync_state` so the symbol-pair logic is untouched |
| `meta` | key (PK), value | Index metadata (key-value) |

**Infrastructure tables (8):**

| Table | Key columns | Description |
|-------|-------------|-------------|
| `health_snapshots` | id (PK), taken_at, nodes_count, edges_count, docs_count, coverage_pct, stale_count, isolated_count, extra | Trend tracking across reindexes |
| `file_index` | path (PK), hash (SHA-256), kind (graph/doc/code), indexed_at | Incremental reindex support |
| `bundle_cache` | cache_key (PK), bundle_json, etag, graph_mtime, docs_mtime, created_at | L2 persistent context cache |
| `search_index` | ref_id, kind, summary, content | FTS5 virtual table for full-text search |
| `code_imports` | id (PK), file_path, line_number, import_path, resolved_ref_id, file_hash | Import relationships between files |
| `rules` | id (PK), name (UNIQUE), description, rule_type (free-form `TEXT`; the loader owns the vocabulary — BDL-061 S4 dropped the CHECK that restated it and broke every existing DB on a new rule type), rule_json, enabled | Architecture rules from rules.yml |
| `graph_snapshots` | id (PK), label, created_at, nodes_json, edges_json | Point-in-time architecture graph captures for drift detection |
| `foreign_edges` | src_ref_id, dst_ref_id, kind, extra, lifecycle, contract_key | Declared cross-repository edges. Separate from `edges` because a foreign endpoint cannot satisfy the FK to local nodes; `beadloom export` unions them into the federation artifact |

### BFS Algorithm

Context Oracle uses BFS with edge prioritization:

| Priority | Edge type | Description |
|----------|-----------|-------------|
| 1 | part_of | Component is part of |
| 2 | touches_entity | Touches entity |
| 3 | uses / implements | Uses / implements |
| 4 | depends_on | Depends on |
| 5 | touches_code | Touches code |

BFS traverses the graph bidirectionally (outgoing + incoming edges), sorting neighbors by priority.

Default parameters:
- `depth` = 2 — graph traversal depth
- `max_nodes` = 20 — node limit per bundle
- `max_chunks` = 10 — text chunk limit per bundle

### Rules Engine

Architecture rules are defined in `.beadloom/_graph/rules.yml` (schema version 3) and enforce boundaries between graph nodes. The YAML key on each rule selects its type.

**Rule types** — the 12 authoring keys `load_rules` dispatches, parsed and evaluated by the `graph/rules/` package and orchestrated by `graph/linter.py`. A rule declares exactly one of them; this repository configures 15 rules across them:

| YAML key | Semantics | Example |
|----------|-----------|---------|
| `deny` | Forbid `depends_on`/import relationships between matched nodes | `domain:* → service:*` — domains must not depend on services |
| `require` | Require edges from matched nodes to targets | Every `domain:*` must have a `part_of` edge to the `beadloom` service |
| `forbid` | Forbid specific edge patterns between tagged node groups | Nodes tagged `ui-layer` must not have `uses` edges to `native-layer` |
| `layers` | Enforce layered architecture direction | Top-down: services → domains → infrastructure |
| `forbid_cycles` | Detect circular dependencies in the graph | No cycles on `uses`/`depends_on` edges |
| `forbid_import` | Control file-level import boundaries | Files in `src/beadloom/tui/**` must not import `beadloom/infrastructure/**` — note the two vocabularies: `from` matches the **file path**, `to` the **dotted import path with dots → slashes** (no source root). A `src/`-prefixed `to` matches nothing (BDL-UX #172) |
| `check` | Enforce complexity / coverage limits per node | `max_symbols: 180` per domain — counting the symbols a node OWNS, nested nodes excluded (Beadloom's `domain-size-limit`; see the recalibration note below) |
| `unregistered_feature_candidate` | Report a source directory with enough symbols to deserve a node and no node declaring it (BDL-051) | default severity `warn` |
| `module_coverage` | Report a source module under `source_root` that no node tracks (BDL-051) | default severity `warn`; `exempt` entries carry a reason |
| `scenario_coverage` | Bind behaviour-bearing nodes to executable Gherkin scenarios, both ways (BDL-061 S4) | default severity `warn`; `for` / `features` / `references` / `non_behavioural` — see the [BDD guide](guides/bdd-scenarios.md) |
| `doc_area_coherence` | Hold a graph to the source-to-docs placement convention derived from the graph itself (BDL-062) | default severity `warn`, raised to `error` here; `threshold` / `min_support` — no layout literal appears in the rule |
| `summary_facts` | Check a number stated in a node `summary` against the fact the project computes (BDL-062) | default severity `warn`, raised to `error` here; a fact the project cannot compute is reported `unverifiable`, never clean |

> Internally each parsed rule carries a `rule_type` string (`deny` / `require` / `forbid` / `layer` / `forbid_import` / `cardinality` / `scenario_coverage` / `doc_area_coherence` / `summary_facts` / …) used by the evaluators; the **authoring key** in `rules.yml` is the column above.
>
> The two counts above differ because they count different things: 12 is how many keys the loader accepts, 15 is how many rules this repository declares. Only the second is checked by `docs audit` — the fact it is checked against is named `rule_type_count` and computes `SELECT COUNT(*) FROM rules`, which is the instance count, not the type count (BDL-UX #179).

**Evaluation:**
- `deny` rules are checked against the `code_imports` table: resolved import ref_ids are matched against rule patterns
- `require` rules are checked against the `edges` table: nodes matching the `for`/`from` pattern must have the specified edge kind to the target
- Node matchers support an optional `exclude` field (list of ref_ids) to exempt specific nodes from rule matching
- `unless_edge` exemptions allow otherwise-forbidden imports when a specific edge kind exists between the nodes
- `forbid` rules check edge patterns between nodes matching tag selectors
- `layers` rules verify dependency direction across ordered architectural layers
- `forbid_cycles` uses an iterative WHITE/GREY/BLACK colored DFS (in `graph/rules/cycles.py`) to find circular dependency paths, reporting each unique cycle once
- `forbid_import` rules query the `code_imports` table for forbidden cross-boundary imports; a rule whose glob matches **zero** candidates anywhere in the index is itself reported (`rule_type: rule_liveness`, `warn`) rather than counted clean, and `exempt:` entries — which baseline a pre-existing crossing and must carry `reason` + `until` — are reported the same way once they suppress nothing, or once an `until:` that leads with an ISO date passes while they still suppress something. What the remaining entries excused is counted on every run (`violations_suppressed`), so `0 violations` cannot mean `0 violations we counted` (BDL-061.49)
- `check` rules count symbols/files per node (cardinality) and verify module coverage; `module-coverage` is `severity: error`
- **Every** rule type reports its own inertness, not only `forbid_import`: a matcher selecting no node, an edge kind the graph does not have, a `check` with no threshold, a `source_root` with no module. A rule that cannot match is otherwise indistinguishable from one that passed, and both read as `N rules evaluated, 0 violations`. Severity depends on how much the rule stood down. A **partial** inertness — one dead glob beside nine live ones, an exemption that excuses nothing, a matcher selecting no node while the rule's other legs still fire — is `warn` whatever the rule declares: it describes the *configuration*, not the code, and `error` would turn an adopter's green pipeline red on upgrade. A **total** stand-down, where the rule could check NONE of its population, carries the severity the project declared. At that point "found nothing wrong" and "never ran" are the same output, and a project that deliberately escalated the rule has had its escalation evaporate exactly when it mattered (BDL-062 `.9`, BDL-UX #195). What that costs an adopter depends on the severity the rule ships: `doc-area-coherence` ships `warn` and still reports `warn`, so nothing changes for anyone, while `graph-summary-facts` ships `error` and will block a project whose summaries state no checkable number — measured on a graph `beadloom init --mode bootstrap` produced, 0 of 3 summaries state one, so that run is reachable rather than exotic. `severity: warn` on the rule is the one-key opt-out (BDL-062 `.14`). `module_coverage`, `scenario_coverage` and `unregistered_feature_candidate` still report a total stand-down at `warn`; all three ship `warn`, so only a project that escalated them is affected (BDL-UX #197). `lint`'s summary carries `rules_inert` so the advertised rule count cannot over-claim (BDL-UX #172)

**Output formats:**
- **Rich** — human-readable with Unicode indicators (✓, ✗, ▲, ▼)
- **JSON** — structured violations array + summary
- **Porcelain** — machine-readable, one TAB-separated line per violation

**CLI:** `beadloom lint [--strict] [--format rich|json|porcelain] [--no-reindex]`

The `--strict` flag exits with code 1 on `error`-severity violations (for CI/CD). Rules support `error` and `warn` severity levels.

> **`domain-size-limit`: 200 → 280 (BDL-059 S3) → 290 (BDL-060 S4) → 180 (BDL-UX #144).** The first two moves were threshold recalibrations under the OLD metric, where `max_symbols` counted every file under a node's path prefix — so an in-domain split changed nothing and the honest option was to raise the bar for legitimately large bounded contexts.
>
> The last move is different in kind: the **metric changed meaning**. `max_symbols` now counts the symbols a node OWNS — files under its source minus files owned by a more specific node — which is what makes the rule's own remedy work: carving a subpackage into its own node genuinely relieves the parent. Under the new metric this repo's largest owner is `application` at 150 (it was 284 under prefix counting), so 290 could never fire again; 180 restores the signal with ~20% headroom.
>
> One consequence is stated openly: this measures a node's OWN code, not its bounded context's total size. A domain carved into many features owns little and will not trip the rule however large its subtree grows. That is a genuinely different signal, tracked as BDL-UX #158 rather than smuggled into this threshold. The limit stays a `warn` signal for re-scoping, never a target.

### Node Tags

Nodes can be assigned tags for use in rule matching:

```yaml
# In services.yml
nodes:
  - ref_id: my-feature
    kind: feature
    tags: [ui-layer, presentation]
```

Tags are arbitrary strings. Rules reference them via `{ tag: <tag-name> }` selectors in `forbid_edge` and `layer` rules.

### Cache Architecture

Context bundles use a two-tier cache to achieve <20ms response times:

**L1 — In-memory (ContextCache):**
- Key: `(ref_id, depth, max_nodes, max_chunks)`
- Invalidation: mtime comparison against `.beadloom/_graph/` and docs directories
- Cleared on reindex

**L2 — SQLite (SqliteCache):**
- Table: `bundle_cache`
- Key: `"<ref_id>:<depth>:<max_nodes>:<max_chunks>"`
- Survives MCP server restarts
- Invalidation: mtime-based, same as L1

**ETag validation:**
- Format: `"sha256:<first-16-hex-chars>"` of sorted bundle JSON
- Returned on cache hit with `cached: true` and `unchanged_since` timestamp
- Clients skip re-fetching if ETag is unchanged

### Incremental Reindex

The `file_index` table tracks SHA-256 hashes of all indexed files (graph YAML, docs, source code).

**Process:**
1. Scan relevant files across graph, docs, and source directories
2. Compute SHA-256 hash per file
3. Compare with stored `file_index.hash`
4. Only re-parse files with changed hashes; skip unchanged
5. Update `file_index` with new hash and timestamp
6. Return `ReindexResult` with `nothing_changed` flag

When nothing changed, the CLI displays current DB counts instead of "0 indexed".

### Health Snapshots

Each reindex captures a health snapshot:

| Metric | Description |
|--------|-------------|
| `nodes_count` | Total graph nodes |
| `edges_count` | Total graph edges |
| `docs_count` | Total indexed documents |
| `coverage_pct` | % of nodes with linked docs |
| `stale_count` | Stale sync_state records |
| `isolated_count` | Nodes with zero edges |

**Trends:** compared against the previous snapshot, displayed as `▲ +8%`, `▼ +2`, etc. Arrows are inverted for "bad increase" metrics (stale, isolated). Snapshots persist across reindexes.

### Architecture Snapshots

`beadloom snapshot` manages point-in-time captures of the architecture graph for historical comparison.

**Commands:**
- `beadloom snapshot save [--name NAME]` — save current graph state
- `beadloom snapshot list` — list saved snapshots
- `beadloom snapshot compare [SNAP_ID]` — compare current graph with a snapshot

Snapshots are stored in SQLite and enable architecture drift detection across releases.

### Agent Prime

`beadloom prime` outputs a compact project context (target: ≤2000 tokens) for AI agent session initialization.

**Sections:**
1. Project metadata (name, version)
2. Architecture summary (node counts by kind, symbol count)
3. Health metrics (stale docs, lint violations, last reindex)
4. Architecture rules (from rules.yml)
5. Domain list (all domain nodes with summaries)
6. Stale docs (doc/code path pairs)
7. Lint violations (evaluated without reindex)
8. Key CLI commands (reference table)
9. Agent instructions (workflow guidance)

**Output formats:** Markdown (default), JSON.

**Graceful degradation:** works without DB (static-only mode with warning).

### CI Gate

`application/gate.py` powers `beadloom ci` — the unified gate that composes the
existing checkers into one verdict with a single exit code: **reindex → `lint
--strict` → sync-check → docs audit → docs-quality → doc-spaces → config-check →
doctor → (optional) federate landscape gate**. Every step's honest result is printed (PASS / WARN / FAIL / SKIP) —
never a green that silently skipped a step. `--format rich|json|github` applies
uniformly; `--hub <export>` arms the cross-service landscape gate. The same gate
runs as the **pre-push Beadloom Gate** hook (`install-hooks --pre-push`) and in
CI (`.github/workflows/ci.yml`).

`WARN` is a fourth outcome, not a softer pass: a step sets `not_verified` when it ran,
found nothing wrong, and could not establish that there was nothing to find. It does not
change the exit code, so no adopter's green project turns red on upgrade, and it does not
print the word that would claim more than the run knows.

### Freshness rests on git, not on the database

`.beadloom/beadloom.db` is a derived cache: git-ignored, per-machine, rebuilt by any
`reindex --full`, and absent on every fresh CI checkout. A baseline kept only there is
destroyed by the act that most needs it — a rebuilt index adopted the current tree as its
own baseline, so `sync-check` reported every pair fresh by construction (BDL-UX #175). Two
baselines therefore live outside it, both committed:

1. **Freshness — git.** Each `sync_state` row records its `baseline_source`. One fabricated
   at index-build time that would otherwise read `ok` is corroborated against `HEAD` through
   a single `git status --porcelain -z -uall`; where git cannot answer, the pair reads
   `unverified` rather than fresh. A `carried` baseline is copied verbatim across a reindex
   and never promoted, so a fabricated one does not become earned by being copied.
2. **Surface size — `.beadloom/sync-surface.json`.** Committed, and written only by the
   deliberate `sync-check --record-surface`. A later run whose declared surface fell says so
   with both numbers. A ratchet only works if lowering it is a deliberate act left in the
   history, so no ordinary run rewrites the ledger — a check that silently re-records the
   number it is checking against re-attests without evidence (BDL-UX #163).

Two consequences for anyone scripting around the index. Deleting the database and rebuilding
is no longer a way to reach a green `sync-check`, and the retired instruction to verify on a
clean database — right for `lint`, vacuous for `sync-check` — must not come back. What a green
still does not prove is stated rather than left to be found: the git leg compares the working
tree against `HEAD`, so it cannot judge whether a long-committed document still describes its
code. `--since <ref>` answers that, and an incremental reindex keeps the stronger accumulated
index baseline where one exists.

### Agentic Flow Composer

The `onboarding` domain composes the packaged multi-agent dev flow from a
declaration in `.beadloom/flow.yml` plus the adopting repository's own fragments
under `.beadloom/flow/`:

```
.beadloom/flow.yml  ──load──▶  flow_config.py
                                 (FlowConfig: tools, architecture, stack,
                                  quality, language, suppressions)
                                      │
                                      ▼
                              composer.py  compose(kind, name, config=, project_root=)
                                      │   1. CORE fragment (stack-neutral)
                                      │   2. SHARED core fragments (core:_writing)
                                      │   3. ONE architecture overlay (ddd|fsd)
                                      │   4. sorted stack overlays
                                      │   5. .beadloom/flow/<kind>/<name>.md   ← the project
                                      │   + the overlays.suppress notice
                                      ▼
              ┌───────────────────────┼────────────────────────┐
              ▼                       ▼                        ▼
    role_composer.py +      agentic_flow_setup.py    agentic_flow_setup.py
    role_adapters.py        composed_command()       composed_claude_md()
              │                       │                        │
              ▼                       ▼                        ▼
   .claude/agents/*         .claude/commands/*        .claude/CLAUDE.md
   .cursor/agents/*
              └───────── every write recorded in ─────────────┘
                          .beadloom/flow-manifest.json
```

- **`flow_config.py`** — `FlowConfig` (frozen) + `resolve_flow_config` (flag → `flow.yml` → default) + `detect_stack`; strict validation. Supported: tools `claude`/`cursor`; architecture `ddd`/`fsd` (exactly one); stack `python`/`fastapi`/`javascript`/`typescript`/`vuejs`. `language` is validated for shape, not against a closed list; `overlays.suppress` is validated through `flow_suppression`.
- **`composer.py`** — `compose(kind, name, *, config, project_root)` for the four kinds `roles` / `commands` / `claude` / `docs` (BDL-061 S4b moved the document skeletons out of `doc_generator.py`'s string literals into `templates/docs/`; `docs` is the one kind composed with `carries_suppressions=False`, because a suppression stands down a rule addressed to an agent and a generated README has none). Deterministic: the same inputs always yield the same bytes, with no dependence on the clock or on ambient state. That property is what licenses `config-check` to compare against a composition rather than against stored bytes. The CORE fragments live at `onboarding/templates/roles/core/<role>.md.txt`, `onboarding/templates/agentic_flow/commands/<cmd>.md.txt` and `onboarding/templates/agentic_flow/CLAUDE.md.txt`; the overlays live under `onboarding/templates/{roles,commands,claude}/{architecture/<arch>,stack/<stack>}/`. The commands and `CLAUDE.md` kept their vendored location as the CORE and gained an overlay root beside it, because moving them would have churned the whole scaffold for no signal.
- **`role_composer.py`** — `compose_role(role, *, architecture, stack, language, suppressions, project_root)`, the roles-shaped door onto `compose`; FSD at parity with DDD. `SHARED_ROLE_FRAGMENTS = ("_writing",)` (BDL-061 S4) composes the writing standard into all four roles as a labelled `core:_writing` layer, so the roles that produce intent documents are held to the same bar as the one that produces reality documents — one text rather than four copies, and language-selectable like every other layer.
- **`role_adapters.py`** — `generate_adapters(config, project_root)` writes the per-tool adapter set(s). `beadloom setup-agentic-flow --tool/--architecture/--stack` is the CLI entrypoint.
- **`flow_manifest.py`** — the sha256 of every composed write, which is what lets a later run tell `stale` (recomposable) from `hand_edited` (reported, never rewritten) from `missing` from `unverified`. `.beadloom/flow-manifest.json` is generated state and belongs in git.
- **`flow_suppression.py`** — a declared stand-down of a core rule (`rule` + `reason` + `until`, all mandatory), rendered as a visible notice into every composed artifact. Expiry is a `config-check` finding rather than a byte, so the composition stays a function of its inputs.
- **`config_sync.py`** — compares each artifact against its composition, maps the manifest state onto a severity, names the project layer in effect and reports suppression liveness.

The core `CLAUDE.md` measures **371 lines** (down from 440), with each removed line
mapped to a replacement in a stack overlay or in `§0 CRITICAL RULES`. The project
layer is what makes that shrinkage possible: a project's own rules have a home that
survives an upgrade instead of being appended to a drift-guarded shipped file.

The AI tech-writer harness (`ai_agents/ai_techwriter/`) is the runtime half of
the flow: a PR-triggered, symbol-scoped, bounded-parallel doc-refresh harness —
see the `ai_agents` domain README + the `ai-techwriter` feature SPEC.

---

## Invariants

- All `ref_id` values are unique within the graph
- Edges reference only existing nodes (FK with ON DELETE CASCADE)
- A document is linked to at most one node via `ref_id`
- On full reindex all tables except `health_snapshots` are recreated (drop + create)
- WAL mode is enabled on every connection open
- Foreign keys are enabled per-connection

## Constraints

- **Code indexer** parses every extension in `_EXTENSION_LOADERS` via tree-sitter: `.py`, `.ts`, `.tsx`, `.js`, `.jsx`, `.go`, `.rs`, `.kt`, `.kts`, `.java`, `.swift`, `.m`, `.mm`, `.c`, `.h`, `.cpp`, `.hpp`. Reindex change detection reads the same set
- **Import analysis** covers Python, TypeScript, JavaScript, Go, Rust, Kotlin, Java, Swift, Objective-C, C and C++ over 17 file extensions — the keys of `context_oracle.code_indexer._EXTENSION_LOADERS`. `supported_extensions()` narrows that set to the grammars actually installed, so a missing optional tree-sitter package removes an extension rather than failing the walk. The count of parsed languages is deliberately not written as a digit here: `language_count` in the audit's fact vocabulary means the languages this project is WRITTEN in (1), so a digit beside the word `languages` is read as a claim about that and reported stale
- Documentation root is configurable via `docs_dir` in `.beadloom/config.yml` (default: `docs/`)
- Documentation SPACES (TO-BE / AS-IS / WORKING) — their roots, kinds, intent documents and the
  WORKING freshness exemption — are configurable via `doc_roots` in `.beadloom/config.yml`
- Source scan paths are configurable via `scan_paths` in `.beadloom/config.yml` (default: `src`, `lib`, `app`)
- Graph is read only from `.beadloom/_graph/*.yml`
- Rules are read from `.beadloom/_graph/rules.yml`
- The 12 authoring keys `load_rules` dispatches: `deny`, `require`, `forbid`, `layers`, `forbid_cycles`, `forbid_import`, `check`, `unregistered_feature_candidate`, `module_coverage`, `scenario_coverage`, `doc_area_coherence`, `summary_facts`. A rule declares exactly one of them, and `graph.rules.loader.AUTHORING_KEYS` is the single definition of the set
- `ai_agents` is a leaf consumer — never imported by core domains/services (`forbid_import` enforced)
- Maximum chunk size: 2000 characters
- Levenshtein suggestions: maximum 5, distance threshold = max(len/2, 3)

## Configuration

`.beadloom/config.yml`:

| Key | Default | Description |
|-----|---------|-------------|
| `languages` | all supported | File extensions to parse (e.g. `[".py", ".ts"]`) |
| `scan_paths` | `["src", "lib", "app"]` | Source directories to scan |
| `docs_dir` | `docs/` | Documentation root directory |
| `doc_roots` | see the [Document Kinds guide](guides/document-kinds.md) | Per-space roots, kinds, intent documents and the WORKING freshness exemption |
| `sync.hook_mode` | `warn` | Pre-commit hook mode: `warn` or `block` |
