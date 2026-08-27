# Beadloom

<!-- beadloom:watches=cli,graph,flow.yml -->

> Read this in other languages: [Русский](README.ru.md)

**Rules for architecture, documentation and contracts, as checks with an exit code. The same for a human and for an agent.**

[![License: MIT](https://img.shields.io/github/license/zoologov/beadloom)](LICENSE)
[![GitHub release](https://img.shields.io/github/v/release/zoologov/beadloom?include_prereleases&sort=semver)](https://github.com/zoologov/beadloom/releases)
[![PyPI](https://img.shields.io/pypi/v/beadloom)](https://pypi.org/project/beadloom/)
[![Python](https://img.shields.io/pypi/pyversions/beadloom)](https://pypi.org/project/beadloom/)
[![CI](https://img.shields.io/github/actions/workflow/status/zoologov/beadloom/ci.yml?branch=main&label=CI)](https://github.com/zoologov/beadloom/actions/workflows/ci.yml)
[![mypy: strict](https://img.shields.io/badge/mypy-strict-blue)](https://mypy-lang.org/)
[![code style: ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![coverage: 80%+](https://img.shields.io/badge/coverage-80%25%2B-green)](pyproject.toml)
[![Docs portal](https://img.shields.io/badge/docs-portal-8A2BE2)](https://zoologov.github.io/beadloom/)

🔎 **See what it produces:** [the interactive architecture graph of Beadloom](https://zoologov.github.io/beadloom/architecture.html) — click a node to open its card and blast radius. The page is built from this repository's own graph by `beadloom docs site`, not drawn by hand.

**Platforms:** macOS and Linux, verified on every CI run &nbsp;|&nbsp; **Python:** 3.10+

---

## The agent forgets what you wrote

An agent writes code faster than you can read it. At the start of a session it remembers the instruction in `CLAUDE.md`. In a long session it forgets.

The reason is known and it is called context rot: the longer the conversation and the larger the file of rules, the harder those instructions compete for the model's attention. Rules weaken exactly when the session has grown long and you need them most. Adding one more paragraph to the file makes it worse.

So you cannot rely on the instruction being read and remembered. You need something that does not depend on memory.

## A rule becomes a command

Beadloom keeps rules in an **architecture graph**. The graph is a description of your system that lives in the repository as ordinary YAML: what parts it has, how they connect, what may reach what. One property of it matters here: you can run a command over the graph.

The rule lives in the graph. There is a command over the graph. The command returns an exit code. An exit code is not forgotten — not by an agent, not by a person, not in CI.

Every check converges into a single Gate. Here is its output on this repository:

```
reindex      PASS: up to date
lint         PASS: 0 error(s), 59 warning(s), 6 crossings suppressed by an exemption
sync-check   PASS: 363 pair(s) fresh
docs-audit   PASS: 20 mention(s) fresh; 5/9 declared fact(s) verified,
                   NOT VERIFIED: edge_count, language_count, nodes_with_framework, test_count
docs-quality WARN: 248 document(s) read; NO CHECK READS: BRIEF, PLAN, SUMMARY
doc-spaces   WARN: to_be 194, as_is 100, working 56
config-check PASS: no blocking drift
doctor       PASS: 13 check(s): 0 error(s), 204 warning(s), 1 info
```

What to look at here is not `PASS` but what stands next to it. Every step names **how much** it checked and **what it did not look at**. A check that had nothing to check does not read as a successful one — [a separate section](#when-a-check-cannot-answer-beadloom-says-so) is about that, and it is the main thing that separates Beadloom from a pile of linters.

One Gate stands in three places: in the pre-push hook, in CI, and in an agent's hands. It does not matter which agent provider you use, because Beadloom is universal and is part of none of them. Claude Code, Cursor, an editor that speaks MCP, a CI job, a person at a keyboard — all of them meet the same `beadloom ci`.

Some rules cannot be turned into a command. They stay as text the agent reads, and Beadloom tries not to let that text grow. Your project's rules live in a separate layer in `.beadloom/flow/`, the shipped core lives apart from it, and an upgrade changes only the core.

## How the Gate knows what is correct

Any indexing of code — embeddings in an IDE, a search over the repository, an agent reading the sources — answers questions about **what is in the code**. Beadloom answers questions about **what you decided about the code**. You cannot read that out of the sources: the decision lives in your head, in a discussion, in a ticket, and the code knows nothing about it.

| Question | Where the answer comes from |
|---|---|
| Where is this class implemented? | visible in the code |
| What does this module import? | visible in the code |
| Is it **allowed** to import that? | only if you wrote it down |
| Does this document still describe the current code? | you wrote down which document describes which code, and Beadloom checks it |
| Who else uses the contract we are about to delete? | written down in a neighbouring repository |
| Is this dependency built already, or only planned? | only if you wrote it down |

Any good indexer will answer the first two. None will answer the rest, and that is not about its quality: the answer is simply not in the sources.

You write it down once, in that same graph. Inside, it is simple: **nodes** (services, domains, features, components) and **edges** between them (`part_of`, `uses`, `depends_on`). The graph can be raised from code you already have with `beadloom init --bootstrap`, then reviewed and maintained by hand.

On reindex, Beadloom merges three sources into one SQLite database: the graph itself, the documentation bound to its nodes, and the code parsed through tree-sitter for symbols. After that the graph can be questioned: `beadloom ctx <node>` returns everything about a node at once, `beadloom why <node>` shows what breaks if you touch it.

## What is built on the graph

The graph on its own is just data. What makes it useful is what stands on top of it.

- **[One Gate, and checks per step](#a-rule-becomes-a-command).** Every check under a single exit code. And `beadloom guard` checks one step of the process on its own, with four outcomes: passed, warning, blocked, could not check.
- **[The agentic development flow](#the-agentic-development-flow)** — configurable and tool-agnostic. Roles dev → test → review → tech-writer, with adapters for Claude Code and Cursor as equals.
- **Context on request, for people and agents alike.** `ctx` returns the code, documentation and rules in force for a node. `why` computes the blast radius. `prime` packs an overview of the project into under 2K tokens. `search` runs full-text over nodes, documentation and code symbols.
- **[Architecture as code](#architecture-as-code).** Boundaries and rules in YAML, checked by `beadloom lint` and blocked by the Gate.
- **Spec-Driven: the spec first, the code after.** Three documentation spaces: **TO-BE** — what you intend to build, **AS-IS** — what is built, **WORKING** — working notes taken as a task proceeds. The last are exempt from the freshness check on purpose: a progress note describes the work, not the code. `beadloom docs spaces` shows all three and finds tasks whose work is finished while the promised document never appeared.
- **[Federation across repositories](#federation-contracts-between-services).** One landscape assembled from the graphs of individual services, with every contract checked against both of its sides.
- **Documentation portal.** `beadloom docs site` builds a VitePress site: [interactive graphs](https://zoologov.github.io/beadloom/architecture.html), a metrics dashboard, and documentation tagged with its freshness.
- **Terminal dashboard.** `beadloom tui` — three screens in the console: dashboard, graph explorer, documentation status.

## The first five minutes

```bash
uv tool install beadloom        # recommended
pipx install beadloom           # alternative
```

```bash
beadloom init --bootstrap          # raise the graph from code you already have
vi .beadloom/_graph/services.yml   # review it: fix domains, rename nodes, add edges
beadloom reindex                   # build the index
beadloom ci                        # run every check at once
```

Three things are worth looking at next: `beadloom ctx <node>` — what the tool knows about a piece of the system, `beadloom prime` — exactly what an agent will see, `beadloom docs site` — how it looks on the portal.

You need no documentation to start: the skeleton is raised from the structure of the code alone. Filling it in can be done by hand or by any AI agent (see `beadloom docs polish`), and keeping it current is Beadloom's job from then on.

## Beadloom has a steep setup cost

The graph has to be raised, reviewed and then maintained. The rules have to be written. The Gate has to go into CI. On a project of ten files, or on a one-off task, that work will not pay for itself: you remember everything anyway, and an agent will manage with what it reads on its own.

The return starts where the system stops fitting in one person's head. When it has been written for years, when several team line-ups have passed through it, when there is more than one service and they live in different repositories. That is when knowledge leaves with people, documentation drifts from the code unnoticed, and a contract breaks in someone else's repository and surfaces in production. The longer the system lives and the more moving parts it has, the sooner the setup pays off.

Who this is usually for:

- **People who run agents in batches.** So that several agents working at once stay predictable. `beadloom waves` works out which tasks can run in parallel and which have to be serialised, and names the reason for every serialised pair. Each agent gets its own context and its own boundaries, and the result of any of them goes through the same Gate. See the [guide to parallel waves](docs/guides/parallel-waves.md).
- **Tech leads and architects.** So that the architecture is explicit, versioned, and outlives team turnover.
- **Platform and DevEx engineers.** So that CI carries working checks on documentation freshness and boundaries, and agents get structural context through MCP.
- **Developers.** So that the first hour of every task is not spent rebuilding the picture.

---

## Federation: contracts between services

The most dangerous bugs hide **between** services. Neither the compiler nor the tests of a single repository reach there, and specialised checks are each built for one protocol.

An event goes to a queue whose only listener was renamed in a neighbouring repository. The broker has no schema and no registry to notice it. A service is built against a dependency that was declared in a plan and never built. An endpoint is still maintained although its last consumer was deleted long ago.

Beadloom brings contracts of every kind — AMQP messages, GraphQL, declared cross-service dependencies — into one landscape graph and checks both sides of each:

```bash
beadloom export --out service-a.json          # in every service repository
beadloom federate service-*.json              # on the hub
```

| Verdict | What it means |
|---------|---------------|
| `CONFIRMED` | Producer and consumer are both present and compatible. |
| `BREAKING` | The consumer uses a name that is no longer in the producer's schema. Caught **before** release, on presence, without comparing versions. |
| `ORPHANED_CONSUMER` | Something consumes a contract nobody produces. |
| `UNDECLARED_PRODUCER` | Something produces a contract nobody consumes. |
| `EXTERNAL` | Marked as "it exists, but it is not ours" (a native bridge, for example), with no false alarms. |
| `DRIFT` | A cross-repository dependency declared active whose target cannot be found. |

The verdict takes lifecycle into account: `planned` is not required to exist yet and raises no false alarm, while `deprecated` that is still in use is plain debt. The hub assembles either a single product or a company landscape of several — products with no shared contracts do not create noise about each other. Every artifact carries a commit SHA and a timestamp, so you can see how stale each service's export is. When the data is missing, the hub writes "unknown" and does not invent a SHA.

> **What is ready:** AMQP and GraphQL with breaking-change checking, federation that is indifferent to language and product, and a gate in CI through `federate --fail-on`. Verified end to end: a divergence with the status `BREAKING` was caught before release.
> **Not yet:** REST/OpenAPI and gRPC. The hub works on assembled artifacts, with no hosted service.

## When a check cannot answer, Beadloom says so

A documentation check answers "all fresh". That sounds good, but two very different facts can stand behind that answer. Either the documentation really does match the code. Or there was nothing to check, and nobody told you.

The second happens more often than it seems. A document is named in the graph and somebody deleted it from disk. A rule has a typo in its path pattern, so it matches no file at all. In CI the repository was just cloned and there is nothing to compare against yet. Beadloom used to answer all of this the same way: "all fresh".

From here on, a "pair" means a document and the code it describes: Beadloom knows which file which document explains, and watches that the two do not drift apart.

| What happened | What Beadloom says |
|---|---|
| A document is declared in the graph but is not on disk | `missing`, and the Gate fails with exit code 2. Deleting the document is not a way to close the question |
| Nothing to compare against: the repository was just cloned | `unverified`. Such a pair is counted separately and never joins the fresh ones. The Gate shows `WARN` and leaves the exit code alone: the code is fine, it is the check that cannot answer |
| A rule matches no file and no node | a `rule_liveness` warning. The summary line says how many of the rules that ran were unable to check anything |
| A temporary exemption from the rules has expired | a warning, and every run prints how many violations that exemption is hiding. The exemption itself keeps working: a build should not go red because the date changed |
| A number in the README that the audit never verified | `docs audit` reports how many declared facts it confirmed out of how many, names the rest, and lists the documents it never opened |
| A task's work is finished and the document it promised never appeared | `docs spaces` shows it. To every other check such a node looks clean: there is nothing to go stale when there is no document at all |
| Documentation marked in the config as temporary and exempt from the freshness check | the number of exempt pairs and the reason are printed next to the number of fresh ones, so an exemption cannot be mistaken for a check |

Separately, about how Beadloom knows a document is stale. It looks at **git**, not at its own index.

This matters because there used to be an easy way to get a green report: delete the local `.beadloom/beadloom.db`. It is in `.gitignore`, lives on one machine, and is absent in CI. Beadloom would rebuild it from scratch, take the current state of the code as its point of reference, and declare all documentation fresh. Now every pair remembers which commit it was checked against, and is compared with `HEAD`. Deleting the database no longer buys anything.

## The agentic development flow

The same graph that answers `prime` and `ctx` also feeds the packaged multi-agent flow. What your project is, you describe once:

```yaml
# .beadloom/flow.yml
tools:        [claude, cursor]   # adapters for one or both
architecture: [ddd]              # ddd | fsd (exactly one)
stack:        [python]           # python, fastapi, javascript, typescript, vuejs
quality:      [clean-code, tdd]
language:     en                 # the language the flow documents are written in
```

`beadloom setup-agentic-flow` composes from this the protocols of four roles, the slash commands and `CLAUDE.md`, and `config-check` watches that what was composed does not drift from the graph. Your project's rules live in a separate layer in `.beadloom/flow/` and survive an upgrade: the upgrade moves the core underneath them. A core rule can be overridden only by a declaration carrying a reason and an expiry, and once it expires `config-check` reports it. Details are in the [guide to project overlays](docs/guides/project-overlays.md).

The flow is local first and goes through the same Gate. On a pull request an AI tech-writer runs: it repairs stale documentation right in the branch, at the level of symbols — a document is rewritten only when the symbol it refers to has changed. The real control stays with CI, and the agent's edit is a proposal that a person reviews and merges.

## Architecture as code

You write boundaries in YAML, and `beadloom lint` checks them:

```yaml
rules:
  - name: no-domain-depends-on-service    # domains may not depend on services
    deny:
      from: { kind: domain }
      to:   { kind: service }
      unless_edge: [part_of]

  - name: tui-no-direct-infra             # the TUI does not reach the database directly
    forbid_import:
      from: "src/beadloom/tui/**"
      to:   "beadloom/infrastructure/**"
```

Each entry declares exactly one of 12 authoring keys: `require`, `deny`, `forbid`, `layers`, `forbid_cycles`, `forbid_import`, `check`, `unregistered_feature_candidate`, `module_coverage`, `scenario_coverage`, `doc_area_coherence` and `summary_facts`. The full reference is in [docs/architecture.md](docs/architecture.md).

A rule that **cannot match anything** reports itself: a matcher that selects no node, a typo in a path pattern, an exemption that suppresses nothing. Their count appears in `lint`'s summary line, so the declared number of rules cannot promise more than was checked.

Beadloom applies its own thesis to itself: the `module-coverage` lint is raised to `error`, so every source module has to be a graph node or an explicit exemption, and a new untracked module fails `beadloom ci`.

Import analysis works for **Python, TypeScript/JavaScript, Go, Rust, Kotlin, Java, Swift, C/C++ and Objective-C**.

---

## Commands

| Command | What it does |
|---------|--------------|
| `init --bootstrap` | Raise the graph from the structure of the code |
| `reindex` | Rebuild the index from the graph, documentation and code |
| `ctx REF_ID` | A context pack for a node (Markdown or `--json`) |
| `why REF_ID` | What depends on a node and what breaks when it changes |
| `search QUERY` | Full-text search over nodes, documentation and symbols |
| `lint` | Check the architecture rules (`--strict` for CI) |
| `sync-check` | Documentation freshness against the code |
| `ci` | The single Gate: every check under one exit code |
| `export` / `federate` | Export the graph and assemble a landscape from several services |
| `docs site` | Build the VitePress portal |

The full reference is **[docs/services/cli.md](docs/services/cli.md)**: every command with every flag, including `guard`, `waves`, `review-brief`, `docs spaces`, `snapshot`, `status --debt-report`, and hook setup through `install-hooks`.

## MCP, configuration, Beads

`beadloom mcp-serve` gives agents **18 tools**: fourteen read and write the graph, four drive the agentic flow. It works with Claude Code, Cursor, Windsurf, Cline and any MCP-compatible tool. The whole catalog is in [docs/services/mcp.md](docs/services/mcp.md).

```json
{ "mcpServers": { "beadloom": { "command": "beadloom", "args": ["mcp-serve"] } } }
```

Everything Beadloom knows about you lives in `.beadloom/` at the root of the repository: `config.yml` (scan paths and languages), `flow.yml` (the agentic flow declaration), `flow/` (your layer of the flow), `_graph/*.yml` (the graph and the rules, under version control), `AGENTS.md` (conventions for agents). The `beadloom.db` index is generated and does not belong in git.

Code can be bound to a graph node with a one-line annotation:

```python
# beadloom:domain=doc-sync
def check_freshness(db: sqlite3.Connection, ref_id: str) -> SyncStatus:
    ...
```

Beadloom complements [Beads](https://github.com/steveyegge/beads): worker agents call `get_context(feature_id)` over MCP and get a ready pack instead of searching the code from scratch. The integration is optional.

**Windows is unverified.** Nothing in this project has ever been run on it. The `windows-latest` CI leg was built and then withdrawn, because it became the critical path of the pipeline. Details are in the *Windows: unverified by decision* section of the [flow guards SPEC](docs/domains/application/features/flow-guards/SPEC.md).

## Documentation

| Document | Description |
|----------|-------------|
| [architecture.md](docs/architecture.md) | System design and component overview |
| [getting-started.md](docs/getting-started.md) | Quick start guide |
| [Multi-agent development](docs/guides/multi-agent-development.md) | How Beadloom's agentic flow is built |
| [Executable acceptance scenarios](docs/guides/bdd-scenarios.md) | Gherkin as the source of truth and what `scenario-coverage` reports |
| [Parallel waves](docs/guides/parallel-waves.md) | What a wave of parallel agents guarantees and what nothing here checks |
| [Document kinds](docs/guides/document-kinds.md) | Mandatory sections and the five writing-standard checks |
| [CI Setup](docs/guides/ci-setup.md) | Integration with GitHub Actions / GitLab CI |
| [VitePress Site](docs/guides/vitepress-site.md) | Publishing the knowledge base on VitePress |
| **Domains** | [Context Oracle](docs/domains/context-oracle/README.md) · [Graph](docs/domains/graph/README.md) · [Doc Sync](docs/domains/doc-sync/README.md) · [Onboarding](docs/domains/onboarding/README.md) · [Infrastructure](docs/domains/infrastructure/README.md) |
| **Services** | [CLI Reference](docs/services/cli.md) · [MCP Server](docs/services/mcp.md) · [TUI Dashboard](docs/services/tui.md) |

## Development

```bash
uv sync --dev              # install with dev dependencies
uv run pytest              # tests
uv run ruff check src/     # linter
uv run mypy                # type checking (strict)
```

## License

MIT
