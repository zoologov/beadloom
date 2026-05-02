# Beadloom

> Read this in other languages: [Русский](README.ru.md)

**Federated architecture infrastructure with intent-vs-reality enforcement.**

Beadloom is the cross-service contract graph for a microservices landscape — it detects drift, breaking changes, and orphaned consumers between your services *before they ship*, across paradigms, languages, and product boundaries. Per-repo Architecture-as-Code (a deterministic context graph, doc-sync, boundary lint) is the foundation; the federated landscape is the product.

[![License: MIT](https://img.shields.io/github/license/zoologov/beadloom)](LICENSE)
[![GitHub release](https://img.shields.io/github/v/release/zoologov/beadloom?include_prereleases&sort=semver)](https://github.com/zoologov/beadloom/releases)
[![PyPI](https://img.shields.io/pypi/v/beadloom)](https://pypi.org/project/beadloom/)
[![Python](https://img.shields.io/pypi/pyversions/beadloom)](https://pypi.org/project/beadloom/)
[![Tests](https://img.shields.io/github/actions/workflow/status/zoologov/beadloom/tests.yml?label=Tests)](https://github.com/zoologov/beadloom/actions)
[![mypy: strict](https://img.shields.io/badge/mypy-strict-blue)](https://mypy-lang.org/)
[![code style: ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![coverage: 80%+](https://img.shields.io/badge/coverage-80%25%2B-green)](pyproject.toml)

---

> An IDE indexes one repo's code. Beadloom maps the contracts *between* your services — and tells you which ones are broken.

**Platforms:** macOS, Linux, Windows &nbsp;|&nbsp; **Python:** 3.10+

## Federation: the cross-service contract graph

In a microservices landscape, the dangerous bugs live *between* services: a consumer relies on a GraphQL field the producer just removed; a queue has a publisher but no subscriber; a declared cross-repo dependency points at a service that was never built. None of that is visible inside a single repo. Beadloom federates the per-repo graphs into one landscape graph and reconciles **declared intent against measured reality** — the moat that a self-indexing agent cannot reproduce, because agents can read your code but cannot invent your *intended* architecture and contracts.

```bash
# In each service repo — emit a deterministic, signed-by-commit artifact:
beadloom export --out service-a.json

# At the hub — compose the landscape and reconcile contracts:
beadloom federate service-a.json service-b.json service-c.json
```

- **Cross-repo identity** — a graph edge names a node in another service as `@<repo>:<ref_id>` (e.g. `consumes @backend:WebAPI`). Plain refs stay local; malformed refs are surfaced, never silently dropped.
- **The contract graph (AMQP + GraphQL)** — contracts are first-class and identified by a **language-neutral** `contract_key`: AMQP as `amqp:<exchange>/<routing>:<message_type>`, GraphQL as `graphql:<schema>`. A TypeScript client consuming a backend's GraphQL schema reconciles across the language boundary, by contract *name*, never by code symbol.
- **Contract-level intent-vs-reality verdicts:**

  | Verdict | Meaning |
  |---------|---------|
  | `CONFIRMED` | Producer and consumer both present and compatible. |
  | `BREAKING` | A consumer references a name the producer's current GraphQL SDL no longer exposes — caught *before* it ships (presence-based, not a version diff). |
  | `ORPHANED_CONSUMER` | Consumes a contract nobody produces. |
  | `UNDECLARED_PRODUCER` | Produces a contract nobody consumes. |
  | `EXTERNAL` | Declared present-but-not-ours (e.g. a native bridge) — never false drift. |
  | `DRIFT` | Edge-level: a declared `active` cross-repo dependency whose target does not resolve. |

- **Lifecycle-aware** — every node and edge carries `active` / `planned` / `deprecated` / `dead` / `external`, so a *planned-but-unbuilt* contract reads as `EXPECTED`, not a false alarm, and a `deprecated` one still present is a cleanup candidate.
- **Nested landscapes — product *and* company scope** — `federate` composes a single product (its back / front / infra / integrations) or a whole company of several products. Standalone products that share no contract never produce mutual noise; cross-product contracts appear only where integration is real.
- **Per-satellite staleness** — each artifact carries its commit SHA + timestamp, so the hub reports how stale each service's view is (and honestly says "unknown" rather than faking a SHA).

> **Status — honest scope.** Shipped today: AMQP + GraphQL contracts with the presence-based breaking-change check, paradigm- and product-agnostic federation, and **CI enforcement** — the contract graph is now CI-gateable via `federate --fail-on` and the unified `beadloom ci` gate (dogfooded on Beadloom's own CI). Dogfooded end-to-end on a real landscape — a real GraphQL `BREAKING` mismatch caught before ship, and a separate FSD-architecture product round-tripped through `export`/`federate` with zero kind loss. The federated contract graph also renders as a **🌟 visual landscape map** in the published VitePress site (`beadloom docs site`). **Not yet:** REST/OpenAPI + gRPC contracts — on the roadmap, not over-promised here. The cross-service hub is run on collected artifacts via a documented pull-based pattern (no SaaS hub).

## Why Beadloom?

As AI agents generate code geometrically, the architecture that holds a landscape together erodes faster than any team can track by hand. Agents can self-index *reality* (what the code does); they cannot invent your *intent* (the architecture, boundaries, and contracts you decided on). The durable value is the **diff between intent and reality** — especially across service boundaries.

- **"A consumer broke when the producer changed."** Cross-service contracts (queues, GraphQL schemas) drift silently — the failure shows up in production, in a different repo than the change.
- **"Only two people understand how this works."** Architecture lives in heads, not in the repo. When they leave, the knowledge leaves with them.
- **"The docs are lying."** Documentation goes stale. Nobody notices until a developer or agent builds on top of outdated specs.
- **"Agents burn context on orientation, not work."** Every session starts from scratch — grep, read, guess. The right 2K tokens beat a noisy 128K window.

The federation contract graph above is the headline. Underneath it, each repo runs the Architecture-as-Code foundation — three queryable primitives that make the per-repo graph honest enough to federate:

1. **Context Oracle** — architecture graph in YAML, stored in Git. Query any node → deterministic context bundle in <20ms. Same query, same result, every time.

2. **Doc Sync Engine** — tracks code↔doc relationships. Catches stale documentation on every commit. No more "the spec says X but the code does Y".

3. **Architecture Rules** — boundary constraints in YAML, validated with `beadloom lint`, enforced in CI. Boundaries are checked at build time — not hoped for at review time.

For AI agents, `beadloom prime` assembles all three into a <2K-token payload — one command replaces the grep→read→guess loop. And `beadloom docs site` publishes the whole thing as a VitePress knowledge base — an AaC/DocAsCode metrics dashboard, interactive architecture, the 🌟 cross-repo landscape map, and the hand-written docs with per-doc freshness badges (every number from the same code path as the gate that measures it).

### Deterministic context, not probabilistic guessing

IDE indexers use semantic search — an LLM decides what's relevant. Beadloom uses **deterministic graph traversal**: BFS over an explicit architecture graph produces the same context bundle every time. The graph is YAML in Git — reviewable, auditable, version-controlled.

|  | Semantic search (IDE) | Beadloom |
|---|---|---|
| **Answers** | "Where is this class?" | "What is this feature and how does it fit?" |
| **Method** | Embeddings + LLM ranking | Explicit graph + BFS |
| **Result** | Probabilistic | Deterministic |
| **Docs** | Doesn't track freshness | Catches stale docs every commit |
| **Architecture** | Doesn't validate | Enforces boundaries, blocks violations |
| **Knowledge** | Dies with the session | Lives in Git, survives team changes |

---

### Research and industry trends

- **[Lost in the Middle](https://arxiv.org/abs/2307.03172)** (Liu et al., 2023) — LLMs lose accuracy on information buried in long contexts. The right 2K tokens beat a noisy 128K window.
- **[Context Engineering for Coding Agents](https://martinfowler.com/articles/exploring-gen-ai/context-engineering-coding-agents.html)** (Fowler, 2025) — structured context is a core capability for coding agents, not a nice-to-have.
- **[From Scattered to Structured](https://arxiv.org/html/2601.19548v1)** (Keim & Kaplan, KIT, 2026) — architectural knowledge dispersed across artifacts causes "architectural erosion"; consolidating it into a structured knowledge base is the fix.
- **[Why AI Coding Agents Aren't Production-Ready](https://venturebeat.com/ai/why-ai-coding-agents-arent-production-ready-brittle-context-windows-broken)** (Raja & Gemawat, VentureBeat, 2025) — practitioners at LinkedIn and Microsoft document how agents hallucinate without architectural context.
- **[Context Quality vs Quantity](https://www.augmentcode.com/guides/context-quality-vs-quantity-5-ai-tools-that-nail-relevance)** (Augment Code, 2025) — relationship-aware context reduces hallucinations by ~40% compared to naive context stuffing.
- **[State of Software Architecture 2025](https://icepanel.io/blog/2026-01-21-state-of-software-architecture-survey-2025)** (IcePanel, 2026) — keeping architecture docs current is the #1 challenge; teams lose trust in outdated documentation.
- **[2026 Agentic Coding Trends](https://claude.com/blog/eight-trends-defining-how-software-gets-built-in-2026)** (Anthropic, 2026) — the industry shifts to agent-orchestration with structured context.
- **[Architecture Reset](https://itbrief.news/story/ai-coding-tools-face-2026-reset-towards-architecture)** (ITBrief, 2026) — enterprises pivot from "vibe coding" to architecture-first development.

---

## Who is it for?

**Tech Lead / Architect** — You want architecture knowledge to be explicit, versionable, and survive team rotation. Beadloom makes the implicit explicit: domains, features, services, dependencies — all in YAML, all in Git. `beadloom lint` enforces boundaries in CI.

**Platform / DevEx Engineer** — You build tooling for the team. Beadloom gives your CI pipeline a doc freshness check and architecture boundary validation that actually work. Agents get structured context out of the box via MCP.

**Individual Developer** — You're tired of spending the first hour on every task figuring out "how does this part of the system work?" `beadloom ctx FEATURE-ID` gives you the answer in seconds.

**AI-Assisted / Agent-Native Developer** — You work with AI agents and need them to work within your architecture, not break it. `beadloom prime` + MCP gives your agent a compact, deterministic context payload at session start.

## Key features

- **Cross-service contract graph (federation)** — `beadloom export` emits a deterministic per-repo artifact; `beadloom federate` aggregates ≥2 services into one landscape graph via `@repo:ref_id` edges and assigns **contract-level** intent-vs-reality verdicts (`CONFIRMED` / `BREAKING` / `ORPHANED_CONSUMER` / `UNDECLARED_PRODUCER` / `EXTERNAL`) over AMQP and GraphQL contracts, plus edge-level drift and per-satellite staleness. Nodes and edges carry a `lifecycle` field (`active` / `planned` / `deprecated` / `dead` / `external`); nested product- and company-landscape scoping
- **Context Oracle** — deterministic graph traversal, compact JSON bundle in <20ms
- **Doc Sync Engine** — tracks code↔doc relationships, detects stale documentation, integrates with git hooks
- **Architecture as Code** — define boundary rules in YAML, validate with `beadloom lint`, enforce in CI
- **Agent Prime** — single entry point for AI agents: `beadloom prime` outputs <2K tokens of architecture context, `setup-rules` creates IDE adapters, `AGENTS.md` carries conventions and MCP tools
- **Full-text search** — FTS5-powered search across nodes, docs, and code symbols
- **Impact analysis** — `beadloom why` shows what depends on a node and what breaks if it changes (with `--reverse` and `--depth N` options)
- **Code-first onboarding** — bootstrap an architecture graph from code structure alone; no docs needed to start
- **Architecture snapshots** — `beadloom snapshot` saves and compares architecture state over time
- **MCP server** — 14 tools for AI agents, including write operations, search, impact analysis, diff, and linting
- **Interactive TUI** — `beadloom tui` terminal dashboard for browsing the graph (alias: `ui`)
- **Documentation Audit** — detect stale facts in project-level docs (README, guides, CONTRIBUTING) with zero configuration. CI gate via `--fail-if=stale>0`
- **Architecture Debt Report** — `beadloom status --debt-report` aggregates lint, sync, complexity into a single score 0-100 with CI gate
- **C4 Architecture Diagrams** — auto-generate C4 Context/Container/Component diagrams in Mermaid and PlantUML formats
- **Local-first** — single CLI + single SQLite file, no Docker, no cloud dependencies

## How it works

Beadloom maintains an **architecture graph** defined in YAML files under `.beadloom/_graph/`. The graph consists of **nodes** (features, services, domains, entities, ADRs) connected by **edges** (part_of, uses, depends_on, etc.).

The indexing pipeline merges three sources into a single SQLite database:

1. **Graph YAML** — nodes and edges that describe the project architecture
2. **Documentation** — Markdown files linked to graph nodes, split into searchable chunks
3. **Code** — source files parsed with tree-sitter to extract symbols and `# beadloom:domain=context-oracle` annotations

When you request context for a node, the Context Oracle runs a breadth-first traversal, collects the relevant subgraph, documentation, and code symbols, and returns a compact bundle.

The Doc Sync Engine tracks which documentation files correspond to which code files. On every commit (via a git hook), it detects stale docs and either warns or blocks the commit.

## Architecture as Code

Beadloom doesn't just describe architecture — it enforces it. Define boundary rules in YAML, validate with `beadloom lint`, and block violations in CI.

**Rules** (`.beadloom/_graph/rules.yml`) — rules from this project:

```yaml
version: 3

tags:
  layer-service: [cli, mcp-server, tui]
  layer-domain: [context-oracle, doc-sync, graph, onboarding]
  layer-infra: [infrastructure]

rules:
  - name: domain-needs-parent
    description: "Every domain must be part_of the beadloom service"
    require:
      for: { kind: domain }
      has_edge_to: { ref_id: beadloom }
      edge_kind: part_of

  - name: feature-needs-domain
    description: "Every feature must be part_of a domain"
    require:
      for: { kind: feature }
      has_edge_to: { kind: domain }
      edge_kind: part_of

  - name: service-needs-parent
    description: "Every service (except root) must be part_of the beadloom service"
    require:
      for: { kind: service, exclude: [beadloom] }
      has_edge_to: { ref_id: beadloom }
      edge_kind: part_of

  - name: no-domain-depends-on-service
    description: "Domains must not have depends_on edges to services"
    deny:
      from: { kind: domain }
      to: { kind: service }
      unless_edge: [part_of]
```

**Advanced rule types** — forbid edges, layer enforcement, cycle detection, import boundaries, and cardinality limits:

```yaml
rules:
  # Forbid edges between tagged groups
  - name: ui-no-native
    severity: error
    forbid:
      from: { tag: ui-layer }
      to: { tag: native-layer }
      edge_kind: uses

  # Layer enforcement (top-down)
  - name: architecture-layers
    severity: warn
    layers:
      - { name: services, tag: layer-service }
      - { name: domains, tag: layer-domain }
      - { name: infrastructure, tag: layer-infra }
    enforce: top-down
    allow_skip: true
    edge_kind: depends_on

  # Cycle detection
  - name: no-dependency-cycles
    severity: warn
    forbid_cycles:
      edge_kind: depends_on

  # Import boundary
  - name: tui-no-direct-infra
    forbid_import:
      from: "src/beadloom/tui/**"
      to: "src/beadloom/infrastructure/**"

  # Cardinality limits
  - name: domain-size-limit
    severity: warn
    check:
      for: { kind: domain }
      max_symbols: 200
```

7 rule types available: `require`, `deny`, `forbid`, `layers`, `forbid_cycles`, `forbid_import`, `check`. NodeMatcher supports `tags` and `exclude` for flexible rule targeting.

**Validate:**

```bash
beadloom lint                 # rich output in terminal
beadloom lint --strict        # exit 1 on violations (for CI)
beadloom lint --format json   # machine-readable output
```

**Agent-aware constraints** — when an agent calls `get_context("why")`, the response includes active rules for that node. Agents respect architectural boundaries by design, not by accident.

Supported languages for import analysis: **Python, TypeScript/JavaScript, Go, Rust, Kotlin, Java, Swift, C/C++, Objective-C**.

## Install

```bash
uv tool install beadloom        # recommended
pipx install beadloom            # alternative
```

## Quick start

```bash
# 1. Scan your codebase and generate an architecture graph
beadloom init --bootstrap

# 2. Review the generated graph (edit domains, rename nodes, add edges)
vi .beadloom/_graph/services.yml

# 3. Build the index and start using it
beadloom reindex
beadloom ctx search              # get context for a feature
beadloom sync-check                # check if docs are up to date
beadloom lint                      # check architecture rules

# 4. Set up context injection for AI agents
beadloom setup-rules               # create IDE adapter files
beadloom prime                      # verify: see what your agent will see
```

No documentation required to start — Beadloom bootstraps from code structure alone.

### Agent Prime — one command, full context

Beadloom injects context into AI agents through a three-layer architecture:

1. **IDE adapters** — `beadloom setup-rules` creates `.cursorrules`, `.windsurfrules`, `.clinerules` that point to `.beadloom/AGENTS.md`
2. **AGENTS.md** — project conventions, architecture rules from `rules.yml`, MCP tool catalog — loaded automatically by the agent
3. **`beadloom prime`** — dynamic context payload (<2K tokens): architecture summary, health metrics, active rules, domain map

For programmatic access, connect via MCP:

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

Works with Claude Code, Cursor, Windsurf, Cline, and any MCP-compatible tool.

## CLI commands

| Command | Description |
|---------|-------------|
| `init --bootstrap` | Scan code and generate an initial architecture graph |
| `init --import DIR` | Import and classify existing documentation |
| `reindex` | Rebuild the SQLite index from graph, docs, and code |
| `ctx REF_ID` | Get a context bundle (Markdown or `--json`) |
| `graph [REF_ID]` | Visualize the architecture graph (Mermaid or JSON) |
| `search QUERY` | Full-text search across nodes, docs, and code symbols |
| `status` | Project index statistics and documentation coverage |
| `doctor` | Validate the architecture graph |
| `sync-check` | Check doc↔code synchronization status |
| `sync-update REF_ID` | Review and update stale docs |
| `docs generate` | Generate documentation skeletons from the architecture graph |
| `docs polish` | Generate structured data for AI-driven documentation enrichment |
| `docs site` | Generate a VitePress knowledge base from the graph (metrics dashboard + interactive architecture + 🌟 cross-repo landscape map + published validated docs) |
| `lint` | Validate code against architecture boundary rules (`--format rich/json/porcelain/github`, with `remediation`) |
| `ci` | Unified CI gate — reindex → lint → sync-check → config-check → doctor → optional federate landscape gate, one exit code |
| `config-check` | AgentConfigAsCode — check (or `--fix`) that generated agent-config (`AGENTS.md`, `CLAUDE.md` auto regions, IDE adapters) matches the graph |
| `why REF_ID` | Impact analysis — upstream deps and downstream dependents |
| `diff` | Show graph changes since a git ref |
| `link REF_ID [URL]` | Manage external tracker links on graph nodes |
| `export` | Export the indexed graph as a deterministic federation artifact (JSON) |
| `federate` | Aggregate ≥2 satellite export artifacts into one federated graph (drift + staleness); `--fail-on` arms the landscape CI gate |
| `tui` | Interactive terminal dashboard (alias: `ui`; requires `beadloom[tui]`) |
| `docs audit` | Detect stale facts in project-level documentation (README, guides) |
| `watch` | Auto-reindex on file changes (requires `beadloom[watch]`) |
| `snapshot` | Save and compare architecture snapshots |
| `install-hooks` | Install the beadloom pre-commit hook |
| `prime` | Output compact project context for AI agent injection |
| `setup-rules` | Create IDE adapter files (`.cursorrules`, `.windsurfrules`, `.clinerules`) |
| `setup-mcp` | Configure MCP server for AI agents |
| `mcp-serve` | Run the MCP server (stdio transport) |

## MCP tools

| Tool | Description |
|------|-------------|
| `prime` | Compact project context for AI agent session start |
| `get_context` | Context bundle for a ref_id (graph + docs + code symbols + constraints) |
| `get_graph` | Subgraph around a node (nodes and edges as JSON) |
| `list_nodes` | List graph nodes, optionally filtered by kind |
| `sync_check` | Check if documentation is up-to-date with code |
| `get_status` | Documentation coverage and index statistics |
| `update_node` | Update a node's summary or metadata in YAML and SQLite |
| `mark_synced` | Mark documentation as synchronized with code |
| `search` | Full-text search across nodes, docs, and code symbols |
| `generate_docs` | Generate structured documentation data for AI-driven enrichment |
| `why` | Impact analysis — upstream and downstream dependencies in the graph |
| `diff` | Graph changes relative to a git revision |
| `lint` | Run architecture lint rules. Returns violations as JSON |
| `get_debt_report` | Architecture debt report — aggregated score with categories and top offenders |

## Configuration

All project data lives under `.beadloom/` in your repository root:

- **`.beadloom/config.yml`** — scan paths, languages, sync engine settings
- **`.beadloom/_graph/*.yml`** — architecture graph definition (YAML, version-controlled)
- **`.beadloom/_graph/rules.yml`** — architecture boundary rules
- **`.beadloom/AGENTS.md`** — project conventions and MCP tool catalog for AI agents
- **`.beadloom/beadloom.db`** — SQLite index (auto-generated, add to `.gitignore`)

Link code to graph nodes with annotations:

```python
# beadloom:domain=doc-sync
def check_freshness(db: sqlite3.Connection, ref_id: str) -> SyncStatus:
    ...
```

## Documentation structure

Beadloom uses a domain-first layout. Here is the actual structure from this project:

```
docs/
  architecture.md                                  # system design
  getting-started.md                               # quick start guide
  guides/
    ci-setup.md                                    # CI integration
  domains/
    context-oracle/
      README.md                                    # domain overview
      features/
        cache/SPEC.md                              # L1+L2 cache spec
        search/SPEC.md                             # FTS5 search spec
        why/SPEC.md                                # impact analysis spec
    graph/
      README.md
      features/
        graph-diff/SPEC.md
        rule-engine/SPEC.md
        import-resolver/SPEC.md
    doc-sync/
      README.md
    onboarding/
      README.md
    infrastructure/
      README.md
      features/
        doctor/SPEC.md
        reindex/SPEC.md
        watcher/SPEC.md
  services/
    cli.md                                         # 34 CLI commands
    mcp.md                                         # 14 MCP tools
    tui.md                                         # TUI dashboard
```

Each domain gets a `README.md` (overview, invariants, API). Each feature gets a `SPEC.md` (purpose, data structures, algorithm, constraints).

## Context bundle example

`beadloom ctx why --json` returns a deterministic context bundle — graph, docs, and code symbols assembled via BFS in <20ms:

```json
{
  "version": 2,
  "focus": {
    "ref_id": "why",
    "kind": "feature",
    "summary": "Impact analysis — upstream deps and downstream consumers via bidirectional BFS"
  },
  "graph": {
    "nodes": [
      { "ref_id": "why", "kind": "feature", "summary": "Impact analysis ..." },
      { "ref_id": "context-oracle", "kind": "domain", "summary": "BFS graph traversal, caching, search" },
      { "ref_id": "beadloom", "kind": "service", "summary": "CLI + MCP server" },
      { "ref_id": "search", "kind": "feature", "summary": "FTS5 full-text search" },
      { "ref_id": "cache", "kind": "feature", "summary": "ETag-based bundle cache" }
    ],
    "edges": [
      { "src": "why", "dst": "context-oracle", "kind": "part_of" },
      { "src": "context-oracle", "dst": "beadloom", "kind": "part_of" },
      { "src": "cli", "dst": "context-oracle", "kind": "uses" }
    ]
  },
  "text_chunks": ["... 10 doc chunks from SPEC.md files ..."],
  "code_symbols": ["... 146 symbols from traversed modules ..."],
  "sync_status": { "stale_docs": [], "last_reindex": "2026-02-13T..." }
}
```

BFS depth=2 from `why` traverses: `why` → `context-oracle` (parent domain) → sibling features (`search`, `cache`), services (`cli`, `mcp-server`), cross-domain deps (`infrastructure`, `graph`) — 24 nodes, 73 edges total.

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
| &nbsp;&nbsp;[Cache](docs/domains/context-oracle/features/cache/SPEC.md) | L1 in-memory + L2 SQLite bundle cache |
| &nbsp;&nbsp;[Search](docs/domains/context-oracle/features/search/SPEC.md) | FTS5 full-text search |
| &nbsp;&nbsp;[Why](docs/domains/context-oracle/features/why/SPEC.md) | Impact analysis via bidirectional BFS |
| [Graph](docs/domains/graph/README.md) | YAML graph format, diff, rule engine, linter |
| &nbsp;&nbsp;[Graph Diff](docs/domains/graph/features/graph-diff/SPEC.md) | Git ref comparison for graph changes |
| &nbsp;&nbsp;[Rule Engine](docs/domains/graph/features/rule-engine/SPEC.md) | Architecture-as-Code deny/require rules |
| &nbsp;&nbsp;[Import Resolver](docs/domains/graph/features/import-resolver/SPEC.md) | Multi-language import analysis |
| [Doc Sync](docs/domains/doc-sync/README.md) | Doc↔code synchronization engine |
| [Onboarding](docs/domains/onboarding/README.md) | Project bootstrap and presets |
| [Infrastructure](docs/domains/infrastructure/README.md) | Database, health metrics, reindex |
| &nbsp;&nbsp;[Doctor](docs/domains/infrastructure/features/doctor/SPEC.md) | Graph validation checks |
| &nbsp;&nbsp;[Reindex](docs/domains/infrastructure/features/reindex/SPEC.md) | Full and incremental reindex pipeline |
| &nbsp;&nbsp;[Watcher](docs/domains/infrastructure/features/watcher/SPEC.md) | Auto-reindex on file changes |
| **Services** | |
| [CLI Reference](docs/services/cli.md) | All 34 CLI commands |
| [MCP Server](docs/services/mcp.md) | All 14 MCP tools for AI agents |
| [TUI Dashboard](docs/services/tui.md) | Interactive terminal dashboard |
| **Guides** | |
| [CI Setup](docs/guides/ci-setup.md) | GitHub Actions / GitLab CI integration |
| [VitePress Site](docs/guides/vitepress-site.md) | Publish a VitePress knowledge base (dashboard + landscape map + validated docs) |

## Known Issues

See [UX Issues Log](.claude/development/BDL-UX-Issues.md) for the full list of known issues.

## License

MIT
