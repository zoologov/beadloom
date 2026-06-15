# Beadloom

<!-- beadloom:watches=cli,graph,flow.yml -->

> Read this in other languages: [Русский](README.ru.md)

**Beadloom is the source of truth about your code: its architecture, its contracts, and its documentation.**

It keeps all of that from drifting away from the code and highlights whatever has gone stale. At its core is a queryable graph derived from the code itself, and on top of that graph it builds tools — cross-service federation, integrity checks, an agentic dev workflow, and more. A single Gate lets nothing into `main` that breaks architectural boundaries and rules, ships stale or missing documentation, or carries a broken contract — the same for people and for agents.

It is one free, MIT-licensed tool, with no cloud: a single CLI and a single SQLite file. The graph lives in Git next to the code, so knowledge of how the system is built outlives team turnover instead of leaving with people.

[![License: MIT](https://img.shields.io/github/license/zoologov/beadloom)](LICENSE)
[![GitHub release](https://img.shields.io/github/v/release/zoologov/beadloom?include_prereleases&sort=semver)](https://github.com/zoologov/beadloom/releases)
[![PyPI](https://img.shields.io/pypi/v/beadloom)](https://pypi.org/project/beadloom/)
[![Python](https://img.shields.io/pypi/pyversions/beadloom)](https://pypi.org/project/beadloom/)
[![CI](https://img.shields.io/github/actions/workflow/status/zoologov/beadloom/ci.yml?branch=main&label=CI)](https://github.com/zoologov/beadloom/actions/workflows/ci.yml)
[![mypy: strict](https://img.shields.io/badge/mypy-strict-blue)](https://mypy-lang.org/)
[![code style: ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![coverage: 80%+](https://img.shields.io/badge/coverage-80%25%2B-green)](pyproject.toml)
[![Docs portal](https://img.shields.io/badge/docs-portal-8A2BE2)](https://zoologov.github.io/beadloom/)

📖 **Documentation portal:** [zoologov.github.io/beadloom](https://zoologov.github.io/beadloom/) — interactive architecture, metrics dashboard, and up-to-date documentation.

**Platforms:** macOS, Linux, Windows &nbsp;|&nbsp; **Python:** 3.10+

---

## At the core — the graph

Everything Beadloom does rests on one data structure: the architecture graph of your system. The graph is bootstrapped from the code itself (`beadloom init --bootstrap`), lives in Git as YAML, and is checked against the real sources on every reindex. You can query it, and it always answers the same question the same way — it is ordinary data you can review and version.

Three parts keep the graph honest:

1. **Context Oracle** — a graph traversal returns a deterministic context bundle for any node in under 20 ms: the code, the documentation, and the rules in force.
2. **Doc Sync Engine** — knows which documentation describes which code and catches drift on every commit. No more "the spec says one thing, the code does another."
3. **Architecture Rules** — boundaries and rules in YAML, checked by `beadloom lint`. A boundary holds at build time, not "at review, if someone notices."

For an AI agent the same three parts are packed into a single bundle under 2K tokens by `beadloom prime` — instead of the usual grep-read-guess loop. Over MCP the agent gets that same context and the rules in force for the part it is working on, so it stays within your architectural boundaries by default.

|  | Semantic search (IDE) | Beadloom |
|---|---|---|
| **Answers** | "Where is this class?" | "What is this feature and how does it fit?" |
| **Method** | Embeddings and model ranking | Explicit graph and traversal |
| **Result** | Probabilistic | Deterministic |
| **Documentation** | Doesn't track freshness | Catches stale docs on every commit |
| **Boundaries** | Doesn't check | Enforces, blocks violations |
| **Knowledge** | Dies with the session | Lives in Git, outlives team turnover |

## On top of the graph — the tools

On that same graph Beadloom builds tools that work across the whole system:

- **Cross-service federation.** The graphs of individual repositories combine into one landscape, where Beadloom checks what each service promises to provide against what its consumers actually use.
- **A configurable, tool-agnostic agentic workflow.** `beadloom setup-agentic-flow` composes a multi-agent workflow (dev → test → review → tech-writer) and writes adapters for Claude Code and Cursor at parity.
- **A published knowledge base.** `beadloom docs site` builds a portal (VitePress) — a metrics dashboard, interactive architecture, a landscape map, and documentation tagged with its freshness.

## A single Gate

Documentation, boundary, and contract checks converge into one Gate. `beadloom ci` runs the full set — reindex, `lint --strict`, sync-check, config-check, doctor, and the optional landscape gate — and works in three places: in a pre-push hook locally, as a required check in CI, and in the agent's hands.

So the rule is simple and the same for everyone. Nothing reaches `main` that breaks architectural boundaries and rules, ships stale or missing documentation, or carries a broken cross-service contract — whether the author is a person or an AI agent. `beadloom install-hooks` installs a pre-push hook that blocks the push on a red Gate (use the documented `git push --no-verify` to bypass), and that same `beadloom ci` stays a required check in CI. There is one gate, and it is deterministic.

## What it solves

The architecture you intended and the code you actually shipped drift apart over time — and no one is watching that gap. Inside a repository, documentation quietly goes stale and architectural boundaries blur. Between services, contracts break just as quietly: a renamed queue listener, a dependency declared in the plan but never built, an endpoint with no consumer left. Each specialized check covers its own protocol, but no one is responsible for the landscape as a whole — so the break surfaces in production, in another service, not where the change was made.

Beadloom makes that gap visible and checkable: documentation and boundaries inside each repository, contracts between services. An AI agent can read your code, but it does not know the architecture you intended or the state of contracts outside the repository — and that is exactly the part that is hard to get any other way.

## Federation: cross-service contract checking

The most dangerous bugs hide **between** services — where the compiler and the tests of a single repository can't reach, and specialized checks are tied to one protocol. An event goes to a queue whose only listener was renamed in a neighboring repository — a broker has neither a schema nor a registry to notice. One service is built against a dependency that was declared in the plan but never built. An endpoint keeps being maintained even though its last consumer was removed long ago. Beadloom brings contracts of every kind — AMQP messages, GraphQL, declared cross-service dependencies — into one landscape graph and checks both sides of each, with an eye on lifecycle: `planned` need not exist yet and raises no false alarm, while `deprecated` that is still in use is plain debt. Not the schema of one protocol, but a map of the whole landscape's intent against what was actually built.

Each service exports its graph as a deterministic, commit-pinned artifact. A hub aggregates them into one landscape and checks the contracts:

```bash
# In each service repo — a deterministic, commit-pinned artifact:
beadloom export --out service-a.json

# At the hub — aggregate the landscape and check the contracts:
beadloom federate service-a.json service-b.json service-c.json
```

- **Cross-repository references.** A graph edge can point to a node in another service as `@<repo>:<ref_id>` (for example, `consumes @backend:WebAPI`). Local references stay local. A wrong reference is surfaced by Beadloom, not silently dropped.
- **Contracts over AMQP and GraphQL.** Contracts are first-class entities with a language-neutral key: AMQP as `amqp:<broker>/<routing>:<message type>`, GraphQL as `graphql:<schema>`. A TypeScript client and the backend match by the contract's **name**.
- **Intent vs. reality for every contract.** Each contract gets a verdict:

  | Verdict | Meaning |
  |---------|---------|
  | `CONFIRMED` | Producer and consumer are both present and compatible. |
  | `BREAKING` | A consumer uses a name no longer present in the producer's current GraphQL schema. Caught **before** release — a presence check, not a version comparison. |
  | `ORPHANED_CONSUMER` | Something consumes a contract that no one produces. |
  | `UNDECLARED_PRODUCER` | Something produces a contract that no one consumes. |
  | `EXTERNAL` | Marked "present, but not ours" (for example, a native bridge) — no false alarms. |
  | `DRIFT` | A cross-repo dependency declared active whose target cannot be found. |

- **Lifecycle-aware.** Every node and edge has a status — `active`, `planned`, `deprecated`, `dead`, or `external`. A planned but not-yet-built contract reads as expected, not as a failure. And a `deprecated` one still in use is flagged as a removal candidate.
- **Product and company scale.** `federate` aggregates either a single product (its backend, frontend, infrastructure, integrations) or a whole company landscape of several products. Products with no shared contracts don't generate noise about each other, and a cross-product contract appears only where the integration is real.
- **Freshness.** Every artifact carries a commit SHA and a timestamp, so the hub shows how stale each service's contract export is. When there is no data, it honestly says "unknown" rather than inventing a SHA.

> **What's ready.** AMQP and GraphQL contracts with presence-based breaking-change detection, federation that is language- and product-agnostic, and CI enforcement — the contract graph can be gated through `federate --fail-on` and the single `beadloom ci` (proven on Beadloom's own CI). Validated end-to-end on a real landscape: a real `BREAKING` GraphQL mismatch caught before release, and a separate FSD product completed the `export`/`federate` round trip without loss. The landscape is drawn as a visual map on the published VitePress portal.
> **Not yet:** REST/OpenAPI and gRPC contracts — that's planned. The hub works on collected artifacts following a documented schema, with no hosted service.

## Agentic dev workflow — configurable, tool-agnostic

The same graph that answers `prime` and `ctx` also powers a packaged multi-agent dev workflow. You describe what the project is once — in `.beadloom/flow.yml`:

```yaml
tools:        [claude, cursor]   # generate adapters for one or both
architecture: [ddd]              # ddd | fsd (exactly one)
stack:        [python]           # python, fastapi, javascript, typescript, vuejs
quality:      [clean-code, tdd]
```

`beadloom setup-agentic-flow` composes each role (dev, test, review, tech-writer) from the CORE protocol, the architecture overlay, and the stack overlays, and writes the adapter set for each tool — `.claude/agents/*` for Claude Code, `.cursor/agents/*` for Cursor — at parity. `config-check` compares every generated adapter byte-for-byte against its composition, so the workflow never drifts from the graph unnoticed.

The workflow is local-first and goes through the same Gate. A pull-request-triggered AI tech-writer orchestrator (shipped inside the package, `python -m beadloom.ai_agents.ai_techwriter`) fixes stale documentation right in the pull-request branch — at the symbol level. A symbol is a named code entity: a function, class, method, or constant (extracted by tree-sitter when it parses the sources). A document is rewritten only when a symbol it references actually changed, not on every edit to a file. The orchestrator has bounded parallelism and verdict classification, so a dead runner or an exhausted quota doesn't freeze the merge. CI stays the real enforcement, and the agent's edit is a proposal that a human reviews and merges.

Because the same workflow runs on Claude Code and Cursor, and the architecture and stack are set by configuration rather than hand-written text, the workflow rolls out without being rewritten for each project.

## Beadloom governs itself

Beadloom applies its own thesis to its own code — there is no shadow code. The `module-coverage` lint is raised to `severity: error`: every source module is either a tracked graph node (a `feature` with a `SPEC.md` or a `component` with a `DOC.md`) or an entry in a small, visible exemption list, so a new untracked module **fails `beadloom ci`**. Internal building blocks get a full `component` node kind (the infrastructure counterpart of `feature`), and even the AI tech-writer orchestrator lives in the graph-tracked `ai_agents` domain. The architecture-as-code thesis here is enforced, not declared.

## Who it's for

- **Tech leads and architects** — make the architecture explicit, versioned, and able to outlive team turnover, with boundaries enforced in CI.
- **Platform and DevEx engineers** — give CI working freshness and boundary checks, and give agents structural context out of the box over MCP.
- **Developers** — stop spending the first hour of every task working out or recalling how things fit: `beadloom ctx <feature>` or the VitePress portal answer in minutes.
- **People working with AI** — so agents work inside the architecture instead of breaking it.

## Installation

```bash
uv tool install beadloom        # recommended
pipx install beadloom           # alternative
```

## Quick start

```bash
# 1. Scan the code and generate an initial architecture graph
#    (in progress: accuracy is being refined on real projects)
beadloom init --bootstrap

# 2. Review the generated graph (fix domains, rename nodes, add edges)
vi .beadloom/_graph/services.yml

# 3. Build the index and start using it
beadloom reindex
beadloom ctx search        # get context for a feature
beadloom sync-check        # are the docs up to date?
beadloom lint              # are the architecture rules satisfied?

# 4. Set up context for AI agents
beadloom setup-rules       # create IDE adapter files
beadloom prime             # see exactly what the agent will see
```

You don't need any starter documentation — Beadloom raises a basic skeleton from the code structure alone. From there you can refine and fill it by hand or with any AI agent (see `beadloom docs polish`), and Beadloom keeps it fresh.

## Architecture as Code

Beadloom doesn't just describe the architecture — it defends it. You write boundary rules in YAML, check them with `beadloom lint`, and block violations in CI. For example, this project's rules:

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

  # Keep the TUI out of the database layer directly
  - name: tui-no-direct-infra
    forbid_import:
      from: "src/beadloom/tui/**"
      to: "src/beadloom/infrastructure/**"

  # Warn when a node grows too large
  - name: domain-size-limit
    severity: warn
    check:
      for: { kind: domain }
      max_symbols: 200      # too much code in one node
```

Seven rule types are available: `require`, `deny`, `forbid`, `layers`, `forbid_cycles`, `forbid_import`, and `check`.

```bash
beadloom lint                 # human-readable terminal output
beadloom lint --strict        # exit code 1 on violations (for CI)
beadloom lint --format json   # machine-readable output
```

When an agent requests context for a node, the rules that apply to it come back in the response, so it respects boundaries by default rather than by accident. Import analysis works for **Python, TypeScript/JavaScript, Go, Rust, Kotlin, Java, Swift, C/C++, and Objective-C**.

## Key features

- **Cross-service contract graph** — `export` in each repository, `federate` combines two or more services into one landscape with a per-contract verdict (`CONFIRMED` / `BREAKING` / `ORPHANED_CONSUMER` / `UNDECLARED_PRODUCER` / `EXTERNAL`) over AMQP and GraphQL, plus a per-service freshness tag. Product and company scale.
- **A single Gate** — `beadloom ci` runs reindex → lint → sync-check → config-check → doctor → the optional landscape gate under one exit code. Ships as a ready-made GitHub Action and a pre-push hook.
- **Context Oracle** — deterministic graph traversal, a compact JSON bundle in under 20 ms.
- **Doc Sync Engine** — tracks the code-to-doc link, catches stale docs, hooks into git.
- **Agent context** — `beadloom prime` (under 2K tokens), `setup-rules` for IDE adapters, an MCP server with 18 tools, and `config-check` that keeps the agent files in agreement with the graph.
- **Agentic dev workflow** — `setup-agentic-flow` composes a configurable, tool-agnostic multi-agent workflow (Claude Code and Cursor; DDD/FSD and stack overlays) from `.beadloom/flow.yml`, enforced through the pre-push Gate and a pull-request-triggered AI tech-writer.
- **No shadow code** — the `module-coverage` lint (`error`) requires every source module to be a graph node or an explicit exemption, and the `component` node kind tracks internal building blocks alongside `feature` nodes.
- **Full-text search** — FTS5 over nodes, documentation, and code symbols.
- **Impact analysis** — `beadloom why` shows what a node depends on and what breaks if it changes.
- **Code-first start** — raise the graph from the code structure alone, with no documentation.
- **Snapshots and debt** — `snapshot` compares architecture over time, and `status --debt-report` rolls lint, sync, and complexity into a single 0–100 score with a CI gate.
- **C4 diagrams** — auto-generated Context / Container / Component in Mermaid and PlantUML.
- **Published site** — `beadloom docs site` builds a knowledge base on VitePress (dashboard, interactive architecture, landscape map, up-to-date documentation).
- **Local and dependency-free** — a single CLI and a single SQLite file. No Docker, no cloud.

## How it works

Beadloom keeps the architecture graph in YAML under `.beadloom/_graph/` — **nodes** (features, services, domains, entities) connected by **edges** (`part_of`, `uses`, `depends_on`, and so on). A reindex merges three sources into a single SQLite database:

1. **Graph YAML** — the nodes and edges that describe the architecture.
2. **Documentation** — Markdown bound to graph nodes and chunked for search.
3. **Code** — sources parsed via tree-sitter for symbols and `# beadloom:domain=...` annotations.

Request a node's context, and Context Oracle traverses the graph breadth-first, gathers the relevant subgraph, documentation, and code symbols, and returns a compact data bundle.

## CLI commands

| Command | Description |
|---------|-------------|
| `init --bootstrap` | Scan the code and generate an initial architecture graph |
| `init --import DIR` | Import and classify existing documentation |
| `reindex` | Rebuild the SQLite index from the graph, docs, and code |
| `ctx REF_ID` | Get a context bundle (Markdown or `--json`) |
| `graph [REF_ID]` | Show the architecture graph (Mermaid or JSON) |
| `search QUERY` | Full-text search over nodes, documentation, and code symbols |
| `status` | Index stats, documentation coverage, and a debt report |
| `doctor` | Validate the architecture graph |
| `sync-check` | Check doc-code freshness |
| `sync-update REF_ID` | Review and update stale documentation |
| `why REF_ID` | Impact analysis — what it depends on and what depends on it |
| `lint` | Check the code against the architecture rules (`--strict`, `--format rich/json/porcelain/github`) |
| `ci` | The single Gate: reindex → lint → sync-check → config-check → doctor → the optional landscape gate |
| `config-check` | Check (or `--fix`) that the generated agent files match the graph |
| `export` | Export the graph as a deterministic artifact for federation |
| `federate` | Aggregate two or more artifacts into one landscape. `--fail-on` turns on the CI gate |
| `docs generate` | Generate documentation skeletons from the graph |
| `docs polish` | Emit structured data for AI documentation enrichment |
| `docs site` | Build the VitePress site (dashboard, architecture, landscape map, validated docs) |
| `docs audit` | Find stale facts in overview documentation (README, guides) |
| `diff` | Show graph changes since a git ref |
| `snapshot` | Save and compare architecture snapshots |
| `link REF_ID [URL]` | Manage links to external trackers on nodes |
| `prime` | Emit compact project context for AI agents |
| `active-sync` | Reconcile each epic's bead-status table in `ACTIVE.md` with the tracker (`bd`) |
| `setup-rules` | Create IDE adapter files (`.cursorrules`, `.windsurfrules`, `.clinerules`) |
| `setup-mcp` | Configure the MCP server for AI agents |
| `setup-agentic-flow` | Compose and write the multi-agent workflow role adapters from `.beadloom/flow.yml` (`--tool`/`--architecture`/`--stack`) |
| `mcp-serve` | Start the MCP server (stdio transport) |
| `tui` / `ui` | Interactive terminal dashboard (needs `beadloom[tui]`) |
| `watch` | Auto-reindex on file changes (needs `beadloom[watch]`) |
| `install-hooks` | Install the pre-commit hook and the pre-push Beadloom Gate (full `beadloom ci`) |

## MCP tools

`beadloom mcp-serve` gives AI agents 18 tools: 14 graph read/write tools — `prime`, `get_context`, `get_graph`, `list_nodes`, `sync_check`, `get_status`, `update_node`, `mark_synced`, `search`, `generate_docs`, `why`, `diff`, `lint`, `get_debt_report` — plus four process tools that drive the agentic workflow: `task_init`, `bead_context`, `checkpoint`, `complete_bead`. Works with Claude Code, Cursor, Windsurf, Cline, and any MCP-compatible tool. To connect:

```json
{
  "mcpServers": {
    "beadloom": { "command": "beadloom", "args": ["mcp-serve"] }
  }
}
```

## Configuration

Everything lives under `.beadloom/` at the repository root:

- **`config.yml`** — scan paths, languages, sync settings.
- **`flow.yml`** — the agentic-workflow declaration: `tools` (claude/cursor), `architecture` (ddd/fsd), `stack` and `quality` overlays (read by `setup-agentic-flow`).
- **`_graph/*.yml`** — the architecture graph (version-controlled).
- **`_graph/rules.yml`** — the boundary rules.
- **`AGENTS.md`** — conventions and the MCP tool catalog for agents.
- **`beadloom.db`** — the SQLite index (auto-generated; add it to `.gitignore`).

You can link code to a graph node with a one-line annotation:

```python
# beadloom:domain=doc-sync
def check_freshness(db: sqlite3.Connection, ref_id: str) -> SyncStatus:
    ...
```

## Documentation

| Document | Description |
|----------|-------------|
| [architecture.md](docs/architecture.md) | System design and component overview |
| [getting-started.md](docs/getting-started.md) | Quick-start guide |
| [Multi-agent development](docs/guides/multi-agent-development.md) | How Beadloom's agentic workflow is built |
| [CI Setup](docs/guides/ci-setup.md) | GitHub Actions / GitLab CI integration |
| [VitePress Site](docs/guides/vitepress-site.md) | Publishing the knowledge base on VitePress |
| **Domains** | [Context Oracle](docs/domains/context-oracle/README.md) · [Graph](docs/domains/graph/README.md) · [Doc Sync](docs/domains/doc-sync/README.md) · [Onboarding](docs/domains/onboarding/README.md) · [Infrastructure](docs/domains/infrastructure/README.md) |
| **Services** | [CLI Reference](docs/services/cli.md) · [MCP Server](docs/services/mcp.md) · [TUI Dashboard](docs/services/tui.md) |

## Beads integration

*Beadloom is the architecture context for [beads](https://github.com/steveyegge/beads).*

Beadloom complements [Beads](https://github.com/steveyegge/beads): worker agents call `get_context(feature_id)` over MCP and get a ready bundle instead of searching the code from scratch. The integration is optional — Beadloom works perfectly well on its own.

## Development

```bash
uv sync --dev              # install with dev dependencies
uv run pytest              # run the tests
uv run ruff check src/     # linter
uv run mypy                # type checking (strict mode)
```

## License

MIT
