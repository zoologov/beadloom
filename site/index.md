# Beadloom

> Read this in other languages: [Русский](/ru/)

**Keep your architecture accurate and trustworthy — from a single repo to a whole microservices landscape, or every IT product in your company.**

Beadloom turns your architecture into something you can query, check, and trust. It keeps a map of how your system is built — domains, services, features, and the dependencies between them — in plain YAML in Git. It watches that your docs and module boundaries don't quietly drift away from the code. And across many services, it catches a broken contract between them before it ships.

[![License: MIT](https://img.shields.io/github/license/zoologov/beadloom)](https://github.com/zoologov/beadloom/blob/main/LICENSE)
[![GitHub release](https://img.shields.io/github/v/release/zoologov/beadloom?include_prereleases&sort=semver)](https://github.com/zoologov/beadloom/releases)
[![PyPI](https://img.shields.io/pypi/v/beadloom)](https://pypi.org/project/beadloom/)
[![Python](https://img.shields.io/pypi/pyversions/beadloom)](https://pypi.org/project/beadloom/)
[![Tests](https://img.shields.io/github/actions/workflow/status/zoologov/beadloom/tests.yml?label=Tests)](https://github.com/zoologov/beadloom/actions)
[![mypy: strict](https://img.shields.io/badge/mypy-strict-blue)](https://mypy-lang.org/)
[![code style: ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![coverage: 80%+](https://img.shields.io/badge/coverage-80%25%2B-green)](https://github.com/zoologov/beadloom/blob/main/pyproject.toml)

**Platforms:** macOS, Linux, Windows &nbsp;|&nbsp; **Python:** 3.10+

---

## What Beadloom gives you

- **A queryable architecture graph.** Your domains, services, features, and dependencies live in YAML in Git. Ask about any node and get a precise, repeatable answer — the same query returns the same result every time, in under 20 ms.
- **Docs that can't quietly go stale.** Beadloom tracks which docs describe which code. When the code changes and the doc doesn't, it tells you — on every commit, in CI, or on demand.
- **Boundaries that are actually enforced.** Write your architecture rules in YAML and `beadloom lint` blocks violations in CI — no matter who (or which AI tool) wrote the code.
- **Contracts checked across services.** Federate the per-repo graphs into one landscape and Beadloom reconciles **what each service says it provides against what its consumers actually use** — flagging a broken or missing contract before it reaches production.
- **One command of context for AI agents.** `beadloom prime` hands an agent a compact (<2K-token) picture of the architecture at the start of a session, so it works within your design instead of guessing at it.
- **A published knowledge base.** `beadloom docs site` builds a VitePress site — a metrics dashboard with recommendations, an interactive architecture view, a cross-service landscape map, and your hand-written docs with a freshness badge on each.

## The problems it solves

- **"A consumer broke when the producer changed."** Contracts between services — queues, GraphQL schemas — drift apart silently, and the failure surfaces in production, in a different repo than the change.
- **"Only two people understand how this works."** Architecture lives in people's heads, not in the repo. When they leave, the knowledge leaves with them.
- **"The docs are lying."** Documentation goes stale and nobody notices — until someone builds on top of an outdated spec.
- **"Agents spend the first hour just orienting."** Every session starts from scratch: grep, read, guess. The right 2K tokens of context beat a noisy 200K-token window.

It all comes down to one thing: the architecture you *decided on* and the code you *actually have* drift apart over time, and nothing watches the gap. Beadloom watches it — within a repo (docs, boundaries) and between services (contracts). An AI agent can read your code, but it doesn't know the architecture you intended or the state of the contracts outside its own repo. That's exactly the part that's hard to get any other way.

## Federation: checking contracts between services

Inside one repo, the dangerous bugs hide *between* services: a client uses a GraphQL field the backend just removed; a queue has a publisher but no subscriber; a service declares a dependency on another that was never built. None of it is visible from inside a single repository.

Each service exports its graph as a deterministic, commit-stamped artifact. A hub then composes them into one landscape and reconciles the contracts:

```bash
# In each service repo — emit a deterministic, commit-stamped artifact:
beadloom export --out service-a.json

# At the hub — compose the landscape and reconcile contracts:
beadloom federate service-a.json service-b.json service-c.json
```

- **Cross-repo references.** A graph edge can point at a node in another service as `@<repo>:<ref_id>` (e.g. `consumes @backend:WebAPI`). Local refs stay local; a malformed reference is reported, never silently dropped.
- **Contracts over AMQP and GraphQL.** Contracts are first-class and identified by a **language-neutral key** — AMQP as `amqp:<exchange>/<routing>:<message_type>`, GraphQL as `graphql:<schema>`. A TypeScript client and a backend match by the contract *name*, across the language boundary.
- **Plan vs. reality, per contract.** Each contract gets a verdict:

  | Verdict | Meaning |
  |---------|---------|
  | `CONFIRMED` | Producer and consumer are both present and compatible. |
  | `BREAKING` | A consumer uses a name the producer's current GraphQL schema no longer exposes — caught *before* it ships (a presence check, not a version diff). |
  | `ORPHANED_CONSUMER` | Something consumes a contract nobody produces. |
  | `UNDECLARED_PRODUCER` | Something produces a contract nobody consumes. |
  | `EXTERNAL` | Declared as present-but-not-ours (e.g. a native bridge) — never a false alarm. |
  | `DRIFT` | A declared `active` cross-repo dependency whose target doesn't resolve. |

- **Lifecycle-aware.** Every node and edge carries a status — `active`, `planned`, `deprecated`, `dead`, or `external`. A *planned-but-unbuilt* contract reads as expected, not as a failure; a `deprecated` one still in use is flagged as a cleanup candidate.
- **Product and company scope.** `federate` composes a single product (its backend, frontend, infra, integrations) or a whole company's IT landscape spanning several products. Products that share no contract don't generate noise about each other; a cross-product contract shows up only where the integration is real.
- **Honest staleness.** Each artifact carries its commit SHA and timestamp, so the hub reports how old each service's view is — and says "unknown" rather than inventing a SHA.

> **What's shipped, honestly.** Today: AMQP and GraphQL contracts with the presence-based breaking-change check, federation that doesn't care about language or product, and **CI enforcement** — the contract graph can gate CI via `federate --fail-on` and the unified `beadloom ci` (used on Beadloom's own CI). Proven end to end on a real landscape — a real GraphQL `BREAKING` caught before release, and a separate FSD-architecture product round-tripped through `export`/`federate` without losing a thing. The landscape also renders as a visual map in the published VitePress site. **Not yet:** REST/OpenAPI and gRPC contracts — on the roadmap, not promised here. The hub runs on collected artifacts via a documented pull-based pattern — there is no hosted service.

## The per-repo foundation

Federation works because each repo keeps an honest graph of itself. Three building blocks make that possible:

1. **Context Oracle** — the architecture graph in YAML, stored in Git. Query any node and get a deterministic context bundle in under 20 ms — the same input always gives the same output.
2. **Doc Sync Engine** — tracks the link between code and docs and catches stale documentation on every commit. No more "the spec says X but the code does Y".
3. **Architecture Rules** — boundary constraints in YAML, checked by `beadloom lint` and enforced in CI. Boundaries are verified at build time, not hoped for at review time.

For AI agents, `beadloom prime` rolls all three into a payload under 2K tokens — one command in place of the grep → read → guess loop. Connect over MCP and an agent gets the same context, plus the active rules for whatever it's working on, so it stays inside your boundaries by design.

### Deterministic context, not a probabilistic guess

An IDE indexer uses semantic search — an LLM decides what's relevant. Beadloom walks an explicit graph instead, so the same node always yields the same bundle. The graph is YAML in Git: reviewable, auditable, versioned.

|  | Semantic search (IDE) | Beadloom |
|---|---|---|
| **Answers** | "Where is this class?" | "What is this feature, and how does it fit?" |
| **Method** | Embeddings + LLM ranking | Explicit graph + traversal |
| **Result** | Probabilistic | Deterministic |
| **Docs** | Doesn't track freshness | Catches stale docs every commit |
| **Boundaries** | Doesn't check them | Enforces them, blocks violations |
| **Knowledge** | Dies with the session | Lives in Git, survives team changes |

## Who it's for

- **Tech leads & architects** — make architecture explicit, versioned, and able to survive team turnover; enforce boundaries in CI.
- **Platform / DevEx engineers** — give CI a doc-freshness check and boundary validation that actually work, and hand agents structured context out of the box via MCP.
- **Individual developers** — stop spending the first hour of every task figuring out how a part of the system works: `beadloom ctx <feature>` (or the VitePress portal) gets you oriented in minutes.
- **AI-assisted developers** — keep your agents working within the architecture instead of breaking it.

## Install

```bash
uv tool install beadloom        # recommended
pipx install beadloom           # alternative
```

## Quick start

```bash
# 1. Scan your codebase and generate an initial architecture graph
#    (work in progress: bootstrap accuracy is still being refined on real projects)
beadloom init --bootstrap

# 2. Review the generated graph (edit domains, rename nodes, add edges)
vi .beadloom/_graph/services.yml

# 3. Build the index and start using it
beadloom reindex
beadloom ctx search        # get context for a feature
beadloom sync-check        # are the docs up to date?
beadloom lint              # are the architecture rules satisfied?

# 4. Set up context for AI agents
beadloom setup-rules       # create IDE adapter files
beadloom prime             # see exactly what your agent will see
```

No documentation required to start — Beadloom bootstraps a skeleton from code structure alone. From there you fill it in by hand or with any AI agent (see `docs polish`), and Beadloom keeps it current.

## Architecture as Code

Beadloom doesn't just describe your architecture — it enforces it. You write boundary rules in YAML, check them with `beadloom lint`, and block violations in CI. These are real rules from this project:

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

  - name: no-domain-depends-on-service
    description: "Domains must not depend on services"
    deny:
      from: { kind: domain }
      to: { kind: service }
      unless_edge: [part_of]

  # Enforce layer direction (services → domains → infrastructure)
  - name: architecture-layers
    severity: warn
    layers:
      - { name: services, tag: layer-service }
      - { name: domains, tag: layer-domain }
      - { name: infrastructure, tag: layer-infra }
    enforce: top-down

  # Keep the TUI out of the database layer
  - name: tui-no-direct-infra
    forbid_import:
      from: "src/beadloom/tui/**"
      to: "src/beadloom/infrastructure/**"

  # Warn when a node grows too large
  - name: domain-size-limit
    severity: warn
    check:
      for: { kind: domain }
      max_symbols: 200      # too much code in one domain
```

Seven rule types are available: `require`, `deny`, `forbid`, `layers`, `forbid_cycles`, `forbid_import`, and `check`.

```bash
beadloom lint                 # readable output in the terminal
beadloom lint --strict        # exit 1 on violations (for CI)
beadloom lint --format json   # machine-readable
```

When an agent asks for context on a node, the response includes the rules that apply to it — so it respects your boundaries by design, not by luck. Import analysis covers **Python, TypeScript/JavaScript, Go, Rust, Kotlin, Java, Swift, C/C++, and Objective-C**.

## Key features

- **Cross-service contract graph** — `export` per repo, `federate` ≥2 services into one landscape with per-contract verdicts (`CONFIRMED` / `BREAKING` / `ORPHANED_CONSUMER` / `UNDECLARED_PRODUCER` / `EXTERNAL`) over AMQP and GraphQL, plus per-service staleness; product- and company-level scope.
- **CI enforcement** — `beadloom ci` runs reindex → lint → sync-check → config-check → doctor → optional landscape gate behind one exit code; ships as a reusable GitHub Action.
- **Context Oracle** — deterministic graph traversal, a compact JSON bundle in under 20 ms.
- **Doc Sync Engine** — tracks code↔doc links, catches stale docs, hooks into git.
- **Agent context** — `beadloom prime` (<2K tokens), `setup-rules` for IDE adapters, an MCP server with 14 tools, and `config-check` to keep the agent files in sync with the graph.
- **Full-text search** — FTS5 across nodes, docs, and code symbols.
- **Impact analysis** — `beadloom why` shows what depends on a node and what breaks if it changes.
- **Code-first onboarding** — bootstrap a graph from code structure alone; no docs needed to start.
- **Snapshots & debt** — `snapshot` compares architecture over time; `status --debt-report` rolls lint, sync, and complexity into one 0–100 score with a CI gate.
- **C4 diagrams** — auto-generated Context / Container / Component diagrams in Mermaid and PlantUML.
- **Published site** — `beadloom docs site` builds a VitePress knowledge base (dashboard, interactive architecture, landscape map, validated docs).
- **Local-first** — one CLI and one SQLite file. No Docker, no cloud — plus a VitePress knowledge base for the team.

## How it works

Beadloom keeps an architecture graph in YAML under `.beadloom/_graph/` — **nodes** (features, services, domains, entities, ADRs) connected by **edges** (`part_of`, `uses`, `depends_on`, …). Reindexing merges three sources into one SQLite database:

1. **Graph YAML** — the nodes and edges that describe the architecture.
2. **Documentation** — Markdown linked to graph nodes, split into searchable chunks.
3. **Code** — source files parsed with tree-sitter for symbols and `# beadloom:domain=...` annotations.

Ask for a node's context and the Context Oracle runs a breadth-first traversal, gathers the relevant subgraph, docs, and code symbols, and returns a compact bundle. The Doc Sync Engine tracks which docs belong to which code and, on every commit (via a git hook), warns or blocks when they fall out of sync.

## CLI commands

| Command | Description |
|---------|-------------|
| `init --bootstrap` | Scan code and generate an initial architecture graph |
| `init --import DIR` | Import and classify existing documentation |
| `reindex` | Rebuild the SQLite index from graph, docs, and code |
| `ctx REF_ID` | Get a context bundle (Markdown or `--json`) |
| `graph [REF_ID]` | Visualize the architecture graph (Mermaid or JSON) |
| `search QUERY` | Full-text search across nodes, docs, and code symbols |
| `status` | Index statistics, documentation coverage, and debt report |
| `doctor` | Validate the architecture graph |
| `sync-check` | Check doc↔code synchronization |
| `sync-update REF_ID` | Review and update stale docs |
| `why REF_ID` | Impact analysis — what it depends on and what depends on it |
| `lint` | Check code against architecture rules (`--strict`, `--format rich/json/porcelain/github`) |
| `ci` | Unified CI gate: reindex → lint → sync-check → config-check → doctor → optional landscape gate |
| `config-check` | Check (or `--fix`) that generated agent files match the graph |
| `export` | Export the indexed graph as a deterministic federation artifact |
| `federate` | Compose ≥2 export artifacts into one landscape. `--fail-on` arms the CI gate |
| `docs generate` | Generate documentation skeletons from the graph |
| `docs polish` | Emit structured data for AI-assisted doc enrichment |
| `docs site` | Build a VitePress site (dashboard, architecture, landscape map, validated docs) |
| `docs audit` | Detect stale facts in project docs (README, guides) |
| `diff` | Show graph changes since a git ref |
| `snapshot` | Save and compare architecture snapshots |
| `link REF_ID [URL]` | Manage external tracker links on nodes |
| `prime` | Output compact project context for AI agents |
| `setup-rules` | Create IDE adapter files (`.cursorrules`, `.windsurfrules`, `.clinerules`) |
| `setup-mcp` | Configure the MCP server for AI agents |
| `mcp-serve` | Run the MCP server (stdio) |
| `tui` / `ui` | Interactive terminal dashboard (requires `beadloom[tui]`) |
| `watch` | Auto-reindex on file changes (requires `beadloom[watch]`) |
| `install-hooks` | Install the pre-commit hook |

## MCP tools

`beadloom mcp-serve` exposes 14 tools to AI agents: `prime`, `get_context`, `get_graph`, `list_nodes`, `sync_check`, `get_status`, `update_node`, `mark_synced`, `search`, `generate_docs`, `why`, `diff`, `lint`, and `get_debt_report`. Works with Claude Code, Cursor, Windsurf, Cline, and any MCP-compatible tool. Wire it up with:

```json
{
  "mcpServers": {
    "beadloom": { "command": "beadloom", "args": ["mcp-serve"] }
  }
}
```

## Configuration

Everything lives under `.beadloom/` in your repo:

- **`config.yml`** — scan paths, languages, sync settings
- **`_graph/*.yml`** — the architecture graph (version-controlled)
- **`_graph/rules.yml`** — boundary rules
- **`AGENTS.md`** — conventions and the MCP tool catalog for agents
- **`beadloom.db`** — the SQLite index (auto-generated; add to `.gitignore`)

Link code to a graph node with a one-line annotation:

```python
# beadloom:domain=doc-sync
def check_freshness(db: sqlite3.Connection, ref_id: str) -> SyncStatus:
    ...
```

## Docs

| Document | Description |
|----------|-------------|
| [architecture.md](/docs/architecture) | System design and component overview |
| [getting-started.md](/docs/getting-started) | Quick start guide |
| [CI Setup](/docs/guides/ci-setup) | GitHub Actions / GitLab CI integration |
| [VitePress Site](/docs/guides/vitepress-site) | Publish a VitePress knowledge base |
| **Domains** | [Context Oracle](/docs/domains/context-oracle/README) · [Graph](/docs/domains/graph/README) · [Doc Sync](/docs/domains/doc-sync/README) · [Onboarding](/docs/domains/onboarding/README) · [Infrastructure](/docs/domains/infrastructure/README) |
| **Services** | [CLI Reference](/docs/services/cli) · [MCP Server](/docs/services/mcp) · [TUI Dashboard](/docs/services/tui) |

## Beads integration

*A context loom for your [beads](https://github.com/steveyegge/beads).*

Beadloom complements [Beads](https://github.com/steveyegge/beads): worker agents call `get_context(feature_id)` over MCP and get a ready-made bundle instead of searching the codebase from scratch. The integration is optional — Beadloom works fine on its own.

## Development

```bash
uv sync --dev              # install with dev dependencies
uv run pytest              # run tests
uv run ruff check src/     # lint
uv run mypy                # type checking (strict)
```

## License

MIT
