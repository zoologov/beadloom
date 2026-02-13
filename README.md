# Beadloom

> Read this in other languages: [Русский](README.ru.md)

**Your architecture shouldn't live in one person's head.**

[![License: MIT](https://img.shields.io/github/license/zoologov/beadloom)](LICENSE)
[![GitHub release](https://img.shields.io/github/v/release/zoologov/beadloom)](https://github.com/zoologov/beadloom/releases)
[![PyPI](https://img.shields.io/pypi/v/beadloom)](https://pypi.org/project/beadloom/)
[![Python](https://img.shields.io/pypi/pyversions/beadloom)](https://pypi.org/project/beadloom/)
[![CI](https://img.shields.io/github/actions/workflow/status/zoologov/beadloom/ci.yml?label=CI)](https://github.com/zoologov/beadloom/actions)
[![mypy: strict](https://img.shields.io/badge/mypy-strict-blue)](https://mypy-lang.org/)
[![code style: ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![coverage: 80%+](https://img.shields.io/badge/coverage-80%25%2B-green)](pyproject.toml)

---

Beadloom is a knowledge management tool for codebases. It turns scattered architecture knowledge into an explicit, queryable graph that lives in your Git repository — accessible to both humans and AI agents.

> IDE finds code. Beadloom tells you what that code means in the context of your system.

**Platforms:** macOS, Linux, Windows &nbsp;|&nbsp; **Python:** 3.10+

## Why Beadloom?

Large codebases have a knowledge problem that code search alone doesn't solve:

- **"Only two people understand how this system works."** Architecture knowledge lives in heads, not in the repo. When those people leave, the knowledge goes with them.
- **"The docs are lying."** Documentation goes stale within weeks. Nobody notices until an agent or a new hire builds on top of outdated specs.
- **"AI agents reinvent context every session."** Each agent run starts from scratch — grepping, reading READMEs, guessing which files matter. Most of the context window burns on orientation, not on actual work.

Beadloom solves this with two primitives:

1. **Context Oracle** — a knowledge graph (YAML in Git) that maps your domains, features, services, and their relationships. Query any node and get a deterministic, compact context bundle in <20ms. Same query, same result, every time.

2. **Doc Sync Engine** — tracks which docs correspond to which code. Detects stale documentation on every commit. No more "the spec says X but the code does Y".

### Deterministic context, not probabilistic guessing

IDE indexers use semantic search — an LLM decides what's relevant. This works for "find similar code", but fails for "explain this feature in the context of the whole system".

Beadloom uses **deterministic graph traversal**: your team defines the architecture graph, and BFS produces the same context bundle every time. The graph is YAML in Git — reviewable in PRs, auditable, version-controlled.

|  | Semantic search (IDE) | Beadloom |
|---|---|---|
| **Answers** | "Where is this class?" | "What is this feature and how does it fit?" |
| **Method** | Embeddings + LLM ranking | Explicit graph + BFS traversal |
| **Result** | Probabilistic file list | Deterministic context bundle |
| **Docs** | Doesn't track freshness | Catches stale docs on every commit |
| **Knowledge** | Dies with the session | Lives in Git, survives team changes |

Beadloom doesn't replace your IDE. It gives your IDE — and your agents — the architectural context they can't infer from code alone.

## Install

```bash
uv tool install beadloom        # recommended
pipx install beadloom            # alternative
```

## Quick start

```bash
# 1. Scan your codebase and generate a knowledge graph
beadloom init --bootstrap

# 2. Review the generated graph (edit domains, rename nodes, add edges)
vi .beadloom/_graph/services.yml

# 3. Build the index and start using it
beadloom reindex
beadloom ctx AUTH-001              # get context for a feature
beadloom sync-check                # check if docs are up to date
```

No documentation required to start — Beadloom bootstraps from code structure alone.

### Connect AI agents via MCP

```bash
beadloom setup-mcp                 # creates .mcp.json automatically
```

Agents call `get_context("AUTH-001")` and receive a ready-made bundle — zero search tokens:

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

Works with Claude Code, Cursor, and any MCP-compatible tool.

## Who is it for?

**Tech Lead / Architect** — You want architecture knowledge to be explicit, versionable, and survive team rotation. Beadloom makes the implicit explicit: domains, features, services, dependencies — all in YAML, all in Git.

**Platform / DevEx Engineer** — You build tooling for the team. Beadloom gives your agents structured context out of the box (via MCP), and your CI pipeline a doc freshness check that actually works.

**Individual Developer** — You're tired of spending the first hour on every task figuring out "how does this part of the system work?" `beadloom ctx FEATURE-ID` gives you the answer in seconds.

## Key features

- **Context Oracle** — deterministic graph traversal, compact JSON bundle in <20ms
- **Doc Sync Engine** — tracks code↔doc relationships, detects stale documentation, integrates with git hooks
- **Architecture as Code** — define boundary rules in YAML, validate with `beadloom lint`, enforce in CI
- **Full-text search** — FTS5-powered search across nodes, docs, and code symbols
- **Impact analysis** — `beadloom why` shows what depends on a node and what breaks if it changes
- **Code-first onboarding** — bootstrap a knowledge graph from code structure alone; no docs needed to start
- **MCP server** — 8 tools for AI agents, including write operations and search
- **Interactive TUI** — `beadloom ui` terminal dashboard for browsing the graph
- **Local-first** — single CLI + single SQLite file, no Docker, no cloud dependencies

## How it works

Beadloom maintains a **knowledge graph** defined in YAML files under `.beadloom/_graph/`. The graph consists of **nodes** (features, services, domains, entities, ADRs) connected by **edges** (part_of, uses, depends_on, etc.).

The indexing pipeline merges three sources into a single SQLite database:

1. **Graph YAML** — nodes and edges that describe the project architecture
2. **Documentation** — Markdown files linked to graph nodes, split into searchable chunks
3. **Code** — source files parsed with tree-sitter to extract symbols and `# beadloom:feature=AUTH-001` annotations

When you request context for a node, the Context Oracle runs a breadth-first traversal, collects the relevant subgraph, documentation, and code symbols, and returns a compact bundle.

The Doc Sync Engine tracks which documentation files correspond to which code files. On every commit (via a git hook), it detects stale docs and either warns or blocks the commit.

## Architecture as Code

Beadloom doesn't just describe architecture — it enforces it. Define boundary rules in YAML, validate with `beadloom lint`, and block violations in CI.

**Rules** (`.beadloom/_graph/rules.yml`):

```yaml
rules:
  - name: billing-auth-boundary
    description: "Billing must not import from auth directly"
    deny:
      from: { domain: billing }
      to: { domain: auth }

  - name: core-has-docs
    description: "Every service must have documentation"
    require:
      for: { kind: service }
      has: documentation
```

**Validate:**

```bash
beadloom lint                 # rich output in terminal
beadloom lint --strict        # exit 1 on violations (for CI)
beadloom lint --format json   # machine-readable output
```

**Agent-aware constraints** — when an agent calls `get_context("AUTH-001")`, the response includes active rules for that node. Agents respect architectural boundaries by design, not by accident.

Supported languages for import analysis: **Python, TypeScript/JavaScript, Go, Rust**.

## CLI commands

| Command | Description |
|---------|-------------|
| `init --bootstrap` | Scan code and generate an initial knowledge graph |
| `init --import DIR` | Import and classify existing documentation |
| `reindex` | Rebuild the SQLite index from graph, docs, and code |
| `ctx REF_ID` | Get a context bundle (Markdown or `--json`) |
| `graph [REF_ID]` | Visualize the knowledge graph (Mermaid or JSON) |
| `search QUERY` | Full-text search across nodes, docs, and code symbols |
| `status` | Project index statistics and documentation coverage |
| `doctor` | Validate the knowledge graph |
| `sync-check` | Check doc↔code synchronization status |
| `sync-update REF_ID` | Review and update stale docs |
| `lint` | Validate code against architecture boundary rules |
| `why REF_ID` | Impact analysis — upstream deps and downstream dependents |
| `diff` | Show graph changes since a git ref |
| `link REF_ID [URL]` | Manage external tracker links on graph nodes |
| `ui` | Interactive terminal dashboard (requires `beadloom[tui]`) |
| `watch` | Auto-reindex on file changes (requires `beadloom[watch]`) |
| `install-hooks` | Install the beadloom pre-commit hook |
| `setup-mcp` | Configure MCP server for AI agents |
| `mcp-serve` | Run the MCP server (stdio transport) |

## MCP tools

| Tool | Description |
|------|-------------|
| `get_context` | Context bundle for a ref_id (graph + docs + code symbols + constraints) |
| `get_graph` | Subgraph around a node (nodes and edges as JSON) |
| `list_nodes` | List graph nodes, optionally filtered by kind |
| `sync_check` | Check if documentation is up-to-date with code |
| `get_status` | Documentation coverage and index statistics |
| `update_node` | Update a node's summary or metadata in YAML and SQLite |
| `mark_synced` | Mark documentation as synchronized with code |
| `search` | Full-text search across nodes, docs, and code symbols |

## Configuration

All project data lives under `.beadloom/` in your repository root:

- **`.beadloom/config.yml`** — scan paths, languages, sync engine settings
- **`.beadloom/_graph/*.yml`** — knowledge graph definition (YAML, version-controlled)
- **`.beadloom/beadloom.db`** — SQLite index (auto-generated, add to `.gitignore`)

Link code to graph nodes with annotations:

```python
# beadloom:feature=AUTH-001
# beadloom:service=user-service
def authenticate(user_id: str) -> bool:
    ...
```

## Documentation structure

Beadloom uses a domain-first layout:

```
docs/
  architecture.md
  decisions/
    ADR-001-cache-strategy.md
  domains/
    auth/
      README.md                  # domain overview, invariants
      features/
        AUTH-001/
          SPEC.md
    billing/
      README.md
  _imported/                     # unclassified docs from import
```

## Beads integration

*A context loom for your [beads](https://github.com/steveyegge/beads).*

Beadloom complements [Beads](https://github.com/steveyegge/beads) by providing structured context to planner/coder/reviewer agents. Beads workers call `get_context(feature_id)` via MCP and receive a ready-made bundle instead of searching the codebase from scratch.

Beadloom works independently of Beads — the integration is optional.

## Development

```bash
uv sync --dev              # install with dev dependencies
uv run pytest              # run tests
uv run ruff check src/     # lint
uv run ruff format src/    # format
uv run mypy                # type checking (strict mode)
```

## Docs

| Document | Description |
|----------|-------------|
| [architecture.md](docs/architecture.md) | System design and component overview |
| [getting-started.md](docs/getting-started.md) | Quick start guide |
| **Domains** | |
| [Context Oracle](docs/domains/context-oracle/README.md) | BFS algorithm, context assembly, caching, search |
| [Graph](docs/domains/graph/README.md) | YAML graph format, diff, rule engine, linter |
| [Doc Sync](docs/domains/doc-sync/README.md) | Doc↔code synchronization engine |
| [Onboarding](docs/domains/onboarding/README.md) | Project bootstrap and presets |
| [Infrastructure](docs/domains/infrastructure/README.md) | Database, health metrics, reindex |
| **Services** | |
| [CLI Reference](docs/services/cli.md) | All 18 CLI commands |
| [MCP Server](docs/services/mcp.md) | All 8 MCP tools for AI agents |
| **Guides** | |
| [CI Setup](docs/guides/ci-setup.md) | GitHub Actions / GitLab CI integration |

## License

MIT
