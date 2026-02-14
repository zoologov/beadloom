# Beadloom: Product Requirements Document (PRD)

## 1. Overview

Beadloom is a local developer tool that solves two key problems of agentic development on large codebases:

1. **Context window burn on orientation.** AI agents spend 80% of tokens searching and reading documentation/code before starting actual work. Beadloom provides a ready-made, compact context bundle at 0 search tokens.

2. **Documentation degradation.** After an agent or human modifies code, related documentation becomes stale. Nobody updates it in time, and within a month any index starts lying. Beadloom tracks doc-to-code relationships and signals when documentation is outdated.

Beadloom is a **Context Oracle + Doc Sync Engine** on top of a Git repository: an architecture graph in YAML, an index in SQLite, a CLI for humans, and an MCP server for agents.

## 2. Goals and Non-Goals

### 2.1 Goals

- **Instant context.** Given a feature/domain/service identifier, deliver a minimal but sufficient context bundle (graph + documents + code) without any searching.
- **Up-to-date documentation.** Track documentation-to-code relationships and detect staleness on every commit.
- **Onboarding for existing projects.** Automatically generate an initial graph and documentation from the codebase (bootstrap), import existing documentation (import), and support gradual coverage (incremental).
- **Native agent integration.** Operate as an MCP server so that Claude Code and other agents receive context without intermediate steps.
- **Locality.** Work without Docker, cloud services, or external dependencies: one CLI + one SQLite file.

### 2.2 Non-Goals (v0)

- No cloud/hosted service -- local developer tool only.
- No web UI/dashboard -- CLI and MCP server only.
- No full-text semantic search (embeddings) in v0 -- deterministic graph traversal only. Embeddings are planned for phase 4.
- No cross-repo/organizational federation -- single repository/monorepo.
- No long-running daemon in v0 -- CLI works directly with SQLite.

## 3. Users and Scenarios

### 3.1 Target Audience

- Developers and tech leads working with large/complex codebases (>100K lines, multiple services/domains).
- Teams actively using AI agents (Claude Code, Cursor, Beads, etc.) and suffering from excessive token spending on context.
- Teams without formalized documentation who need a quick start (bootstrap).

### 3.2 Key Scenarios

**Onboarding (one-time):**

- "We have 200K lines of code and no documentation. I want to get an initial graph of domains/services/entities and draft documents in 5 minutes so I can start working with Beadloom."
- "We have scattered documentation in `docs/`. I want to import it into the Beadloom structure, automatically classifying and linking it to code."
- "Our project is huge. I want to start with one domain (`payments`) and gradually expand coverage."

**Daily work (Context Oracle):**

- "As an agent, I'm given the task 'add a date filter to PROJ-123'. I call `get_context("PROJ-123")` and receive: domain, invariants, related services, key code files -- all in a single JSON ready for prompt insertion."
- "As a developer, I want to see the dependency graph around the `api-routing` service as a Mermaid diagram."

**After changes (Doc Sync):**

- "An agent modified `services/routing/api.py`. On commit, Beadloom reports: 'SPEC.md for PROJ-123 is stale (api.py changed since last sync). Update the documentation.'"
- "I run `beadloom sync-check` and see all stale documents in the project, with details on which code changed."

## 4. Core Capabilities (v0)

### 4.1 Onboarding: Project Initialization

**Without flags -- interactive mode:**

```
$ beadloom init

Welcome to Beadloom!

What would you like to do?
  1. Bootstrap — generate graph and docs from code (no existing docs)
  2. Import    — import and classify existing documentation
  3. Scope     — bootstrap a specific directory only

Choose [1/2/3]:
```

**Repeated run (`.beadloom/_graph/` already exists):**

```
$ beadloom init

Beadloom is already initialized in this project.

  1. Re-bootstrap — regenerate graph (manual edits will be LOST)
  2. Merge        — add new nodes, keep existing (mark conflicts)
  3. Cancel

Choose [1/2/3]:
```

Three launch modes for existing projects:

**Bootstrap (no documentation):**
```
beadloom init --bootstrap
```
- Scans the project structure (directories, package manifests, entry points).
- Extracts symbols via tree-sitter: modules, classes, functions, routes, types.
- Clusters code by directories/packages into `service` and `domain` candidates.
- Generates a draft YAML graph with `confidence: low|medium|high` labels.
- Creates stub documentation (minimal .md files with TODO sections).
- Creates/updates `.gitignore` (adds `.beadloom/beadloom.db`).
- Creates `.beadloom/config.yml` with default settings.
- Displays an interactive report for human review.

**Import (scattered documentation exists):**
```
beadloom init --import ./docs
```
- Finds all .md files in the specified directory.
- Classifies documents: ADR, feature spec, domain description, API documentation, other.
- Extracts mentions of services, features, and entities from the text.
- Offers an interactive strategy selection:

```
How should Beadloom organize your documentation?

  1. Restructure — copy docs into standard layout (docs/domains/<domain>/features/, ...)
     + Better integration with context builder and sync engine
     + Clean, consistent structure
     + GitHub/GitLab renders domain README.md automatically
     - Original file paths change
     - May require updating internal links

  2. Map in place — keep docs where they are, just build the graph
     + No file changes, zero risk
     + Works with any existing doc structure
     - Sync engine tracks changes less precisely
     - Context builder relies on naming heuristics

Choose [1/2]:
```

- Unrecognized documents: in mode 1, placed in `docs/_imported/`; in mode 2, left in place, mapped as `other`.

**Incremental (gradual coverage):**
```
beadloom init --scope src/payments
```
- Creates a graph and documentation only for the specified scope.
- The rest of the project is marked as `unmapped`.
- `beadloom status` shows coverage by domains/services.

### 4.2 Knowledge Store (SQLite)

A single file `.beadloom/beadloom.db` -- a read-model, rebuildable from Git:

- `nodes` -- graph nodes (domains, features, services, entities, ADRs). `ref_id` is globally unique.
- `edges` -- relationships between nodes.
- `docs` -- document index with references to graph nodes.
- `chunks` -- document chunks for context bundles.
- `code_symbols` -- code symbols with references to graph nodes.
- `sync_state` -- doc-to-code synchronization state (hashes, statuses).

SQLite operates in WAL mode (`journal_mode=WAL`) to support concurrent access by CLI and MCP server.

Source of truth is Git (YAML graph + documentation + code). SQLite is a derived cache.

### 4.3 Graph Model

**Nodes:**

| Kind | Description | Example ref_id |
|------|-------------|----------------|
| `domain` | Domain context | `routing`, `billing` |
| `feature` | Feature/epic | `PROJ-123`, `BILL-12` |
| `service` | Service/component | `api-routing`, `mobile-app` |
| `entity` | Domain entity | `Track`, `Route`, `User` |
| `adr` | Architectural decision | `ADR-001`, `ADR-015` |

`ref_id` is a globally unique node identifier. Recommended convention: if names overlap between types, use a suffix/prefix (`routing` for a domain, `routing-api` for a service). `beadloom doctor` warns about potential conflicts.

**Edges:**

| Kind | Semantics | Example |
|------|-----------|---------|
| `part_of` | Nesting | feature -> domain, service -> domain |
| `depends_on` | Dependency | service -> service |
| `uses` | Usage | feature -> service/entity |
| `implements` | Implementation | service -> feature |
| `touches_entity` | Works with entity | feature/service -> entity |
| `touches_code` | Code linkage | node -> code_symbol |

The graph is stored in `.beadloom/_graph/*.yml` (versioned in Git) and indexed in SQLite.

**YAML to SQLite Mapping:**

| YAML field | SQLite | Description |
|------------|--------|-------------|
| `ref_id` | `nodes.ref_id` (PK) | Unique identifier |
| `kind` | `nodes.kind` | Node type |
| `summary` | `nodes.summary` | Text description |
| `source` | `nodes.source` | Path to source code (optional) |
| `confidence` | -- | Bootstrap only, not indexed |
| `docs` | `docs.ref_id` | Creates entries in `docs` table with corresponding `ref_id` |
| `extra.*` | `nodes.extra` | Arbitrary metadata (JSON) |

### 4.4 Context Oracle (Context Builder)

A deterministic (no LLM) context retrieval process:

1. **Input:** `ref_id` (e.g., `PROJ-123`) or multiple `ref_id`s.
2. **Focus determination:** find nodes in the graph by `ref_id`.
3. **Graph expansion:** traverse edges at depth 1-2, with a node limit and edge type prioritization.
4. **Chunk collection:** for each node in the subgraph, gather relevant documentation sections and code symbols.
5. **Output:** JSON context bundle (graph + text chunks + code symbols).

**Document chunking strategy:**
- Markdown files are split by `##` (H2) headings.
- Each chunk is one section with its heading.
- Maximum chunk size: 2000 characters. Sections exceeding 2000 characters are split by paragraphs.
- Chunks are assigned a section type (`spec`, `invariants`, `api`, `tests`, `constraints`, `other`) based on keywords in the heading.

The context bundle is inserted directly into the agent's prompt, saving the entire context window that would otherwise be spent on searching.

### 4.5 Doc Sync Engine

A mechanism for tracking documentation freshness:

- For each doc-to-code relationship, `code_hash_at_sync` is stored -- a hash of related files at the time of the last documentation update.
- During `beadloom sync-check` or git pre-commit hook:
  - current code hashes are compared with stored ones;
  - documents with changed code are marked as `stale`;
  - a report is generated showing exactly what changed.
- `beadloom sync-update <ref_id>` -- updates documentation manually or via LLM (`--auto`).

**`--auto` and LLM dependency:**

The `--auto` flag is an **optional** capability requiring a configured LLM provider. Configuration in `.beadloom/config.yml`:

```yaml
llm:
  provider: anthropic       # anthropic | openai | ollama | none
  model: claude-sonnet-4-20250514
  api_key_env: ANTHROPIC_API_KEY
```

Without LLM configuration, the `--auto` command returns an error with setup instructions. All other commands (oracle, sync-check, doctor) work fully locally without LLM.

### 4.6 CLI

```
beadloom help
    Help for all commands and flags.

beadloom version
    Beadloom version and environment information.

beadloom init [--bootstrap|--import <path>|--scope <path>]
    Initialize a project. Without flags -- interactive mode.
    Creates .beadloom/, config.yml, _graph/*.yml.
    Automatically updates .gitignore.

beadloom reindex
    Full rebuild of the SQLite index from Git (drop + re-create). Incremental -- phase 4.

beadloom ctx <ref_id> [<ref_id>...] [--json|--markdown] [--depth N] [--max-nodes N] [--max-chunks N]
    Get a context bundle by one or more identifiers.
    Default: Markdown (human-readable). --json for agents.
    --depth: graph traversal depth (default 2).
    --max-nodes: maximum nodes in subgraph (default 20).
    --max-chunks: maximum text chunks (default 10).

beadloom graph <ref_id> [--depth N] [--json]
    Show subgraph around a node.
    Default: Mermaid diagram. --json for machine format.

beadloom sync-check [--ref <ref_id>] [--porcelain]
    Check documentation freshness. Without --ref: entire project.
    --porcelain: machine-readable output (for git hooks and scripts).

beadloom sync-update <ref_id> [--auto]
    Update stale documentation for a node.
    Default: interactively ($EDITOR). --auto: via LLM (requires configuration).

beadloom status
    Project coverage: % of documented domains/services/features.

beadloom doctor
    Integrity validation: broken ref_ids, missing documents,
    empty summaries, orphaned edges, duplicate ref_ids.

beadloom setup-mcp [--global] [--remove]
    Create/update .mcp.json for agent connections.
    --global: write to ~/.claude/mcp.json (for all projects).
    --remove: remove Beadloom configuration from .mcp.json.

beadloom install-hooks
    Install git pre-commit hook for automatic sync-check.
```

**Global flags:**
- `--verbose` / `-v` -- verbose output.
- `--quiet` / `-q` -- minimal output (errors only).

**Exit codes:**
- `0` -- success.
- `1` -- error.
- `2` -- stale documents found (for `sync-check`; allows git hooks to distinguish errors from warnings).

### 4.7 MCP Server (Agent Integration)

Beadloom provides an MCP server (Model Context Protocol) for native integration with Claude Code and other MCP-compatible agents.

Connection via `.mcp.json`:
```json
{
  "mcpServers": {
    "beadloom": {
      "command": "beadloom",
      "args": ["mcp-serve"]
    }
  }
}
```

MCP tools:

| Tool | Description |
|------|-------------|
| `get_context(ref_id, depth?, max_nodes?, max_chunks?)` | Get context bundle |
| `get_graph(ref_id, depth?)` | Get subgraph |
| `sync_check(ref_id?)` | Check documentation freshness |
| `list_nodes(kind?)` | List graph nodes (by type) |
| `get_status()` | Coverage and index status |

The MCP server is launched on-demand by the agent (stdio transport), no separate daemon required.

**L1 cache:** In-memory bundle cache saves tokens on repeated requests within one session -- instead of the full bundle (~2000 tokens), a short response `{"cached": true}` (~20 tokens) is returned. Invalidation by file mtime.

**Stale index detection:** If `_graph/*.yml` or documents have changed since the last `reindex`, the MCP server adds a warning `"warning": "index is stale, run beadloom reindex"` to the response.

Quick setup:
```
beadloom setup-mcp    # automatically creates .mcp.json in the project
```

### 4.8 Documentation Conventions

`.beadloom/` structure (configuration and index):
```
.beadloom/
  beadloom.db          # SQLite -- derived, in .gitignore
  config.yml           # Project configuration -- versioned
  _graph/              # YAML graph -- versioned
    domains.yml
    services.yml
    features.yml
    entities.yml
```

`beadloom init` automatically adds to `.gitignore`:
```
# Beadloom (auto-generated)
.beadloom/beadloom.db
```

`docs/` structure (documentation, versioned in Git):
```
docs/
  architecture.md
  decisions/
    <adr_id>.md
  domains/
    <domain>/
      README.md            # domain overview, invariants, contracts
      features/
        <feature_id>/
          SPEC.md
          API.md
  _imported/               # unrecognized after import
```

Principle: **domain-first hierarchy**. Features are grouped by domains (10-15 domain folders instead of 200 flat feature folders). Domain `README.md` renders automatically on GitHub/GitLab. `decisions/` is separate -- ADRs are cross-domain. Lowercase folders -- modern standard.

Cross-domain features: a feature lives under its primary domain (first `part_of` edge in the graph). The graph knows all relationships; `get_context` collects documents from any paths.

In **map-in-place** mode (import), the structure is not enforced -- the graph references original paths.

Code annotations (optional, for linking symbols to the graph):
```python
# beadloom:feature=PROJ-123 domain=routing entity=Track
async def list_tracks(...):
    ...
```

## 5. Installation and Quick Start

### 5.1 Installation

```bash
# Recommended method (uv manages Python versions automatically)
uv tool install beadloom

# Alternatives
pipx install beadloom          # isolated installation
pip install beadloom            # into active environment
```

### 5.2 Quick Start

```bash
cd your-project
beadloom init --bootstrap       # auto-generate graph from code
# ... review .beadloom/_graph/*.yml ...
beadloom reindex                # build index
beadloom setup-mcp              # connect agents
# Done. Agent can call get_context().
```

### 5.3 Requirements

- Python 3.10+ (when installed via `uv` -- managed automatically).
- Git.
- No other system dependencies.

## 6. Constraints and Technology Stack

- **Locality:** no Docker, no external services, no network dependencies. LLM is an optional dependency only for `sync-update --auto`.
- **Single SQLite file** alongside the repository (`.beadloom/beadloom.db`), WAL mode for concurrent access.
- **CLI-first:** no daemon in v0. CLI and MCP server work directly with SQLite.
- **Determinism:** the context builder does not use LLM. Graph traversal is pure logic.
- **Implementation language:** Python (ease of prototyping, rich CLI ecosystem, tree-sitter bindings, SQLite).
- **Distribution:** PyPI (`uv tool install` / `pipx install`). Install script for automation.

## 7. Integrations

### 7.1 Claude Code and MCP-Compatible Agents

- Agent connects Beadloom as an MCP server.
- Instead of grep/glob across the entire codebase, calls `get_context("PROJ-123")`.
- Receives a compact bundle: graph, key documentation sections, code files/symbols.
- The entire context window remains available for work, not orientation.

### 7.2 Beads

- Beadloom complements Beads, not replaces it.
- Beads planner/workers call `get_context(feature_id)` via MCP and receive ready-made context for coder/reviewer agents.

### 7.3 Git hooks

- Pre-commit hook calls `beadloom sync-check --porcelain` for changed files.
- Exit code `2` = stale docs found -- warning or block (configurable via `hook_mode`).
- If documentation is stale -- warning (or commit block, depending on settings).

## 8. Phased Implementation

| Phase | What | Value |
|-------|------|-------|
| **0 -- Onboarding** | `init` (interactive/bootstrap/import/scope), `status`, `.gitignore` | Without data, other phases are useless |
| **1 -- Context Oracle** | `reindex`, `ctx`, `graph`, `doctor`, `help`, `version` | Core value: instant context |
| **2 -- MCP Server** | `mcp-serve`, `setup-mcp`, L1 cache, stale index detection, agent tools | Native integration with Claude Code |
| **3 -- Doc Sync** | `sync-check` (+ `--porcelain`), `sync-update` (+ `--auto`), `install-hooks`, LLM config | Killer feature: documentation doesn't rot |
| **4 -- Polish** | Embeddings for fuzzy queries, incremental reindex, caching | Scaling and performance |

## 9. Future Development (post-v0)

- Embeddings and semantic search for free-text queries.
- Auto-generation/update of node summaries via LLM.
- Multi-repository support and cross-repo graphs.
- Web interface for graph visualization.
- Optional daemon for heavy scenarios (caching, background re-indexing).
- Auto-reindex in MCP server upon detecting changes.
