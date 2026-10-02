# Beadloom

<!-- beadloom:watches=cli,graph,flow.yml -->

> Read this in other languages: [Русский](README.ru.md)

**An engineering control loop for autonomous agents: the bounds of a task, architectural context, and checks that say honestly what they did not check.**

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

**Platforms:** Linux is verified on every CI run. The project is developed on macOS, but CI does not run it there &nbsp;|&nbsp; **Python:** 3.10 to 3.13

---

## Why prompts and `CLAUDE.md` are no longer enough

A chatbot that answers questions, and an agent handed something small: generate a function, put a table together, work through a log. None of that surprises anyone any more. That is the baseline.

Past it a new era begins: autonomous multi-agent systems. Several agents work on one repository at the same time — they work the task out, break it into parts, plan the order, agree between themselves and keep the statuses. Each of them uses tools, writes and checks code, edits documentation. And they stay on it for hours, with nobody watching.

Autonomy raises more than speed. It also raises the chance that the agent understands the task differently from how it was meant. Asked to fix a failing test, it deleted the test, and the build went green. Asked to bring coverage up to eighty percent, it wrote tests that call the code and assert nothing. Formally, the task is done. This has a name: goal misalignment.

There is a worse case. The agent looks as though it is going along with the rules, while leaving part of what it did unsaid and routing around part of the checks. This is called scheming, hidden strategic behaviour. Such scenarios are already being studied in labs. In everyday work it goes past us. First it goes past, then we throw up our hands and say the model has got worse.

With several agents something arrives that a single one never produces. Two of them edit one file in one tree. The first calls the work finished, not having seen that it was redone alongside. The check goes green while that happens, because there is nothing left for it to check.

So you can no longer rely on the agent recalling and correctly applying what is written in a prompt, in `AGENTS.md` or in `CLAUDE.md`. In a short session it still works. In a long one the context grows, the rules sink into it, and they weaken exactly when they start to matter.

What is needed is an engineering control loop: explicit bounds on a task and on what it is allowed to touch, architectural context, isolated parallel work, executable checks, evidence of what was done, and an honest record of what could not be checked.

Beadloom is an attempt to build that loop into the repository itself.

## A check that passed and a check with nothing to check are different facts

Most tools answer two ways: pass or fail. That leaves out a third case, and the third case is the one that hurts — the check ran over nothing and said `pass`.

This happens more often than you would think. A rule whose path pattern has a typo matches no file. A document is declared in the graph and was deleted from disk. A freshness check on a fresh clone has no baseline to compare against. A guard is configured correctly, wired to nothing, and has never once fired.

There is one honest answer here: "I did not check this." The usual answer is green.

Beadloom says what it did not do. Excerpts from real runs, with long lines wrapped:

```
[PASS] docs-audit: 20 mention(s) fresh; 4/9 declared fact(s) verified, NOT VERIFIED:
       cli_command_count, edge_count, language_count, nodes_with_framework, test_count
[SKIP] scope-check: skipped — the branch 'master' names no work item among the planning
       documents, so there are no declared axes to judge against
[SKIP] readme-pair: skipped — no document pair is declared; add a `document_pairs:` block
       of `source:`/`follower:` entries to .beadloom/config.yml
Rule 'domain-needs-parent' cannot fire: its `for` kind 'domain' matches none of the 1 nodes
in the graph. It is counted as evaluated but checks nothing
```

A guard has six outcomes rather than two:

- `pass` — it checked, and it has nothing against the edit;
- `warn` — worth a look, but the work is not stopped;
- `block` — a rule is broken, the edit does not go through;
- `skip` — there was nothing to check, and that is not dressed up as success;
- `error` — the guard refuses to interpret what it was handed. Also does not go through;
- `unresolved` — the guard could not evaluate *itself*: its own code would not import, its config would not parse.

`unresolved` is worth a sentence of its own. A broken guard that forbids everything also forbids the edit that would repair it, and an agent cannot get out of that on its own. So here Beadloom warns instead of blocking.

What each check declines to assert is set out [further down](#when-a-check-cannot-answer-beadloom-says-so).

## What Beadloom does not do

It knows nothing about the model itself. Whether an agent is honest, what it keeps quiet about, whether it would behave differently unobserved — Beadloom does not answer these questions. Those are properties of the model, and they are worked on elsewhere.

It does not replace sandboxing, secret handling, access control or human review. An agent with network access and production credentials is an infrastructure question before it is a workflow question.

What it does is narrower and can be checked: it bounds where one change may reach, shows what a change touches, keeps several agents out of each other's files, and refuses to report a check as passed when it had nothing to check.

## What is covered, and what is not

Beadloom is made of several layers, each of which the industry calls something "as code". Here is what is covered, by what exactly, and where the boundary runs.

| Layer | | Covered by |
|---|---|---|
| Architecture as code | yes | the graph in versioned YAML, `lint` over it, `impact`, the graph's file layout |
| Policy as code | yes | guards as data, rules about a task's scope, six verdicts and their exit codes |
| Documentation as code | yes | document-to-code pairs, freshness against `HEAD`, a tech-writer on the pull request |
| Context as code | yes | `ctx`, `prime`, `why`, the declared typed surface |
| Coordination as code | yes | `waves`, `rooms`, `clean-room`, issue numbers handed out by exclusive file create |
| Assurance as code | yes | `guard --liveness`, `scope-check`, `mutation`, an explicit "not checked" in every report |
| Agentic workflow as code | yes | `flow.yml`, roles, adapters, and `config-check` over them |
| Security & privacy as code | partly | the firing record keeps the command name and the files, never the command line |
| Runtime agent governance | partly | the loop covers tools and edits in the repository, not a full authorization plane for actions |
| Model alignment | no | Beadloom does not judge a model's goals or its honesty |
| Frontier-AI safety | not a goal | it does not replace model evaluations, sandboxes or capability thresholds |

The bottom three rows are not a roadmap. They are the boundary of the project, and it is drawn on purpose.

## A rule becomes a command

Beadloom keeps rules in an **architecture graph**. The graph is a description of your system that lives in the repository as ordinary YAML: what parts it has, how they connect, what may reach what. One property of it matters here: you can run a command over the graph.

The rule lives in the graph. There is a command over the graph. The command returns an exit code. An exit code is not forgotten — not by an agent, not by a person, not in CI.

Every check converges into a single Gate. Here is its output on this repository at the 7.0.0 release, on 29 September 2026. Long lines are wrapped, and omitted text is marked with "…":

```
Beadloom CI gate

  [PASS] reindex: up to date
  [PASS] lint: 0 error(s), 73 warning(s), 10 crossings suppressed by an exemption,
         architecture-layers judged 371 of 379 live depends_on edge(s)
  [PASS] sync-check: 519 pair(s) fresh
  [PASS] docs-audit: 20 mention(s) fresh; 4/9 declared fact(s) verified, NOT VERIFIED:
         cli_command_count, edge_count, language_count, nodes_with_framework, test_count
  [WARN] docs-quality: 292 document(s) read; … NO CHECK READS: PLAN, SUMMARY; …
  [PASS] issue-log: 277 entr(ies) uniquely numbered; … PARTLY CHECKED: 235 of 277 …
  [PASS] readme-pair: 1 pair(s) held, 118 block(s) compared, 0 finding(s); …
  [WARN] doc-spaces: to_be 229, as_is 124, working 65; …
  [PASS] scope-check: 0 path(s) outside the axes BDL-075 declares (…); 3 judged, …
  [PASS] config-check: no blocking drift; 1 artifact(s) reported (warn)
  [PASS] doctor: 13 check(s): 0 error(s), 240 warning(s), 4 info
  …
PASS — gate clean
Room: Darwin arm64 · CPython 3.13.7 · 10 cores · extras … · locale utf-8
  23 of 23 declared room(s) not entered by this run: …
Not run by this gate:
  the test suite — `uv run pytest --cov=beadloom …` (.github/workflows/ci.yml: tests)
  the style linter — `uv run ruff check src/ tests/` (.github/workflows/ci.yml: tests)
  the type checker — `uv run mypy src/` (.github/workflows/ci.yml: tests)
…
```

What to look at here is not `PASS` but what stands next to it. Every step names **how much** it checked and **what it did not look at**. A check that had nothing to check does not read as a successful one — [a separate section](#when-a-check-cannot-answer-beadloom-says-so) is about that, and it is the main thing that separates Beadloom from a pile of linters.

The last lines say the same about the Gate itself. It names the machine the run happened on, the CI environments the run did not enter, and the checks it did not run at all: the tests, the linter and the type checker. A green verdict is about that machine and the checks the Gate ran, not about the project as a whole.

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

- **[One Gate, and checks per step](#a-rule-becomes-a-command).** Every check under a single exit code. And `beadloom guard` checks one step of the process on its own and returns one of the six verdicts [described above](#a-check-that-passed-and-a-check-with-nothing-to-check-are-different-facts).
- **[The agentic development flow](#the-agentic-development-flow)** — configurable and tool-agnostic. Five roles: explore, dev, test, review and tech-writer. The adapters for Claude Code and Cursor are equals.
- **Context on request, for people and agents alike.** `ctx` returns the code, documentation and rules in force for a node. `why` computes the blast radius. `prime` packs an overview of the project into under two thousand tokens. `search` runs full-text over nodes and documentation.
- **[Architecture as code](#architecture-as-code).** Boundaries and rules in YAML, checked by `beadloom lint` and blocked by the Gate.
- **[Tests on the graph](#tests-are-bound-to-the-graph).** Every node shows which tests belong to it. Rules watch over the suite itself, and mutation testing shows whether the tests would notice a fault.
- **Spec-Driven: the spec first, the code after.** Three documentation spaces: **TO-BE** — what you intend to build, **AS-IS** — what is built, **WORKING** — working notes taken as a task proceeds. The last are exempt from the freshness check on purpose: a progress note describes the work, not the code. `beadloom docs spaces` shows all three and finds tasks whose work is finished while the promised document never appeared.
- **[Federation across repositories](#federation-contracts-between-services).** One landscape assembled from the graphs of individual services, with every contract checked against both of its sides.
- **Documentation portal.** `beadloom docs site` builds a VitePress site: [interactive graphs](https://zoologov.github.io/beadloom/architecture.html), a metrics dashboard, and documentation tagged with its freshness. The theme ships in the package, so your project's portal is built by `beadloom docs site`, just like ours. Building it needs `Node.js 22` or later. The steps are in [Getting Started](docs/getting-started.md#publish-the-portal).
- **Terminal dashboard.** `beadloom tui` — three screens in the console: dashboard, graph explorer, documentation status. It works when Beadloom is installed with the `tui` extra.

## The first five minutes

```bash
uv tool install beadloom        # recommended
pipx install beadloom           # alternative
uv tool install "beadloom[languages,tui]"   # eight more languages and the terminal dashboard
```

```bash
beadloom init --bootstrap          # raise the graph from code you already have
vi .beadloom/_graph/services.yml   # review it: fix domains, rename nodes, add edges
beadloom reindex                   # build the index
beadloom ci                        # run every check at once
```

`beadloom init` checks the graph it has just written against the rules it wrote beside it. When the scaffold breaks one of them, `init` names the rule and the node and exits 1, instead of exiting 0 and leaving you to find it at the first `beadloom ci`. The scaffold stays on disk either way.

Three things are worth looking at next: `beadloom ctx <node>` — what the tool knows about a piece of the system, `beadloom prime` — exactly what an agent will see, `beadloom docs site` — how it looks on the portal.

You need no documentation to start: the skeleton is raised from the structure of the code alone. Filling it in can be done by hand or by any AI agent (see `beadloom docs polish`), and keeping it current is Beadloom's job from then on.

## Beadloom has a steep setup cost

The graph has to be raised, reviewed and then maintained. The rules have to be written. The Gate has to go into CI. On a project of ten files, or on a one-off task, that work will not pay for itself: you remember everything anyway, and an agent will manage with what it reads on its own.

The return starts in two situations. The first is two agents or more working on the repository at once: almost everything here answers a question that does not come up with one. The second is the system no longer fitting in one person's head. When it has been written for years, when several team line-ups have passed through it, when there is more than one service and they live in different repositories. That is when knowledge leaves with people, documentation drifts from the code unnoticed, and a contract breaks in someone else's repository and surfaces in production. The longer the system lives and the more moving parts it has, the sooner the setup pays off.

Who this is usually for:

- **People who run agents in batches.** So that several agents working at once stay predictable. `beadloom waves` works out which tasks can run in parallel and which have to be serialised, and names the reason for every pair it had to serialise. Each agent gets its own context and its own boundaries, and the result of any of them goes through the same Gate. See the [guide to parallel waves](docs/guides/parallel-waves.md).
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
| A document is declared in the graph but is not on disk | `missing`. `sync-check` exits with code 2, and the Gate fails and exits with code 1. Deleting the document is not a way to close the question |
| Nothing to compare against: the repository was just cloned | `unverified`. Such a pair is counted separately and never joins the fresh ones. The Gate shows `WARN` and leaves the exit code alone: the code is fine, it is the check that cannot answer |
| A rule matches no file and no node | a `rule_liveness` warning. The summary line says how many of the rules that ran were unable to check anything |
| A temporary exemption from the rules has expired | a warning, and every run prints how many violations that exemption is hiding. The exemption itself keeps working: a build should not go red because the date changed |
| A number in the README that the audit never verified | `docs audit` reports how many declared facts it confirmed out of how many, names the rest, and lists the documents it never opened |
| A task's work is finished and the document it promised never appeared | `docs spaces` shows it. To every other check such a node looks clean: there is nothing to go stale when there is no document at all |
| Documentation marked in the config as temporary and exempt from the freshness check | the number of exempt pairs and the reason are printed next to the number of fresh ones, so an exemption cannot be mistaken for a check |
| A translation of a document has drifted from its original: one has a paragraph the other lacks | `readme-pair` compares the pairs in the `document_pairs:` block by structure: headings, paragraphs, lists, tables and code blocks. It does not compare the text itself. When no pair is declared, the step says it was skipped, not that it passed |

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

`beadloom setup-agentic-flow` composes from this the protocols of five roles, the slash commands and `CLAUDE.md`, and `config-check` watches that what was composed does not drift from the graph. Your project's rules live in a separate layer in `.beadloom/flow/` and survive an upgrade: the upgrade moves the core underneath them. A core rule can be overridden only by a declaration carrying a reason and an expiry, and once it expires `config-check` reports it. Details are in the [guide to project overlays](docs/guides/project-overlays.md).

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

Each entry declares exactly one of 15 authoring keys: `require`, `deny`, `forbid`, `layers`, `forbid_cycles`, `forbid_import`, `check`, `unregistered_feature_candidate`, `module_coverage`, `scenario_coverage`, `doc_area_coherence`, `summary_facts`, `test_binding`, `test_import_boundary` and `scenario_binding`. The full reference is in [docs/architecture.md](docs/architecture.md).

A rule that **cannot match anything** reports itself: a matcher that selects no node, a typo in a path pattern, an exemption that suppresses nothing. Their count appears in `lint`'s summary line, so the declared number of rules cannot promise more than was checked.

Beadloom applies its own thesis to itself: the `module-coverage` lint is raised to `error`, so every source module has to be a graph node or an explicit exemption, and a new untracked module fails `beadloom ci`.

Import analysis works for **Python** right after installation. **TypeScript/JavaScript, Go, Rust, Kotlin, Java, Swift, C/C++ and Objective-C** need the `languages` extra: `uv tool install "beadloom[languages]"`. `beadloom init` reads a Swift project through `Package.swift` (Swift Package Manager). It does not read an Xcode project, and only reports how many Swift files were left without a node.

## Tests are bound to the graph

The agent at the start of this README brought coverage up to eighty percent with tests that assert nothing. Coverage does not see that: it only shows that a line ran. Beadloom looks at tests from three sides.

What counts as a test is written once, in the `test` role: one behaviour per test, arrange, one action, and a check of its result. These requirements are the same for any stack.

A test file belongs to a graph node in one of three ways: its path mirrors the path of the code it tests, it sits beside that code, or the node lists its tests under the `tests:` key. Beadloom guesses nothing else. A file that none of the three binds is counted apart, and every report about tests states how many such files there are: any one of them may test a node that at first sight has no tests. `beadloom ctx <node>` shows a node's tests. Three rules watch over the suite itself:

- `test_binding` — whether every test file belongs to a node, and whether every node of a chosen kind has a test;
- `test_import_boundary` — whether a test imports something the rule forbids it;
- `scenario_binding` — whether an acceptance scenario sits in its node's folder.

On every run, each rule says how much of the suite it checked.

Whether a test would notice a fault is what mutation testing shows: small faults are put into the code, and it is checked whether any test fails. The project chooses the program that does this, and `beadloom mutation` scores what that program wrote. With `--changed-since main` the command states what has to be checked for this change: the changed functions in the declared scope, their nodes, and the tests bound to them. With `--sample-of` it reads the result as a random sample and prints a confidence interval. The floor counts as missed only when the whole interval lies below it. In this repository every pull request is checked this way, and once a week a random sample is drawn from the whole declared scope.

Details are in the [testing guide](docs/guides/testing.md).

---

## Commands

| Command | What it does |
|---------|--------------|
| `init --bootstrap` | Raise the graph from the structure of the code |
| `reindex` | Rebuild the index from the graph, documentation and code |
| `ctx REF_ID` | A context pack for a node (Markdown or `--json`) |
| `why REF_ID` | What depends on a node and what breaks when it changes |
| `search QUERY` | Full-text search over nodes and documentation |
| `lint` | Check the architecture rules (`--strict` for CI) |
| `sync-check` | Documentation freshness against the code |
| `ci` | The single Gate: every check under one exit code |
| `impact TARGET` | Who else writes the same place, who calls this code, and how many branches it has. `TARGET` is a path or a symbol name |
| `scope-check` | Whether a commit stayed inside the axes its work item declared |
| `waves --parent BEAD` | Which tasks can run at once, derived from the tracker rather than typed out |
| `clean-room BEAD` | A room built from `HEAD` plus the files you name, so one agent's verdict is about its own work |
| `guard --liveness` | Which guards exist, and what each one is actually wired to |
| `export` / `federate` | Export the graph and assemble a landscape from several services |
| `docs site` | Build the VitePress portal |

The full reference is **[docs/services/cli.md](docs/services/cli.md)**: every command with every flag, including `axes`, `typed-surface`, `bd-calls`, `issue-number`, `rooms`, `mutation`, `review-brief`, `version-surface`, `docs spaces`, `snapshot`, `status --debt-report`, and hook setup through `install-hooks`.

## MCP, configuration, Beads

`beadloom mcp-serve` gives agents **18 tools**: fourteen read and write the graph, four drive the agentic flow. It works with Claude Code, Cursor, Windsurf, Cline and any MCP-compatible tool. The whole catalog is in [docs/services/mcp.md](docs/services/mcp.md).

```json
{ "mcpServers": { "beadloom": { "command": "beadloom", "args": ["mcp-serve"] } } }
```

Everything Beadloom knows about you lives in `.beadloom/` at the root of the repository: `config.yml` (where the code and the tests are, languages, document pairs and check settings), `flow.yml` (the agentic flow declaration), `flow/` (your layer of the flow), `_graph/*.yml` (the graph and the rules, under version control), `AGENTS.md` (conventions for agents). The `beadloom.db` index is generated and does not belong in git.

Code can be bound to a graph node with a one-line annotation:

```python
# beadloom:domain=doc-sync
def check_freshness(db: sqlite3.Connection, ref_id: str) -> SyncStatus:
    ...
```

Beadloom complements [Beads](https://github.com/steveyegge/beads): worker agents call `get_context(ref_id)` over MCP and get a ready pack instead of searching the code from scratch. The integration is optional.

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
| [Testing](docs/guides/testing.md) | Where a test lives, how it binds to a graph node, what `lint` reports about the suite and how to read the mutation score |
| [CI Setup](docs/guides/ci-setup.md) | Integration with GitHub Actions / GitLab CI |
| [VitePress Site](docs/guides/vitepress-site.md) | Publishing the knowledge base on VitePress |
| **Domains** | [Context Oracle](docs/domains/context-oracle/README.md) · [Graph](docs/domains/graph/README.md) · [Doc Sync](docs/domains/doc-sync/README.md) · [Onboarding](docs/domains/onboarding/README.md) · [Infrastructure](docs/domains/infrastructure/README.md) |
| **Services** | [CLI Reference](docs/services/cli.md) · [MCP Server](docs/services/mcp.md) · [TUI Dashboard](docs/services/tui.md) |

## Development

```bash
uv sync --extra all             # dependencies and development tools, as in CI
uv run pytest                   # tests
uv run ruff check src/ tests/   # linter
uv run mypy src/                # type checking (strict)
```

## License

MIT
