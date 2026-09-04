# Getting Started

<!-- beadloom:watches=cli,flow.yml -->

This guide takes you from zero to a working Beadloom setup — including the
configurable, multi-agent dev flow.

## What Beadloom does

Beadloom keeps the architecture you *intended* and the code you *actually
shipped* from drifting apart. It stores a queryable map of your system —
domains, services, features, components, and the contracts between them — as
plain YAML in Git, then continuously checks the real code against it:

- **Docs that can't go stale.** Beadloom tracks which docs describe which code and flags the ones that fall behind — on every commit, in CI, or on demand.
- **Boundaries that are enforced.** You write architecture rules in YAML; `beadloom lint` blocks violations in CI, no matter who (or which AI tool) wrote the code.
- **Contracts checked across services.** Federate per-repo graphs into one landscape and Beadloom reconciles what each service *says it provides* against what its consumers *actually use* — catching a broken contract before it ships.
- **Context for AI agents.** `beadloom prime` hands an agent a compact (<2K-token) picture of the architecture, and `setup-agentic-flow` composes a full multi-agent workflow (explore, then dev → test → review → tech-writer) for Claude Code and Cursor.
- **A self-governing model.** No shadow code: every source module must be a tracked graph node or explicitly exempt, enforced as a CI error.

## Requirements

- Python 3.10+
- uv (recommended) or pip
- Optional: a git repo (for the hooks and the agentic flow), `bd` (the [beads](https://github.com/steveyegge/beads) tracker, for the agentic flow)

## Install

```bash
uv tool install beadloom        # recommended
pipx install beadloom           # alternative
pip install beadloom            # also works
```

Optional extras (language parsers, TUI, file watcher):

```bash
uv tool install "beadloom[languages]"   # TS/JS, Go, Rust, Kotlin, Java, Swift, C/C++, Objective-C
uv tool install "beadloom[tui]"         # interactive terminal dashboard
uv tool install "beadloom[watch]"       # file watcher for auto-reindex
uv tool install "beadloom[graphql]"     # typed GraphQL contract checking (graphql-core)
uv tool install "beadloom[all]"         # everything
```

The current release is **3.0.2**. `beadloom --version` reports the build you actually
installed. This line is the one place a document states the version as a claim, and
`beadloom docs audit` compares it against `pyproject.toml` on every run — so a release that
bumps the manifest and forgets the prose is reported instead of merely being wrong. Every
other version literal in the documentation is a dependency pin or a historical reference to
the release a feature arrived in.

## Initialize

```bash
cd your-project
beadloom init --bootstrap     # scan code → generate an initial graph
```

`--bootstrap` scans your code structure and proposes domains, services, and
features. Use `--yes` (`-y`) to skip prompts (CI / automation).
`init` creates:

- `.beadloom/_graph/services.yml` — the architecture graph (nodes + edges)
- `.beadloom/_graph/rules.yml` — auto-generated architecture lint rules
- `.beadloom/config.yml` — project configuration
- `docs/` — documentation skeletons for each graph node
- `.mcp.json` (or equivalent) — MCP config for the detected editor

It also runs a full reindex: code symbols are extracted, imports resolved, and
`depends_on` edges inferred from code.

**`init` checks its own output, and can exit 1.** After the graph is written and indexed,
every entry point that wrote a file under `.beadloom/_graph/` — `--yes` in any mode,
`--bootstrap`, `--import` and the interactive wizard — runs the same lint step `beadloom
ci` runs. When the scaffold does not pass the rules the same run wrote beside it, `init`
withdraws the completion it has already printed, names each failing rule with its node and
the graph file that node was written into, and exits 1. The scaffold is left on disk: the
exit code reports the state, it does not withdraw the graph. Until BDL-067 there was no
such check, so a virgin `beadloom init --yes --mode bootstrap` exited 0 and the next
command an adopter runs — `beadloom ci` — was red on a rule that same run had written
(BDL-UX #192). A scripted `beadloom init --yes && beadloom ci` now stops at `init`
instead. The [CLI reference](services/cli.md) has the two report shapes, the two paths
that take no verdict, and the one graph file shape that still ends `init` in a traceback.

> No documentation is required to start — Beadloom bootstraps a skeleton from
> code structure alone. You fill it in by hand or with any AI agent (see
> `beadloom docs polish`), and Beadloom keeps it current.

## Configuration

Everything lives under `.beadloom/` in your repo.

### `.beadloom/config.yml`

| Key | Default | Description |
|-----|---------|-------------|
| `scan_paths` | `["src", "lib", "app"]` | Source directories to scan |
| `languages` | all supported | File extensions to parse (e.g. `[".py", ".ts"]`) |
| `docs_dir` | `docs/` | Documentation root directory |
| `sync.hook_mode` | `warn` | Pre-commit hook mode: `warn` or `block` |

### `.beadloom/flow.yml` — the agentic dev flow

Declare *what your project is*, once. `setup-agentic-flow` reads this to compose
the role workflow:

```yaml
tools:        [claude, cursor]   # generate adapters for one or both
architecture: [ddd]              # ddd | fsd (exactly one)
stack:        [python]           # python, fastapi, javascript, typescript, vuejs
quality:      [clean-code, tdd]
language:     en                 # the language the flow's documents are written in
```

Then:

```bash
# Compose the roles, the slash commands and CLAUDE.md from
# CORE + architecture overlay + stack overlays + your project layer:
beadloom setup-agentic-flow

# Override the flow.yml selection from flags:
beadloom setup-agentic-flow --tool cursor --architecture fsd --stack typescript,vuejs
```

This writes `.claude/agents/*` (Claude Code) and/or `.cursor/agents/*` (Cursor)
at parity, plus `.claude/commands/*` and `.claude/CLAUDE.md`. `config-check`
compares each of them against its composition, so the workflow never silently
drifts.

Your project's own rules go in `.beadloom/flow/{roles,commands,claude}/` rather
than into the composed files: that fourth layer composes last, is never
overwritten, and survives every upgrade. See the
[Project Overlays guide](guides/project-overlays.md) for adding a fragment,
declaring a suppression, and migrating an edit you already made by hand.

### Git hooks — pre-commit + the pre-push Gate

```bash
beadloom install-hooks
```

Installs **both** hooks by default:

- **pre-commit** (lighter) — judges **the commit, not the tree**: lint over the staged source files, a type check over the staged files inside the surface the project declares typed (derived per run from `[tool.mypy]`; a surface that could not be derived reads `NOT CHECKED` with its reason and never blocks), `sync-check --staged` over the pairs the commit stages either side of, and the ACTIVE/tracker coherence step (`warn` or `block` via `--mode`). It prints how many modified or untracked files outside the commit it did not judge, so a narrow green is not read as a whole-tree green. Re-run `beadloom install-hooks` after upgrading — an already-installed hook keeps its old whole-tree behaviour until you do.
- **pre-push Beadloom Gate** (authoritative) — runs the full `beadloom ci` (reindex → `lint --strict` → sync-check → docs-audit → docs-quality → doc-spaces → config-check → doctor) over the whole tree and **blocks the push on red**. It is fail-safe (a no-op when `beadloom` isn't on `PATH`); `git push --no-verify` is the documented escape hatch.

Select one with `--pre-commit` / `--pre-push`; remove with `--remove`.

### MCP + IDE rules

```bash
beadloom setup-mcp                 # .mcp.json (Claude Code) / .cursor/mcp.json (Cursor) / Windsurf config
beadloom setup-mcp --tool cursor   # target a specific editor
beadloom setup-rules               # thin IDE adapter files pointing at .beadloom/AGENTS.md
```

The MCP server (`beadloom mcp-serve`) exposes 18 tools — 14 graph read/write
tools plus four process tools (`task_init`, `bead_context`, `checkpoint`,
`complete_bead`) that drive the agentic flow.

## Usage examples

### A. The core loop

```bash
beadloom prime              # compact (<2K-token) project context for an agent
beadloom ctx sync-check     # full context bundle for a node (add --json to parse)
beadloom why sync-check     # impact analysis: upstream deps + downstream dependents
beadloom graph              # Mermaid architecture diagram
beadloom search "stale"     # FTS5 search across nodes, docs, and code symbols
beadloom status             # node/edge/doc counts, coverage, health trends
```

Validate before you commit:

```bash
$ beadloom sync-check
✓ 149/149 doc-code pairs in sync

$ beadloom lint --strict    # exit 1 on error-severity violations (for CI)
✓ All architecture rules satisfied

$ beadloom ci               # the unified gate, one exit code
reindex        PASS
lint           PASS
sync-check     PASS
docs-audit     PASS
docs-quality   WARN
doc-spaces     WARN
config-check   PASS
doctor         PASS
✓ CI gate passed
```

> `sync-check` exits 2 when docs are stale. `beadloom sync-update <ref> --yes`
> walks you through (or auto-applies) the fix until the stale count reaches 0.
>
> `docs-quality` and `doc-spaces` are **warn-only**: they report and never change the
> exit code, so adding Beadloom to a project with existing documents cannot turn a
> green build red. `WARN` there means the step ran and part of what it reports on was
> not verifiable — it is not a softer PASS. See the
> [Document Kinds guide](guides/document-kinds.md).

### B. The agentic dev flow walkthrough

With `flow.yml` configured and `setup-agentic-flow` run, a feature flows through
gated waves. The process roles live in your editor adapters (`.claude/commands/*`
for Claude Code); the five work roles are subagents:

1. **`/task-init`** — scaffold the work item (PRD/RFC/CONTEXT/PLAN/ACTIVE or BRIEF) and create the beads (tracked in `bd`).
   - **explore** — step 0.5, mandatory and before the type is chosen: derive the `## Axes` section with `beadloom impact <path|symbol> --section` and paste it into the BRIEF or the RFC. The axis count is what says whether a work item is a bug, so the type is decided from a derivation rather than from how the request was phrased. This role creates no bead, so the bead DAG stays four-role.
2. **`/coordinator`** — orchestrate the waves, gated by bead dependencies. `beadloom waves <bead>...` decides which of the ready beads may run at the same time from the code they occupy, and states the media a concurrent wave shares regardless:
   - **dev** — implement the bead (TDD), update its `SPEC.md`/`DOC.md`.
   - **test** — write/extend tests, verify coverage.
   - **review** — read-only quality + boundary check (`beadloom review-brief`, `beadloom diff`, `lint`); the brief withholds the author's own comments until a verdict is recorded.
   - **tech-writer** — refresh the docs the change touched (`sync-update`).
3. **Push** — the **pre-push Beadloom Gate** runs `beadloom ci`; a red gate blocks the push ("no code reaches `main` without current docs and clean boundaries").
4. **PR** — opening the PR triggers CI *and* the AI tech-writer (below); a human merges once green.

Each agent starts from `beadloom prime` / `beadloom ctx <ref>` instead of
grepping the codebase from scratch, so it works inside your architecture.

### C. The AI tech-writer

On a pull request, a packaged harness repairs drifted docs **on the PR branch**:

```bash
# Run it manually against the drift since a git ref (the push's parent commit);
# --platform selects the CI adapter, --dry-run reports the wiring without a model/PR:
python -m beadloom.ai_agents.ai_techwriter --platform github --since "$(git rev-parse origin/main)" --dry-run
```

It is **symbol-scoped** (a doc is rewritten only when a symbol it references
actually changed), bounded-parallel, and verdict-classified — `ok` / `flagged` /
`infra` — so a genuine unresolved doc drift blocks the PR, but a dead runner or
exhausted quota never freezes merges. CI is the true enforcement; the refresh is
a proposal a human merges.

### D. Federation — hub + satellites

Inside one repo the dangerous bugs hide *between* services. Each service
("satellite") exports its graph; a hub composes them and reconciles contracts:

```bash
# In each service repo — emit a deterministic, commit-stamped artifact:
beadloom export --out service-a.json

# At the hub — compose >=2 artifacts into one landscape and reconcile contracts:
beadloom federate service-a.json service-b.json service-c.json

# Arm the CI landscape gate (writes the artifact, THEN exits 1 on a bad verdict):
beadloom federate service-*.json --fail-on default
#   default fail-set = breaking,drift,orphaned_consumer,undeclared_producer
```

`federate` writes `.beadloom/federated.json` + `.beadloom/federated.txt` and
assigns each contract a verdict (`CONFIRMED` / `BREAKING` / `ORPHANED_CONSUMER`
/ `UNDECLARED_PRODUCER` / `EXTERNAL` / `DRIFT`) over AMQP and GraphQL, plus
per-satellite staleness. `beadloom ci --hub <export> --fail-on default` folds the
landscape gate into the unified CI verdict.

## Publish a knowledge base

```bash
beadloom docs site --out site            # generate a VitePress content tree
(cd site && npm install && npm run docs:build)   # build the static site
```

The site is a metrics dashboard, an interactive architecture view, a
cross-service landscape map, and your hand-written docs with a freshness badge
on each. `docs site` reads the graph read-only and never writes into your
source `docs/` tree.

## Keep docs in sync

```bash
beadloom sync-check          # doc↔code freshness (exit 2 = stale)
beadloom sync-update <ref>   # review/apply the fix for a node (--yes to auto-apply)
beadloom docs audit          # detect stale numeric/version facts in prose docs (--stale-only, --json); also the docs-audit gate step
                             # a claim is a whitespace-delimited token whose whole core is a number ("6,390" counts, "BDL-061.33" and "v2.2.0" do not)
beadloom docs quality        # check planning documents against the writing standard (--check NAME, --json, --strict)
                             # exit 0 with findings unless --strict; also the docs-quality gate step
```

`sync-check` also reports an `incomplete` row for a document that is current and no longer
carries the sections its kind's peers carry. It never blocks. See
[Document kinds](guides/document-kinds.md).

## Limits

- Code indexer parses Python, TypeScript/JavaScript, Go, Rust out of the box; Kotlin, Java, Swift, C/C++, Objective-C via `beadloom[languages]`. Import analysis spans 9 languages.
- Documentation is indexed from `docs/` (configurable via `config.yml`).
- The graph is YAML under `.beadloom/_graph/`; rules in `.beadloom/_graph/rules.yml`.
- Maximum documentation chunk size: 2000 characters.

## Next steps

- [Architecture](architecture.md) — system design, the node-kind model, the rules engine, the agentic-flow configurator.
- [Executable acceptance scenarios](guides/bdd-scenarios.md) — Gherkin as the source of truth, and what `scenario-coverage` reports.
- [Document kinds](guides/document-kinds.md) — required sections and the five writing-standard checks.
- [Parallel waves](guides/parallel-waves.md) — what a wave of concurrent agents guarantees, and what it only reports.
- [CI Setup](guides/ci-setup.md) — GitHub Actions / GitLab CI integration.
- [VitePress Site](guides/vitepress-site.md) — publish the knowledge base.
